/**
 * Device-local print preferences (not synced to ERPNext).
 * Browsers cannot target a named printer from JavaScript; the OS print dialog applies.
 * Stored name is used as the default choice in settings and for future integrations.
 */

const STORAGE_KEY = "pos_next_local_print_settings"

/** @returns {{ defaultPrinter: string }} */
export function getLocalPrintSettings() {
	try {
		const raw = localStorage.getItem(STORAGE_KEY)
		if (!raw) {
			return { defaultPrinter: "" }
		}
		const parsed = JSON.parse(raw)
		return {
			defaultPrinter: typeof parsed.defaultPrinter === "string" ? parsed.defaultPrinter : "",
		}
	} catch {
		return { defaultPrinter: "" }
	}
}

/** @param {{ defaultPrinter?: string }} prefs */
export function setLocalPrintSettings(prefs) {
	try {
		const prev = getLocalPrintSettings()
		localStorage.setItem(
			STORAGE_KEY,
			JSON.stringify({
				defaultPrinter: prefs.defaultPrinter ?? prev.defaultPrinter ?? "",
			}),
		)
	} catch {
		// ignore quota / private mode
	}
}
