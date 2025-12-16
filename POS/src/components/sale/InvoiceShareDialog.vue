<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Share Invoice'),
			size: 'lg'
		}"
	>
		<template #body-title>
			<span class="sr-only">{{ __('Share invoice via WhatsApp, SMS, or Email') }}</span>
		</template>

		<template #body-content>
			<div class="space-y-6">
				<!-- Channel Selection Tabs -->
				<div class="flex space-x-2 border-b">
					<button
						v-if="sharingOptions.whatsapp?.enabled"
						@click="activeChannel = 'whatsapp'"
						:class="[
							'px-4 py-2 border-b-2 font-medium transition-colors',
							activeChannel === 'whatsapp'
								? 'border-blue-500 text-blue-600'
								: 'border-transparent text-gray-500 hover:text-gray-700'
						]"
					>
						{{ __('WhatsApp (API)') }}
					</button>
					<button
						v-if="sharingOptions.sms?.enabled"
						@click="activeChannel = 'sms'"
						:class="[
							'px-4 py-2 border-b-2 font-medium transition-colors',
							activeChannel === 'sms'
								? 'border-blue-500 text-blue-600'
								: 'border-transparent text-gray-500 hover:text-gray-700'
						]"
					>
						{{ __('SMS') }}
					</button>
					<button
						v-if="sharingOptions.email?.enabled"
						@click="activeChannel = 'email'"
						:class="[
							'px-4 py-2 border-b-2 font-medium transition-colors',
							activeChannel === 'email'
								? 'border-blue-500 text-blue-600'
								: 'border-transparent text-gray-500 hover:text-gray-700'
						]"
					>
						{{ __('Email') }}
					</button>
					<button
						v-if="sharingOptions.whatsapp_web?.enabled"
						@click="activeChannel = 'whatsapp_web'"
						:class="[
							'px-4 py-2 border-b-2 font-medium transition-colors',
							activeChannel === 'whatsapp_web'
								? 'border-blue-500 text-blue-600'
								: 'border-transparent text-gray-500 hover:text-gray-700'
						]"
					>
						{{ __('WhatsApp Web') }}
					</button>
				</div>

				<!-- Loading state -->
				<div
					v-if="isLoadingOptions"
					class="p-4 bg-gray-50 border border-gray-200 rounded-lg"
				>
					<p class="text-sm text-gray-600">
						{{ __('Loading sharing options...') }}
					</p>
				</div>

				<!-- No channels available message -->
				<div
					v-else-if="!hasEnabledChannels"
					class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg"
				>
					<p class="text-sm text-yellow-800">
						{{ __('No sharing channels are enabled. Please configure invoice sharing in POS Profile settings.') }}
					</p>
				</div>

				<!-- WhatsApp Channel (API) -->
				<div v-if="activeChannel === 'whatsapp' && sharingOptions.whatsapp?.enabled" class="space-y-4">
					<div class="p-3 bg-blue-50 border border-blue-200 rounded-lg mb-4">
						<p class="text-xs text-blue-800">
							{{ __('WhatsApp API - Sends invoice via WhatsApp API. Requires mobile number and configured WhatsApp integration.') }}
						</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">
							{{ __('Mobile Number') }}
						</label>
						<Input
							v-model="contactInfo.mobile"
							type="text"
							:placeholder="__('+1234567890')"
							:disabled="isSending"
						/>
						<p class="mt-1 text-xs text-gray-500">
							{{ __('Include country code (e.g., +1 for USA)') }}
						</p>
					</div>
				</div>

				<!-- SMS Channel -->
				<div v-if="activeChannel === 'sms' && sharingOptions.sms?.enabled" class="space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">
							{{ __('Mobile Number') }}
						</label>
						<Input
							v-model="contactInfo.mobile"
							type="text"
							:placeholder="__('+1234567890')"
							:disabled="isSending"
						/>
					</div>
				</div>

				<!-- Email Channel -->
				<div v-if="activeChannel === 'email' && sharingOptions.email?.enabled" class="space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">
							{{ __('Email Address') }}
						</label>
						<Input
							v-model="contactInfo.email"
							type="email"
							:placeholder="__('customer@example.com')"
							:disabled="isSending"
						/>
					</div>
				</div>

				<!-- WhatsApp Web Channel -->
				<div v-if="activeChannel === 'whatsapp_web' && sharingOptions.whatsapp_web?.enabled" class="space-y-4">
					<div class="p-3 bg-green-50 border border-green-200 rounded-lg mb-4">
						<p class="text-sm text-green-800 font-medium mb-2">
							{{ __('WhatsApp Web/Desktop - Opens in Browser or Desktop App') }}
						</p>
						<p class="text-sm text-green-700">
							{{ __('Opens WhatsApp Web in browser or WhatsApp Desktop app (if installed) with the invoice link ready to share. Mobile number is optional.') }}
						</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">
							{{ __('Mobile Number (Optional)') }}
						</label>
						<Input
							v-model="contactInfo.mobile"
							type="text"
							:placeholder="__('+1234567890')"
							:disabled="isSending"
						/>
						<p class="mt-1 text-xs text-gray-500">
							{{ __('Include country code (e.g., +1 for USA). If provided, will pre-fill the recipient.') }}
						</p>
					</div>
				</div>

				<!-- Error Message -->
				<div v-if="errorMessage" class="p-4 bg-red-50 border border-red-200 rounded-lg">
					<p class="text-sm text-red-800">{{ errorMessage }}</p>
				</div>

				<!-- Success Message -->
				<div v-if="successMessage" class="p-4 bg-green-50 border border-green-200 rounded-lg">
					<p class="text-sm text-green-800">{{ successMessage }}</p>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end space-x-2">
				<Button variant="ghost" @click="closeDialog" :disabled="isSending">
					{{ __('Cancel') }}
				</Button>
				<Button
					variant="solid"
					@click="shareInvoice"
					:loading="isSending"
					:disabled="!canSend || isSending"
				>
					{{ __('Send') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Dialog, Input, Button } from 'frappe-ui'
import { useInvoiceSharing } from '@/composables/useInvoiceSharing'
import { useInvoiceSharingStore } from '@/stores/invoiceSharing'
import { useToast } from '@/composables/useToast'

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false
	},
	invoiceName: {
		type: String,
		required: true
	},
	posProfile: {
		type: String,
		required: true
	},
	customerMobile: {
		type: String,
		default: ''
	},
	customerEmail: {
		type: String,
		default: ''
	},
	customerName: {
		type: String,
		default: ''
	},
	initialChannel: {
		type: String,
		default: null,
		validator: (value) => !value || ['whatsapp', 'whatsapp_web', 'sms', 'email'].includes(value)
	},
	initialSharingOptions: {
		type: Object,
		default: null
	}
})

const emit = defineEmits(['update:modelValue', 'shared'])

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
})

const { shareViaWhatsApp, shareViaWhatsAppWeb, shareViaSMS, shareViaEmail, getSharingOptions } = useInvoiceSharing()
const sharingStore = useInvoiceSharingStore()
const { showSuccess, showError } = useToast()

const activeChannel = ref('whatsapp')
const contactInfo = ref({
	mobile: '',
	email: ''
})
const sharingOptions = ref({
	whatsapp: { enabled: false },
	whatsapp_web: { enabled: false },
	sms: { enabled: false },
	email: { enabled: false }
})
const isSending = ref(false)
const isLoadingOptions = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const messagePreview = ref('')

const hasEnabledChannels = computed(() => {
	return (
		sharingOptions.value.whatsapp?.enabled ||
		sharingOptions.value.whatsapp_web?.enabled ||
		sharingOptions.value.sms?.enabled ||
		sharingOptions.value.email?.enabled
	)
})

const canSend = computed(() => {
	if (activeChannel.value === 'whatsapp_web') {
		return true // WhatsApp Web doesn't require contact info (optional)
	} else if (activeChannel.value === 'whatsapp' || activeChannel.value === 'sms') {
		return contactInfo.value.mobile && contactInfo.value.mobile.length >= 10
	} else if (activeChannel.value === 'email') {
		return contactInfo.value.email && contactInfo.value.email.includes('@')
	}
	return false
})

// Load sharing options when dialog opens
watch(show, async (newValue) => {
	if (newValue) {
		// Set loading state before loading options
		isLoadingOptions.value = true
		
		// Always fetch fresh options from API to ensure we have latest settings
		// This ensures changes in POS Profile are reflected immediately
		if (props.posProfile) {
			// Always load fresh options from API (force refresh)
			try {
				const options = await getSharingOptions(props.posProfile, props.invoiceName, true) // forceRefresh = true
				if (options) {
					sharingOptions.value = {
						whatsapp: { enabled: Boolean(options.whatsapp?.enabled), template: options.whatsapp?.template },
						whatsapp_web: { enabled: Boolean(options.whatsapp_web?.enabled) },
						sms: { enabled: Boolean(options.sms?.enabled), template: options.sms?.template },
						email: { enabled: Boolean(options.email?.enabled), template: options.email?.template }
					}
					
					// Pre-fill customer contact info from API response if not already set via props
					if (options?.customer) {
						if (!contactInfo.value.mobile && options.customer.mobile_no) {
							contactInfo.value.mobile = options.customer.mobile_no
						}
						if (!contactInfo.value.email && options.customer.email_id) {
							contactInfo.value.email = options.customer.email_id
						}
					}
				}
				isLoadingOptions.value = false
			} catch (error) {
				console.error('Failed to load sharing options:', error)
				// Fallback to cached options if API fails
				const cachedOptions = sharingStore.getSharingOptions(props.posProfile)
				if (cachedOptions) {
					sharingOptions.value = {
						whatsapp: { enabled: Boolean(cachedOptions.whatsapp?.enabled), template: cachedOptions.whatsapp?.template },
						whatsapp_web: { enabled: Boolean(cachedOptions.whatsapp_web?.enabled) },
						sms: { enabled: Boolean(cachedOptions.sms?.enabled), template: cachedOptions.sms?.template },
						email: { enabled: Boolean(cachedOptions.email?.enabled), template: cachedOptions.email?.template }
					}
				}
				isLoadingOptions.value = false
			}
		} else {
			// No POS profile, use initial options or default
			if (props.initialSharingOptions) {
				sharingOptions.value = {
					whatsapp: { enabled: Boolean(props.initialSharingOptions.whatsapp?.enabled), template: props.initialSharingOptions.whatsapp?.template },
					whatsapp_web: { enabled: Boolean(props.initialSharingOptions.whatsapp_web?.enabled) },
					sms: { enabled: Boolean(props.initialSharingOptions.sms?.enabled), template: props.initialSharingOptions.sms?.template },
					email: { enabled: Boolean(props.initialSharingOptions.email?.enabled), template: props.initialSharingOptions.email?.template }
				}
				isLoadingOptions.value = false
			} else {
				sharingOptions.value = {
					whatsapp: { enabled: false },
					whatsapp_web: { enabled: false },
					sms: { enabled: false },
					email: { enabled: false }
				}
				await loadSharingOptions()
			}
		}
		
		// Pre-fill contact info from customer
		contactInfo.value.mobile = props.customerMobile || ''
		contactInfo.value.email = props.customerEmail || ''
		
		// Reset messages
		errorMessage.value = ''
		successMessage.value = ''
		
		// Set active channel: use initialChannel if provided and enabled, otherwise first available
		if (props.initialChannel) {
			if (sharingOptions.value[props.initialChannel]?.enabled) {
				activeChannel.value = props.initialChannel
			}
		} else if (sharingOptions.value.whatsapp?.enabled) {
			activeChannel.value = 'whatsapp'
		} else if (sharingOptions.value.whatsapp_web?.enabled) {
			activeChannel.value = 'whatsapp_web'
		} else if (sharingOptions.value.sms?.enabled) {
			activeChannel.value = 'sms'
		} else if (sharingOptions.value.email?.enabled) {
			activeChannel.value = 'email'
		}
		
		// Load message preview
		await loadMessagePreview()
		
		// Clear loading state after everything is loaded
		isLoadingOptions.value = false
	}
})

// Update preview when channel or template changes
watch([activeChannel, () => sharingOptions.value], async () => {
	if (show.value) {
		await loadMessagePreview()
	}
}, { deep: true })

async function loadSharingOptions() {
	try {
		// Only fetch customer-specific info if invoice is provided
		// The sharing options themselves should already be cached
		const options = await getSharingOptions(props.posProfile, props.invoiceName)
		console.log('Loaded sharing options (for customer info):', options)
		
		// Update sharing options only if we got them (should be from cache)
		if (options) {
			sharingOptions.value = {
				whatsapp: { enabled: Boolean(options.whatsapp?.enabled), template: options.whatsapp?.template },
				whatsapp_web: { enabled: Boolean(options.whatsapp_web?.enabled) },
				sms: { enabled: Boolean(options.sms?.enabled), template: options.sms?.template },
				email: { enabled: Boolean(options.email?.enabled), template: options.email?.template }
			}
		}
		
		// Pre-fill customer contact info from API response if not already set via props
		if (options?.customer) {
			if (!contactInfo.value.mobile && options.customer.mobile_no) {
				contactInfo.value.mobile = options.customer.mobile_no
			}
			if (!contactInfo.value.email && options.customer.email_id) {
				contactInfo.value.email = options.customer.email_id
			}
		}
		
		console.log('Sharing options after assignment:', sharingOptions.value)
		console.log('Has enabled channels:', hasEnabledChannels.value)
		
		// Ensure loading state is cleared after options are loaded
		isLoadingOptions.value = false
	} catch (error) {
		console.error('Failed to load sharing options:', error)
		// Don't reset options on error, keep cached ones
		// Ensure loading state is cleared even on error
		isLoadingOptions.value = false
	}
}

async function loadMessagePreview() {
	// For now, show template from options
	if (activeChannel.value === 'whatsapp' && sharingOptions.value.whatsapp?.template) {
		messagePreview.value = sharingOptions.value.whatsapp.template
	} else if (activeChannel.value === 'sms' && sharingOptions.value.sms?.template) {
		messagePreview.value = sharingOptions.value.sms.template
	} else {
		messagePreview.value = ''
	}
}

async function shareInvoice() {
	errorMessage.value = ''
	successMessage.value = ''
	isSending.value = true

	try {
		let result

		// Get customer name from props or invoice
		const customerName = props.customerName || 'Customer'
		
		if (activeChannel.value === 'whatsapp') {
			result = await shareViaWhatsApp(
				props.invoiceName,
				contactInfo.value.mobile,
				messagePreview.value || 'Your invoice is ready!',
				props.posProfile,
				customerName
			)
		} else if (activeChannel.value === 'sms') {
			result = await shareViaSMS(
				props.invoiceName,
				contactInfo.value.mobile,
				messagePreview.value || 'Your invoice is ready!',
				props.posProfile,
				customerName
			)
		} else if (activeChannel.value === 'email') {
			result = await shareViaEmail(
				props.invoiceName,
				contactInfo.value.email,
				props.posProfile,
				customerName
			)
		} else if (activeChannel.value === 'whatsapp_web') {
			result = await shareViaWhatsAppWeb(
				props.invoiceName,
				props.posProfile,
				contactInfo.value.mobile || null
			)
		}

		if (result && result.success) {
			successMessage.value = result.message
			showSuccess(result.message)
			emit('shared', {
				channel: activeChannel.value,
				recipient: activeChannel.value === 'email' 
					? contactInfo.value.email 
					: activeChannel.value === 'whatsapp_web'
						? 'WhatsApp Web'
						: contactInfo.value.mobile
			})
			
			// Close dialog after 1.5 seconds
			setTimeout(() => {
				closeDialog()
			}, 1500)
		} else {
			errorMessage.value = result.message || __('Failed to send invoice')
			showError(errorMessage.value)
		}
	} catch (error) {
		errorMessage.value = error.message || __('An error occurred while sharing the invoice')
		showError(errorMessage.value)
	} finally {
		isSending.value = false
	}
}

function closeDialog() {
	show.value = false
	// Reset state
	setTimeout(() => {
		errorMessage.value = ''
		successMessage.value = ''
		isLoadingOptions.value = false
		contactInfo.value = {
			mobile: '',
			email: ''
		}
	}, 300)
}
</script>

<style scoped>
.sr-only {
	position: absolute;
	width: 1px;
	height: 1px;
	padding: 0;
	margin: -1px;
	overflow: hidden;
	clip: rect(0, 0, 0, 0);
	white-space: nowrap;
	border-width: 0;
}
</style>

