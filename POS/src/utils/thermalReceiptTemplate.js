/**
 * Thermal receipt HTML — mirrors POS Next Receipt print format (print_format.json).
 * Used for offline printing when server printview is unavailable.
 */

import { getCurrencySymbol } from "@/utils/currency"
import { __ } from "@/utils/translation"

const RECEIPT_STYLES = `
	@page {
		size: 80mm auto;
		margin: 0mm;
	}
	body {
		font-family: 'DejaVu Sans', 'Arial', sans-serif;
		width: 80mm;
		max-width: 80mm;
		margin: 0 auto;
		padding: 10px;
		font-size: 11px;
		line-height: 1.4;
	}
	.text-center { text-align: center; }
	.bold { font-weight: bold; }
	.divider {
		border-top: 1px dashed #333;
		margin: 12px 0;
		padding: 0;
	}
	.row {
		display: table;
		width: 100%;
		margin: 4px 0;
	}
	.row > span:first-child {
		display: table-cell;
		text-align: left;
		width: 60%;
	}
	.row > span:last-child {
		display: table-cell;
		text-align: right;
		width: 40%;
	}
	.item-section {
		margin-bottom: 12px;
	}
	.item-name {
		font-weight: bold;
		margin-bottom: 3px;
		font-size: 11px;
	}
	.item-details {
		font-size: 10px;
		color: #555;
	}
	.discount-line {
		font-size: 9px;
		color: #28a745;
		padding-left: 10px;
	}
	.serial-line {
		font-size: 9px;
		color: #666;
		background-color: #f5f5f5;
		padding: 4px 6px;
		margin-top: 4px;
		border-radius: 3px;
	}
	.serial-label {
		font-weight: bold;
		margin-bottom: 2px;
	}
	.total-row {
		font-size: 14px;
		font-weight: bold;
		border-top: 2px solid #000;
		padding-top: 8px;
		margin-top: 8px;
	}
	.outstanding-row {
		font-size: 13px;
		font-weight: bold;
		color: #dc3545;
		background-color: #fff3cd;
		padding: 6px;
		margin-top: 8px;
		border-radius: 4px;
	}
	.footer {
		border-top: 2px solid #000;
		margin-top: 15px;
		padding-top: 10px;
		text-align: center;
		font-size: 10px;
	}
	.letter-head, .letter-head-footer {
		margin-bottom: 12px;
		text-align: center;
	}
	.letter-head img, .letter-head-footer img {
		max-width: 100%;
		height: auto;
	}
	@media print {
		body { width: 80mm; max-width: 80mm; padding: 5mm; }
	}
	.no-print { display: none; }
	@media screen {
		.no-print { display: block; }
	}
`

function fmtAmount(value) {
	return Number.parseFloat(value || 0).toFixed(2)
}

function fmtQty(value) {
	return String(Math.round(Number.parseFloat(value || 0)))
}

function isPartialPayment(doc) {
	return (
		doc.status === "Partly Paid" ||
		doc.status === __("Pending sync") ||
		(doc.outstanding_amount &&
			doc.outstanding_amount > 0 &&
			doc.outstanding_amount < doc.grand_total)
	)
}

function formatPostingDateTime(doc) {
	const date = doc.posting_date || new Date().toISOString().slice(0, 10)
	let time = ""
	if (doc.posting_time) {
		time = String(doc.posting_time).split(".")[0]
	}
	return time ? `${date} ${time}` : date
}

function renderItems(doc, currencySymbol) {
	return (doc.items || [])
		.filter(Boolean)
		.map((item) => {
			const qty = item.qty ?? item.quantity ?? 0
			const rate = item.price_list_rate ?? item.rate ?? 0
			const lineTotal = Number(qty) * Number(rate)
			const hasDiscount =
				(item.discount_percentage &&
					Number.parseFloat(item.discount_percentage) > 0) ||
				(item.discount_amount && Number.parseFloat(item.discount_amount) > 0)

			let html = `
<div class="item-section">
	<div class="item-name">${item.item_name || item.item_code || ""}</div>
	<div class="row item-details">
		<span>${fmtQty(qty)} × ${currencySymbol} ${fmtAmount(rate)}</span>
		<span><b>${currencySymbol} ${fmtAmount(lineTotal)}</b></span>
	</div>`

			if (hasDiscount) {
				const pct = item.discount_percentage
					? ` (${Number.parseFloat(item.discount_percentage).toFixed(1)}%)`
					: ""
				html += `
	<div class="row discount-line">
		<span>Discount${pct}</span>
		<span>-${currencySymbol} ${fmtAmount(item.discount_amount || 0)}</span>
	</div>`
			}

			if (item.serial_no) {
				html += `
	<div class="serial-line">
		<div class="serial-label">Serial No:</div>
		<div>${String(item.serial_no).replace(/\n/g, ", ")}</div>
	</div>`
			}

			html += `
</div>`
			return html
		})
		.join("")
}

function renderTotals(doc, currencySymbol) {
	let html = ""
	const totalTax =
		doc.total_taxes_and_charges ?? doc.total_tax ?? 0

	if (totalTax && Number(totalTax) > 0) {
		html += `
<div class="row" style="font-size: 11px;">
	<span>Subtotal:</span>
	<span>${currencySymbol} ${fmtAmount((doc.grand_total || 0) - totalTax)}</span>
</div>
<div class="row" style="font-size: 11px;">
	<span>Tax:</span>
	<span>${currencySymbol} ${fmtAmount(totalTax)}</span>
</div>`
	}

	if (doc.discount_amount) {
		const pct = doc.additional_discount_percentage
			? ` (${Number.parseFloat(doc.additional_discount_percentage).toFixed(1)}%)`
			: ""
		html += `
<div class="row" style="font-size: 11px; color: #28a745;">
	<span>Additional Discount${pct}:</span>
	<span>-${currencySymbol} ${fmtAmount(Math.abs(doc.discount_amount))}</span>
</div>`
	}

	html += `
<div class="row total-row">
	<span>TOTAL:</span>
	<span>${currencySymbol} ${fmtAmount(doc.grand_total)}</span>
</div>`

	return html
}

function renderPayments(doc, currencySymbol) {
	const payments = (doc.payments || []).filter(Boolean)
	if (!payments.length) {
		return ""
	}

	let html = `
<div class="divider"></div>
<div class="bold" style="margin-bottom: 6px; font-size: 11px;">Payments:</div>`

	for (const payment of payments) {
		html += `
<div class="row" style="font-size: 10px;">
	<span>${payment.mode_of_payment || __("Payment")}:</span>
	<span>${currencySymbol} ${fmtAmount(payment.amount)}</span>
</div>`
	}

	html += `
<div class="row bold" style="font-size: 11px; margin-top: 6px; border-top: 1px solid #ccc; padding-top: 4px;">
	<span>Total Paid:</span>
	<span>${currencySymbol} ${fmtAmount(doc.paid_amount || 0)}</span>
</div>`

	if (doc.change_amount && doc.change_amount > 0) {
		html += `
<div class="row bold" style="font-size: 10px; margin-top: 4px;">
	<span>Change:</span>
	<span>${currencySymbol} ${fmtAmount(doc.change_amount)}</span>
</div>`
	}

	if (doc.outstanding_amount && doc.outstanding_amount > 0) {
		html += `
<div class="row outstanding-row">
	<span>BALANCE DUE:</span>
	<span>${currencySymbol} ${fmtAmount(doc.outstanding_amount)}</span>
</div>`
	}

	return html
}

/**
 * Build full thermal receipt HTML matching POS Next Receipt print format.
 * @param {Object} doc - Normalized invoice document
 * @param {Object} options - { currency, letterHeadHtml, letterHeadFooter }
 */
export function buildThermalReceiptHtml(doc, options = {}) {
	const currency = options.currency || doc.currency || "USD"
	const currencySymbol = getCurrencySymbol(currency)
	const letterHeadHtml = options.letterHeadHtml || ""
	const letterHeadFooter = options.letterHeadFooter || ""

	const body = `
${letterHeadHtml ? `<div class="letter-head">${letterHeadHtml}</div>` : ""}
<div class="text-center bold" style="font-size: 16px; margin-bottom: 8px;">${doc.company || "POS Next"}</div>
<div class="text-center" style="font-size: 11px; margin-bottom: 12px;">TAX INVOICE</div>

<div style="font-size: 10px; margin-bottom: 12px; line-height: 1.5;">
	<div style="margin-bottom: 2px;"><b>Invoice:</b> ${doc.name || ""}</div>
	<div style="margin-bottom: 2px;"><b>Date:</b> ${formatPostingDateTime(doc)}</div>
	${doc.customer_name ? `<div style="margin-bottom: 2px;"><b>Customer:</b> ${doc.customer_name}</div>` : ""}
	${
		isPartialPayment(doc)
			? `<div style="margin-bottom: 2px; color: #dc3545; font-weight: bold;"><b>Status:</b> PARTIAL PAYMENT</div>`
			: ""
	}
</div>

<div class="divider"></div>

${renderItems(doc, currencySymbol)}

<div class="divider"></div>

${renderTotals(doc, currencySymbol)}

${renderPayments(doc, currencySymbol)}

<div class="footer">
	<div style="margin-bottom: 4px; font-size: 11px;">Thank you for your business!</div>
	<div style="font-size: 8px; color: #888;">Powered by Bazaks</div>
</div>

${letterHeadFooter ? `<div class="letter-head-footer">${letterHeadFooter}</div>` : ""}`

	return `<!DOCTYPE html>
<html>
<head>
	<meta charset="UTF-8">
	<title>${__("Invoice - {0}", [doc.name || ""])}</title>
	<style>${RECEIPT_STYLES}</style>
</head>
<body>
${body}
<div class="no-print" style="text-align: center; margin-top: 20px;">
	<button onclick="window.print()" style="padding: 10px 20px; font-size: 14px; cursor: pointer;">
		${__("Print Receipt")}
	</button>
	<button onclick="window.close()" style="padding: 10px 20px; font-size: 14px; cursor: pointer; margin-left: 10px;">
		${__("Close")}
	</button>
</div>
</body>
</html>`
}
