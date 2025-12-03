# -*- coding: utf-8 -*-
# Copyright (c) 2024, POS Next and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_user_language():
	"""
	Get the language preference for the current user.

	Returns:
		dict: User's language preference

	Security checks:
	- User must be authenticated (not Guest)
	"""
	# Check if user is authenticated
	if frappe.session.user == "Guest":
		frappe.throw("Authentication required", frappe.AuthenticationError)

	# Get user's language preference
	language = frappe.db.get_value("User", frappe.session.user, "language") or "en"

	return {
		"success": True,
		"locale": language.lower()
	}


@frappe.whitelist()
def change_user_language(locale):
	"""
	Change the language preference for the current user.

	Args:
		locale (str): Language code (e.g., 'en', 'ar')

	Returns:
		dict: Success status and message

	Security checks:
	- User must be authenticated (not Guest)
	- User must be enabled
	"""
	# Check if user is authenticated
	if frappe.session.user == "Guest":
		frappe.throw("Authentication required", frappe.AuthenticationError)

	# Verify user is enabled
	if not frappe.db.get_value("User", frappe.session.user, "enabled"):
		frappe.throw("User is disabled", frappe.AuthenticationError)

	# Validate locale parameter
	if not locale:
		frappe.throw("Locale parameter is required", frappe.ValidationError)

	# Normalize locale to lowercase
	locale = locale.lower()

	allowed_locales = {'en', 'fr'}
	if locale not in allowed_locales:
		frappe.throw(f"Locale '{locale}' is not supported", frappe.ValidationError)

	# Update user's language preference
	try:
		frappe.db.set_value("User", frappe.session.user, "language", locale)
		frappe.db.commit()

		return {
			"success": True,
			"message": f"Language changed to {locale}",
			"locale": locale
		}
	except Exception as e:
		frappe.log_error(f"Failed to change user language: {str(e)}")
		frappe.throw(f"Failed to change language: {str(e)}", frappe.ValidationError)
