<template>
	<Dialog v-model="show" :options="{ title: __('Delivery Note'), size: 'md' }">
		<template #body-content>
			<p class="text-[11px] text-gray-600 mb-2 text-start">
				{{ __('Select a Delivery Note with unbilled quantity for this customer.') }}
			</p>
			<Input
				v-model="searchTxt"
				type="text"
				class="mb-3"
				:placeholder="__('Search delivery note…')"
				:disabled="loading || fetchingItems"
				@keyup.enter="loadNotes"
			/>
			<div
				v-if="loading"
				class="flex items-center justify-center py-8 text-gray-500 text-sm gap-2"
			>
				<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-amber-500"></div>
				{{ __('Loading…') }}
			</div>
			<div
				v-else-if="!notes.length"
				class="text-center py-6 text-sm text-gray-500"
			>
				{{ __('No delivery notes to bill') }}
			</div>
			<div v-else class="flex flex-col gap-1 max-h-64 overflow-y-auto pe-0.5">
				<button
					v-for="dn in notes"
					:key="dn.name"
					type="button"
					:disabled="fetchingItems || isLoaded(dn.name)"
					class="w-full text-start px-3 py-2 rounded-lg border border-gray-200 hover:bg-amber-50 hover:border-amber-300 transition-colors disabled:opacity-50"
					:class="isLoaded(dn.name) ? 'bg-gray-50 cursor-not-allowed' : ''"
					@click="addFromDeliveryNote(dn.name)"
				>
					<span class="text-xs font-semibold text-gray-900">{{ dn.name }}</span>
					<span v-if="dn.posting_date" class="text-[10px] text-gray-500 ms-2">
						{{ formatPostingDate(dn.posting_date) }}
					</span>
					<span v-if="isLoaded(dn.name)" class="text-[10px] text-green-600 ms-2">
						{{ __('Already in cart') }}
					</span>
				</button>
			</div>
			<div v-if="errorMessage" class="mt-3 text-xs text-red-600 text-start">
				{{ errorMessage }}
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end w-full gap-2">
				<Button variant="subtle" :disabled="fetchingItems" @click="show = false">
					{{ __('Close') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { call } from "@/utils/apiWrapper"
import { Button, Dialog, Input } from "frappe-ui"
import { ref, watch } from "vue"

const props = defineProps({
	modelValue: Boolean,
	customer: {
		type: [String, Object],
		default: null,
	},
	company: String,
	posProfile: String,
	loadedDeliveryNotes: {
		type: Array,
		default: () => [],
	},
})

const emit = defineEmits(["update:modelValue", "items-added"])

const show = ref(props.modelValue)
const searchTxt = ref("")
const notes = ref([])
const loading = ref(false)
const fetchingItems = ref(false)
const errorMessage = ref("")
let searchDebounce = null

watch(
	() => props.modelValue,
	(val) => {
		show.value = val
		if (val) {
			searchTxt.value = ""
			errorMessage.value = ""
			loadNotes()
		}
	},
)

watch(show, (val) => {
	emit("update:modelValue", val)
})

watch(searchTxt, () => {
	if (!show.value) return
	window.clearTimeout(searchDebounce)
	searchDebounce = window.setTimeout(() => {
		loadNotes()
	}, 300)
})

function customerName() {
	if (!props.customer) return null
	if (typeof props.customer === "string") return props.customer
	return props.customer?.name || null
}

function formatPostingDate(d) {
	if (!d) return ""
	if (typeof d === "string" && d.includes("-")) {
		return d.length >= 10 ? d.slice(0, 10) : d
	}
	return String(d)
}

function isLoaded(deliveryNoteName) {
	return props.loadedDeliveryNotes.includes(deliveryNoteName)
}

async function loadNotes() {
	const cust = customerName()
	if (!cust || !props.company) {
		notes.value = []
		return
	}
	loading.value = true
	errorMessage.value = ""
	try {
		const res = await call(
			"pos_next.api.delivery_notes.list_delivery_notes_for_billing",
			{
				customer: cust,
				company: props.company,
				txt: searchTxt.value?.trim() || undefined,
			},
		)
		const rows = Array.isArray(res) ? res : res?.message
		notes.value = Array.isArray(rows) ? rows : []
	} catch (e) {
		console.error(e)
		errorMessage.value =
			e?.message || e?.exc || __("Could not load delivery notes")
		notes.value = []
	} finally {
		loading.value = false
	}
}

async function addFromDeliveryNote(deliveryNoteName) {
	if (!deliveryNoteName) return
	if (isLoaded(deliveryNoteName)) {
		errorMessage.value = __("Delivery Note {0} is already in the cart", [
			deliveryNoteName,
		])
		return
	}
	fetchingItems.value = true
	errorMessage.value = ""
	try {
		const res = await call(
			"pos_next.api.delivery_notes.get_cart_items_from_delivery_note",
			{
				delivery_note: deliveryNoteName,
				pos_profile: props.posProfile || undefined,
			},
		)
		const payload =
			res && typeof res === "object" && "message" in res ? res.message : res
		const items = payload?.items
		if (!Array.isArray(items) || items.length === 0) {
			errorMessage.value = __("No billable lines on this delivery note")
			return
		}
		emit("items-added", {
			items,
			delivery_note: payload.delivery_note || deliveryNoteName,
		})
		show.value = false
	} catch (e) {
		console.error(e)
		errorMessage.value =
			e?.message || e?.exc || __("Could not load items from delivery note")
	} finally {
		fetchingItems.value = false
	}
}
</script>
