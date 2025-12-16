<template>
	<Dialog
		v-model="show"
		:options="{ title: __('Invoice Details'), size: '5xl' }"
	>
		<template #body-content>
			<div v-if="loading" class="text-center py-12">
				<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto"></div>
				<p class="mt-3 text-sm text-gray-500">{{ __('Loading invoice details...') }}</p>
			</div>

			<div v-else-if="invoiceData" class="flex flex-col gap-6">
				<!-- Invoice Header -->
				<div class="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg p-4 md:p-5 border border-indigo-100">
					<div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
						<div class="flex-1">
							<div class="flex items-center gap-3 mb-2 flex-wrap">
								<h3 class="text-lg md:text-xl font-bold text-gray-900">{{ invoiceData.name }}</h3>
								<span
									v-if="invoiceData.is_return"
									class="px-3 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800"
								>
									{{ __('Return Invoice') }}
								</span>
								<span
									v-else
									:class="[
										'px-3 py-1 text-xs font-semibold rounded-full',
										getInvoiceStatusColor(invoiceData)
									]"
								>
									{{ __(invoiceData.status) }}
								</span>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
								<div class="text-start">
									<span class="text-gray-600">{{ __('Customer:') }}</span>
									<span class="ms-2 font-semibold text-gray-900">{{ invoiceData.customer_name || invoiceData.customer }}</span>
								</div>
								<div class="text-start">
									<span class="text-gray-600">{{ __('Date:') }}</span>
									<span class="ms-2 font-medium text-gray-900">{{ formatDate(invoiceData.posting_date) }} {{ formatTime(invoiceData.posting_time) }}</span>
								</div>
								<div v-if="invoiceData.return_against" class="text-start">
									<span class="text-gray-600">{{ __('Return Against:') }}</span>
									<span class="ms-2 font-medium text-gray-900">{{ invoiceData.return_against }}</span>
								</div>
							</div>
						</div>
						<div class="text-start sm:text-end">
							<div class="text-xs text-gray-500 mb-1">{{ __('Grand Total') }}</div>
							<div class="text-xl md:text-2xl font-bold text-indigo-600">
								{{ formatCurrency(invoiceData.grand_total) }}
							</div>
						</div>
					</div>
				</div>

				<!-- Items Section -->
				<div>
					<h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center">
						<svg class="w-4 h-4 me-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
						</svg>
						{{ __('Items') }}
					</h4>
					<!-- Mobile Cards View -->
					<div class="md:hidden flex flex-col gap-3">
						<div
							v-for="(item, idx) in invoiceData.items"
							:key="idx"
							class="bg-white border border-gray-200 rounded-lg p-3"
						>
							<!-- Item Name & Amount Row -->
							<div class="flex items-center justify-between gap-3 mb-2">
								<div class="flex-1 min-w-0 text-center">
									<div class="text-sm font-semibold text-gray-900">{{ item.item_name }}</div>
									<div class="text-xs text-gray-500">{{ item.item_code }}</div>
								</div>
							</div>
							<!-- Details Grid -->
							<div class="grid grid-cols-3 gap-2 text-center border-t border-gray-100 pt-2">
								<div>
									<div class="text-xs text-gray-500">{{ __('Qty') }}</div>
									<div class="text-sm font-medium text-gray-900">{{ item.quantity }}</div>
								</div>
								<div>
									<div class="text-xs text-gray-500">{{ __('Rate') }}</div>
									<div class="text-sm font-medium text-gray-900">{{ formatCurrency(item.rate) }}</div>
								</div>
								<div>
									<div class="text-xs text-gray-500">{{ __('Amount') }}</div>
									<div class="text-sm font-semibold text-gray-900">{{ formatCurrency(item.amount) }}</div>
								</div>
							</div>
							<!-- Discount Row (if applicable) -->
							<div v-if="item.discount_percentage" class="text-center text-xs text-orange-600 mt-2 pt-2 border-t border-gray-100">
								{{ __('Discount:') }} {{ item.discount_percentage }}%
							</div>
						</div>
					</div>
					<!-- Desktop Table View -->
					<div class="hidden md:block border border-gray-200 rounded-lg overflow-hidden">
						<table class="min-w-full divide-y divide-gray-200">
							<thead class="bg-gray-50">
								<tr>
									<th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ __('Item') }}</th>
									<th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ __('Qty') }}</th>
									<th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ __('Rate') }}</th>
									<th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ __('Discount') }}</th>
									<th class="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ __('Amount') }}</th>
								</tr>
							</thead>
							<tbody class="bg-white divide-y divide-gray-200">
								<tr v-for="(item, idx) in invoiceData.items" :key="idx" class="hover:bg-gray-50">
									<td class="px-4 py-3 text-center">
										<div class="text-sm font-medium text-gray-900">{{ item.item_name }}</div>
										<div class="text-xs text-gray-500">{{ item.item_code }}</div>
									</td>
									<td class="px-4 py-3 text-center text-sm text-gray-900">{{ item.quantity }}</td>
									<td class="px-4 py-3 text-center text-sm text-gray-900">{{ formatCurrency(item.rate) }}</td>
									<td class="px-4 py-3 text-center text-sm text-gray-600">
										{{ item.discount_percentage ? `${item.discount_percentage}%` : '-' }}
									</td>
									<td class="px-4 py-3 text-center text-sm font-semibold text-gray-900">{{ formatCurrency(item.amount) }}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>

				<!-- Totals Section -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
					<!-- Payment Info -->
					<div v-if="invoiceData.payments && invoiceData.payments.length > 0">
						<h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center">
							<svg class="w-4 h-4 me-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>
							</svg>
							{{ __('Payments') }}
						</h4>
						<div class="flex flex-col gap-2">
							<div
								v-for="(payment, idx) in invoiceData.payments"
								:key="idx"
								class="flex justify-between items-center p-3 bg-green-50 border border-green-200 rounded-lg"
							>
								<div class="text-start">
									<div class="text-sm font-medium text-gray-900">{{ payment.mode_of_payment }}</div>
									<div v-if="payment.account" class="text-xs text-gray-500">{{ payment.account }}</div>
								</div>
								<div class="text-sm font-semibold text-green-700">{{ formatCurrency(payment.amount) }}</div>
							</div>
						</div>
					</div>

					<!-- Summary -->
					<div>
						<h4 class="text-sm font-semibold text-gray-700 mb-3 text-start">{{ __('Summary') }}</h4>
						<div class="flex flex-col gap-2 bg-gray-50 p-4 rounded-lg border border-gray-200">
							<div class="flex justify-between text-sm">
								<span class="text-gray-600">{{ __('Net Total:') }}</span>
								<span class="font-medium text-gray-900">{{ formatCurrency(invoiceData.net_total || invoiceData.total) }}</span>
							</div>
							<div v-if="invoiceData.total_taxes_and_charges" class="flex justify-between text-sm">
								<span class="text-gray-600">{{ __('Taxes:') }}</span>
								<span class="font-medium text-gray-900">{{ formatCurrency(invoiceData.total_taxes_and_charges) }}</span>
							</div>
							<div v-if="invoiceData.discount_amount" class="flex justify-between text-sm">
								<span class="text-gray-600">{{ __('Discount:') }}</span>
								<span class="font-medium text-red-600">-{{ formatCurrency(invoiceData.discount_amount) }}</span>
							</div>
							<div class="pt-2 border-t border-gray-300 flex justify-between">
								<span class="font-semibold text-gray-900">{{ __('Grand Total:') }}</span>
								<span class="font-bold text-lg text-indigo-600">{{ formatCurrency(invoiceData.grand_total) }}</span>
							</div>
							<div v-if="invoiceData.paid_amount" class="flex justify-between text-sm">
								<span class="text-gray-600">{{ __('Paid Amount:') }}</span>
								<span class="font-semibold text-green-600">{{ formatCurrency(invoiceData.paid_amount) }}</span>
							</div>
							<div v-if="invoiceData.outstanding_amount" class="flex justify-between text-sm">
								<span class="text-gray-600">{{ __('Outstanding:') }}</span>
								<span class="font-semibold text-orange-600">{{ formatCurrency(invoiceData.outstanding_amount) }}</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Additional Info -->
				<div v-if="invoiceData.remarks" class="bg-gray-50 p-4 rounded-lg border border-gray-200">
					<h4 class="text-sm font-semibold text-gray-700 mb-2 text-start">{{ __('Remarks') }}</h4>
					<p class="text-sm text-gray-600 text-start">{{ invoiceData.remarks }}</p>
				</div>
			</div>

			<div v-else class="text-center py-12">
				<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
				</svg>
				<p class="mt-2 text-sm text-gray-500">{{ __('Failed to load invoice details') }}</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-between items-center w-full">
				<Button variant="subtle" @click="show = false">
					{{ __('Close') }}
				</Button>
				<Button @click="handlePrint">
					<template #prefix>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
						</svg>
					</template>
					{{ __('Print') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { useFormatters } from "@/composables/useFormatters"
import { formatCurrency as formatCurrencyUtil } from "@/utils/currency"
import { getInvoiceStatusColor } from "@/utils/invoice"
import { logger } from "@/utils/logger"
import { printInvoiceByName } from "@/utils/printInvoice"
import { useToast } from "@/composables/useToast"
import { Button, Dialog, call } from "frappe-ui"
import { ref, watch, nextTick } from "vue"

const log = logger.create('InvoiceDetailDialog')
const { formatDate, formatTime } = useFormatters()
const { showSuccess, showError } = useToast()

const props = defineProps({
	modelValue: Boolean,
	invoiceName: String,
	posProfile: String,
	currency: {
		type: String,
		default: "USD",
	},
})

function formatCurrency(amount) {
	return formatCurrencyUtil(Number.parseFloat(amount || 0), props.currency)
}

const emit = defineEmits(["update:modelValue"])

const show = ref(props.modelValue)
const loading = ref(false)
const invoiceData = ref(null)

watch(
	() => props.modelValue,
	(val) => {
		show.value = val
		if (val && props.invoiceName) {
			loadInvoiceDetails()
		}
	},
)

watch(show, async (val) => {
	emit("update:modelValue", val)
	if (!val) {
		// Clear data when closing
		invoiceData.value = null
	} else {
		// Ensure dialog appears above other dialogs
		await nextTick()
		const dialogs = document.querySelectorAll('.modal-container, .modal-backdrop')
		dialogs.forEach(dialog => {
			const title = dialog.querySelector('[class*="title"]')
			if (title && title.textContent?.includes('Invoice Details')) {
				dialog.style.zIndex = '400'
			}
		})
	}
})

async function loadInvoiceDetails() {
	if (!props.invoiceName) return

	loading.value = true
	try {
		const result = await call("pos_next.api.invoices.get_invoice", {
			invoice_name: props.invoiceName,
		})

		// Map server 'qty' to 'quantity' for internal consistency
		if (result && result.items) {
			result.items = result.items.map((item) => ({
				...item,
				quantity: item.qty,
			}))
		}
		invoiceData.value = result
	} catch (error) {
		log.error("Error loading invoice details:", error)
		invoiceData.value = null
	} finally {
		loading.value = false
	}
}

async function handlePrint() {
	if (!props.invoiceName) return
	
	try {
		// printInvoiceByName will automatically fetch the print format from the invoice's POS Profile
		await printInvoiceByName(props.invoiceName)
		showSuccess(__('Invoice sent to printer'))
	} catch (error) {
		log.error("Error printing invoice:", error)
		showError(error.message || __('Failed to print invoice'))
	}
}
</script>

