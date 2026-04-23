import { call } from "@/utils/apiWrapper"
import { logger } from "@/utils/logger"
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
	const name =
		queueId != null ? `OFFLINE-${queueId}` : `OFFLINE-${Date.now()}`
	return normalizeInvoiceForThermalPrint({
		name,
		doctype: "Sales Invoice",
		company: d.company || "POS Next",
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
	})
}

export function offlineQueueRowToInvoice(row, displayName) {
	const d = row?.data || {}
	const invoiceName =
		displayName ||
		(row?.id != null ? `OFFLINE-${row.id}` : `OFFLINE-${row.timestamp}`)
	return normalizeInvoiceForThermalPrint({
		name: invoiceName,
		doctype: "Sales Invoice",
		company: d.company || "POS Next",
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
	})
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
	const format = printFormat || "POS Next Receipt"

	const params = new URLSearchParams({
		doctype: doctype,
		name: invoiceData.name,
		format: format,
		no_letterhead: letterhead ? 0 : 1,
		_lang: "en",
		trigger_print: 1,
		_t: Date.now(),
	})

	if (letterhead) {
		params.append("letterhead", letterhead)
	}

	const printUrl = `/printview?${params.toString()}`
	const printWindow = window.open(printUrl, "_blank", "width=800,height=600")

	if (!printWindow) {
		if (hasThermalLineItems(invoiceData)) {
			return printInvoiceCustom(invoiceData)
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
 * Generates and prints a custom POS receipt using a thermal printer layout.
 */
function printInvoiceCustom(invoiceData) {
	const safe = normalizeInvoiceForThermalPrint(invoiceData)
	const printWindow = window.open("", "_blank", "width=350,height=600")

	if (!printWindow?.document) {
		throw new Error(
			__(
				"Could not open print window. Check popup blocker settings.",
			),
		)
	}

	const printContent = `
		<!DOCTYPE html>
		<html>
		<head>
			<meta charset="UTF-8">
			<title>${__("Invoice - {0}", [safe.name])}</title>
			<style>
				* {
					margin: 0;
					padding: 0;
					box-sizing: border-box;
				}

				body {
					font-family: 'Courier New', monospace;
					padding: 10px;
					width: 80mm;
					margin: 0;
					max-width: 80mm;
				}

				.receipt {
					width: 100%;
				}

				.header {
					text-align: center;
					margin-bottom: 20px;
					border-bottom: 2px dashed #000;
					padding-bottom: 10px;
				}

				.company-name {
					font-size: 18px;
					font-weight: bold;
					margin-bottom: 5px;
				}

				.invoice-info {
					margin-bottom: 15px;
					font-size: 12px;
				}

				.invoice-info div {
					display: flex;
					justify-content: space-between;
					margin-bottom: 3px;
				}

				.partial-status {
					color: #dc3545;
					font-weight: bold;
					margin-bottom: 5px;
				}

				.items-table {
					width: 100%;
					margin-bottom: 15px;
					border-top: 1px dashed #000;
					border-bottom: 1px dashed #000;
					padding: 10px 0;
				}

				.item-row {
					margin-bottom: 10px;
					font-size: 12px;
				}

				.item-name {
					font-weight: bold;
					margin-bottom: 3px;
				}

				.item-details {
					display: flex;
					justify-content: space-between;
					font-size: 11px;
					color: #333;
				}

				.item-discount {
					display: flex;
					justify-content: space-between;
					font-size: 10px;
					color: #28a745;
					margin-top: 2px;
				}

				.item-serials {
					font-size: 9px;
					color: #666;
					margin-top: 3px;
					padding: 3px 5px;
					background-color: #f5f5f5;
					border-radius: 2px;
				}

				.item-serials-label {
					font-weight: bold;
					margin-bottom: 2px;
				}

				.item-serials-list {
					word-break: break-all;
				}

				.totals {
					margin-top: 15px;
					border-top: 1px dashed #000;
					padding-top: 10px;
				}

				.total-row {
					display: flex;
					justify-content: space-between;
					margin-bottom: 5px;
					font-size: 12px;
				}

				.grand-total {
					font-size: 16px;
					font-weight: bold;
					border-top: 2px solid #000;
					padding-top: 10px;
					margin-top: 10px;
				}

				.payments {
					margin-top: 15px;
					border-top: 1px dashed #000;
					padding-top: 10px;
				}

				.payment-row {
					display: flex;
					justify-content: space-between;
					margin-bottom: 3px;
					font-size: 11px;
				}

				.total-paid {
					font-weight: bold;
					border-top: 1px solid #ccc;
					padding-top: 5px;
					margin-top: 5px;
				}

				.outstanding-row {
					display: flex;
					justify-content: space-between;
					font-size: 13px;
					font-weight: bold;
					color: #dc3545;
					background-color: #fff3cd;
					padding: 8px;
					margin-top: 8px;
					border-radius: 4px;
				}

				.footer {
					text-align: center;
					margin-top: 20px;
					padding-top: 10px;
					border-top: 2px dashed #000;
					font-size: 11px;
				}

				@media print {
					@page {
						size: 80mm auto;
						margin: 0;
					}

					body {
						width: 80mm;
						padding: 5mm;
						margin: 0;
					}

					.no-print {
						display: none;
					}
				}
			</style>
		</head>
		<body>
			<div class="receipt">
				<div class="header">
					<div class="company-name">${safe.company || "POS Next"}</div>
					<div style="font-size: 12px;">${__("TAX INVOICE")}</div>
				</div>

				<div class="invoice-info">
					<div>
						<span>${__("Invoice #:")}</span>
						<span><strong>${safe.name}</strong></span>
					</div>
					<div>
						<span>${__("Date:")}</span>
						<span>${new Date(safe.posting_date || Date.now()).toLocaleString()}</span>
					</div>
					${
						safe.customer_name
							? `
					<div>
						<span>${__("Customer:")}</span>
						<span>${safe.customer_name}</span>
					</div>
					`
							: ""
					}
					${
						(safe.status === "Partly Paid" ||
							(safe.outstanding_amount &&
								safe.outstanding_amount > 0 &&
								safe.outstanding_amount < safe.grand_total))
							? `
					<div class="partial-status">
						<span>${__("Status:")}</span>
						<span>${__("PARTIAL PAYMENT")}</span>
					</div>
					`
							: ""
					}
				</div>

				<div class="items-table">
					${safe.items
						.map((item) => {
							if (!item) {
								return ""
							}
							const hasItemDiscount =
								(item.discount_percentage &&
									Number.parseFloat(item.discount_percentage) > 0) ||
								(item.discount_amount &&
									Number.parseFloat(item.discount_amount) > 0)
							const isFree = item.is_free_item
							const qty = item.quantity || item.qty || 0

							const displayRate = item.price_list_rate || item.rate || 0
							const subtotal = Number(qty) * Number(displayRate)

							return `
						<div class="item-row">
							<div class="item-name">
								${item.item_name || item.item_code} ${isFree ? __("(FREE)") : ""}
							</div>
							<div class="item-details">
								<span>${qty} × ${formatCurrency(displayRate)}</span>
								<span><strong>${formatCurrency(subtotal)}</strong></span>
							</div>
							${
								hasItemDiscount
									? `
							<div class="item-discount">
								<span>Discount ${item.discount_percentage ? `(${Number(item.discount_percentage).toFixed(2)}%)` : ""}</span>
								<span>-${formatCurrency(item.discount_amount || 0)}</span>
							</div>
							`
									: ""
							}
							${
								item.serial_no
									? `
							<div class="item-serials">
								<div class="item-serials-label">${__("Serial No:")}</div>
								<div class="item-serials-list">${String(item.serial_no).replace(/\n/g, ", ")}</div>
							</div>
							`
									: ""
							}
						</div>
						`
						})
						.join("")}
				</div>

				<div class="totals">
					${
						safe.total_taxes_and_charges &&
						safe.total_taxes_and_charges > 0
							? `
					<div class="total-row">
						<span>${__("Subtotal:")}</span>
						<span>${formatCurrency((safe.grand_total || 0) - (safe.total_taxes_and_charges || 0))}</span>
					</div>
					<div class="total-row">
						<span>${__("Tax:")}</span>
						<span>${formatCurrency(safe.total_taxes_and_charges)}</span>
					</div>
					`
							: ""
					}
					${
						safe.discount_amount
							? `
					<div class="total-row" style="color: #28a745;">
						<span>Additional Discount${safe.additional_discount_percentage ? ` (${Number(safe.additional_discount_percentage).toFixed(1)}%)` : ""}:</span>
						<span>-${formatCurrency(Math.abs(safe.discount_amount))}</span>
					</div>
					`
							: ""
					}
					<div class="total-row grand-total">
						<span>${__("TOTAL:")}</span>
						<span>${formatCurrency(safe.grand_total)}</span>
					</div>
				</div>

				${
					safe.payments.length > 0
						? `
				<div class="payments">
					<div style="font-weight: bold; margin-bottom: 5px; font-size: 12px;">Payments:</div>
					${safe.payments
						.map(
							(payment) => {
								if (!payment) {
									return ""
								}
								const mode = payment.mode_of_payment || __("Payment")
								const amt = payment.amount
								return `
						<div class="payment-row">
							<span>${mode}:</span>
							<span>${formatCurrency(amt)}</span>
						</div>
					`
							},
						)
						.join("")}
					<div class="payment-row total-paid">
						<span>${__("Total Paid:")}</span>
						<span>${formatCurrency(safe.paid_amount || 0)}</span>
					</div>
					${
						safe.change_amount && safe.change_amount > 0
							? `
					<div class="payment-row" style="font-weight: bold; margin-top: 5px;">
						<span>${__("Change:")}</span>
						<span>${formatCurrency(safe.change_amount)}</span>
					</div>
					`
							: ""
					}
					${
						safe.outstanding_amount && safe.outstanding_amount > 0
							? `
					<div class="outstanding-row">
						<span>${__("BALANCE DUE:")}</span>
						<span>${formatCurrency(safe.outstanding_amount)}</span>
					</div>
					`
							: ""
					}
				</div>
				`
						: ""
				}

				<div class="footer">
					<div style="margin-bottom: 5px;">${__("Thank you for your business!")}</div>
					<div style="font-size: 10px; color: #6b7280; margin-top: 8px;">
						Powered by <a href="https://bazaks.com" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 600;">Bazaks</a>
					</div>
				</div>
			</div>

			<div class="no-print" style="text-align: center; margin-top: 20px;">
				<button onclick="window.print()" style="padding: 10px 20px; font-size: 14px; cursor: pointer;">
					${__("Print Receipt")}
				</button>
				<button onclick="window.close()" style="padding: 10px 20px; font-size: 14px; cursor: pointer; margin-left: 10px;">
					${__("Close")}
				</button>
			</div>
		</body>
		</html>
	`

	printWindow.document.write(printContent)
	printWindow.document.close()

	printWindow.onload = () => {
		setTimeout(() => {
			printWindow.print()
		}, 250)
	}

	return true
}

/** Thermal HTML receipt when PDF/printview is unavailable (e.g. popup blocked). */
export function printThermalReceipt(invoiceData) {
	return printInvoiceCustom(invoiceData)
}

function formatCurrency(amount) {
	return Number.parseFloat(amount || 0).toFixed(2)
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
			return printInvoiceCustom(offlineQueueRowToInvoice(row, trimmed))
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

	if (!printFormat && invoiceDoc.pos_profile) {
		try {
			const posProfileDoc = await call("frappe.client.get", {
				doctype: "POS Profile",
				name: invoiceDoc.pos_profile,
			})

			if (posProfileDoc) {
				printFormat = posProfileDoc.print_format
				letterhead = letterhead || posProfileDoc.letter_head
			}
		} catch (error) {
			log.warn("Could not fetch POS Profile print settings:", error)
		}
	}

	return await printInvoice(invoiceDoc, printFormat, letterhead)
}
