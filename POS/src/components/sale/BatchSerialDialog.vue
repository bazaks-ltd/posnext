<template>
	<Dialog
		v-model="show"
		:options="{ title: item?.has_batch_no ? __('Select Batch Numbers') : __('Select Serial Numbers'), size: 'lg' }"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<!-- Item Info -->
				<div v-if="item" class="bg-blue-50 rounded-lg p-3">
					<div class="flex items-center gap-3">
						<div class="w-12 h-12 bg-gray-100 rounded-md flex-shrink-0 flex items-center justify-center overflow-hidden">
							<img
								v-if="item.image"
								:src="item.image"
								:alt="item.item_name"
								loading="lazy"
								class="w-full h-full object-cover"
							/>
							<svg v-else class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
							</svg>
						</div>
				<div class="flex-1">
					<h3 class="text-sm font-semibold text-gray-900">{{ item.item_name }}</h3>
					<p class="text-xs text-gray-600">{{ item.item_code }}</p>
				</div>
			<!-- Show quantity info for batch items only -->
			<div v-if="item?.has_batch_no" class="text-end">
				<div class="flex items-center gap-2 justify-end">
					<label class="text-xs text-gray-600">{{ __('Requested') }}:</label>
					<input
						v-model.number="localQuantity"
						type="number"
						min="0.0001"
						step="any"
						class="w-16 px-2 py-1 text-sm font-semibold text-gray-900 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
						@input="handleQuantityChange"
					/>
					<button
						type="button"
						@click="autoDistribute"
						class="px-2 py-1 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors"
						:disabled="!localQuantity || localQuantity <= 0"
						:title="__('Auto-distribute quantity based on expiry dates (FIFO)')"
					>
						{{ __('Auto') }}
					</button>
				</div>
				<p v-if="totalAvailableQty > 0" class="text-xs text-green-600 mt-1">
					{{ __('Available') }}: <span class="font-semibold">{{ totalAvailableQty }}</span>
				</p>
				<p v-if="totalSelectedQty > 0" class="text-xs text-blue-600 mt-1">
					{{ __('Selected') }}: <span class="font-semibold">{{ totalSelectedQty }}</span>
				</p>
			</div>
		</div>
		</div>

			<!-- Quantity Warning for Batches -->
			<div v-if="item?.has_batch_no && localQuantity > totalAvailableQty && !allowNegativeStock" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
				<div class="flex items-start gap-2">
					<svg class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
					</svg>
					<div class="flex-1">
						<p class="text-sm font-medium text-red-800">{{ __('Insufficient Stock') }}</p>
						<p class="text-xs text-red-600 mt-1">
							{{ __('Requested quantity ({0}) exceeds available stock ({1})', [localQuantity, totalAvailableQty]) }}
						</p>
					</div>
				</div>
			</div>

			<!-- Batch Selection -->
			<div v-if="item?.has_batch_no">
				<label class="block text-sm font-medium text-gray-700 mb-2">
					{{ __('Select Batch Numbers and Quantities') }}
				</label>
				<div class="flex flex-col gap-2 max-h-80 overflow-y-auto">
					<div
						v-for="batch in availableBatches"
						:key="batch.batch_no"
						:class="[
							'border rounded-lg p-3 transition-all',
							getBatchSelectedQty(batch.batch_no) > 0
								? 'border-blue-500 bg-blue-50'
								: 'border-gray-200'
						]"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="flex-1">
								<h4 class="text-sm font-semibold text-gray-900">{{ batch.batch_no }}</h4>
								<div class="flex items-center gap-3 mt-1">
									<span class="text-xs text-gray-600">
										{{ __('Available: {0}', [batch.qty]) }}
									</span>
									<span v-if="batch.expiry_date" class="text-xs text-gray-600">
										{{ __('Exp: {0}', [formatDate(batch.expiry_date)]) }}
									</span>
								</div>
							</div>
							<div class="flex items-center gap-2">
								<button
									type="button"
									@click="decrementBatchQty(batch)"
									:disabled="getBatchSelectedQty(batch.batch_no) <= 0"
									class="w-7 h-7 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-bold rounded transition-colors flex items-center justify-center"
								>
									−
								</button>
								<input
									:value="getBatchSelectedQty(batch.batch_no)"
									@input="(e) => updateBatchQty(batch, e.target.value)"
									@blur="() => validateBatchQty(batch)"
									type="number"
									min="0"
									:max="allowNegativeStock ? null : batch.qty"
									step="any"
									class="w-16 px-2 py-1 text-sm font-semibold text-center border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
									:class="{ 'border-red-500 bg-red-50': !allowNegativeStock && getBatchSelectedQty(batch.batch_no) > batch.qty }"
								/>
								<button
									type="button"
									@click="incrementBatchQty(batch)"
									:disabled="!allowNegativeStock && getBatchSelectedQty(batch.batch_no) >= batch.qty"
									class="w-7 h-7 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 disabled:bg-gray-50 disabled:text-gray-300 text-gray-700 font-bold rounded transition-colors flex items-center justify-center"
								>
									+
								</button>
							</div>
						</div>
						<!-- Warning if exceeds available qty -->
						<div v-if="!allowNegativeStock && getBatchSelectedQty(batch.batch_no) > batch.qty" class="mt-2 flex items-center gap-1 text-xs text-red-600">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
							</svg>
							<span>{{ __('Exceeds available quantity') }}</span>
						</div>
					</div>
				</div>
			</div>

				<!-- Serial Number Selection -->
				<div v-if="item?.has_serial_no">
					<!-- Header with count and actions -->
					<div class="flex items-center justify-between mb-2">
						<label class="block text-sm font-medium text-gray-700">
							{{ __('Select Serial Numbers') }}
							<span v-if="totalSelectedSerials > 0" class="ms-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
								{{ __("{0} selected", [totalSelectedSerials]) }}
							</span>
						</label>
						<div class="flex gap-2">
							<button
								v-if="selectedSerials.length > 0"
								type="button"
								@click="clearAllSerials"
								class="text-xs text-gray-600 hover:text-gray-800 font-medium"
							>
								{{ __('Clear All') }}
							</button>
							<button
								v-if="filteredSerials.length > 0 && selectedSerials.length < filteredSerials.length"
								type="button"
								@click="selectAllSerials"
								class="text-xs text-blue-600 hover:text-blue-800 font-medium"
							>
								{{ __('Select All') }}
							</button>
						</div>
					</div>

					<!-- Search Input -->
					<div class="relative mb-3">
						<input
							v-model="serialSearchQuery"
							type="text"
							:placeholder="__('Search serial numbers...')"
							class="w-full px-3 py-2 ps-9 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
						/>
						<svg class="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
						</svg>
					</div>

					<!-- Loading State -->
					<div v-if="isLoadingSerials" class="flex items-center justify-center py-8">
						<svg class="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						<span class="ms-2 text-sm text-gray-600">{{ __('Loading serial numbers...') }}</span>
					</div>

					<!-- Empty State -->
					<div v-else-if="availableSerials.length === 0" class="text-center py-8">
						<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
						</svg>
						<p class="mt-2 text-sm text-gray-600">{{ __('No serial numbers available') }}</p>
					</div>

					<!-- No Results State -->
					<div v-else-if="filteredSerials.length === 0" class="text-center py-8">
						<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
						</svg>
						<p class="mt-2 text-sm text-gray-600">{{ __('No serial numbers match your search') }}</p>
					</div>

					<!-- Serial Numbers List -->
					<div v-else class="flex flex-col gap-2 max-h-80 overflow-y-auto">
						<div
							v-for="serial in filteredSerials"
							:key="serial.serial_no"
							@click="toggleSerial(serial)"
							:class="[
								'border rounded-lg p-3 cursor-pointer transition-all',
								isSerialSelected(serial.serial_no)
									? 'border-blue-500 bg-blue-50'
									: 'border-gray-200 hover:border-blue-300'
							]"
						>
							<div class="flex items-center gap-3">
								<!-- Selection order badge (start) -->
								<span
									v-if="isSerialSelected(serial.serial_no)"
									class="flex-shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-medium"
								>
									{{ getSelectionOrder(serial.serial_no) }}
								</span>
								<!-- Serial info (center) -->
								<div class="flex-1 min-w-0 text-start">
									<h4 class="text-sm font-semibold text-gray-900">{{ serial.serial_no }}</h4>
									<p v-if="serial.warehouse" class="text-xs text-gray-600">
										{{ serial.warehouse }}
									</p>
								</div>
								<!-- Checkbox indicator (end) -->
								<div :class="[
									'flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-all ms-auto',
									isSerialSelected(serial.serial_no)
										? 'bg-blue-600 border-blue-600'
										: 'border-gray-300 bg-white'
								]">
									<svg v-if="isSerialSelected(serial.serial_no)" class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
									</svg>
								</div>
							</div>
						</div>
					</div>

				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex gap-2">
				<Button variant="subtle" @click="show = false">
					{{ __('Cancel') }}
				</Button>
				<Button
					variant="solid"
					@click="handleConfirm"
					:disabled="!isValid"
				>
					{{ __('Confirm') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, createResource } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useSerialNumberStore } from "@/stores/serialNumber"
import { call } from "@/utils/apiWrapper"

const props = defineProps({
	modelValue: Boolean,
	item: Object,
	quantity: {
		type: Number,
		default: 1,
	},
	warehouse: String,
})

const emit = defineEmits(["update:modelValue", "batch-serial-selected"])

// Serial Number Store for caching
const serialStore = useSerialNumberStore()

const show = ref(props.modelValue)
const availableBatches = ref([])
const availableSerials = ref([])
const selectedBatch = ref(null) // For backward compatibility - keep track of last selected
const selectedSerials = ref([])
const serialSearchQuery = ref("")
const localQuantity = ref(props.quantity) // Editable requested quantity
const selectedBatches = ref(new Map()) // Map of batch_no -> qty
const allowNegativeStock = ref(false) // Will be loaded from settings

// Load settings
import { usePOSSettingsStore } from "@/stores/posSettings"
const settingsStore = usePOSSettingsStore()

// Check if negative stock is allowed
watch(
	() => props.modelValue,
	(val) => {
		if (val) {
			// Load allow negative stock setting
			allowNegativeStock.value = settingsStore.currentProfile?.allow_negative_stock || false
		}
	},
	{ immediate: true }
)

// Resource for loading batches with actual quantities
const batchesResource = createResource({
	url: "erpnext.stock.doctype.batch.batch.get_batch_qty",
	makeParams() {
		return {
			item_code: props.item?.item_code,
			warehouse: props.warehouse,
		}
	},
	auto: false,
	async onSuccess(data) {
		if (data && Array.isArray(data)) {
			// Filter batches with qty > 0 and fetch expiry dates
			const validBatches = []
			for (const batch of data) {
				if (batch.qty > 0 && batch.batch_no) {
					try {
						// Fetch batch metadata (expiry date, disabled status)
						const batchDoc = await call("frappe.client.get_value", {
							doctype: "Batch",
							filters: { name: batch.batch_no },
							fieldname: ["expiry_date", "disabled"],
						})
						
						// Only include non-disabled, non-expired batches
						const isNotExpired =
							!batchDoc.expiry_date ||
							new Date(batchDoc.expiry_date) > new Date()
						const isEnabled = batchDoc.disabled === 0

						if (isNotExpired && isEnabled) {
							validBatches.push({
								batch_no: batch.batch_no,
								qty: batch.qty,
								expiry_date: batchDoc.expiry_date,
							})
						}
					} catch (error) {
						console.error(`Error fetching batch ${batch.batch_no}:`, error)
					}
				}
			}
			
		// Sort by expiry date (earliest first) and creation
		validBatches.sort((a, b) => {
			if (a.expiry_date && b.expiry_date) {
				return new Date(a.expiry_date) - new Date(b.expiry_date)
			}
			if (a.expiry_date) return -1
			if (b.expiry_date) return 1
			return 0
		})
		
		availableBatches.value = validBatches
		
		// Auto-distribute after batches are loaded
		if (localQuantity.value > 0) {
			autoDistribute()
		}
	}
},
onError(error) {
	console.error("Error loading batches:", error)
	// Fallback: try to get batches from Batch doctype
	loadBatchesFallback()
},
})

// Fallback method if get_batch_qty fails
async function loadBatchesFallback() {
	try {
		const batches = await call("frappe.client.get_list", {
			doctype: "Batch",
			filters: {
				item: props.item?.item_code,
				disabled: 0,
			},
			fields: ["name as batch_no", "expiry_date", "batch_qty as qty"],
			limit_page_length: 100,
			order_by: "expiry_date asc, creation asc",
		})
		
	// Filter non-expired batches with qty > 0
	availableBatches.value = batches.filter((batch) => {
		const isNotExpired =
			!batch.expiry_date || new Date(batch.expiry_date) > new Date()
		return batch.qty > 0 && isNotExpired
	})
	
	// Auto-distribute after batches are loaded
	if (localQuantity.value > 0) {
		autoDistribute()
	}
} catch (error) {
		console.error("Error in batch fallback:", error)
		availableBatches.value = []
	}
}

watch(
	() => props.modelValue,
	(val) => {
		show.value = val
		if (val && props.item) {
			localQuantity.value = props.quantity // Reset local quantity when dialog opens
			loadBatchesOrSerials()
		}
	},
)

watch(
	() => props.quantity,
	(newQty) => {
		localQuantity.value = newQty
	}
)

watch(show, (val) => {
	emit("update:modelValue", val)
	if (!val) {
		resetSelection()
	}
})

const totalSelectedSerials = computed(() => {
	return selectedSerials.value.length
})

const totalAvailableQty = computed(() => {
	if (!availableBatches.value || availableBatches.value.length === 0) {
		return 0
	}
	return availableBatches.value.reduce((total, batch) => total + (batch.qty || 0), 0)
})

const totalSelectedQty = computed(() => {
	let total = 0
	for (const qty of selectedBatches.value.values()) {
		total += qty || 0
	}
	return total
})

const filteredSerials = computed(() => {
	if (!serialSearchQuery.value.trim()) {
		return availableSerials.value
	}
	const query = serialSearchQuery.value.toLowerCase().trim()
	return availableSerials.value.filter((serial) =>
		serial.serial_no.toLowerCase().includes(query)
	)
})

const isValid = computed(() => {
	if (props.item?.has_batch_no) {
		// Valid if at least one batch with qty > 0 is selected
		// And if negative stock is disabled, total selected must not exceed available
		const hasSelection = totalSelectedQty.value > 0
		const withinLimit = allowNegativeStock.value || totalSelectedQty.value <= totalAvailableQty.value
		return hasSelection && withinLimit
	}
	if (props.item?.has_serial_no) {
		// Valid if at least one serial is selected
		return totalSelectedSerials.value >= 1
	}
	return true
})

// Use store loading state for serials
const isLoadingSerials = computed(() => serialStore.loading)

async function loadBatchesOrSerials() {
	if (props.item?.has_batch_no) {
		batchesResource.reload()
	} else if (props.item?.has_serial_no) {
		// Set warehouse in store
		serialStore.setWarehouse(props.warehouse)
		// Fetch from store (uses cache if valid)
		const serials = await serialStore.fetchSerials(props.item.item_code)
		availableSerials.value = serials
	}
}

function selectBatch(batch) {
	selectedBatch.value = batch
}

// New batch quantity management functions
function getBatchSelectedQty(batchNo) {
	return selectedBatches.value.get(batchNo) || 0
}

function updateBatchQty(batch, value) {
	const qty = parseFloat(value) || 0
	if (qty <= 0) {
		selectedBatches.value.delete(batch.batch_no)
	} else {
		selectedBatches.value.set(batch.batch_no, qty)
		selectedBatch.value = batch // Keep track of last selected for backward compatibility
	}
}

function incrementBatchQty(batch) {
	const currentQty = getBatchSelectedQty(batch.batch_no)
	const newQty = currentQty + 1
	if (allowNegativeStock.value || newQty <= batch.qty) {
		updateBatchQty(batch, newQty)
	}
}

function decrementBatchQty(batch) {
	const currentQty = getBatchSelectedQty(batch.batch_no)
	if (currentQty > 0) {
		updateBatchQty(batch, currentQty - 1)
	}
}

function validateBatchQty(batch) {
	const currentQty = getBatchSelectedQty(batch.batch_no)
	if (!allowNegativeStock.value && currentQty > batch.qty) {
		// Auto-correct to max available
		updateBatchQty(batch, batch.qty)
	}
}

function handleQuantityChange() {
	// Auto-distribute when quantity changes
	autoDistribute()
}

function autoDistribute() {
	// Auto-distribute requested quantity across batches based on FIFO (expiry date)
	if (!localQuantity.value || localQuantity.value <= 0) return
	
	// Clear current selections
	selectedBatches.value.clear()
	
	// Sort batches by expiry date (earliest first) - they should already be sorted
	const sortedBatches = [...availableBatches.value].sort((a, b) => {
		// Batches with expiry date come first
		if (a.expiry_date && b.expiry_date) {
			return new Date(a.expiry_date) - new Date(b.expiry_date)
		}
		if (a.expiry_date) return -1
		if (b.expiry_date) return 1
		return 0
	})
	
	let remainingQty = localQuantity.value
	
	for (const batch of sortedBatches) {
		if (remainingQty <= 0) break
		
		const qtyToTake = Math.min(remainingQty, batch.qty)
		if (qtyToTake > 0) {
			selectedBatches.value.set(batch.batch_no, qtyToTake)
			selectedBatch.value = batch // Keep track of last selected
			remainingQty -= qtyToTake
		}
	}
	
	// If still have remaining qty and negative stock is allowed, add to last batch
	if (remainingQty > 0 && allowNegativeStock.value && sortedBatches.length > 0) {
		const lastBatch = sortedBatches[sortedBatches.length - 1]
		const currentQty = selectedBatches.value.get(lastBatch.batch_no) || 0
		selectedBatches.value.set(lastBatch.batch_no, currentQty + remainingQty)
	}
}

function toggleSerial(serial) {
	const index = selectedSerials.value.findIndex(
		(s) => s.serial_no === serial.serial_no,
	)
	if (index > -1) {
		selectedSerials.value.splice(index, 1)
	} else {
		// Allow selecting multiple serial numbers without limit
		selectedSerials.value.push(serial)
	}
}

function isSerialSelected(serialNo) {
	return selectedSerials.value.some((s) => s.serial_no === serialNo)
}

function getSelectionOrder(serialNo) {
	return selectedSerials.value.findIndex((s) => s.serial_no === serialNo) + 1
}

function selectAllSerials() {
	// Add all filtered serials that aren't already selected
	filteredSerials.value.forEach((serial) => {
		if (!isSerialSelected(serial.serial_no)) {
			selectedSerials.value.push(serial)
		}
	})
}

function clearAllSerials() {
	selectedSerials.value = []
}

async function handleConfirm() {
	const result = {}

	if (props.item?.has_batch_no) {
		// Build array of selected batches with quantities
		const batchSelections = []
		for (const [batchNo, qty] of selectedBatches.value.entries()) {
			if (qty > 0) {
				batchSelections.push({ batch_no: batchNo, qty })
			}
		}

		console.log("Batch selections:", batchSelections)

		if (batchSelections.length > 0) {
			result.batches = batchSelections
			result.quantity = totalSelectedQty.value
			
			// Create bundle for the batches
			try {
				// Let frappe-ui handle the serialization
				console.log("Calling create_batch_bundle with:", {
					item_code: props.item.item_code,
					warehouse: props.warehouse,
					batches: batchSelections,
					type_of_transaction: "Outward"
				})
				
				const bundleResponse = await call("pos_next.api.serial_batch_bundle.create_batch_bundle", {
					item_code: props.item.item_code,
					warehouse: props.warehouse,
					batches: batchSelections,
					type_of_transaction: "Outward"
				})
				
				console.log("Bundle response:", bundleResponse)
				
				if (bundleResponse && bundleResponse.success) {
					result.serial_and_batch_bundle = bundleResponse.bundle_name
					result._bundle_data = bundleResponse.bundle_data
					console.log("Bundle created:", result.serial_and_batch_bundle, result._bundle_data)
				} else {
					console.error("Bundle creation failed:", bundleResponse)
				}
			} catch (error) {
				console.error("Error creating batch bundle:", error)
			}
			
			// Also set the first batch for display
			result.batch_no = batchSelections[0].batch_no
		}
	}

	if (props.item?.has_serial_no) {
		const selectedList = selectedSerials.value.map((s) => s.serial_no)
		result.serial_no = selectedList.join("\n")
		result.quantity = selectedList.length

		// Remove selected serials from cache (they're now in cart)
		serialStore.consumeSerials(props.item.item_code, selectedList)
	}

	console.log("Emitting batch-serial-selected with result:", result)
	emit("batch-serial-selected", result)
	show.value = false
}

function resetSelection() {
	selectedBatch.value = null
	selectedSerials.value = []
	serialSearchQuery.value = ""
	availableBatches.value = []
	selectedBatches.value.clear()
	localQuantity.value = props.quantity
	// Don't clear availableSerials - it's managed by the store cache
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	return new Date(dateStr).toLocaleDateString()
}
</script>
