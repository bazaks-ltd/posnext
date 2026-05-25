import { call } from "@/utils/apiWrapper"
import { logger } from "@/utils/logger"
import {
	enrichInvoiceForPrint,
	getPosPrintSettings,
} from "@/utils/posPrintSettings"
import { buildThermalReceiptHtml } from "@/utils/thermalReceiptTemplate"
import { __ } from "@/utils/translation"
import { offlineWorker } from "@/utils/offline/workerClient"

const log = logger.create("PrintInvoice")

function hasThermalLineItems(invoiceData) {
	return (
		invoiceData &&
		Array.isArray(invoiceData.items) &&
		invoiceData.items.filter(Boolean).length > 0
	)
}

/**
 * Normalize queued offline payload for the thermal receipt HTML fallback.
 */
export function buildOfflineThermalInvoice(invoiceData, queueId) {
	const d = invoiceData || {}
	const settings = getPosPrintSettings()
	const name =
		queueId != null ? `OFFLINE-${queueId}` : `OFFLINE-${Date.now()}`
	return normalizeInvoiceForThermalPrint(
		enrichInvoiceForPrint({
			name,
			doctype: "Sales Invoice",
			company: d.company || settings.company || "POS Next",
			currency: d.currency || settings.currency,
			posting_date: new Date().toISOString().slice(0, 10),
			customer_name: d.customer_name || d.customer,
			items: d.items,
			payments: d.payments,
			grand_total: d.grand_total,
			total_taxes_and_charges: d.total_tax ?? d.total_taxes_and_charges,
			discount_amount: d.discount_amount,
			additional_discount_percentage: d.additional_discount_percentage,
			paid_amount: d.paid_amount,
			outstanding_amount: d.outstanding_amount,
			change_amount: d.change_amount,
			status: __("Pending sync"),
		}),
	)
}

export function offlineQueueRowToInvoice(row, displayName) {
	const d = row?.data || {}
	const settings = getPosPrintSettings()
	const invoiceName =
		displayName ||
		(row?.id != null ? `OFFLINE-${row.id}` : `OFFLINE-${row.timestamp}`)
	return normalizeInvoiceForThermalPrint(
		enrichInvoiceForPrint({
			name: invoiceName,
			doctype: "Sales Invoice",
			company: d.company || settings.company || "POS Next",
			currency: d.currency || settings.currency,
			posting_date: new Date(row.timestamp).toISOString().slice(0, 10),
			customer_name: d.customer_name || d.customer,
			items: d.items,
			payments: d.payments,
			grand_total: d.grand_total,
			total_taxes_and_charges: d.total_tax ?? d.total_taxes_and_charges,
			discount_amount: d.discount_amount,
			additional_discount_percentage: d.additional_discount_percentage,
			paid_amount: d.paid_amount,
			outstanding_amount: d.outstanding_amount,
			change_amount: d.change_amount,
			status: __("Pending sync"),
		}),
	)
}

export function normalizeInvoiceForThermalPrint(raw) {
	const items = Array.isArray(raw?.items)
		? raw.items.filter(Boolean)
		: []
	const payments = Array.isArray(raw?.payments)
		? raw.payments.filter(Boolean)
		: []
	return {
		...raw,
		items,
		payments,
	}
}

function resolvePrintOptions(printFormat = null, letterhead = null) {
	const settings = getPosPrintSettings()
	return {
		printFormat: printFormat || settings.printFormat || "POS Next Receipt",
		letterhead: letterhead || settings.letterhead || null,
		letterHeadHtml: settings.letterHeadHtml || "",
		letterHeadFooter: settings.letterHeadFooter || "",
		currency: settings.currency || null,
	}
}

/**
 * Print invoice using Frappe's print format system
 * @param {Object} invoiceData - The invoice document data
 * @param {string} printFormat - The print format name (optional)
 * @param {string} letterhead - The letterhead name (optional)
 * @note Use "POS Next Receipt" format for thermal printer (80mm) or configure via POS Profile
 */
export async function printInvoice(
	invoiceData,
	printFormat = null,
	letterhead = null,
) {
	if (!invoiceData?.name) {
		throw new Error(__("Invalid invoice data"))
	}

	const doctype = invoiceData.doctype || "Sales Invoice"
	const options = resolvePrintOptions(printFormat, letterhead)

	const params = new URLSearchParams({
		doctype: doctype,
		name: invoiceData.name,
		format: options.printFormat,
		no_letterhead: 0,
		_lang: "en",
		trigger_print: 1,
		_t: Date.now(),
	})

	if (options.letterhead) {
		params.append("letterhead", options.letterhead)
	}

	const printUrl = `/printview?${params.toString()}`
	const printWindow = window.open(printUrl, "_blank", "width=800,height=600")

	if (!printWindow) {
		if (hasThermalLineItems(invoiceData)) {
			return printInvoiceCustom(invoiceData, options)
		}
		throw new Error(
			__(
				"Could not open print window. Allow popups or use thermal receipt fallback with line items.",
			),
		)
	}

	return true
}

/**
 * Generates and prints a thermal receipt using the same layout as POS Next Receipt.
 */
function printInvoiceCustom(invoiceData, options = null) {
	const resolved = options || resolvePrintOptions()
	const safe = normalizeInvoiceForThermalPrint(
		enrichInvoiceForPrint(invoiceData),
	)
	const printWindow = window.open("", "_blank", "width=350,height=600")

	if (!printWindow?.document) {
		throw new Error(
			__(
				"Could not open print window. Check popup blocker settings.",
			),
		)
	}

	const printContent = buildThermalReceiptHtml(safe, {
		currency: safe.currency || resolved.currency,
		letterHeadHtml: resolved.letterHeadHtml,
		letterHeadFooter: resolved.letterHeadFooter,
	})

	printWindow.document.write(printContent)
	printWindow.document.close()

	printWindow.onload = () => {
		setTimeout(() => {
			printWindow.print()
		}, 250)
	}

	return true
}

/** Thermal HTML receipt when PDF/printview is unavailable (e.g. offline or popup blocked). */
export function printThermalReceipt(invoiceData, options = null) {
	return printInvoiceCustom(invoiceData, options)
}

/**
 * Print invoice by name, fetching print format from POS Profile
 * @param {string} invoiceName - The name of the invoice to print
 * @param {string} printFormat - Optional print format override
 * @param {string} letterhead - Optional letterhead override
 */
export async function printInvoiceByName(
	invoiceName,
	printFormat = null,
	letterhead = null,
) {
	const trimmed = String(invoiceName || "").trim()
	if (!trimmed) {
		throw new Error(__("Invoice name is required"))
	}

	const offlineMatch = /^OFFLINE-(\d+)$/i.exec(trimmed)
	if (offlineMatch) {
		const row = await offlineWorker.getOfflineInvoiceById(offlineMatch[1])
		if (row?.data) {
			return printInvoiceCustom(
				offlineQueueRowToInvoice(row, trimmed),
				resolvePrintOptions(printFormat, letterhead),
			)
		}
		throw new Error(
			__("Offline receipt not found. It may have already synced."),
		)
	}

	if (typeof navigator !== "undefined" && navigator.onLine === false) {
		throw new Error(
			__(
				"You are offline. You can only print receipts saved in the offline queue (OFFLINE-…).",
			),
		)
	}

	const invoiceDoc = await call("pos_next.api.invoices.get_invoice", {
		invoice_name: trimmed,
	})

	if (!invoiceDoc) {
		throw new Error(__("Invoice not found"))
	}

	let resolvedFormat = printFormat
	let resolvedLetterhead = letterhead

	if (!resolvedFormat && invoiceDoc.pos_profile) {
		try {
			const posProfileDoc = await call("frappe.client.get", {
				doctype: "POS Profile",
				name: invoiceDoc.pos_profile,
			})

			if (posProfileDoc) {
				resolvedFormat =
					posProfileDoc.print_format ||
					posProfileDoc.custom_default_print_format
				resolvedLetterhead =
					resolvedLetterhead || posProfileDoc.letter_head
			}
		} catch (error) {
			log.warn("Could not fetch POS Profile print settings:", error)
		}
	}

	return await printInvoice(
		invoiceDoc,
		resolvedFormat,
		resolvedLetterhead,
	)
}
