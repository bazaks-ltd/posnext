import { createResource } from "frappe-ui"
import { computed, ref, toRaw } from "vue"
import { isOffline } from "@/utils/offline"
import { useSerialNumberStore } from "@/stores/serialNumber"

/** Match ERPNext Sales Taxes row: prices include VAT when this is set on the template */
function isIncludedInPrintRate(value) {
	if (value === true || value === 1) return true
	if (typeof value === "string") {
		const s = value.trim().toLowerCase()
		if (s === "1" || s === "true" || s === "yes") return true
	}
	return Number(value) === 1
}

function createLineId() {
	if (typeof crypto !== "undefined" && crypto.randomUUID) {
		return crypto.randomUUID()
	}
	return `line-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

export function useInvoice() {
	// Serial Number Store for returning serials when items are removed
	const serialStore = useSerialNumberStore()
	// State
	const invoiceItems = ref([])
	const customer = ref(null)
	const payments = ref([])
	const salesTeam = ref([]) // Sales team for Sales Invoice
	const posProfile = ref(null)
	const posOpeningShift = ref(null) // POS Opening Shift name
	const additionalDiscount = ref(0)
	const couponCode = ref(null)
	const taxRules = ref([]) // Tax rules from POS Profile
	// Tax mode is derived from the Taxes & Charges template (included_in_print_rate).
	// We intentionally do not store a separate "tax inclusive" flag in POS Settings.
	const taxInclusive = computed(() => {
		const rules = Array.isArray(taxRules.value) ? taxRules.value : []
		return rules.some((t) => isIncludedInPrintRate(t?.included_in_print_rate))
	})

	// Performance: Incrementally maintained aggregates (updated on add/remove/change)
	// This avoids O(n) array reductions on every reactive change
	const _cachedSubtotal = ref(0)
	const _cachedTotalTax = ref(0)
	const _cachedTotalDiscount = ref(0)
	const _cachedTotalPaid = ref(0)

	// Resources
	const updateInvoiceResource = createResource({
		url: "pos_next.api.invoices.update_invoice",
		makeParams(params) {
			return { data: JSON.stringify(params.data) }
		},
		auto: false,
	})

	const submitInvoiceResource = createResource({
		url: "pos_next.api.invoices.submit_invoice",
		makeParams(params) {
			return {
				invoice: JSON.stringify(params.invoice),
				data: JSON.stringify(params.data || {}),
			}
		},
		auto: false,
		onError(error) {
			// Store the full error details for later access
			console.error("submitInvoiceResource onError:", error)

			// Attach the resource's error data to the error object
			if (submitInvoiceResource.error) {
				error.resourceError = submitInvoiceResource.error
			}
		},
	})

	const validateCartItemsResource = createResource({
		url: "pos_next.api.invoices.validate_cart_items",
		makeParams({ items, pos_profile }) {
			return {
				items: JSON.stringify(items),
				pos_profile: pos_profile,
			}
		},
		auto: false,
	})

	const applyOffersResource = createResource({
		url: "pos_next.api.invoices.apply_offers",
		makeParams({ invoice_data, selected_offers }) {
			const params = {
				invoice_data: JSON.stringify(invoice_data),
			}

			if (selected_offers && selected_offers.length) {
				params.selected_offers = JSON.stringify(selected_offers)
			}

			return params
		},
		auto: false,
	})

	const getItemDetailsResource = createResource({
		url: "pos_next.api.items.get_item_details",
		auto: false,
	})

	const getTaxesResource = createResource({
		url: "pos_next.api.pos_profile.get_taxes",
		auto: false,
	})

	const getDefaultCustomerResource = createResource({
		url: "pos_next.api.pos_profile.get_default_customer",
		makeParams({ pos_profile }) {
			return { pos_profile }
		},
		auto: false,
	})

	const cleanupDraftsResource = createResource({
		url: "pos_next.api.invoices.cleanup_old_drafts",
		auto: false,
	})

	// ========================================================================
	// COMPUTED TOTALS - IMPORTANT: Subtotal uses price_list_rate (original price)
	// ========================================================================
	// Formula depends on tax_inclusive mode:
	//
	// TAX EXCLUSIVE (default):
	// - Subtotal: Sum of (price_list_rate × quantity) = net amounts
	// - Tax: Calculated and added on top
	// - Grand Total = Subtotal - Discount + Tax
	//
	// TAX INCLUSIVE:
	// - Subtotal: Sum of (price_list_rate × quantity) = gross amounts (includes tax)
	// - Tax: Extracted from prices (for display only)
	// - Grand Total = Subtotal - Discount (tax already included!)
	//
	// This ensures tax is not double-counted in inclusive mode!
	// ========================================================================
	const subtotal = computed(() => _cachedSubtotal.value)
	const totalTax = computed(() => _cachedTotalTax.value)
	const totalDiscount = computed(
		() => _cachedTotalDiscount.value + (additionalDiscount.value || 0),
	)
	const grandTotal = computed(() => {
		const discount = _cachedTotalDiscount.value + (additionalDiscount.value || 0)

		if (taxInclusive.value) {
			// Tax inclusive: Subtotal already includes tax, so don't add it again
			return _cachedSubtotal.value - discount
		} else {
			// Tax exclusive: Add tax on top of subtotal
			return _cachedSubtotal.value + _cachedTotalTax.value - discount
		}
	})
	const totalPaid = computed(() => _cachedTotalPaid.value)

	const remainingAmount = computed(() => {
		return grandTotal.value - totalPaid.value
	})

	const canSubmit = computed(() => {
		return (
			invoiceItems.value.length > 0 && remainingAmount.value <= 0.01 // Allow small rounding differences
		)
	})

	function findLineItem(lineRef) {
		if (lineRef === undefined || lineRef === null) {
			return undefined
		}
		const byLineId = invoiceItems.value.find((i) => i.lineId === lineRef)
		if (byLineId) {
			return byLineId
		}
		return invoiceItems.value.find((i) => i.item_code === lineRef)
	}

	// Actions
	function addItem(item, quantity = 1) {
		// For items with bundles, don't merge - each bundle should be a separate line
		// For batch items with serial_and_batch_bundle, treat each bundle as unique
		const existingItem = invoiceItems.value.find((i) => {
			// Items must have same item_code
			if (i.item_code !== item.item_code) return false
			
			// If item has a bundle, it should NOT be merged with other items
			// Each bundle is a separate line item
			if (item.serial_and_batch_bundle || i.serial_and_batch_bundle) {
				return false // Never merge items with bundles
			}
			
			// For batch items without bundles, check if same batch
			if (item.batch_no || i.batch_no) {
				return i.batch_no === item.batch_no
			}
			
			// Otherwise, can merge
			return true
		})

		if (existingItem) {
			// Store old values before update for incremental cache adjustment
			// Use price_list_rate for subtotal calculations (before discount)
			const oldPriceListRate = existingItem.price_list_rate || existingItem.rate
			const oldAmount = existingItem.quantity * oldPriceListRate
			const oldTax = existingItem.tax_amount || 0
			const oldDiscount = existingItem.discount_amount || 0

			// For serial items, merge the serial numbers
			if (existingItem.has_serial_no && item.serial_no) {
				const existingSerials = existingItem.serial_no
					? existingItem.serial_no.split('\n').filter(s => s.trim())
					: []
				const newSerials = item.serial_no.split('\n').filter(s => s.trim())
				// Combine serials (avoid duplicates)
				const allSerials = [...new Set([...existingSerials, ...newSerials])]
				existingItem.serial_no = allSerials.join('\n')
				// For serial items, quantity must match serial count
				existingItem.quantity = allSerials.length
			} else {
				existingItem.quantity += quantity
			}
			recalculateItem(existingItem)

			// Update cache incrementally (new values - old values)
			// Use price_list_rate for subtotal (before discount)
			const priceListRate = existingItem.price_list_rate || existingItem.rate
			_cachedSubtotal.value +=
				existingItem.quantity * priceListRate - oldAmount
			_cachedTotalTax.value += (existingItem.tax_amount || 0) - oldTax
			_cachedTotalDiscount.value +=
				(existingItem.discount_amount || 0) - oldDiscount
		} else {
			const newItem = {
				item_code: item.item_code,
				item_name: item.item_name,
				rate: item.rate || item.price_list_rate || 0,
				price_list_rate: item.price_list_rate || item.rate || 0,
				quantity: quantity,
				discount_amount: 0,
				discount_percentage: 0,
				tax_amount: 0,
				amount: quantity * (item.rate || item.price_list_rate || 0),
				stock_qty: item.stock_qty || 0,
				image: item.image,
				uom: item.uom || item.stock_uom,
				stock_uom: item.stock_uom,
				conversion_factor: item.conversion_factor || 1,
				warehouse: item.warehouse,
				actual_batch_qty: item.actual_batch_qty || 0,
				has_batch_no: item.has_batch_no || 0,
				has_serial_no: item.has_serial_no || 0,
				batch_no: item.batch_no,
				serial_no: item.serial_no,
				serial_and_batch_bundle: item.serial_and_batch_bundle, // Add bundle reference
				_bundle_data: item._bundle_data, // Add bundle data for display
				item_uoms: item.item_uoms || [], // Available UOMs for this item
				is_stock_item: item.is_stock_item !== false, // false = service (no UOM selector in cart)
				// Add item_group and brand for offer eligibility checking
				item_group: item.item_group,
				brand: item.brand,
				// Item Tax Template total % (when Sales template row rate is 0)
				pos_item_tax_rate: item.pos_item_tax_rate,
				// Preserve variant_of and template_item for variant tracking
				variant_of: item.variant_of,
				template_item: item.template_item,
				lineId: item.lineId || createLineId(),
			}
			invoiceItems.value.push(newItem)
			// Recalculate the newly added item to apply taxes
			recalculateItem(newItem)

			// Update cache incrementally (add new item values)
			// Use price_list_rate for subtotal (before discount)
			const priceListRate = newItem.price_list_rate || newItem.rate
			_cachedSubtotal.value += newItem.quantity * priceListRate
			_cachedTotalTax.value += newItem.tax_amount || 0
			_cachedTotalDiscount.value += newItem.discount_amount || 0
		}
	}

	function removeItem(lineRef) {
		const itemToRemove = findLineItem(lineRef)
		if (!itemToRemove) {
			return
		}
		// Update cache incrementally (subtract removed item values)
		// Use price_list_rate for subtotal (before discount)
		const priceListRate = itemToRemove.price_list_rate || itemToRemove.rate
		_cachedSubtotal.value -= itemToRemove.quantity * priceListRate
		_cachedTotalTax.value -= itemToRemove.tax_amount || 0
		_cachedTotalDiscount.value -= itemToRemove.discount_amount || 0

		// Return serial numbers back to cache if item has serials
		if (itemToRemove.serial_no && itemToRemove.has_serial_no) {
			serialStore.returnSerials(itemToRemove.item_code, itemToRemove.serial_no)
		}

		invoiceItems.value = invoiceItems.value.filter((i) => {
			if (itemToRemove.lineId && i.lineId) {
				return i.lineId !== itemToRemove.lineId
			}
			return i !== itemToRemove
		})
	}

	function updateItemQuantity(lineRef, quantity) {
		const item = findLineItem(lineRef)
		if (item) {
			// Store old values before update for incremental cache adjustment
			// Use price_list_rate for subtotal calculations (before discount)
			const oldPriceListRate = item.price_list_rate || item.rate
			const oldAmount = item.quantity * oldPriceListRate
			const oldTax = item.tax_amount || 0
			const oldDiscount = item.discount_amount || 0
			const oldQuantity = item.quantity

			const newQuantity = Number.parseFloat(quantity) || 1

			// Handle serial number items - adjust serials when quantity changes
			if (item.has_serial_no && item.serial_no) {
				const serialList = item.serial_no.split('\n').filter(s => s.trim())

				if (newQuantity < oldQuantity) {
					// Quantity decreased - return excess serials to cache
					const serialsToReturn = serialList.slice(newQuantity)
					const serialsToKeep = serialList.slice(0, newQuantity)

					if (serialsToReturn.length > 0) {
						serialStore.returnSerials(item.item_code, serialsToReturn)
						item.serial_no = serialsToKeep.join('\n')
					}
				}
				// Note: Increasing quantity for serial items requires selecting new serials
				// which should be handled by reopening the serial dialog
			}

			item.quantity = newQuantity
			recalculateItem(item)

			// Update cache incrementally (new values - old values)
			// Use price_list_rate for subtotal (before discount)
			const priceListRate = item.price_list_rate || item.rate
			_cachedSubtotal.value += item.quantity * priceListRate - oldAmount
			_cachedTotalTax.value += (item.tax_amount || 0) - oldTax
			_cachedTotalDiscount.value += (item.discount_amount || 0) - oldDiscount
		}
	}

	function updateItemRate(lineRef, rate) {
		const item = findLineItem(lineRef)
		if (item) {
			// Store old values before update for incremental cache adjustment
			// Use price_list_rate for subtotal calculations (before discount)
			const oldPriceListRate = item.price_list_rate || item.rate
			const oldAmount = item.quantity * oldPriceListRate
			const oldTax = item.tax_amount || 0
			const oldDiscount = item.discount_amount || 0

			item.rate = Number.parseFloat(rate) || 0
			recalculateItem(item)

			// Update cache incrementally (new values - old values)
			// Use price_list_rate for subtotal (before discount)
			const priceListRate = item.price_list_rate || item.rate
			_cachedSubtotal.value += item.quantity * priceListRate - oldAmount
			_cachedTotalTax.value += (item.tax_amount || 0) - oldTax
			_cachedTotalDiscount.value += (item.discount_amount || 0) - oldDiscount
		}
	}

	function updateItemDiscount(lineRef, discountPercentage) {
		const item = findLineItem(lineRef)
		if (item) {
			// Validate discount percentage (0-100)
			let validDiscount = Number.parseFloat(discountPercentage) || 0
			if (validDiscount < 0) validDiscount = 0
			if (validDiscount > 100) validDiscount = 100

			// Store old values before update for incremental cache adjustment
			// Use price_list_rate for subtotal calculations (before discount)
			const oldPriceListRate = item.price_list_rate || item.rate
			const oldAmount = item.quantity * oldPriceListRate
			const oldTax = item.tax_amount || 0
			const oldDiscount = item.discount_amount || 0

			item.discount_percentage = validDiscount
			item.discount_amount = 0 // Let recalculateItem compute it
			recalculateItem(item)

			// Update cache incrementally (new values - old values)
			// Use price_list_rate for subtotal (before discount)
			const priceListRate = item.price_list_rate || item.rate
			_cachedSubtotal.value += item.quantity * priceListRate - oldAmount
			_cachedTotalTax.value += (item.tax_amount || 0) - oldTax
			_cachedTotalDiscount.value += (item.discount_amount || 0) - oldDiscount
		}
	}

	function calculateDiscountAmount(discount, baseAmount = null) {
		/**
		 * ⭐ SINGLE SOURCE OF TRUTH FOR ALL DISCOUNT CALCULATIONS ⭐
		 *
		 * This function centralizes discount calculation logic.
		 * All components should use this for consistency.
		 *
		 * IMPORTANT: Discounts are ALWAYS calculated on SUBTOTAL (before tax)
		 * This ensures tax is applied AFTER discount, which is the correct order.
		 *
		 * Calculation Order:
		 * 1. Subtotal (item total)
		 * 2. - Discount (calculated here)
		 * 3. = Net Amount
		 * 4. + Tax (on net amount)
		 * 5. = Grand Total
		 *
		 * @param {Object} discount - { percentage, amount, offer }
		 * @param {Number} baseAmount - Base amount to calculate on (defaults to subtotal)
		 * @returns {Number} Calculated discount amount
		 */
		if (!discount) return 0

		const base = baseAmount !== null ? baseAmount : subtotal.value

		if (discount.percentage > 0) {
			// Percentage discount on SUBTOTAL (before tax)
			return (base * discount.percentage) / 100
		} else if (discount.amount > 0) {
			// Fixed amount discount
			return discount.amount
		}

		return 0
	}

	function applyDiscount(discount) {
		/**
		 * Apply discount as Additional Discount (grand total level)
		 * This prevents conflicts with item-level pricing rules
		 * @param {Object} discount - { percentage, amount, name, code, apply_on }
		 */
		if (!discount) return

		// Store coupon code for tracking
		couponCode.value = discount.code || discount.name

		// Use centralized calculation to handle percentage/amount and clamping
		let discountAmount = calculateDiscountAmount(discount, subtotal.value)

		// Clamp discount to subtotal (cannot exceed total)
		if (discountAmount > subtotal.value) {
			discountAmount = subtotal.value
		}

		// Ensure non-negative
		if (discountAmount < 0) {
			discountAmount = 0
		}

		// Apply discount as Additional Discount on grand total
		// This preserves item-level pricing rules while applying coupon discount
		additionalDiscount.value = discountAmount

		// Rebuild cache after applying additional discount
		rebuildIncrementalCache()
	}

	function removeDiscount() {
		/**
		 * Remove additional discount (coupon discount)
		 */
		// Clear additional discount
		additionalDiscount.value = 0

		// Clear coupon code
		couponCode.value = null

		// Rebuild cache after removing discount
		rebuildIncrementalCache()
	}

	// Performance: Cache tax calculation to avoid repeated loops
	let cachedTaxRate = 0
	let taxRulesCacheKey = ""

	function calculateTotalTaxRate() {
		const rules = Array.isArray(taxRules.value) ? taxRules.value : []
		// Create cache key from tax rules
		const currentKey = JSON.stringify(rules)

		// Return cached value if tax rules haven't changed
		if (currentKey === taxRulesCacheKey && cachedTaxRate !== 0) {
			return cachedTaxRate
		}

		// Calculate total tax rate
		let totalRate = 0
		if (rules.length > 0) {
			for (const taxRule of rules) {
				const chargeType = String(taxRule.charge_type || "").trim()
				if (
					chargeType === "On Net Total" ||
					chargeType === "On Previous Row Total"
				) {
					const r = Number.parseFloat(taxRule.rate)
					totalRate += Number.isFinite(r) ? r : 0
				}
			}
		}

		// Cache the result
		cachedTaxRate = totalRate
		taxRulesCacheKey = currentKey

		return totalRate
	}

	function rebuildIncrementalCache() {
		/**
		 * Rebuild cache from scratch - used when bulk operations modify all items
		 * (e.g., loading tax rules, applying discounts to all items)
		 */
		_cachedSubtotal.value = 0
		_cachedTotalTax.value = 0
		_cachedTotalDiscount.value = 0

		for (const item of invoiceItems.value) {
			// Use price_list_rate for subtotal (before discount)
			const priceListRate = item.price_list_rate || item.rate
			_cachedSubtotal.value += item.quantity * priceListRate
			_cachedTotalTax.value += item.tax_amount || 0
			_cachedTotalDiscount.value += item.discount_amount || 0
		}

		_cachedTotalPaid.value = 0
		for (const payment of payments.value) {
			_cachedTotalPaid.value += payment.amount || 0
		}
	}

	/**
	 * Recalculates all pricing fields for an invoice item.
	 *
	 * This function is the single source of truth for item-level calculations,
	 * ensuring consistency between UI display and backend invoice data.
	 *
	 * Calculation Flow:
	 * 1. Base Amount    = price_list_rate × quantity
	 * 2. Discount       = Applied based on percentage or fixed amount
	 * 3. Net Amount     = Base Amount - Discount (may include/exclude tax)
	 * 4. Tax Amount     = Calculated based on tax_inclusive mode
	 * 5. Final Amount   = Stored in item.amount for backend processing
	 *
	 * Important Design Decisions:
	 * - item.rate always reflects the original list price (price_list_rate)
	 * - Discounts are stored separately (discount_amount, discount_percentage)
	 * - This allows UI to display original prices with clear discount visibility
	 * - Backend receives calculated net rate (amount/quantity) for accurate totals
	 *
	 * Tax Modes:
	 * - Tax Inclusive: Price includes tax. Extract net = gross / (1 + tax_rate)
	 * - Tax Exclusive: Tax added on top. Tax = net × tax_rate
	 *
	 * @param {Object} item - Invoice item object with quantity, rates, and discount fields
	 */
	function recalculateItem(item) {
		// Determine the base unit price (original list price)
		const priceListRate = item.price_list_rate || item.rate
		const baseAmount = item.quantity * priceListRate

		// Calculate discount from either percentage or fixed amount
		let discountAmount = 0
		if (item.discount_percentage > 0) {
			discountAmount = (baseAmount * item.discount_percentage) / 100
		} else if (item.discount_amount > 0) {
			discountAmount = item.discount_amount
			// Sync percentage when amount is provided directly
			item.discount_percentage =
				baseAmount > 0 ? (discountAmount / baseAmount) * 100 : 0
		}
		item.discount_amount = discountAmount

		// Calculate tax based on inclusive/exclusive mode
		const templateRate = calculateTotalTaxRate()
		const itemRateRaw = Number.parseFloat(item.pos_item_tax_rate)
		const totalTaxRate =
			Number.isFinite(itemRateRaw) && itemRateRaw > 0
				? itemRateRaw
				: templateRate
		let netAmount = 0
		let taxAmount = 0

		if (taxInclusive.value && totalTaxRate > 0) {
			// Tax-inclusive: Work backwards from gross to extract net and tax
			const grossAmount = baseAmount - discountAmount
			netAmount = grossAmount / (1 + totalTaxRate / 100)
			taxAmount = grossAmount - netAmount
		} else {
			// Tax-exclusive: Calculate tax on top of net amount
			netAmount = baseAmount - discountAmount
			taxAmount = (netAmount * totalTaxRate) / 100
		}

		// Update item fields
		item.tax_amount = taxAmount
		item.rate = priceListRate  // Preserve original price for display
		item.amount = netAmount    // Net amount for backend calculations
	}

	function addPayment(payment) {
		const amount = Number.parseFloat(payment.amount) || 0
		payments.value.push({
			mode_of_payment: payment.mode_of_payment,
			amount: amount,
			type: payment.type,
		})
		// Update cache incrementally
		_cachedTotalPaid.value += amount
	}

	function removePayment(index) {
		if (payments.value[index]) {
			// Update cache incrementally (subtract removed payment)
			_cachedTotalPaid.value -= payments.value[index].amount || 0
		}
		payments.value.splice(index, 1)
	}

	function updatePayment(index, amount) {
		if (payments.value[index]) {
			// Store old value before update for incremental cache adjustment
			const oldAmount = payments.value[index].amount || 0
			const newAmount = Number.parseFloat(amount) || 0

			payments.value[index].amount = newAmount

			// Update cache incrementally (new value - old value)
			_cachedTotalPaid.value += newAmount - oldAmount
		}
	}

	async function validateStock() {
		/**
		 * Validate stock availability before submission
		 * Returns array of errors if stock is insufficient
		 */
		// Use toRaw() to ensure we get current, non-reactive values (prevents stale cached quantities)
		const rawItems = toRaw(invoiceItems.value)

		const items = rawItems.map((item) => ({
			item_code: item.item_code,
			qty: item.quantity,
			warehouse: item.warehouse,
			conversion_factor: item.conversion_factor || 1,
			stock_qty: item.quantity * (item.conversion_factor || 1),
			is_stock_item: item.is_stock_item !== false, // default to true
		}))

		try {
			const result = await validateCartItemsResource.submit({
				items: items,
				pos_profile: posProfile.value,
			})
			return result || []
		} catch (error) {
			console.error("Stock validation error:", error)
			return []
		}
	}

	async function saveDraft() {
		/**
		 * Save invoice as draft (Step 1)
		 * This creates the invoice with docstatus=0
		 */
		// Use toRaw() to ensure we get current, non-reactive values (prevents stale cached quantities)
		const rawItems = toRaw(invoiceItems.value)
		const rawPayments = toRaw(payments.value)

		const invoiceData = {
			doctype: "Sales Invoice",
			pos_profile: posProfile.value,
			posa_pos_opening_shift: posOpeningShift.value,
			customer: customer.value?.name || customer.value,
			items: rawItems.map((item) => {
				const isStockItem = item.is_stock_item !== false
				const itemData = {
					item_code: item.item_code,
					item_name: item.item_name,
					qty: item.quantity,
					// IMPORTANT: Rate calculation depends on tax mode and discounts
					// Tax-inclusive mode: Send gross amount (price after discount, before tax extraction)
					//   - With discount: price_list_rate - discount_amount
					//   - Without discount: price_list_rate
					//   ERPNext will extract net amount based on included_in_print_rate flag
					// Tax-exclusive mode: Send net amount (after discount, before tax addition)
					rate: taxInclusive.value
						? ((item.price_list_rate || item.rate) - (item.discount_amount || 0) / (item.quantity || 1))
						: (item.quantity > 0 ? item.amount / item.quantity : item.rate),
					price_list_rate: item.price_list_rate || item.rate,
					uom: item.uom,
					conversion_factor: item.conversion_factor || 1,
					discount_percentage: item.discount_percentage || 0,
					discount_amount: item.discount_amount || 0,
					is_stock_item: isStockItem,
				}
				// Non-stock (service) items: omit warehouse so backend does not require it
				if (isStockItem && item.warehouse) {
					itemData.warehouse = item.warehouse
				}
				
				// If using serial_and_batch_bundle, don't include batch_no or serial_no
				// ERPNext will use the bundle instead
				if (item.serial_and_batch_bundle) {
					itemData.serial_and_batch_bundle = item.serial_and_batch_bundle
				} else {
					// Only include legacy fields if no bundle exists
					if (item.batch_no) {
						itemData.batch_no = item.batch_no
					}
					if (item.serial_no) {
						itemData.serial_no = item.serial_no
					}
				}
				
				return itemData
			}),
			payments: rawPayments.map((p) => ({
				mode_of_payment: p.mode_of_payment,
				amount: p.amount,
				type: p.type,
			})),
			discount_amount: additionalDiscount.value || 0,
			coupon_code: couponCode.value,
			is_pos: 1,
			update_stock: 1,
		}

		const result = await updateInvoiceResource.submit({ data: invoiceData })
		return result?.data || result
	}

	async function submitInvoice() {
		/**
		 * Two-step submission process:
		 * 1. Create/update draft invoice
		 * 2. Validate stock and submit
		 */
		try {
			// Step 1: Create invoice draft
			// Use toRaw() to ensure we get current, non-reactive values (prevents stale cached quantities)
			const rawItems = toRaw(invoiceItems.value)
			const rawPayments = toRaw(payments.value)
			const rawSalesTeam = toRaw(salesTeam.value)

			const invoiceData = {
				doctype: "Sales Invoice",
				pos_profile: posProfile.value,
				posa_pos_opening_shift: posOpeningShift.value,
				customer: customer.value?.name || customer.value,
				items: rawItems.map((item) => {
					const isStockItem = item.is_stock_item !== false
					const itemData = {
						item_code: item.item_code,
						item_name: item.item_name,
						qty: item.quantity,
						// IMPORTANT: Rate calculation depends on tax mode and discounts
						// Tax-inclusive mode: Send gross amount (price after discount, before tax extraction)
						//   - With discount: price_list_rate - discount_amount
						//   - Without discount: price_list_rate
						//   ERPNext will extract net amount based on included_in_print_rate flag
						// Tax-exclusive mode: Send net amount (after discount, before tax addition)
						rate: taxInclusive.value
							? ((item.price_list_rate || item.rate) - (item.discount_amount || 0) / (item.quantity || 1))
							: (item.quantity > 0 ? item.amount / item.quantity : item.rate),
						price_list_rate: item.price_list_rate || item.rate,
						uom: item.uom,
						conversion_factor: item.conversion_factor || 1,
						discount_percentage: item.discount_percentage || 0,
						discount_amount: item.discount_amount || 0,
						is_stock_item: isStockItem,
					}
					// Non-stock (service) items: omit warehouse so backend does not require it
					if (isStockItem && item.warehouse) {
						itemData.warehouse = item.warehouse
					}
					
					// If using serial_and_batch_bundle, don't include batch_no or serial_no
					// ERPNext will use the bundle instead
					if (item.serial_and_batch_bundle) {
						itemData.serial_and_batch_bundle = item.serial_and_batch_bundle
					} else {
						// Only include legacy fields if no bundle exists
						if (item.batch_no) {
							itemData.batch_no = item.batch_no
						}
						if (item.serial_no) {
							itemData.serial_no = item.serial_no
						}
					}
					
					return itemData
				}),
				payments: rawPayments.map((p) => ({
					mode_of_payment: p.mode_of_payment,
					amount: p.amount,
					type: p.type,
				})),
				discount_amount: additionalDiscount.value || 0,
				coupon_code: couponCode.value,
				is_pos: 1,
				update_stock: 1, // Critical: Ensures stock is updated
			}

			// Add sales_team if provided
			if (rawSalesTeam && rawSalesTeam.length > 0) {
				invoiceData.sales_team = rawSalesTeam.map((member) => ({
					sales_person: member.sales_person,
					allocated_percentage: member.allocated_percentage || 0,
				}))
			}

			const draftInvoice = await updateInvoiceResource.submit({
				data: invoiceData,
			})

			let invoiceDoc = draftInvoice
			if (
				draftInvoice &&
				typeof draftInvoice === "object" &&
				"data" in draftInvoice
			) {
				invoiceDoc = draftInvoice.data
			}

			if (!invoiceDoc || !invoiceDoc.name) {
				throw new Error(
					"Failed to create draft invoice - no invoice name returned",
				)
			}

			const submitData = {
				change_amount:
					remainingAmount.value < 0 ? Math.abs(remainingAmount.value) : 0,
			}

			try {
				const result = await submitInvoiceResource.submit({
					invoice: invoiceDoc,
					data: submitData,
				})

				// Check if resource has error (frappe-ui pattern)
				if (submitInvoiceResource.error) {
					const resourceError = submitInvoiceResource.error
					console.error("Submit invoice resource error:", resourceError)

					// Create a detailed error object
					const detailedError = new Error(
						resourceError.message || "Invoice submission failed",
					)
					detailedError.exc_type = resourceError.exc_type
					detailedError._server_messages = resourceError._server_messages
					detailedError.httpStatus = resourceError.httpStatus
					detailedError.messages = resourceError.messages

					throw detailedError
				}

				resetInvoice()
				return result
			} catch (error) {
				// Preserve original error object with all its properties
				console.error("Submit invoice error:", error)
				console.log("submitInvoiceResource.error:", submitInvoiceResource.error)

				// If resource has error data, extract and attach it
				if (submitInvoiceResource.error) {
					const resourceError = submitInvoiceResource.error
					console.log("Resource error details:", {
						exc_type: resourceError.exc_type,
						_server_messages: resourceError._server_messages,
						httpStatus: resourceError.httpStatus,
						messages: resourceError.messages,
						messagesContent: JSON.stringify(resourceError.messages),
						data: resourceError.data,
						exception: resourceError.exception,
						keys: Object.keys(resourceError),
					})

					// The messages array likely contains the detailed error info
					if (resourceError.messages && resourceError.messages.length > 0) {
						console.log("First message:", resourceError.messages[0])
					}

					// Attach all resource error properties to the error
					error.exc_type = resourceError.exc_type || error.exc_type
					error._server_messages = resourceError._server_messages
					error.httpStatus = resourceError.httpStatus
					error.messages = resourceError.messages
					error.exception = resourceError.exception
					error.data = resourceError.data

					console.log("After attaching, error.messages:", error.messages)
				}

				throw error
			}
		} catch (error) {
			// Outer catch to ensure error propagates
			console.error("Submit invoice outer error:", error)
			throw error
		}
	}

	/**
	 * Sets the default customer from POS Profile if available.
	 * This is called when resetting/clearing the cart to auto-select
	 * the default customer configured in the POS Profile.
	 */
	async function setDefaultCustomer() {
		// Reset to null first
		customer.value = null

		// Only fetch default customer if we have a POS Profile
		if (!posProfile.value) {
			return
		}

		try {
			const result = await getDefaultCustomerResource.submit({
				pos_profile: posProfile.value,
			})

			// Set the default customer if one is configured
			if (result && result.customer) {
				// Create customer object matching the structure from customer selection
				customer.value = {
					name: result.customer,
					customer_name: result.customer_name || result.customer,
					customer_group: result.customer_group,
				}
			}
		} catch (error) {
			// Silently fail - default customer is optional
			console.log("No default customer set in POS Profile")
		}
	}

	/**
	 * Resets the invoice to a clean state.
	 * If a POS Profile is active and has a default customer, it will be pre-selected.
	 */
	function resetInvoice() {
		invoiceItems.value = []
		payments.value = []
		additionalDiscount.value = 0
		couponCode.value = null

		// Reset incremental cache
		_cachedSubtotal.value = 0
		_cachedTotalTax.value = 0
		_cachedTotalDiscount.value = 0
		_cachedTotalPaid.value = 0

		// Set default customer from POS Profile if available
		setDefaultCustomer()
	}

	/**
	 * Clears the cart and resets to default state.
	 * If a POS Profile is active and has a default customer, it will be pre-selected.
	 */
	async function clearCart() {
		// Return all serial numbers back to cache before clearing
		for (const item of invoiceItems.value) {
			if (item.has_serial_no && item.serial_no) {
				serialStore.returnSerials(item.item_code, item.serial_no)
			}
		}

		invoiceItems.value = []
		payments.value = []
		additionalDiscount.value = 0
		couponCode.value = null

		// Reset incremental cache
		_cachedSubtotal.value = 0
		_cachedTotalTax.value = 0
		_cachedTotalDiscount.value = 0
		_cachedTotalPaid.value = 0

		// Set default customer from POS Profile if available
		setDefaultCustomer()

		// Cleanup old draft invoices (older than 1 hour) in background
		// Skip if offline to avoid network errors
		if (!isOffline()) {
			try {
				await cleanupDraftsResource.submit({
					pos_profile: posProfile.value,
					max_age_hours: 1,
				})
			} catch (error) {
				// Silent fail - don't block cart clearing
				console.warn("Failed to cleanup old drafts:", error)
			}
		}
	}

	async function loadTaxRules(profileName) {
		/**
		 * Load tax rules from POS Profile.
		 * Tax-inclusive mode is inferred from the returned rules.
		 */
		try {
			const result = await getTaxesResource.submit({ pos_profile: profileName })
			// Frappe wraps whitelist return values as { message: ... }; other resources use .message too
			const rules = Array.isArray(result)
				? result
				: Array.isArray(result?.message)
					? result.message
					: Array.isArray(result?.data)
						? result.data
						: []
			taxRules.value = rules

			// Recalculate all items with new tax rules
			invoiceItems.value.forEach((item) => recalculateItem(item))

			// Rebuild cache after bulk operation
			rebuildIncrementalCache()

			return taxRules.value
		} catch (error) {
			console.error("Error loading tax rules:", error)
			taxRules.value = []
			return []
		}
	}

	return {
		// State
		invoiceItems,
		customer,
		payments,
		salesTeam,
		posProfile,
		posOpeningShift,
		additionalDiscount,
		couponCode,
		taxRules,
		taxInclusive,

		// Computed
		subtotal,
		totalTax,
		totalDiscount,
		grandTotal,
		totalPaid,
		remainingAmount,
		canSubmit,

		// Actions
		addItem,
		removeItem,
		updateItemQuantity,
		updateItemRate,
		updateItemDiscount,
		calculateDiscountAmount,
		applyDiscount,
		removeDiscount,
		addPayment,
		removePayment,
		updatePayment,
		validateStock,
		saveDraft,
		submitInvoice,
		resetInvoice,
		clearCart,
		setDefaultCustomer,
		loadTaxRules,
		recalculateItem,
		rebuildIncrementalCache,

		// Resources
		updateInvoiceResource,
		submitInvoiceResource,
		validateCartItemsResource,
		applyOffersResource,
		getItemDetailsResource,
		getTaxesResource,
	}
}
