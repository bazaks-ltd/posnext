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
						{{ __('WhatsApp') }}
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
						@click="activeChannel = 'download'"
						:class="[
							'px-4 py-2 border-b-2 font-medium transition-colors',
							activeChannel === 'download'
								? 'border-blue-500 text-blue-600'
								: 'border-transparent text-gray-500 hover:text-gray-700'
						]"
					>
						{{ __('Download PDF') }}
					</button>
				</div>

				<!-- No channels available message -->
				<div
					v-if="!hasEnabledChannels"
					class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg"
				>
					<p class="text-sm text-yellow-800">
						{{ __('No sharing channels are enabled. Please configure invoice sharing in POS Profile settings.') }}
					</p>
				</div>

				<!-- WhatsApp Channel -->
				<div v-if="activeChannel === 'whatsapp' && sharingOptions.whatsapp?.enabled" class="space-y-4">
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

					<div v-if="messagePreview">
						<label class="block text-sm font-medium text-gray-700 mb-1">
							{{ __('Message Preview') }}
						</label>
						<div class="p-3 bg-gray-50 border border-gray-200 rounded text-sm whitespace-pre-wrap">
							{{ messagePreview }}
						</div>
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

					<div v-if="messagePreview">
						<label class="block text-sm font-medium text-gray-700 mb-1">
							{{ __('Message Preview') }}
						</label>
						<div class="p-3 bg-gray-50 border border-gray-200 rounded text-sm whitespace-pre-wrap">
							{{ messagePreview }}
						</div>
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

				<!-- Download PDF Channel -->
				<div v-if="activeChannel === 'download'" class="space-y-4">
					<div class="p-4 bg-blue-50 border border-blue-200 rounded-lg">
						<p class="text-sm text-blue-800">
							{{ __('Click the "Download PDF" button below to save the invoice as a PDF file to your device.') }}
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
					v-if="activeChannel !== 'download'"
					variant="solid"
					@click="shareInvoice"
					:loading="isSending"
					:disabled="!canSend || isSending"
				>
					{{ __('Send') }}
				</Button>
				<Button
					v-else
					variant="solid"
					theme="blue"
					@click="downloadPDF"
					:loading="isDownloading"
					:disabled="isDownloading"
				>
					{{ __('Download PDF') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Dialog, Input, Button } from 'frappe-ui'
import { useInvoiceSharing } from '@/composables/useInvoiceSharing'
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
		validator: (value) => !value || ['whatsapp', 'sms', 'email', 'download'].includes(value)
	}
})

const emit = defineEmits(['update:modelValue', 'shared'])

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
})

const { shareViaWhatsApp, shareViaSMS, shareViaEmail, getSharingOptions } = useInvoiceSharing()
const { showSuccess, showError } = useToast()

const activeChannel = ref('whatsapp')
const contactInfo = ref({
	mobile: '',
	email: ''
})
const sharingOptions = ref({
	whatsapp: { enabled: false },
	sms: { enabled: false },
	email: { enabled: false }
})
const isSending = ref(false)
const isDownloading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const messagePreview = ref('')

const hasEnabledChannels = computed(() => {
	return (
		sharingOptions.value.whatsapp?.enabled ||
		sharingOptions.value.sms?.enabled ||
		sharingOptions.value.email?.enabled
	)
})

const canSend = computed(() => {
	if (activeChannel.value === 'whatsapp' || activeChannel.value === 'sms') {
		return contactInfo.value.mobile && contactInfo.value.mobile.length >= 10
	} else if (activeChannel.value === 'email') {
		return contactInfo.value.email && contactInfo.value.email.includes('@')
	}
	return false
})

// Load sharing options when dialog opens
watch(show, async (newValue) => {
	if (newValue) {
		await loadSharingOptions()
		// Pre-fill contact info from customer
		contactInfo.value.mobile = props.customerMobile || ''
		contactInfo.value.email = props.customerEmail || ''
		
		// Reset messages
		errorMessage.value = ''
		successMessage.value = ''
		
		// Set active channel: use initialChannel if provided and enabled, otherwise first available
		if (props.initialChannel) {
			if (props.initialChannel === 'download' || sharingOptions.value[props.initialChannel]?.enabled) {
				activeChannel.value = props.initialChannel
			}
		} else if (sharingOptions.value.whatsapp?.enabled) {
			activeChannel.value = 'whatsapp'
		} else if (sharingOptions.value.sms?.enabled) {
			activeChannel.value = 'sms'
		} else if (sharingOptions.value.email?.enabled) {
			activeChannel.value = 'email'
		} else {
			// Default to download if no sharing channels enabled
			activeChannel.value = 'download'
		}
		
		// Load message preview (skip for download channel)
		if (activeChannel.value !== 'download') {
			await loadMessagePreview()
		}
	}
})

// Update preview when channel or template changes
watch([activeChannel, () => sharingOptions.value], async () => {
	if (show.value && activeChannel.value !== 'download') {
		await loadMessagePreview()
	}
}, { deep: true })

async function loadSharingOptions() {
	try {
		const options = await getSharingOptions(props.posProfile, props.invoiceName)
		console.log('Loaded sharing options:', options)
		sharingOptions.value = options || {
			whatsapp: { enabled: false },
			sms: { enabled: false },
			email: { enabled: false }
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
	} catch (error) {
		console.error('Failed to load sharing options:', error)
		sharingOptions.value = {
			whatsapp: { enabled: false },
			sms: { enabled: false },
			email: { enabled: false }
		}
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
		}

		if (result.success) {
			successMessage.value = result.message
			showSuccess(result.message)
			emit('shared', {
				channel: activeChannel.value,
				recipient: activeChannel.value === 'email' ? contactInfo.value.email : contactInfo.value.mobile
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

async function downloadPDF() {
	errorMessage.value = ''
	successMessage.value = ''
	isDownloading.value = true

	try {
		// Get print format from sharing options (returned by API) or use default
		const printFormat = sharingOptions.value.print_format || 'Standard'
		
		// Build download URL using Frappe's download_pdf endpoint
		const params = new URLSearchParams({
			doctype: 'Sales Invoice',
			name: props.invoiceName,
			format: printFormat,
			no_letterhead: 0
		})
		
		const downloadUrl = `/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`
		
		// Create a temporary link and trigger download
		const link = document.createElement('a')
		link.href = downloadUrl
		link.download = `${props.invoiceName}.pdf`
		link.style.display = 'none'
		document.body.appendChild(link)
		link.click()
		document.body.removeChild(link)
		
		// Show success message
		successMessage.value = __('PDF download started')
		showSuccess(__('Invoice PDF download started'))
		
		// Close dialog after 1 second
		setTimeout(() => {
			closeDialog()
		}, 1000)
	} catch (error) {
		errorMessage.value = error.message || __('Failed to download PDF')
		showError(errorMessage.value)
	} finally {
		isDownloading.value = false
	}
}

function closeDialog() {
	show.value = false
	// Reset state
	setTimeout(() => {
		errorMessage.value = ''
		successMessage.value = ''
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

