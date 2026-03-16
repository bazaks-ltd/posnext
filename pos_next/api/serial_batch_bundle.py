import json

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate

from erpnext.stock.doctype.batch.batch import get_batch_qty


def _validate_batch_for_bundle(batch_no, item_code, warehouse, requested_qty):
	"""
	Validate batch: belongs to item, has enough qty in warehouse, not expired, not disabled.
	Returns available qty in warehouse; throws if invalid.
	"""
	if not frappe.db.exists("Batch", batch_no):
		frappe.throw(_("Batch {0} does not exist").format(batch_no))

	batch_doc = frappe.get_cached_doc("Batch", batch_no)
	if batch_doc.item != item_code:
		frappe.throw(
			_("Batch {0} does not belong to item {1}").format(batch_no, item_code)
		)
	if batch_doc.disabled:
		frappe.throw(_("Batch {0} is disabled").format(batch_no))

	today = nowdate()
	if batch_doc.expiry_date and str(batch_doc.expiry_date) <= str(today):
		frappe.throw(_("Batch {0} has expired").format(batch_no))

	available = get_batch_qty(batch_no, warehouse) or 0
	if flt(available) < flt(requested_qty):
		frappe.throw(
			_("Insufficient quantity for batch {0} in warehouse {1} (available: {2}, requested: {3})").format(
				batch_no, warehouse, flt(available), flt(requested_qty)
			)
		)
	return flt(available)


@frappe.whitelist()
def create_batch_bundle(item_code, warehouse, batches, type_of_transaction="Outward"):
	"""
	Create a Serial and Batch Bundle for multiple batches.

	Validates each batch: item match, qty available in warehouse, not expired, not disabled.
	"""
	try:
		if isinstance(batches, str):
			try:
				batches = json.loads(batches)
			except json.JSONDecodeError as je:
				frappe.throw(_("Invalid batches JSON format"))

		if not batches or not isinstance(batches, list):
			frappe.throw(_("No batches provided"))
		if len(batches) == 0:
			frappe.throw(_("Batches list is empty"))

		company = frappe.get_cached_value("Warehouse", warehouse, "company")
		if not company:
			frappe.throw(_("Warehouse {0} does not have a company set").format(warehouse))

		# Validate each batch before creating bundle
		for batch in batches:
			if not isinstance(batch, dict):
				frappe.throw(_("Each batch must be a dict with batch_no and qty"))
			batch_no = batch.get("batch_no")
			qty = batch.get("qty")
			if not batch_no or qty is None:
				frappe.throw(_("Each batch must have batch_no and qty"))
			requested_qty = abs(flt(qty))
			if type_of_transaction == "Outward" and requested_qty > 0:
				_validate_batch_for_bundle(
					batch_no, item_code, warehouse, requested_qty
				)

		bundle_doc = frappe.get_doc({
			"doctype": "Serial and Batch Bundle",
			"item_code": item_code,
			"warehouse": warehouse,
			"company": company,
			"type_of_transaction": type_of_transaction,
			"has_batch_no": 1,
			"has_serial_no": 0,
			"posting_datetime": now_datetime(),
			"voucher_type": "POS Invoice",
		})

		for batch in batches:
			batch_no = batch.get("batch_no")
			qty = flt(batch.get("qty"))
			if type_of_transaction == "Outward":
				qty = -1 * abs(qty)
			bundle_doc.append("entries", {
				"batch_no": batch_no,
				"qty": qty,
				"warehouse": warehouse,
			})

		if not bundle_doc.entries:
			frappe.throw(_("No valid batch entries to create bundle"))

		bundle_doc.insert(ignore_permissions=True)

		return {
			"success": True,
			"bundle_name": bundle_doc.name,
			"bundle_data": {
				"name": bundle_doc.name,
				"entries": [
					{
						"batch_no": entry.batch_no,
						"qty": abs(entry.qty),
						"warehouse": entry.warehouse,
					}
					for entry in bundle_doc.entries
				],
			},
		}
	except Exception as e:
		frappe.log_error(
			frappe.get_traceback(),
			"pos_next.api.serial_batch_bundle.create_batch_bundle",
		)
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_bundle_details(bundle_name):
	"""
	Get details of a Serial and Batch Bundle
	
	Args:
		bundle_name: Name of the bundle
	
	Returns:
		Bundle details with entries
	"""
	try:
		bundle = frappe.get_doc("Serial and Batch Bundle", bundle_name)
		
		return {
			"success": True,
			"bundle": {
				"name": bundle.name,
				"item_code": bundle.item_code,
				"warehouse": bundle.warehouse,
				"entries": [
					{
						"batch_no": entry.batch_no,
						"qty": abs(entry.qty),
						"warehouse": entry.warehouse
					}
					for entry in bundle.entries
				]
			}
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "pos_next.api.serial_batch_bundle.get_bundle_details")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def update_batch_bundle(bundle_name, batches):
	"""
	Update an existing Serial and Batch Bundle
	
	Args:
		bundle_name: Name of the bundle to update
		batches: List of dict with batch_no and qty (JSON string or list)
	
	Returns:
		Success status
	"""
	try:
		# Parse batches if it's a string
		if isinstance(batches, str):
			import json
			batches = json.loads(batches)
		
		# Validate batches
		if not batches or not isinstance(batches, list):
			frappe.throw(_("Invalid batches data"))
		
		bundle_doc = frappe.get_doc("Serial and Batch Bundle", bundle_name)
		
		# Clear existing entries
		bundle_doc.entries = []
		
		# Add new entries
		for batch in batches:
			if not isinstance(batch, dict):
				continue
				
			batch_no = batch.get("batch_no")
			qty = batch.get("qty")
			
			if not batch_no or not qty:
				continue
			
			# For outward transactions, qty should be negative
			qty = float(qty)
			if bundle_doc.type_of_transaction == "Outward":
				qty = -1 * abs(qty)
			
			bundle_doc.append("entries", {
				"batch_no": batch_no,
				"qty": qty,
				"warehouse": bundle_doc.warehouse
			})
		
		# Validate that we have entries
		if not bundle_doc.entries:
			frappe.throw(_("No valid batch entries to update bundle"))
		
		bundle_doc.save(ignore_permissions=True)
		
		return {
			"success": True,
			"bundle_name": bundle_doc.name
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "pos_next.api.serial_batch_bundle.update_batch_bundle")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def delete_batch_bundle(bundle_name):
	"""
	Delete a Serial and Batch Bundle
	
	Args:
		bundle_name: Name of the bundle to delete
	
	Returns:
		Success status
	"""
	try:
		frappe.delete_doc("Serial and Batch Bundle", bundle_name, ignore_permissions=True)
		return {"success": True}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "pos_next.api.serial_batch_bundle.delete_batch_bundle")
		return {"success": False, "error": str(e)}

