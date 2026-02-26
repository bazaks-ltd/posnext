<template>
	<Dialog v-model="show" :options="{ title: __('Edit Item Details'), size: 'md' }">
		<template #body-title>
			<span class="sr-only">{{ __('Edit item quantity, UOM, warehouse, and discount') }}</span>
		</template>
		<template #body-content>
			<div v-if="localItem" class="flex flex-col gap-4">
				<!-- Item Header -->
				<div class="flex items-center gap-3 pb-4 border-b border-gray-200">
					<!-- Item Image -->
					<div class="w-16 h-16 bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center overflow-hidden">
						<img
							v-if="localItem.image"
							:src="localItem.image"
							:alt="localItem.item_name"
							class="w-full h-full object-cover"
						/>
						<svg
							v-else
							class="h-8 w-8 text-gray-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
							/>
						</svg>
					</div>
				<!-- Item Info -->
				<div class="flex-1 min-w-0">
					<h3 class="text-base font-semibold text-gray-900 truncate">
						{{ localItem.item_name }}
					</h3>
				<p class="text-sm text-gray-500 truncate">
					{{ formatCurrency(localItem.price_list_rate || localItem.rate) }} / {{ localItem.stock_uom || __('Unit', null, 'UOM') }}
				</p>
				<!-- Show batch number(s) if item has batch -->
				<div v-if="localItem.has_batch_no" class="mt-1 flex items-center gap-1 flex-wrap">
					<!-- Multiple batches from bundle -->
					<span v-if="bundleBatches.length > 1" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
						<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>
						</svg>
						{{ __('Multiple Batches') }} ({{ bundleBatches.length }})
					</span>
					<!-- Single batch -->
					<span v-else-if="localItem.batch_no" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
						<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>
						</svg>
						{{ __('Batch') }}: {{ localItem.batch_no }}
					</span>
				</div>
			</div>
		</div>

				<!-- Two Column Layout for Quantity, UOM, Rate, Warehouse -->
				<div class="grid grid-cols-2 gap-4">
					<!-- Left Column: Quantity and Rate -->
					<div class="flex flex-col gap-4">
						<!-- Quantity Control -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-2 text-start">{{ __('Quantity') }}</label>
							<!-- For serial items, quantity is read-only (controlled by serial list) -->
							<div v-if="localItem?.has_serial_no && localSerials.length > 0" class="w-full h-10 border border-gray-300 rounded-lg bg-gray-50 flex items-center justify-center">
								<span class="text-sm font-semibold text-gray-600">{{ localSerials.length }}</span>
							</div>
							<!-- For non-serial items, show quantity controls -->
							<div v-else class="w-full h-10 border border-gray-300 rounded-lg bg-white flex items-center overflow-hidden">
								<button
									type="button"
									@click="decrementQuantity"
									class="w-[40px] h-[40px] min-w-[40px] bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-gray-700 font-bold text-lg transition-colors flex items-center justify-center border-e border-gray-300"
									style="flex: 0 0 40px;"
								>
									−
								</button>
								<div class="flex-1 h-full flex items-center justify-center px-3">
									<input
										v-model.number="localQuantity"
										type="number"
										min="0.0001"
										step="any"
										inputmode="decimal"
										class="w-full text-center border-0 text-sm font-semibold focus:outline-none focus:ring-0 bg-transparent"
										@input="handleQuantityInput"
										@blur="handleQuantityBlur"
										@keydown.enter="$event.target.blur()"
									/>
								</div>
								<button
									type="button"
									@click="incrementQuantity"
									class="w-[40px] h-[40px] min-w-[40px] bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-gray-700 font-bold text-lg transition-colors flex items-center justify-center border-s border-gray-300"
									style="flex: 0 0 40px;"
								>
									+
								</button>
							</div>
						</div>

						<!-- Rate -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-2 text-start">{{ __('Rate') }}</label>
							<div class="relative h-10">
								<span class="absolute inset-y-0 start-0 ps-3 flex items-center text-gray-500 text-sm font-medium">
									{{ currencySymbol }}
								</span>
								<input
									v-model.number="localRate"
									type="number"
									min="0"
									step="0.01"
									readonly
									class="w-full h-10 border border-gray-300 rounded-lg ps-16 pe-3 text-sm font-semibold bg-gray-50 cursor-not-allowed"
								/>
							</div>
						</div>
					</div>

					<!-- Right Column: UOM and Warehouse -->
					<div class="flex flex-col gap-4">
						<!-- UOM Selector -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-2 text-start">{{ __('UOM') }}</label>
							<select
								v-model="localUom"
								@change="handleUomChange"
								class="w-full h-10 border border-gray-300 rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
							>
								<option :value="localItem.stock_uom">{{ localItem.stock_uom }}</option>
								<option
									v-if="availableUoms.length > 0"
									v-for="uomData in availableUoms"
									:key="uomData.uom"
									:value="uomData.uom"
								>
									{{ uomData.uom }}
								</option>
							</select>
						</div>

						<!-- Warehouse Selector -->
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-2 text-start">{{ __('Warehouse') }}</label>
							<select
								v-model="localWarehouse"
								@change="handleWarehouseChange"
								class="w-full h-10 border border-gray-300 rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
							>
								<option
									v-if="warehouses.length > 0"
									v-for="warehouse in warehouses"
									:key="warehouse.name"
									:value="warehouse.name"
								>
									{{ warehouse.warehouse || warehouse.name }}
								</option>
								<option v-else :value="localWarehouse">
									{{ localWarehouse || __('Default') }}
								</option>
							</select>
						</div>
				</div>
			</div>

			<!-- Batch Number Section (only for batch items) -->
			<div v-if="localItem?.has_batch_no" class="border-t border-gray-200 pt-4">
				<div class="flex items-center justify-between mb-3">
					<label class="block text-sm font-medium text-gray-700 text-start">
						{{ __('Batch Management') }}
					</label>
					<button
						type="button"
						@click="showBatchManagement = true"
						class="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
					>
						{{ __('Manage Batches') }}
					</button>
				</div>
				
				<!-- Bundle Batches Display -->
				<div v-if="bundleBatches.length > 0" class="space-y-2">
					<div
						v-for="(batch, index) in bundleBatches"
						:key="index"
						class="p-3 bg-blue-50 border border-blue-200 rounded-lg"
					>
						<div class="flex items-start justify-between">
							<div class="flex-1">
								<h4 class="text-sm font-semibold text-gray-900">{{ batch.batch_no }}</h4>
								<div class="flex items-center gap-3 mt-1">
									<span class="text-xs text-gray-600">
										{{ __('Qty: {0}', [batch.qty]) }}
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Single Batch Display (legacy) -->
				<div v-else-if="localItem.batch_no" class="p-3 bg-blue-50 border border-blue-200 rounded-lg">
					<div class="flex items-start justify-between">
						<div class="flex-1">
							<h4 class="text-sm font-semibold text-gray-900">{{ localItem.batch_no }}</h4>
							<div class="flex items-center gap-3 mt-1">
								<span class="text-xs text-gray-600">
									{{ __('Qty: {0}', [localQuantity]) }}
								</span>
								<span v-if="currentBatchExpiry" class="text-xs text-gray-600">
									{{ __('Exp: {0}', [formatDate(currentBatchExpiry)]) }}
								</span>
							</div>
						</div>
					</div>
				</div>

				<!-- No batch selected -->
				<div v-else class="p-3 bg-gray-50 border border-gray-200 rounded-lg text-center">
					<p class="text-sm text-gray-500">{{ __('No batch selected') }}</p>
					<button
						type="button"
						@click="showBatchManagement = true"
						class="mt-2 text-xs font-medium text-blue-600 hover:text-blue-800"
					>
						{{ __('Select Batch') }}
					</button>
				</div>
			</div>

			<!-- Serial Numbers Section (only for serial items) -->
			<div v-if="localItem?.has_serial_no && localSerials.length > 0" class="border-t border-gray-200 pt-4">
					<div class="flex items-center justify-between mb-3">
						<label class="block text-sm font-medium text-gray-700 text-start">
							{{ __('Serial Numbers') }}
							<span class="ms-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
								{{ localSerials.length }}
							</span>
						</label>
					</div>
					<div class="flex flex-col gap-2 max-h-40 overflow-y-auto">
						<div
							v-for="(serial, index) in localSerials"
							:key="serial"
							class="flex items-center justify-between gap-2 p-2 bg-gray-50 rounded-lg"
						>
							<div class="flex items-center gap-2">
								<span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-medium">
									{{ index + 1 }}
								</span>
								<span class="text-sm font-medium text-gray-900">{{ serial }}</span>
							</div>
							<button
								type="button"
								@click="removeSerial(serial)"
								:disabled="localSerials.length <= 1"
								class="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
								:title="localSerials.length <= 1 ? __('Cannot remove last serial') : __('Remove serial')"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
								</svg>
							</button>
						</div>
					</div>
				</div>

				<!-- Item Discount Section (only if allowed by POS Profile) -->
				<div v-if="settingsStore.allowItemDiscount" class="border-t border-gray-200 pt-4">
					<label class="block text-sm font-medium text-gray-700 mb-3 text-start">{{ __('Item Discount') }}</label>
					<div class="grid grid-cols-2 gap-3">
						<!-- Discount Type -->
						<div>
							<label class="block text-xs text-gray-600 mb-1 text-start">{{ __('Discount Type') }}</label>
							<select
								v-model="discountType"
								@change="handleDiscountTypeChange"
								class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							>
								<option value="percentage">{{ __('Percentage (%)') }}</option>
								<option value="amount">{{ __('Amount') }}</option>
							</select>
						</div>
						<!-- Discount Value -->
						<div>
							<label class="block text-xs text-gray-600 mb-1 text-start">{{ discountType === 'percentage' ? __('Percentage') : __('Amount') }}</label>
							<div class="relative">
								<input
									v-model.number="discountValue"
									type="number"
									min="0"
									:max="discountType === 'percentage' ? 100 : undefined"
									step="0.01"
									class="w-full border border-gray-300 rounded-lg px-3 py-2 pe-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
									@input="calculateDiscount"
								/>
								<span class="absolute inset-y-0 end-0 pe-3 flex items-center text-gray-500 text-sm">
									{{ discountType === 'percentage' ? '%' : '' }}
								</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Totals -->
				<div class="bg-gray-50 rounded-lg p-4 flex flex-col gap-2">
					<div class="flex items-center justify-between text-sm">
						<span class="text-gray-600">{{ __('Subtotal:') }}</span>
						<span class="font-semibold text-gray-900">{{ formatCurrency(calculatedSubtotal) }}</span>
					</div>
					<div v-if="calculatedDiscount > 0" class="flex items-center justify-between text-sm text-red-600">
						<span>{{ __('Discount:') }}</span>
						<span class="font-semibold">-{{ formatCurrency(calculatedDiscount) }}</span>
					</div>
					<div class="flex items-center justify-between pt-2 border-t border-gray-200">
						<span class="text-base font-bold text-gray-900">{{ __('Total:') }}</span>
						<span class="text-lg font-bold text-blue-600">{{ formatCurrency(calculatedTotal) }}</span>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button variant="subtle" @click="cancel">{{ __('Cancel') }}</Button>
				<Button
					variant="solid"
					@click="updateItem"
					:disabled="!hasStock || isCheckingStock"
				>
					<span v-if="isCheckingStock">{{ __('Checking Stock...') }}</span>
					<span v-else-if="!hasStock">{{ __('No Stock Available') }}</span>
					<span v-else>{{ __('Update Item') }}</span>
				</Button>
			</div>
		</template>
	</Dialog>

	<!-- Batch Management Dialog -->
	<Dialog v-model="showBatchManagement" :options="{ title: __('Manage Batches'), size: 'lg' }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<!-- Header Info -->
				<div class="flex items-center gap-3 pb-3 border-b border-gray-200">
					<div class="w-12 h-12 bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center">
						<svg class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
						</svg>
					</div>
					<div class="flex-1">
						<h3 class="text-sm font-semibold text-gray-900">{{ localItem?.item_name }}</h3>
						<p class="text-xs text-gray-600">{{ __('Warehouse') }}: {{ localWarehouse }}</p>
					</div>
				</div>

				<!-- Loading State -->
				<div v-if="loadingBatches" class="flex items-center justify-center py-8">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
				</div>

				<!-- Batch Management List -->
				<div v-else-if="availableBatches.length > 0" class="space-y-2 max-h-96 overflow-y-auto">
					<div
						v-for="batch in availableBatches"
						:key="batch.batch_no"
						:class="[
							'border rounded-lg p-3 transition-all',
							getBatchQtyForManagement(batch.batch_no) > 0
								? 'border-blue-500 bg-blue-50'
								: 'border-gray-200'
						]"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="flex-1">
								<div class="flex items-center gap-2">
									<h4 class="text-sm font-semibold text-gray-900">{{ batch.batch_no }}</h4>
									<span
										v-if="getBatchQtyForManagement(batch.batch_no) > 0"
										class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
									>
										{{ __('Selected') }}
									</span>
								</div>
								<div class="flex items-center gap-4 mt-1">
									<span class="text-xs text-gray-600">
										{{ __('Available: {0}', [batch.qty]) }}
									</span>
									<span v-if="batch.expiry_date" class="text-xs font-medium" :class="isExpiringSoon(batch.expiry_date) ? 'text-orange-600' : 'text-gray-600'">
										{{ __('Expiry: {0}', [formatDate(batch.expiry_date)]) }}
									</span>
								</div>
							</div>
							<div class="flex items-center gap-2">
								<button
									type="button"
									@click="decrementBatchQtyManagement(batch)"
									:disabled="getBatchQtyForManagement(batch.batch_no) <= 0"
									class="w-7 h-7 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-bold rounded transition-colors flex items-center justify-center"
								>
									−
								</button>
								<input
									:value="getBatchQtyForManagement(batch.batch_no)"
									@input="(e) => updateBatchQtyManagement(batch, e.target.value)"
									@blur="() => validateBatchQtyManagement(batch)"
									type="number"
									min="0"
									:max="settingsStore.currentProfile?.allow_negative_stock ? null : batch.qty"
									step="any"
									:class="[
										'w-16 px-2 py-1 text-sm font-semibold text-center border rounded focus:outline-none focus:ring-2',
										isBatchQtyExceedingAvailable(batch, getBatchQtyForManagement(batch.batch_no))
											? 'border-red-500 bg-red-50 focus:ring-red-500'
											: 'border-gray-300 focus:ring-blue-500'
									]"
								/>
								<button
									type="button"
									@click="incrementBatchQtyManagement(batch)"
									:disabled="!settingsStore.currentProfile?.allow_negative_stock && getBatchQtyForManagement(batch.batch_no) >= batch.qty"
									class="w-7 h-7 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-bold rounded transition-colors flex items-center justify-center"
								>
									+
								</button>
							</div>
						</div>
						<!-- Warning if exceeds available qty -->
						<div v-if="isBatchQtyExceedingAvailable(batch, getBatchQtyForManagement(batch.batch_no))" class="mt-2 flex items-center gap-1 text-xs text-red-600">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
							</svg>
							<span>{{ __('Exceeds available quantity') }}</span>
						</div>
					</div>
				</div>

				<!-- No Batches Available -->
				<div v-else class="flex flex-col items-center justify-center py-8 text-center">
					<svg class="w-16 h-16 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
					</svg>
					<p class="text-sm font-medium text-gray-900">{{ __('No Batches Available') }}</p>
					<p class="text-xs text-gray-500 mt-1">{{ __('No stock available for this item in the selected warehouse') }}</p>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex gap-2">
				<Button variant="subtle" @click="showBatchManagement = false">{{ __('Cancel') }}</Button>
				<Button
					variant="solid"
					@click="confirmBatchManagement"
					:disabled="getTotalBatchQtyManagement() <= 0 || hasInvalidBatchQuantities"
				>
					{{ __('Confirm') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { useToast } from "@/composables/useToast"
import { usePOSSettingsStore } from "@/stores/posSettings"
import { useSerialNumberStore } from "@/stores/serialNumber"
import { usePOSCartStore } from "@/stores/posCart"
import { getItemStock } from "@/utils/stockValidator"
import { formatCurrency as formatCurrencyUtil, getCurrencySymbol } from "@/utils/currency"
import { Button, Dialog, call } from "frappe-ui"
import { computed, ref, watch } from "vue"

const { showSuccess, showError, showWarning } = useToast()
const settingsStore = usePOSSettingsStore()
const serialStore = useSerialNumberStore()
const cartStore = usePOSCartStore()

const props = defineProps({
	modelValue: Boolean,
	item: Object,
	warehouses: {
		type: Array,
		default: () => [],
	},
	currency: {
		type: String,
		default: "EGP",
	},
})

const emit = defineEmits(["update:modelValue", "update-item"])

// Local state
const localItem = ref(null)
const localQuantity = ref(1)
const localUom = ref("")
const localRate = ref(0)
const localWarehouse = ref("")
const discountType = ref("percentage")
const discountValue = ref(0)
const calculatedSubtotal = ref(0)
const calculatedDiscount = ref(0)
const calculatedTotal = ref(0)
const hasStock = ref(true)
const isCheckingStock = ref(false)
const localSerials = ref([]) // List of serial numbers for this item
const removedSerials = ref([]) // Track serials removed during this edit session
const originalSerials = ref([]) // Original serials when dialog opened

// Batch handling
const showBatchManagement = ref(false)
const availableBatches = ref([])
const loadingBatches = ref(false)
const batchQtys = ref(new Map()) // Map of batch_no -> qty for management
const currentBatchExpiry = ref(null)
const bundleBatches = ref([]) // Batches from the bundle

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
})

const availableUoms = computed(() => {
	if (!localItem.value || !localItem.value.item_uoms) return []
	return localItem.value.item_uoms.filter(
		(u) => u.uom !== localItem.value.stock_uom,
	)
})

const currencySymbol = computed(() => getCurrencySymbol(props.currency))

// Initialize local state when item changes
watch(
	() => props.item,
	(newItem) => {
		if (newItem) {
			localItem.value = { ...newItem }
			localQuantity.value = newItem.quantity || 1
			localUom.value = newItem.uom || newItem.stock_uom || __("Unit")
			localRate.value = newItem.rate || 0
			localWarehouse.value =
				newItem.warehouse || props.warehouses[0]?.name || ""

			// Initialize serial numbers
			if (newItem.has_serial_no && newItem.serial_no) {
				const serials = newItem.serial_no.split('\n').filter(s => s.trim())
				localSerials.value = [...serials]
				originalSerials.value = [...serials] // Keep original for cancel
				removedSerials.value = [] // Reset removed serials tracker
				// For serial items, quantity must match serial count
				localQuantity.value = serials.length
			} else {
				localSerials.value = []
				originalSerials.value = []
				removedSerials.value = []
			}

		// Initialize batch numbers and bundle
		bundleBatches.value = []
		if (newItem.has_batch_no) {
			console.log("Initializing batch data:", {
				has_bundle_data: !!newItem._bundle_data,
				bundle_data: newItem._bundle_data,
				batch_no: newItem.batch_no,
				serial_and_batch_bundle: newItem.serial_and_batch_bundle
			})
			
			// Check if item has bundle data
			if (newItem._bundle_data && newItem._bundle_data.entries) {
				bundleBatches.value = newItem._bundle_data.entries.map(entry => ({
					batch_no: entry.batch_no,
					qty: entry.qty
				}))
				console.log("Initialized bundleBatches:", bundleBatches.value)
			} else if (newItem.batch_no) {
				// Single batch (legacy)
				loadBatchExpiry(newItem.batch_no)
			}
		} else {
			currentBatchExpiry.value = null
		}

			// Initialize discount - check amount first since it's more specific
			if (newItem.discount_amount && newItem.discount_amount > 0) {
				discountType.value = "amount"
				discountValue.value = newItem.discount_amount
			} else if (newItem.discount_percentage && newItem.discount_percentage > 0) {
				discountType.value = "percentage"
				discountValue.value = newItem.discount_percentage
			} else {
				discountType.value = "percentage"
				discountValue.value = 0
			}

			// Reset stock check state
			hasStock.value = true
			isCheckingStock.value = false

			calculateTotals()
		}
	},
	{ immediate: true },
)

/**
 * Intelligently determine the step size based on current quantity
 * - Whole numbers (1, 2, 3): step by 1
 * - Multiples of 0.5 (1.5, 2.5): step by 0.5
 * - Multiples of 0.25 (0.25, 0.75): step by 0.25
 * - Multiples of 0.1 (0.1, 0.3): step by 0.1
 * - Other decimals: step by 0.01
 */
function getSmartStep(quantity) {
	// Check if it's a whole number
	if (quantity === Math.floor(quantity)) {
		return 1
	}

	// Round to 4 decimal places to avoid floating point errors
	const rounded = Math.round(quantity * 10000) / 10000

	// Check if it's a multiple of 0.5
	if (Math.abs((rounded % 0.5)) < 0.0001) {
		return 0.5
	}

	// Check if it's a multiple of 0.25
	if (Math.abs((rounded % 0.25)) < 0.0001) {
		return 0.25
	}

	// Check if it's a multiple of 0.1
	if (Math.abs((rounded % 0.1)) < 0.0001) {
		return 0.1
	}

	// For other decimals, use 0.01 for fine control
	return 0.01
}

function incrementQuantity() {
	const step = getSmartStep(localQuantity.value)
	localQuantity.value = Math.round((localQuantity.value + step) * 10000) / 10000
	calculateTotals()
}

function decrementQuantity() {
	const step = getSmartStep(localQuantity.value)
	const newQty = Math.round((localQuantity.value - step) * 10000) / 10000

	if (newQty > 0) {
		localQuantity.value = newQty
		calculateTotals()
	}
}

function handleQuantityInput() {
	// Allow any value during typing, just recalculate totals
	// Don't validate or reset - let user type freely
	if (localQuantity.value > 0 && !isNaN(localQuantity.value)) {
		calculateTotals()
	}
}

function handleQuantityBlur() {
	// Validate and fix the quantity when user is done editing (leaves the field)
	if (!localQuantity.value || localQuantity.value <= 0 || isNaN(localQuantity.value)) {
		// If invalid, reset to 1
		localQuantity.value = 1
	} else {
		// Round to 4 decimal places for consistency
		localQuantity.value = Math.round(localQuantity.value * 10000) / 10000
	}
	calculateTotals()
}

function handleUomChange() {
	// When UOM changes, we need to fetch new rate from server
	// For now, we'll just recalculate with current rate
	calculateTotals()
}

async function handleWarehouseChange() {
	if (!localItem.value || !localWarehouse.value) return

	isCheckingStock.value = true
	try {
		// Check stock availability in the new warehouse
		const availableStock = await getItemStock(
			localItem.value.item_code,
			localWarehouse.value,
		)

		if (availableStock === 0) {
			hasStock.value = false
			showError(
				__('"{0}" is not available in warehouse "{1}". Please select another warehouse.', 
				[localItem.value.item_name, localWarehouse.value])
			)
		} else if (availableStock < localQuantity.value) {
			hasStock.value = false
			showWarning(
				__('Only {0} units of "{1}" available in "{2}". Current quantity: {3}', [
					availableStock,
					localItem.value.item_name,
					localWarehouse.value,
					localQuantity.value
				])
			)
		} else {
			hasStock.value = true
			showSuccess(
				__('{0} units available in "{1}"', [availableStock, localWarehouse.value])
			)
		}
	} catch (error) {
		console.error("Error checking warehouse stock:", error)
		hasStock.value = true // Allow update if stock check fails
	} finally {
		isCheckingStock.value = false
	}
}

function handleDiscountTypeChange() {
	// Reset discount value when type changes
	discountValue.value = 0
	calculateTotals()
}

function calculateDiscount() {
	if (discountType.value === "percentage") {
		// Ensure percentage doesn't exceed 100
		if (discountValue.value > 100) {
			discountValue.value = 100
		}
		calculatedDiscount.value =
			(calculatedSubtotal.value * discountValue.value) / 100
	} else {
		// Ensure amount doesn't exceed subtotal
		if (discountValue.value > calculatedSubtotal.value) {
			discountValue.value = calculatedSubtotal.value
		}
		calculatedDiscount.value = discountValue.value
	}
	calculatedTotal.value = calculatedSubtotal.value - calculatedDiscount.value
}

function calculateTotals() {
	calculatedSubtotal.value = localRate.value * localQuantity.value
	calculateDiscount()
}

function removeSerial(serialNo) {
	// Remove from local list
	const index = localSerials.value.indexOf(serialNo)
	if (index > -1) {
		localSerials.value.splice(index, 1)
		// Track removed serial (will be returned to cache on confirm)
		removedSerials.value.push(serialNo)
		// Update quantity to match serial count
		localQuantity.value = localSerials.value.length
		calculateTotals()
	}
}

function formatCurrency(amount) {
	return formatCurrencyUtil(Number.parseFloat(amount || 0), props.currency)
}

async function updateItem() {
	const updatedItem = {
		...localItem.value,
		quantity: localQuantity.value,
		uom: localUom.value,
		rate: localRate.value,
		warehouse: localWarehouse.value,
		discount_percentage:
			discountType.value === "percentage" ? discountValue.value : 0,
		discount_amount:
			discountType.value === "amount" ? discountValue.value : 0,
	}

	// Update serial numbers if item has serials
	if (localItem.value.has_serial_no) {
		updatedItem.serial_no = localSerials.value.join('\n')
		updatedItem.quantity = localSerials.value.length

		// Return removed serials to cache now that update is confirmed
		if (removedSerials.value.length > 0) {
			serialStore.returnSerials(localItem.value.item_code, removedSerials.value)
		}
	}

	// Update bundle if we have a bundle and batches have changed
	if (localItem.value.has_batch_no && localItem.value.serial_and_batch_bundle && bundleBatches.value.length > 0) {
		const oldTotalQty = bundleBatches.value.reduce((sum, b) => sum + b.qty, 0)
		const newTotalQty = localQuantity.value
		
		// Always update bundle to ensure it matches current batch distribution
		// If quantity changed, update bundle batches proportionally
		let batchesToUpdate = bundleBatches.value
		if (oldTotalQty !== newTotalQty && oldTotalQty > 0) {
			const ratio = newTotalQty / oldTotalQty
			batchesToUpdate = bundleBatches.value.map(b => ({
				batch_no: b.batch_no,
				qty: Math.round(b.qty * ratio * 100) / 100 // Round to 2 decimals
			}))
			
			// Ensure total matches (adjust last batch if needed)
			const calculatedTotal = batchesToUpdate.reduce((sum, b) => sum + b.qty, 0)
			if (calculatedTotal !== newTotalQty && batchesToUpdate.length > 0) {
				const diff = newTotalQty - calculatedTotal
				batchesToUpdate[batchesToUpdate.length - 1].qty += diff
			}
		}
		
		// Update bundle in backend
		try {
			await call("pos_next.api.serial_batch_bundle.update_batch_bundle", {
				bundle_name: localItem.value.serial_and_batch_bundle,
				item_code: localItem.value.item_code,
				warehouse: localWarehouse.value,
				batches: JSON.stringify(batchesToUpdate),
				type_of_transaction: "Outward"
			})
			
			// Update local bundle batches
			bundleBatches.value = batchesToUpdate
			
			// Update local item with new bundle data
			localItem.value._bundle_data = {
				entries: batchesToUpdate
			}
		} catch (error) {
			console.error("Error updating batch bundle:", error)
			showError(__("Failed to update batch bundle: {0}", [error.message || error]))
			return // Don't proceed with update if bundle update failed
		}
		
		// Include bundle reference and updated data
		updatedItem.serial_and_batch_bundle = localItem.value.serial_and_batch_bundle
		updatedItem._bundle_data = {
			entries: batchesToUpdate
		}
	} else if (localItem.value.serial_and_batch_bundle) {
		// Just include bundle reference if no batches to update
		updatedItem.serial_and_batch_bundle = localItem.value.serial_and_batch_bundle
		if (bundleBatches.value.length > 0) {
			updatedItem._bundle_data = {
				entries: bundleBatches.value
			}
		}
	}

	emit("update-item", updatedItem)
	show.value = false
}

function cancel() {
	show.value = false
}

// Batch handling functions
async function loadBatchExpiry(batchNo) {
	if (!batchNo) return
	
	try {
		// Use frappe-ui's call function
		const response = await call("frappe.client.get_value", {
			doctype: "Batch",
			filters: { name: batchNo },
			fieldname: ["expiry_date"]
		})
		
		if (response && response.expiry_date) {
			currentBatchExpiry.value = response.expiry_date
		}
	} catch (error) {
		console.error("Error loading batch expiry:", error)
	}
}

async function loadAvailableBatches() {
	if (!localItem.value || !localWarehouse.value) {
		console.error("Missing item or warehouse", { item: localItem.value, warehouse: localWarehouse.value })
		return
	}
	
	loadingBatches.value = true
	availableBatches.value = []
	
	try {
		console.log("Loading batches for", localItem.value.item_code, "in warehouse", localWarehouse.value)
		
		// Use frappe-ui's call function
		const batches = await call("erpnext.stock.doctype.batch.batch.get_batch_qty", {
			item_code: localItem.value.item_code,
			warehouse: localWarehouse.value
		})
		
		console.log("Batch response:", batches)
		
		if (batches && Array.isArray(batches)) {
			// Fetch expiry dates for each batch
			const batchesWithExpiry = []
			for (const batch of batches) {
				if (batch.qty > 0 && batch.batch_no) {
					try {
						const batchDoc = await call("frappe.client.get_value", {
							doctype: "Batch",
							filters: { name: batch.batch_no },
							fieldname: ["expiry_date", "disabled"]
						})
						
						if (batchDoc) {
							const isNotExpired = !batchDoc.expiry_date || new Date(batchDoc.expiry_date) > new Date()
							const isEnabled = batchDoc.disabled === 0 || batchDoc.disabled === undefined
							
							if (isNotExpired && isEnabled) {
								batchesWithExpiry.push({
									batch_no: batch.batch_no,
									qty: batch.qty,
									expiry_date: batchDoc.expiry_date
								})
							}
						}
					} catch (error) {
						console.error(`Error fetching batch ${batch.batch_no}:`, error)
						// Still add batch even if we can't get expiry
						batchesWithExpiry.push({
							batch_no: batch.batch_no,
							qty: batch.qty,
							expiry_date: null
						})
					}
				}
			}
			
			// Sort by expiry date
			batchesWithExpiry.sort((a, b) => {
				if (a.expiry_date && b.expiry_date) {
					return new Date(a.expiry_date) - new Date(b.expiry_date)
				}
				if (a.expiry_date) return -1
				if (b.expiry_date) return 1
				return 0
			})
			
			availableBatches.value = batchesWithExpiry
			console.log("Loaded batches:", batchesWithExpiry)
		} else {
			console.warn("No batches found or invalid response")
		}
	} catch (error) {
		console.error("Error loading batches:", error)
		showError(__("Failed to load batches: {0}", [error.message || error]))
	} finally {
		loadingBatches.value = false
	}
}

// Batch management functions
function getBatchQtyForManagement(batchNo) {
	return batchQtys.value.get(batchNo) || 0
}

function isBatchQtyExceedingAvailable(batch, qty) {
	const allowNegativeStock = settingsStore.currentProfile?.allow_negative_stock || false
	if (allowNegativeStock) {
		return false // No validation if negative stock is allowed
	}
	return qty > batch.qty
}

function updateBatchQtyManagement(batch, value) {
	const qty = parseFloat(value) || 0
	if (qty <= 0) {
		batchQtys.value.delete(batch.batch_no)
	} else {
		// Allow invalid quantities to be stored temporarily so error message can show
		batchQtys.value.set(batch.batch_no, qty)
	}
}

function validateBatchQtyManagement(batch) {
	const currentQty = getBatchQtyForManagement(batch.batch_no)
	const allowNegativeStock = settingsStore.currentProfile?.allow_negative_stock || false
	if (!allowNegativeStock && currentQty > batch.qty) {
		// Auto-correct to max available when input loses focus
		batchQtys.value.set(batch.batch_no, batch.qty)
	}
}

function incrementBatchQtyManagement(batch) {
	const currentQty = getBatchQtyForManagement(batch.batch_no)
	const allowNegativeStock = settingsStore.currentProfile?.allow_negative_stock || false
	const maxQty = allowNegativeStock ? Infinity : batch.qty
	
	if (currentQty < maxQty) {
		updateBatchQtyManagement(batch, currentQty + 1)
	}
	// Inline error message will be shown automatically if quantity exceeds available stock
}

function decrementBatchQtyManagement(batch) {
	const currentQty = getBatchQtyForManagement(batch.batch_no)
	if (currentQty > 0) {
		updateBatchQtyManagement(batch, currentQty - 1)
	}
}

function getTotalBatchQtyManagement() {
	let total = 0
	for (const qty of batchQtys.value.values()) {
		total += qty || 0
	}
	return total
}

// Check if any batch quantity exceeds available stock
const hasInvalidBatchQuantities = computed(() => {
	const allowNegativeStock = settingsStore.currentProfile?.allow_negative_stock || false
	if (allowNegativeStock) {
		return false // No validation if negative stock is allowed
	}
	
	for (const [batchNo, qty] of batchQtys.value.entries()) {
		if (qty > 0) {
			const batch = availableBatches.value.find(b => b.batch_no === batchNo)
			if (batch && qty > batch.qty) {
				return true
			}
		}
	}
	return false
})

async function confirmBatchManagement() {
	// Validate all batch quantities before confirming
	// Note: Invalid quantities are already prevented by disabled Confirm button and inline error messages
	// This is an additional safety check
	const allowNegativeStock = settingsStore.currentProfile?.allow_negative_stock || false
	if (!allowNegativeStock && hasInvalidBatchQuantities.value) {
		return // Don't proceed if validation fails (user should see inline error messages)
	}
	
	const selectedBatches = []
	for (const [batchNo, qty] of batchQtys.value.entries()) {
		if (qty > 0) {
			selectedBatches.push({ batch_no: batchNo, qty })
		}
	}

	if (selectedBatches.length > 0) {
		// Calculate total quantity
		const totalQty = selectedBatches.reduce((sum, b) => sum + b.qty, 0)
		localQuantity.value = totalQty
		
		// Update bundle batches for display
		bundleBatches.value = selectedBatches.map(b => ({
			batch_no: b.batch_no,
			qty: b.qty
		}))
		
		// Update or create bundle
		try {
			if (localItem.value.serial_and_batch_bundle) {
				// Update existing bundle
				await call("pos_next.api.serial_batch_bundle.update_batch_bundle", {
					bundle_name: localItem.value.serial_and_batch_bundle,
					item_code: localItem.value.item_code,
					warehouse: localWarehouse.value,
					batches: JSON.stringify(selectedBatches),
					type_of_transaction: "Outward"
				})
				
				// Update local item with new bundle data
				localItem.value._bundle_data = {
					entries: selectedBatches
				}
			} else {
				// Create new bundle
				const response = await call("pos_next.api.serial_batch_bundle.create_batch_bundle", {
					item_code: localItem.value.item_code,
					warehouse: localWarehouse.value,
					batches: JSON.stringify(selectedBatches),
					type_of_transaction: "Outward"
				})
				
				if (response && response.success) {
					localItem.value.serial_and_batch_bundle = response.bundle_name
					localItem.value._bundle_data = response.bundle_data || {
						entries: selectedBatches
					}
				}
			}
			
			// Set first batch as primary for display
			localItem.value.batch_no = selectedBatches[0].batch_no
			
			// Immediately update the cart item with the new bundle data
			// This ensures the changes persist even if user closes dialog without clicking "Update Item"
			await cartStore.updateItemDetails(localItem.value.item_code, {
				quantity: totalQty,
				serial_and_batch_bundle: localItem.value.serial_and_batch_bundle,
				_bundle_data: {
					entries: selectedBatches
				},
				batch_no: selectedBatches[0].batch_no
			})
		} catch (error) {
			console.error("Error updating batch bundle:", error)
			showError(__("Failed to update batch bundle: {0}", [error.message || error]))
			return // Don't close dialog if update failed
		}
		
		showBatchManagement.value = false
		calculateTotals()
	}
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const date = new Date(dateStr)
	return date.toLocaleDateString()
}

function isExpiringSoon(dateStr) {
	if (!dateStr) return false
	const expiryDate = new Date(dateStr)
	const today = new Date()
	const daysUntilExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24))
	return daysUntilExpiry <= 30 && daysUntilExpiry > 0 // Warning if expiring within 30 days
}

// Watch for batch management dialog open
watch(showBatchManagement, (newVal) => {
	if (newVal) {
		// Initialize with current bundle batches or single batch
		batchQtys.value.clear()
		if (bundleBatches.value.length > 0) {
			// Initialize from bundle
			for (const batch of bundleBatches.value) {
				batchQtys.value.set(batch.batch_no, batch.qty)
			}
		} else if (localItem.value?.batch_no && localQuantity.value > 0) {
			// Initialize from single batch
			batchQtys.value.set(localItem.value.batch_no, localQuantity.value)
		}
		loadAvailableBatches()
	}
})
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

/* Hide number input spinners */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
	-webkit-appearance: none;
	margin: 0;
}

input[type="number"] {
	-moz-appearance: textfield;
}
</style>
