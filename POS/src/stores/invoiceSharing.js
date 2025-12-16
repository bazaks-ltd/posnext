/**
 * Invoice Sharing Store
 * Manages state for invoice sharing functionality
 */

import { defineStore } from 'pinia'

export const useInvoiceSharingStore = defineStore('invoiceSharing', {
	state: () => ({
		// Available sharing channels from POS Profile (keyed by profile name)
		sharingOptionsByProfile: {},
		
		// Sharing history (last 50 shares)
		history: [],
		
		// Contact information cache
		contactCache: {},
		
		// Template cache
		templateCache: {}
	}),

	getters: {
		/**
		 * Get sharing options for a specific POS profile
		 */
		getSharingOptions: (state) => (posProfile) => {
			return state.sharingOptionsByProfile[posProfile] || {
				whatsapp: { enabled: false, template: null },
				whatsapp_web: { enabled: false },
				sms: { enabled: false, template: null },
				email: { enabled: false, template: null },
				print_format: null
			}
		},

		/**
		 * Check if any sharing channel is enabled for a POS profile
		 */
		hasEnabledChannels: (state) => (posProfile) => {
			const options = state.sharingOptionsByProfile[posProfile]
			if (!options) return false
			return (
				options.whatsapp?.enabled ||
				options.whatsapp_web?.enabled ||
				options.sms?.enabled ||
				options.email?.enabled
			)
		},

		/**
		 * Get enabled channels list for a POS profile
		 */
		enabledChannels: (state) => (posProfile) => {
			const options = state.sharingOptionsByProfile[posProfile]
			if (!options) return []
			const channels = []
			if (options.whatsapp?.enabled) channels.push('whatsapp')
			if (options.sms?.enabled) channels.push('sms')
			if (options.email?.enabled) channels.push('email')
			return channels
		},

		/**
		 * Get last shared invoice
		 */
		lastShared(state) {
			return state.history.length > 0 ? state.history[0] : null
		},

		/**
		 * Get sharing history for a specific invoice
		 */
		getHistoryForInvoice: (state) => (invoiceName) => {
			return state.history.filter(item => item.invoice === invoiceName)
		}
	},

	actions: {
		/**
		 * Set sharing options from POS Profile (keyed by profile name)
		 */
		setSharingOptions(posProfile, options) {
			if (!posProfile) {
				console.warn('Cannot set sharing options: POS Profile name is required')
				return
			}
			
			this.sharingOptionsByProfile[posProfile] = {
				whatsapp: options.whatsapp || { enabled: false },
				whatsapp_web: options.whatsapp_web || { enabled: false },
				sms: options.sms || { enabled: false },
				email: options.email || { enabled: false },
				print_format: options.print_format || null
			}
			
			// Persist to localStorage
			this._saveSharingOptions()
		},

		/**
		 * Add to sharing history
		 */
		addToHistory(item) {
			// Add to beginning of array
			this.history.unshift(item)
			
			// Keep only last 50 items
			if (this.history.length > 50) {
				this.history = this.history.slice(0, 50)
			}
			
			// Persist to localStorage
			this._saveHistory()
		},

		/**
		 * Clear sharing history
		 */
		clearHistory() {
			this.history = []
			localStorage.removeItem('pos_invoice_sharing_history')
		},

		/**
		 * Cache contact information
		 */
		cacheContact(customer, contactInfo) {
			this.contactCache[customer] = {
				...contactInfo,
				cached_at: new Date().toISOString()
			}
			
			// Persist to localStorage
			this._saveContactCache()
		},

		/**
		 * Get cached contact information
		 */
		getCachedContact(customer) {
			const cached = this.contactCache[customer]
			if (!cached) return null
			
			// Check if cache is still fresh (24 hours)
			const cachedAt = new Date(cached.cached_at)
			const now = new Date()
			const hoursDiff = (now - cachedAt) / (1000 * 60 * 60)
			
			if (hoursDiff > 24) {
				// Cache expired
				delete this.contactCache[customer]
				this._saveContactCache()
				return null
			}
			
			return cached
		},

		/**
		 * Cache template
		 */
		cacheTemplate(channel, template) {
			this.templateCache[channel] = {
				template: template,
				cached_at: new Date().toISOString()
			}
		},

		/**
		 * Get cached template
		 */
		getCachedTemplate(channel) {
			return this.templateCache[channel]?.template || null
		},

		/**
		 * Initialize store from localStorage
		 */
		initialize() {
			// Load history from localStorage
			const savedHistory = localStorage.getItem('pos_invoice_sharing_history')
			if (savedHistory) {
				try {
					this.history = JSON.parse(savedHistory)
				} catch (e) {
					console.error('Failed to load sharing history:', e)
				}
			}
			
			// Load contact cache from localStorage
			const savedCache = localStorage.getItem('pos_invoice_sharing_contacts')
			if (savedCache) {
				try {
					this.contactCache = JSON.parse(savedCache)
				} catch (e) {
					console.error('Failed to load contact cache:', e)
				}
			}
			
			// Load sharing options from localStorage
			const savedOptions = localStorage.getItem('pos_invoice_sharing_options')
			if (savedOptions) {
				try {
					this.sharingOptionsByProfile = JSON.parse(savedOptions)
				} catch (e) {
					console.error('Failed to load sharing options:', e)
				}
			}
		},

		/**
		 * Save history to localStorage
		 */
		_saveHistory() {
			try {
				localStorage.setItem('pos_invoice_sharing_history', JSON.stringify(this.history))
			} catch (e) {
				console.error('Failed to save sharing history:', e)
			}
		},

		/**
		 * Save contact cache to localStorage
		 */
		_saveContactCache() {
			try {
				localStorage.setItem('pos_invoice_sharing_contacts', JSON.stringify(this.contactCache))
			} catch (e) {
				console.error('Failed to save contact cache:', e)
			}
		},

		/**
		 * Clear sharing options for a specific POS profile
		 */
		clearSharingOptions(posProfile) {
			if (posProfile && posProfile in this.sharingOptionsByProfile) {
				delete this.sharingOptionsByProfile[posProfile]
				this._saveSharingOptions()
			}
		},

		/**
		 * Save sharing options to localStorage
		 */
		_saveSharingOptions() {
			try {
				localStorage.setItem('pos_invoice_sharing_options', JSON.stringify(this.sharingOptionsByProfile))
			} catch (e) {
				console.error('Failed to save sharing options:', e)
			}
		}
	}
})

