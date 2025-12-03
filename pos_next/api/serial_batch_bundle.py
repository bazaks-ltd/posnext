import frappe
from frappe import _


@frappe.whitelist()
def create_batch_bundle(item_code, warehouse, batches, type_of_transaction="Outward"):
	"""
	Create a Serial and Batch Bundle for multiple batches
	
	Args:
		item_code: Item Code
		warehouse: Warehouse
		batches: List of dict with batch_no and qty (JSON string or list)
		type_of_transaction: "Outward" for sales, "Inward" for purchase
	
	Returns:
		Bundle name
	"""
	try:
		# Log incoming data for debugging
		import json
		frappe.logger().info("="*80)
		frappe.logger().info("create_batch_bundle START")
		frappe.logger().info(f"item_code: {item_code}, type: {type(item_code)}")
		frappe.logger().info(f"warehouse: {warehouse}, type: {type(warehouse)}")
		frappe.logger().info(f"batches: {batches}, type: {type(batches)}")
		frappe.logger().info(f"type_of_transaction: {type_of_transaction}, type: {type(type_of_transaction)}")
		frappe.logger().info("="*80)
		
		# Also print to console for immediate visibility
		print("="*80)
		print("create_batch_bundle called")
		print(f"item_code: {item_code}, type: {type(item_code)}")
		print(f"warehouse: {warehouse}, type: {type(warehouse)}")
		print(f"batches: {batches}, type: {type(batches)}")
		print(f"type_of_transaction: {type_of_transaction}")
		print("="*80)
		
		# Parse batches if it's a string (from JSON.stringify)
		if isinstance(batches, str):
			try:
				batches = json.loads(batches)
				frappe.logger().debug(f"Parsed batches from JSON string: {batches}")
			except json.JSONDecodeError as je:
				frappe.logger().error(f"Failed to parse batches JSON: {je}")
				frappe.throw(_("Invalid batches JSON format"))
		
		# frappe.whitelist() might have already parsed it
		frappe.logger().debug(f"Final batches type: {type(batches)}, value: {batches}")
		
		# Validate batches
		if not batches:
			frappe.throw(_("No batches provided"))
			
		if not isinstance(batches, list):
			frappe.throw(_(f"Batches must be a list, got {type(batches)}"))
			
		if len(batches) == 0:
			frappe.throw(_("Batches list is empty"))
		
		# Create the bundle (don't set voucher_type without voucher_no)
		frappe.logger().debug("Creating new Serial and Batch Bundle doc")
		
		# Import required utilities
		from frappe.utils import now_datetime
		
		# Get company from warehouse (required for validation)
		company = frappe.get_cached_value("Warehouse", warehouse, "company")
		if not company:
			frappe.throw(_("Warehouse {0} does not have a company set").format(warehouse))
		
		try:
			bundle_doc = frappe.get_doc({
				"doctype": "Serial and Batch Bundle",
				"item_code": item_code,
				"warehouse": warehouse,
				"company": company,  # Required for validation
				"type_of_transaction": type_of_transaction,
				"has_batch_no": 1,
				"has_serial_no": 0,
				"posting_datetime": now_datetime(),  # Required for validation
				"voucher_type": "POS Invoice",  # Required field, will be linked to actual invoice later
			})
			frappe.logger().debug(f"Bundle doc created successfully: {bundle_doc}")
		except Exception as e:
			frappe.logger().error(f"Error creating bundle doc: {e}")
			raise
		
		# Add entries for each batch
		frappe.logger().debug(f"Adding {len(batches)} batch entries")
		for i, batch in enumerate(batches):
			if not isinstance(batch, dict):
				frappe.logger().warning(f"Batch {i} is not a dict: {type(batch)}")
				continue
				
			batch_no = batch.get("batch_no")
			qty = batch.get("qty")
			
			if not batch_no or not qty:
				frappe.logger().warning(f"Batch {i} missing batch_no or qty")
				continue
			
			# For outward transactions, qty should be negative
			qty = float(qty)
			if type_of_transaction == "Outward":
				qty = -1 * abs(qty)
			
			frappe.logger().debug(f"Appending entry: batch_no={batch_no}, qty={qty}, warehouse={warehouse}")
			try:
				bundle_doc.append("entries", {
					"batch_no": batch_no,
					"qty": qty,
					"warehouse": warehouse
				})
			except Exception as e:
				frappe.logger().error(f"Error appending entry {i}: {e}")
				raise
		
		# Validate that we have entries
		if not bundle_doc.entries:
			frappe.throw(_("No valid batch entries to create bundle"))
		
		# Save the bundle
		frappe.logger().debug(f"Inserting bundle with {len(bundle_doc.entries)} entries")
		try:
			bundle_doc.insert(ignore_permissions=True)
			frappe.logger().debug(f"Bundle inserted successfully: {bundle_doc.name}")
		except Exception as e:
			frappe.logger().error(f"Error inserting bundle: {e}")
			frappe.logger().error(f"Traceback: {frappe.get_traceback()}")
			raise
		
		return {
			"success": True,
			"bundle_name": bundle_doc.name,
			"bundle_data": {
				"name": bundle_doc.name,
				"entries": [
					{
						"batch_no": entry.batch_no,
						"qty": abs(entry.qty),
						"warehouse": entry.warehouse
					}
					for entry in bundle_doc.entries
				]
			}
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "pos_next.api.serial_batch_bundle.create_batch_bundle")
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

