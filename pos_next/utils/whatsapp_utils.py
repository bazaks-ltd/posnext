# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
WhatsApp Utility Functions for POS Next
Similar to KLiK PoS implementation
"""

import json

import frappe
from frappe import _
from frappe.desk.form.utils import get_pdf_link
from frappe.integrations.utils import make_post_request
from frappe.utils import get_url


def format_phone_number(number):
	"""Format phone number for WhatsApp API (remove + and spaces)"""
	if not number:
		return ""
	# Remove + and spaces
	cleaned = number.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
	return cleaned


def get_document_attachment_url(doctype, docname, print_format=None):
	"""Get PDF attachment URL for a document"""
	try:
		site_url = get_url()
		
		# Generate PDF and attach it
		if doctype == "Sales Invoice":
			pdf_url = generate_and_attach_invoice_pdf(docname, print_format)
			if pdf_url:
				return pdf_url
		
		# Fallback: Use document share key
		doc = frappe.get_doc(doctype, docname)
		key = doc.get_document_share_key()
		frappe.db.commit()
		
		if not print_format:
			print_format = "Standard"
		
		link = get_pdf_link(doctype, docname, print_format=print_format)
		
		# Check if we're using a local URL
		if "127.0.0.1" in site_url or "localhost" in site_url:
			frappe.logger().warning(
				f"Local URL detected: {site_url}. Document sharing may not work with WhatsApp API."
			)
			return None
		
		return f"{site_url}{link}&key={key}"
	except Exception as e:
		frappe.log_error(f"Error getting document attachment URL: {str(e)}", "WhatsApp Messaging")
		return None


def generate_and_attach_invoice_pdf(invoice_name, print_format="Standard"):
	"""
	Generate PDF for a Sales Invoice, attach it, and return full URL
	"""
	try:
		# Generate PDF content
		pdf_content = frappe.get_print("Sales Invoice", invoice_name, print_format, as_pdf=True)
		
		# Create File record in /files
		filedoc = frappe.get_doc({
			"doctype": "File",
			"file_name": f"{invoice_name}.pdf",
			"attached_to_doctype": "Sales Invoice",
			"attached_to_name": invoice_name,
			"content": pdf_content,
			"is_private": 0,
		})
		filedoc.save(ignore_permissions=True)
		
		# Return full URL to the file
		return get_url(filedoc.file_url)
		
	except Exception:
		frappe.log_error(frappe.get_traceback(), "generate_and_attach_invoice_pdf Failed")
		raise


@frappe.whitelist()
def send_whatsapp_message(
	to_number,
	message_type="text",
	message_content=None,
	template_name=None,
	template_parameters=None,
	reference_doctype=None,
	reference_name=None,
	attach_document=False,
):
	"""
	Standalone function to send WhatsApp messages (similar to KLiK PoS)
	
	Args:
		to_number (str): Phone number with country code (e.g., "1234567890")
		message_type (str): "text" or "template"
		message_content (str): Text message content (for text messages)
		template_name (str): Template name from WhatsApp Message Templates
		template_parameters (list): List of parameters for template
		reference_doctype (str): Reference doctype name
		reference_name (str): Reference document name
		attach_document (bool): Whether to attach document PDF
		
	Returns:
		dict: Response with success status and message details
	"""
	try:
		# Get WhatsApp settings
		if not frappe.db.exists("WhatsApp Setup", "WhatsApp Setup"):
			return {"success": False, "error": "WhatsApp Setup not found. Please configure WhatsApp Setup in POS Next."}
		
		settings = frappe.get_doc("WhatsApp Setup", "WhatsApp Setup")
		if not settings.enabled:
			return {"success": False, "error": "WhatsApp is not enabled"}
		
		token = settings.get_password("token")
		if not token:
			return {"success": False, "error": "WhatsApp token not configured"}
		
		# Format phone number
		formatted_number = format_phone_number(to_number)
		
		if message_type == "text":
			return send_text_message(
				formatted_number,
				message_content,
				settings,
				token,
				reference_doctype,
				reference_name,
				attach_document,
			)
		elif message_type == "template":
			return send_template_message(
				formatted_number,
				template_name,
				template_parameters,
				settings,
				token,
				reference_doctype,
				reference_name,
				attach_document,
			)
		else:
			return {
				"success": False,
				"error": f"Unsupported message type: {message_type}",
			}
			
	except Exception as e:
		frappe.log_error(f"WhatsApp Message Error: {str(e)}", "WhatsApp Messaging")
		return {"success": False, "error": str(e)}


def send_text_message(
	to_number,
	message_content,
	settings,
	token,
	reference_doctype=None,
	reference_name=None,
	attach_document=False,
):
	"""Send a simple text message with optional document attachment"""
	
	# If we need to attach a document, we need to send as a document message
	if attach_document and reference_doctype and reference_name:
		# Get document URL
		document_url = get_document_attachment_url(reference_doctype, reference_name)
		
		if document_url:
			data = {
				"messaging_product": "whatsapp",
				"to": to_number,
				"type": "document",
				"document": {
					"link": document_url,
					"filename": f"{reference_name}.pdf",
					"caption": message_content or "Invoice",
				},
			}
		else:
			# Fallback to text message with PDF generation instructions
			enhanced_message = f"{message_content or 'Your invoice'}\n\n📄 PDF Generation: Your invoice PDF is ready but cannot be sent via WhatsApp in development mode. Please contact support to get your PDF."
			data = {
				"messaging_product": "whatsapp",
				"to": to_number,
				"type": "text",
				"text": {"preview_url": True, "body": enhanced_message},
			}
	else:
		# Regular text message
		data = {
			"messaging_product": "whatsapp",
			"to": to_number,
			"type": "text",
			"text": {"preview_url": True, "body": message_content or "Message"},
		}
	
	return make_whatsapp_api_call(data, settings, token, reference_doctype, reference_name, "Manual")


def send_template_message(
	to_number,
	template_name,
	template_parameters,
	settings,
	token,
	reference_doctype=None,
	reference_name=None,
	attach_document=False,
):
	"""Send a template message"""
	
	# Get template details if template_name is provided
	if template_name and frappe.db.exists("WhatsApp Message Templates", template_name):
		template = frappe.get_doc("WhatsApp Message Templates", template_name)
		
		# Validate template parameters
		if template_parameters:
			# Ensure template_parameters is a list
			if isinstance(template_parameters, str):
				try:
					template_parameters = json.loads(template_parameters)
				except Exception:
					template_parameters = [template_parameters]
			
			# Validate each parameter
			validated_parameters = []
			for param in template_parameters:
				if param is not None:
					validated_parameters.append(str(param).strip())
				else:
					validated_parameters.append("")
			
			template_parameters = validated_parameters
		
		data = {
			"messaging_product": "whatsapp",
			"to": to_number,
			"type": "template",
			"template": {
				"name": template.actual_name or template.template_name,
				"language": {"code": template.language_code},
				"components": [],
			},
		}
		
		# Add body parameters if provided
		if template_parameters:
			parameters = []
			for param in template_parameters:
				param_text = str(param).strip()
				if param_text:
					parameters.append({"type": "text", "text": param_text})
			
			if parameters:
				data["template"]["components"].append({"type": "body", "parameters": parameters})
		
		# Handle attachments
		if attach_document and reference_doctype and reference_name:
			url = get_document_attachment_url(reference_doctype, reference_name)
			if url:
				data["template"]["components"].append(
					{
						"type": "header",
						"parameters": [
							{
								"type": "document",
								"document": {
									"link": url,
									"filename": f"{reference_name}.pdf",
								},
							}
						],
					}
				)
		
		return make_whatsapp_api_call(
			data,
			settings,
			token,
			reference_doctype,
			reference_name,
			"Template",
			template_name,
			template_parameters,
		)
	else:
		# No template - send as text message
		return send_text_message(
			to_number,
			"Your invoice is ready!",
			settings,
			token,
			reference_doctype,
			reference_name,
			attach_document,
		)


def make_whatsapp_api_call(
	data,
	settings,
	token,
	reference_doctype=None,
	reference_name=None,
	message_type="Manual",
	template_name=None,
	template_parameters=None,
):
	"""Make the actual API call to WhatsApp"""
	headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
	
	try:
		# Validate required settings
		if not settings.url:
			return {"success": False, "error": "WhatsApp URL is not configured"}
		if not settings.version:
			return {"success": False, "error": "WhatsApp API version is not configured"}
		if not settings.phone_id:
			return {"success": False, "error": "WhatsApp Phone ID is not configured"}
		if not token:
			return {"success": False, "error": "WhatsApp token is not configured"}
		
		# Validate phone number format
		if not data.get("to") or not data["to"].isdigit():
			return {
				"success": False,
				"error": f"Invalid phone number format: {data.get('to')}. Must be digits only (without +)",
			}
		
		# Make the API call
		response = make_post_request(
			f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
			headers=headers,
			data=json.dumps(data),
		)
		
		frappe.logger().debug(f"WhatsApp API Response: {json.dumps(response, indent=2)}")
		
		# Log communication
		_log_whatsapp_communication(
			data["to"],
			message_type,
			data,
			response,
			reference_doctype,
			reference_name,
			template_name,
			template_parameters,
		)
		
		return {
			"success": True,
			"message_id": response.get("messages", [{}])[0].get("id"),
		}
		
	except Exception as e:
		error_message = str(e)
		error_details = {}
		
		# Try to get detailed error information
		if frappe.flags.integration_request:
			try:
				error_response = frappe.flags.integration_request.json()
				error_details = error_response
				if "error" in error_response:
					error_message = error_response["error"].get(
						"message", error_response["error"].get("Error", error_message)
					)
			except Exception:
				pass
		
		# Log detailed error information
		frappe.log_error(
			f"WhatsApp API Error Details:\n"
			f"Error: {error_message}\n"
			f"URL: {settings.url}/{settings.version}/{settings.phone_id}/messages\n"
			f"Data: {json.dumps(data, indent=2)}\n"
			f"Error Details: {json.dumps(error_details, indent=2)}",
			"WhatsApp Messaging",
		)
		
		return {
			"success": False,
			"error": error_message,
			"error_details": error_details,
		}


def _log_whatsapp_communication(
	to_number,
	message_type,
	request_data,
	response,
	reference_doctype=None,
	reference_name=None,
	template_name=None,
	template_parameters=None,
):
	"""Log WhatsApp communication attempt"""
	try:
		# Create communication entry
		comm_doc = frappe.get_doc({
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "WhatsApp",
			"sent_or_received": "Sent",
			"content": request_data.get("text", {}).get("body") if request_data.get("type") == "text" else f"Template: {template_name}",
			"subject": _("Invoice Notification"),
			"sender": frappe.session.user,
			"recipients": to_number,
			"status": "Sent" if response.get("messages") else "Error",
		})
		
		if reference_doctype and reference_name:
			comm_doc.reference_doctype = reference_doctype
			comm_doc.reference_name = reference_name
		
		comm_doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		# Don't fail if logging fails
		pass

