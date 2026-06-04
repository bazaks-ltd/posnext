<template>
	<Transition name="fade">
		<div
			v-if="show"
			class="fixed inset-0 bg-black bg-opacity-50 z-[300]"
			@click.self="handleClose"
		>
			<div class="fixed inset-0 flex items-center justify-center p-4">
				<div class="w-full h-full max-w-[95vw] max-h-[95vh] bg-white rounded-lg shadow-2xl overflow-hidden flex flex-col">
					<div class="flex items-center justify-between px-6 py-5 border-b bg-gradient-to-r from-rose-50 to-red-50">
						<div class="flex items-center gap-3">
							<div class="p-2 bg-rose-100 rounded-lg">
								<svg class="w-6 h-6 text-rose-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
								</svg>
							</div>
							<div>
								<h2 class="text-xl font-bold text-gray-900">{{ __('Reports') }}</h2>
								<p class="text-sm text-gray-600">{{ __('Sales by cost center with tax, totals, and payment modes') }}</p>
							</div>
						</div>
						<button
							@click="handleClose"
							class="p-2 hover:bg-white/50 rounded-lg transition-colors"
						>
							<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
							</svg>
						</button>
					</div>

					<div class="border-b border-gray-200 bg-gray-50">
						<nav class="flex gap-2 px-6">
							<button
								v-for="tab in reportTabs"
								:key="tab.id"
								@click="selectReport(tab.id)"
								:class="[
									'px-4 py-3 text-sm font-semibold transition-all border-b-2',
									activeReport === tab.id
										? 'text-rose-800 border-rose-600'
										: 'text-gray-600 border-transparent hover:text-gray-800',
								]"
							>
								{{ tab.label }}
							</button>
						</nav>
					</div>

					<div class="px-6 py-4 border-b bg-white flex flex-wrap items-end gap-4">
						<div v-if="activeReport === 'daily'" class="flex flex-wrap gap-4 items-end">
							<div>
								<label class="block text-xs font-medium text-gray-600 mb-1">{{ __('From Date') }}</label>
								<input v-model="filters.from_date" type="date" class="border rounded-lg px-3 py-2 text-sm" />
							</div>
							<div>
								<label class="block text-xs font-medium text-gray-600 mb-1">{{ __('To Date') }}</label>
								<input v-model="filters.to_date" type="date" class="border rounded-lg px-3 py-2 text-sm" />
							</div>
						</div>
						<div v-else class="text-sm text-gray-600">
							<span class="font-medium text-gray-800">{{ __('Shift') }}:</span>
							{{ filters.pos_opening_shift || __('No open shift') }}
						</div>
						<Button :loading="loading" @click="loadReport">
							{{ __('Run Report') }}
						</Button>
						<Button variant="subtle" @click="openInDesk">
							{{ __('Open in Desk') }}
						</Button>
					</div>

					<div class="flex-1 overflow-auto bg-gray-50 p-6">
						<div v-if="loading" class="flex justify-center py-16">
							<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-rose-600"></div>
						</div>
						<div v-else-if="errorMessage" class="text-center py-12 text-red-600 text-sm">
							{{ errorMessage }}
						</div>
						<div v-else-if="!tableRows.length" class="text-center py-12 text-gray-500 text-sm">
							{{ __('Run the report to see results') }}
						</div>
						<div v-else class="bg-white rounded-lg border overflow-hidden">
							<table class="min-w-full text-sm">
								<thead class="bg-gray-100">
									<tr>
										<th
											v-for="col in displayColumns"
											:key="col.fieldname"
											class="px-4 py-3 text-left font-semibold text-gray-700"
										>
											{{ col.label }}
										</th>
									</tr>
								</thead>
								<tbody>
									<tr
										v-for="(row, idx) in tableRows"
										:key="idx"
										:class="rowClass(row)"
									>
										<td
											v-for="col in displayColumns"
											:key="col.fieldname"
											class="px-4 py-2.5"
											:class="cellClass(col, row)"
										>
											{{ formatCell(row, col) }}
										</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				</div>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import { Button, call } from "frappe-ui"
import { computed, ref, watch } from "vue"

const props = defineProps({
	modelValue: Boolean,
	company: String,
	posProfile: String,
	openingShift: String,
	currency: String,
})

const emit = defineEmits(["update:modelValue"])

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
})

const reportTabs = [
	{ id: "daily", label: __("Daily Sales by Cost Center"), reportName: "Daily Sales by Cost Center" },
	{
		id: "shift",
		label: __("Current Shift Sales by Cost Center"),
		reportName: "Current Shift Sales by Cost Center",
	},
]

const activeReport = ref("daily")
const loading = ref(false)
const errorMessage = ref("")
const columns = ref([])
const tableRows = ref([])
const filters = ref({
	company: "",
	pos_profile: "",
	from_date: "",
	to_date: "",
	pos_opening_shift: "",
	include_non_pos: 0,
})

const activeReportName = computed(
	() => reportTabs.find((t) => t.id === activeReport.value)?.reportName || "",
)

const displayColumns = computed(() =>
	(columns.value || []).filter((col) => col.fieldname && !col.hidden),
)

watch(
	() => props.modelValue,
	(open) => {
		if (open) {
			initFilters()
		}
	},
)

watch(activeReport, () => {
	tableRows.value = []
	columns.value = []
	errorMessage.value = ""
	initFilters()
})

async function initFilters() {
	try {
		const defaults = await call("pos_next.api.reports.get_default_report_filters", {
			report_name: activeReportName.value,
			company: props.company,
			pos_profile: props.posProfile,
		})
		filters.value = {
			...defaults,
			pos_opening_shift:
				defaults.pos_opening_shift || props.openingShift || filters.value.pos_opening_shift,
		}
	} catch (e) {
		console.error(e)
		filters.value.company = props.company || filters.value.company
		filters.value.pos_profile = props.posProfile || filters.value.pos_profile
		filters.value.pos_opening_shift = props.openingShift || ""
		const today = new Date().toISOString().slice(0, 10)
		filters.value.from_date = today
		filters.value.to_date = today
	}
}

function selectReport(id) {
	activeReport.value = id
}

async function loadReport() {
	if (activeReport.value === "shift" && !filters.value.pos_opening_shift) {
		errorMessage.value = __("Open a POS shift to run this report")
		return
	}

	loading.value = true
	errorMessage.value = ""
	try {
		const result = await call("pos_next.api.reports.run_pos_report", {
			report_name: activeReportName.value,
			filters: filters.value,
		})
		columns.value = result?.columns || []
		tableRows.value = (result?.result || []).filter((row) => row && Object.keys(row).length)
	} catch (e) {
		errorMessage.value = e?.message || __("Failed to load report")
		tableRows.value = []
	} finally {
		loading.value = false
	}
}

function formatCell(row, col) {
	const value = row[col.fieldname]
	if (value === null || value === undefined || value === "") {
		return ""
	}
	if (col.fieldtype === "Currency") {
		return formatCurrency(value)
	}
	return value
}

function formatCurrency(amount) {
	const num = Number.parseFloat(amount) || 0
	const code = props.currency || ""
	try {
		return new Intl.NumberFormat(undefined, {
			style: code ? "currency" : "decimal",
			currency: code || undefined,
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		}).format(num)
	} catch {
		return num.toFixed(2)
	}
}

function rowClass(row) {
	if (row.is_section) return "bg-rose-50 font-semibold text-rose-900"
	if (row.bold) return "bg-gray-100 font-bold"
	return "border-t border-gray-100"
}

function cellClass(col, row) {
	if (col.fieldtype === "Currency") return "text-right tabular-nums"
	if (row.bold) return "font-bold"
	return ""
}

function openInDesk() {
	const reportSlug = encodeURIComponent(activeReportName.value)
	window.open(`/app/query-report/${reportSlug}`, "_blank")
}

function handleClose() {
	show.value = false
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
