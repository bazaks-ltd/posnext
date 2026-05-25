/**
 * Cached POS Profile print settings (print format, letter head) for online/offline printing.
 */

const SHIFT_STORAGE_KEY = "pos_shift_data"

/** @returns {{ printFormat: string|null, letterhead: string|null, letterHeadHtml: string, letterHeadFooter: string, currency: string|null, company: string|null }} */
export function getPosPrintSettings() {
	const empty = {
		printFormat: null,
		letterhead: null,
		letterHeadHtml: "",
		letterHeadFooter: "",
		currency: null,
		company: null,
	}

	try {
		const raw = localStorage.getItem(SHIFT_STORAGE_KEY)
		if (!raw) {
			return empty
		}

		const data = JSON.parse(raw)
		const profile = data?.pos_profile || {}
		const letterHeadPrint = data?.letter_head_print || {}

		return {
			printFormat:
				profile.print_format ||
				profile.custom_default_print_format ||
				null,
			letterhead: profile.letter_head || null,
			letterHeadHtml: letterHeadPrint.content || "",
			letterHeadFooter: letterHeadPrint.footer || "",
			currency: profile.currency || null,
			company: profile.company || data?.company?.name || null,
		}
	} catch {
		return empty
	}
}

/**
 * Merge invoice data with cached profile fields needed for thermal printing.
 * @param {Object} invoiceData
 */
export function enrichInvoiceForPrint(invoiceData) {
	const settings = getPosPrintSettings()
	return {
		...invoiceData,
		company: invoiceData.company || settings.company,
		currency: invoiceData.currency || settings.currency,
	}
}
