/**
 * Invoice Sharing Composable
 * Handles WhatsApp, SMS, and Email sharing for invoices
 */

import { ref } from 'vue'
import { call } from 'frappe-ui'
import { useInvoiceSharingStore } from '@/stores/invoiceSharing'

export function useInvoiceSharing() {
	const store = useInvoiceSharingStore()
	const isLoading = ref(false)

	/**
	 * Share invoice via WhatsApp (similar to KLiK PoS)
	 */
	async function shareViaWhatsApp(invoiceName, mobileNo, message, posProfile, customerName) {
		isLoading.value = true
		try {
			const result = await call('pos_next.api.invoice_sharing.send_invoice_whatsapp', {
				mobile_no: mobileNo,
				customer_name: customerName || '',
				invoice_data: invoiceName,
				message: message || 'Your invoice is ready!',
				pos_profile: posProfile
			})
			
			// Store in history
			if (result.status === 'success') {
				store.addToHistory({
					invoice: invoiceName,
					channel: 'whatsapp',
					recipient: mobileNo,
					timestamp: new Date().toISOString()
				})
			}

			return {
				success: result.status === 'success',
				message: result.status === 'success' ? 'Invoice shared via WhatsApp successfully' : 'Failed to share via WhatsApp'
			}
		} catch (error) {
			console.error('WhatsApp sharing error:', error)
			return {
				success: false,
				message: error.message || 'Failed to share via WhatsApp'
			}
		} finally {
			isLoading.value = false
		}
	}

	/**
	 * Share invoice via SMS (similar to KLiK PoS)
	 */
	async function shareViaSMS(invoiceName, mobileNo, message, posProfile, customerName) {
		isLoading.value = true
		try {
			const result = await call('pos_next.api.invoice_sharing.send_invoice_sms', {
				mobile_no: mobileNo,
				customer_name: customerName || '',
				invoice_data: invoiceName,
				message: message || 'Your invoice is ready!',
				pos_profile: posProfile
			})
			
			// Store in history
			if (result.status === 'success') {
				store.addToHistory({
					invoice: invoiceName,
					channel: 'sms',
					recipient: mobileNo,
					timestamp: new Date().toISOString()
				})
			}

			return {
				success: result.status === 'success',
				message: result.status === 'success' ? 'Invoice shared via SMS successfully' : 'Failed to share via SMS'
			}
		} catch (error) {
			console.error('SMS sharing error:', error)
			return {
				success: false,
				message: error.message || 'Failed to share via SMS'
			}
		} finally {
			isLoading.value = false
		}
	}

	/**
	 * Share invoice via WhatsApp Web/Desktop (opens WhatsApp Web or Desktop app with invoice link)
	 */
	async function shareViaWhatsAppWeb(invoiceName, posProfile, mobileNo = null) {
		isLoading.value = true
		try {
			const result = await call('pos_next.api.invoice_sharing.get_whatsapp_web_url', {
				invoice_name: invoiceName,
				pos_profile: posProfile,
				mobile_no: mobileNo || null
			})
			
			if (result.success && result.url) {
				// result.url contains primary URL based on preference (whatsapp:// or web)
				// result.web_url contains alternative/fallback URL
				// result.preference contains the preference: "whatsapp_protocol" or "web"
				
				const preference = result.preference || 'whatsapp_protocol'
				
				if (preference === 'web') {
					// User prefers web.whatsapp.com - open directly in browser
					window.open(result.url, '_blank', 'noopener,noreferrer')
				} else {
					// Default: Try whatsapp:// protocol first, fallback to web if it doesn't work
					// Record if window had focus before attempting to open WhatsApp
					const hadFocus = document.hasFocus()
					let opened = false
					
					// Try opening WhatsApp using whatsapp:// protocol (works for desktop app and mobile)
					// Use a single method to avoid multiple opens
					try {
						const link = document.createElement('a')
						link.href = result.url
						link.style.display = 'none'
						link.target = '_blank'
						document.body.appendChild(link)
						link.click()
						// Remove link immediately
						setTimeout(() => {
							if (document.body.contains(link)) {
								document.body.removeChild(link)
							}
						}, 50)
						opened = true
					} catch (e) {
						console.log('Failed to open WhatsApp app:', e)
					}
					
					// Wait a moment to see if WhatsApp app opened (took focus away)
					// If window still has focus after 300ms, WhatsApp likely didn't open, so open web version
					setTimeout(() => {
						// Only open web version if:
						// 1. We tried to open the app (opened = true)
						// 2. Window still has focus (WhatsApp didn't take over)
						if (opened && (document.hasFocus() || !hadFocus)) {
							// WhatsApp app didn't open, open web version as fallback
							if (result.web_url) {
								window.open(result.web_url, '_blank', 'noopener,noreferrer')
							}
						} else if (!opened) {
							// If we couldn't even try to open the app, open web version directly
							if (result.web_url) {
								window.open(result.web_url, '_blank', 'noopener,noreferrer')
							} else {
								// Fallback to regular URL if web_url not available
								window.open(result.url, '_blank', 'noopener,noreferrer')
							}
						}
					}, 300)
				}
				
				// Store in history
				store.addToHistory({
					invoice: invoiceName,
					channel: 'whatsapp_web',
					recipient: mobileNo || 'WhatsApp Web/Desktop',
					timestamp: new Date().toISOString()
				})
				
				return {
					success: true,
					message: 'WhatsApp opened successfully'
				}
			}
			
			return {
				success: false,
				message: 'Failed to generate WhatsApp URL'
			}
		} catch (error) {
			console.error('WhatsApp Web sharing error:', error)
			return {
				success: false,
				message: error.message || 'Failed to open WhatsApp'
			}
		} finally {
			isLoading.value = false
		}
	}

	/**
	 * Share invoice via Email (similar to KLiK PoS)
	 */
	async function shareViaEmail(invoiceName, email, posProfile, customerName) {
		isLoading.value = true
		try {
			const result = await call('pos_next.api.invoice_sharing.send_invoice_email', {
				email: email,
				customer_name: customerName || '',
				invoice_data: invoiceName,
				pos_profile: posProfile
			})
			
			// Store in history
			if (result.status === 'success') {
				store.addToHistory({
					invoice: invoiceName,
					channel: 'email',
					recipient: email,
					timestamp: new Date().toISOString()
				})
			}

			return {
				success: result.status === 'success',
				message: result.status === 'success' ? 'Invoice shared via Email successfully' : 'Failed to share via Email'
			}
		} catch (error) {
			console.error('Email sharing error:', error)
			return {
				success: false,
				message: error.message || 'Failed to share via Email'
			}
		} finally {
			isLoading.value = false
		}
	}

	/**
	 * Get available sharing options for POS Profile
	 * Checks store cache first, only calls API if not cached
	 */
	async function getSharingOptions(posProfile, invoiceName = null, forceRefresh = false) {
		try {
			// Check store cache first (unless force refresh is requested)
			if (!forceRefresh && posProfile) {
				// Check if options are actually cached (exist in store state)
				const hasCachedOptions = posProfile in store.sharingOptionsByProfile
				if (hasCachedOptions) {
					const cachedOptions = store.getSharingOptions(posProfile)
					console.log('Found cached sharing options for profile:', posProfile)
					
					// If invoice name is provided, we need customer info, so call API but merge with cache
					if (invoiceName) {
						console.log('Invoice provided, fetching customer info from API')
						const options = await call('pos_next.api.invoice_sharing.get_sharing_options', {
							pos_profile: posProfile,
							invoice_name: invoiceName
						})
						
						// Merge cached sharing options with customer info from API
						return {
							...cachedOptions,
							customer: options?.customer
						}
					}
					
					// No invoice name, return cached options directly
					console.log('Using cached sharing options (no invoice)')
					return cachedOptions
				}
			}
			
			// If not cached or force refresh, call API
			console.log('Calling API for sharing options, profile:', posProfile, 'invoice:', invoiceName)
			const options = await call('pos_next.api.invoice_sharing.get_sharing_options', {
				pos_profile: posProfile,
				invoice_name: invoiceName
			})
			
			// Debug logging
			console.log('Sharing options received from API:', options)
			console.log('Email enabled:', options.email?.enabled)
			console.log('WhatsApp enabled:', options.whatsapp?.enabled)
			console.log('SMS enabled:', options.sms?.enabled)
			
			// Cache the options (only the sharing config, not customer-specific data)
			if (posProfile && options) {
				const optionsToCache = {
					whatsapp: options.whatsapp || { enabled: false },
					whatsapp_web: options.whatsapp_web || { enabled: false },
					sms: options.sms || { enabled: false },
					email: options.email || { enabled: false },
					print_format: options.print_format || null
				}
				store.setSharingOptions(posProfile, optionsToCache)
				console.log('Cached sharing options for profile:', posProfile)
			}

			return options
		} catch (error) {
			console.error('Failed to get sharing options:', error)
			console.error('Error details:', error.message, error)
			
			// Try to return cached options as fallback
			if (posProfile && posProfile in store.sharingOptionsByProfile) {
				const cachedOptions = store.getSharingOptions(posProfile)
				console.log('Using cached options as fallback due to API error')
				return cachedOptions
			}
			
			return {
				whatsapp: { enabled: false },
				whatsapp_web: { enabled: false },
				sms: { enabled: false },
				email: { enabled: false }
			}
		}
	}

	/**
	 * Validate contact information
	 */
	async function validateContactInfo(contact, channel) {
		try {
			const result = await call('pos_next.api.invoice_sharing.validate_contact_info', {
				contact: contact,
				channel: channel
			})

			return result || { valid: false }
		} catch (error) {
			console.error('Validation error:', error)
			return {
				valid: false,
				message: error.message || 'Validation failed'
			}
		}
	}

	/**
	 * Get sharing history
	 */
	function getSharingHistory() {
		return store.history
	}

	/**
	 * Clear sharing history
	 */
	function clearHistory() {
		store.clearHistory()
	}

	return {
		isLoading,
		shareViaWhatsApp,
		shareViaWhatsAppWeb,
		shareViaSMS,
		shareViaEmail,
		getSharingOptions,
		validateContactInfo,
		getSharingHistory,
		clearHistory
	}
}

