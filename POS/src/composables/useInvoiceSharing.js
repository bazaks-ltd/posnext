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
		shareViaSMS,
		shareViaEmail,
		getSharingOptions,
		validateContactInfo,
		getSharingHistory,
		clearHistory
	}
}

