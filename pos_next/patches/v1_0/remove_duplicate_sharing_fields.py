# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
Patch to remove duplicate invoice sharing custom fields
Removes old fields with _sharing suffix that were causing duplicates
"""

import frappe


def execute():
	"""Remove duplicate custom fields with _sharing suffix"""
	
	# List of duplicate fields to remove
	duplicate_fields = [
		"POS Profile-custom_enable_whatsapp_sharing",
		"POS Profile-custom_enable_sms_sharing",
		"POS Profile-custom_enable_email_sharing",
	]
	
	for field_name in duplicate_fields:
		if frappe.db.exists("Custom Field", field_name):
			try:
				frappe.delete_doc("Custom Field", field_name, force=1)
				frappe.db.commit()
				print(f"Removed duplicate field: {field_name}")
			except Exception as e:
				print(f"Error removing field {field_name}: {str(e)}")
				frappe.db.rollback()
	
	# Clear cache to ensure changes are reflected
	frappe.clear_cache(doctype="POS Profile")
	print("Patch executed: Removed duplicate sharing fields")

