# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
Invoice Sharing API - Native WhatsApp, SMS, and Email sharing for invoices
"""

import json
import frappe
from frappe import _
from frappe.utils import get_url, cint


@frappe.whitelist()
def send_invoice_whatsapp(**kwargs):
    """
    Send invoice via WhatsApp with PDF attachment (similar to KLiK PoS).
    Accepts frontend payload and sends invoice WhatsApp message with PDF attachment.
    """
    data = kwargs
    
    mobile = data.get("mobile_no")
    customer_name = data.get("customer_name")
    invoice_no = data.get("invoice_data") or data.get("invoice_name")
    message_text = data.get("message", "Your invoice is ready!")
    
    if not (mobile and invoice_no):
        frappe.throw(_("Mobile number and invoice number are required."))
    
    try:
        doc = frappe.get_doc("Sales Invoice", invoice_no)
        
        # Get POS Profile configuration
        pos_profile = doc.pos_profile or data.get("pos_profile")
        print_format = None
        
        if pos_profile:
            # Check if WhatsApp is enabled
            whatsapp_enabled = cint(frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "custom_enable_whatsapp"
            ))
            
            if not whatsapp_enabled:
                frappe.throw(_("WhatsApp sharing is not enabled for this POS Profile"))
            
            # Get print format
            print_format = frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "custom_default_print_format"
            ) or "Standard"
        else:
            print_format = "Standard"
        
        # Format invoice amount
        from frappe.utils import fmt_money
        invoice_amount = fmt_money(doc.rounded_total or doc.grand_total, currency=doc.currency)
        
        # Use WhatsApp utility function (similar to KLiK PoS)
        from pos_next.utils.whatsapp_utils import send_whatsapp_message
        
        # Send WhatsApp message with document attachment
        result = send_whatsapp_message(
            to_number=mobile,
            message_type="text",
            message_content=message_text,
            reference_doctype="Sales Invoice",
            reference_name=invoice_no,
            attach_document=True,
        )
        
        if result.get("success"):
            return {
                "status": "success",
                "recipient": mobile,
                "invoice": invoice_no,
                "amount": invoice_amount,
                "print_format": print_format,
                "message_id": result.get("message_id"),
                "timestamp": frappe.utils.now(),
            }
        else:
            frappe.throw(_("Failed to send WhatsApp message: {0}").format(result.get("error")))
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Send Invoice WhatsApp Failed")
        frappe.throw(_("Failed to send WhatsApp message: {0}").format(str(e)))


@frappe.whitelist()
def send_invoice_sms(**kwargs):
    """
    Send invoice via SMS (similar to KLiK PoS).
    Accepts frontend payload and sends invoice SMS using ERPNext's built-in SMS functionality.
    """
    data = kwargs
    
    mobile = data.get("mobile_no")
    customer_name = data.get("customer_name")
    invoice_no = data.get("invoice_data") or data.get("invoice_name")
    message_text = data.get("message", "Your invoice is ready!")
    
    if not (mobile and invoice_no):
        frappe.throw(_("Mobile number and invoice number are required."))
    
    try:
        doc = frappe.get_doc("Sales Invoice", invoice_no)
        
        # Get POS Profile configuration
        pos_profile = doc.pos_profile or data.get("pos_profile")
        print_format = None
        
        if pos_profile:
            # Check if SMS is enabled
            sms_enabled = cint(frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "custom_enable_sms"
            ))
            
            if not sms_enabled:
                frappe.throw(_("SMS sharing is not enabled for this POS Profile"))
            
            # Get print format
            print_format = frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "custom_default_print_format"
            ) or "Standard"
        else:
            print_format = "Standard"
        
        # Format invoice amount
        from frappe.utils import fmt_money
        invoice_amount = fmt_money(doc.rounded_total or doc.grand_total, currency=doc.currency)
        
        # Create SMS message with invoice details
        sms_message = f"""
Hi {customer_name or 'Customer'}!
Thank you for your purchase at {frappe.defaults.get_user_default('Company')}.
Invoice: {doc.name}
Amount: {invoice_amount}
Thank you!
        """.strip()
        
        # Use custom message if provided
        if message_text and message_text != "Your invoice is ready!":
            sms_message = message_text
        
        # Send SMS using ERPNext's built-in SMS functionality
        from frappe.core.doctype.sms_settings.sms_settings import send_sms
        send_sms(receiver_list=[mobile], msg=sms_message, success_msg=True)
        
        return {
            "status": "success",
            "recipient": mobile,
            "invoice": invoice_no,
            "amount": invoice_amount,
            "print_format": print_format,
            "message": sms_message,
            "timestamp": frappe.utils.now(),
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Send Invoice SMS Failed")
        frappe.throw(_("Failed to send SMS: {0}").format(str(e)))


@frappe.whitelist()
def send_invoice_email(**kwargs):
    """
    Send invoice via Email with PDF attachment (similar to KLiK PoS).
    Accepts frontend payload and sends invoice email with PDF attachment.
    """
    data = kwargs
    
    email = data.get("email")
    customer_name = data.get("customer_name")
    invoice_no = data.get("invoice_data") or data.get("invoice_name")
    
    if not (email and invoice_no):
        frappe.throw(_("Email and invoice number are required."))
    
    try:
        doc = frappe.get_doc("Sales Invoice", invoice_no)
        
        # Get POS Profile configuration
        pos_profile = doc.pos_profile or data.get("pos_profile")
        print_format = None
        
        if pos_profile:
            # Check if Email is enabled
            email_enabled = cint(frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "custom_enable_email"
            ))
            
            if not email_enabled:
                frappe.throw(_("Email sharing is not enabled for this POS Profile"))
            
            # Get print format
            print_format = frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "custom_default_print_format"
            ) or "Standard"
        else:
            print_format = "Standard"
        
        # Generate PDF
        pdf_data = frappe.get_print("Sales Invoice", doc.name, print_format=print_format, as_pdf=True)
        
        # Format invoice amount
        from frappe.utils import fmt_money
        invoice_amount = fmt_money(doc.rounded_total or doc.grand_total, currency=doc.currency)
        
        # Create email subject and message
        subject = _("Invoice {0} from {1}").format(doc.name, frappe.defaults.get_user_default('Company'))
        message = f"""
			<p>Dear {customer_name or 'Customer'},</p>
			<p>Please find attached your invoice <b>{doc.name}</b>.</p>
			<p>The total amount due is <b>{invoice_amount}</b>.</p>
			<p>Thank you for your business.</p>
			<br>
		"""
        
        attachments = [{"fname": f"{doc.name}.pdf", "fcontent": pdf_data}]
        
        # Send email synchronously (blocking) - not queued
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message,
            attachments=attachments,
        )
        
        # Return after email is sent
        return {
            "status": "success",
            "recipients": [email],
            "invoice": invoice_no,
            "amount": invoice_amount,
            "print_format": print_format,
            "timestamp": frappe.utils.now(),
            "message": _("Email sent successfully"),
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Send Invoice Email Failed")
        frappe.throw(_("Failed to send invoice email: {0}").format(str(e)))


@frappe.whitelist()
def get_sharing_options(pos_profile, invoice_name=None):
    """
    Get available sharing options for a POS Profile.
    
    Args:
        pos_profile: POS Profile name
        invoice_name: Optional invoice name to get customer details
        
    Returns:
        dict: Available sharing channels and customer contact info
    """
    try:
        if not frappe.db.exists("POS Profile", pos_profile):
            frappe.throw(_("POS Profile {0} does not exist").format(pos_profile))
        
        # Get sharing configuration (matching KLiK PoS field names)
        # Try multiple methods to get custom field values
        profile_doc = frappe.get_doc("POS Profile", pos_profile)
        
        # Method 1: Try direct attribute access
        whatsapp_enabled = getattr(profile_doc, "custom_enable_whatsapp", None)
        sms_enabled = getattr(profile_doc, "custom_enable_sms", None)
        email_enabled = getattr(profile_doc, "custom_enable_email", None)
        
        # Method 2: If not found, try database query
        if whatsapp_enabled is None:
            whatsapp_enabled = frappe.db.get_value("POS Profile", pos_profile, "custom_enable_whatsapp") or 0
        if sms_enabled is None:
            sms_enabled = frappe.db.get_value("POS Profile", pos_profile, "custom_enable_sms") or 0
        if email_enabled is None:
            email_enabled = frappe.db.get_value("POS Profile", pos_profile, "custom_enable_email") or 0
        
        # Convert to integer (handles both string "1"/"0" and integer 1/0, and None)
        whatsapp_enabled = cint(whatsapp_enabled) if whatsapp_enabled is not None else 0
        sms_enabled = cint(sms_enabled) if sms_enabled is not None else 0
        email_enabled = cint(email_enabled) if email_enabled is not None else 0
        
        # Get template values
        whatsapp_template = getattr(profile_doc, "custom_whatsapp_template", None) or frappe.db.get_value("POS Profile", pos_profile, "custom_whatsapp_template")
        sms_template = getattr(profile_doc, "custom_sms_template", None) or frappe.db.get_value("POS Profile", pos_profile, "custom_sms_template")
        email_template = getattr(profile_doc, "custom_email_template", None) or frappe.db.get_value("POS Profile", pos_profile, "custom_email_template")
        print_format = getattr(profile_doc, "custom_default_print_format", None) or frappe.db.get_value("POS Profile", pos_profile, "custom_default_print_format")
        
        options = {
            "whatsapp": {
                "enabled": whatsapp_enabled,
                "template": whatsapp_template,
            },
            "sms": {
                "enabled": sms_enabled,
                "template": sms_template,
            },
            "email": {
                "enabled": email_enabled,
                "template": email_template,
            },
            "print_format": print_format,
        }
        
        # Debug logging
        frappe.logger().info(f"Sharing options for {pos_profile}: WhatsApp={whatsapp_enabled}, SMS={sms_enabled}, Email={email_enabled}")
        
        # Get customer contact details if invoice provided
        if invoice_name and frappe.db.exists("Sales Invoice", invoice_name):
            invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
            customer = invoice_doc.customer
            
            if customer and frappe.db.exists("Customer", customer):
                customer_doc = frappe.get_doc("Customer", customer)
                
                # Get primary contact
                primary_contact = None
                if customer_doc.customer_primary_contact:
                    primary_contact = frappe.get_doc("Contact", customer_doc.customer_primary_contact)
                
                options["customer"] = {
                    "name": customer,
                    "customer_name": customer_doc.customer_name,
                    "mobile_no": customer_doc.mobile_no or (primary_contact.mobile_no if primary_contact else None),
                    "email_id": customer_doc.email_id or (primary_contact.email_id if primary_contact else None),
                }
        
        return options
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Sharing Options Error")
        return {
            "whatsapp": {"enabled": False},
            "sms": {"enabled": False},
            "email": {"enabled": False},
        }


@frappe.whitelist()
def download_invoice_pdf(invoice_name, print_format=None, pos_profile=None):
    """
    Download invoice as PDF file.
    
    Args:
        invoice_name: Name of the Sales Invoice
        print_format: Optional print format (defaults to POS Profile setting or "Standard")
        pos_profile: Optional POS Profile name to get print format from
        
    Returns:
        PDF file download response
    """
    try:
        if not invoice_name:
            frappe.throw(_("Invoice name is required"))
        
        # Validate invoice exists
        if not frappe.db.exists("Sales Invoice", invoice_name):
            frappe.throw(_("Invoice {0} not found").format(invoice_name))
        
        doc = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Get print format from POS Profile if not provided
        if not print_format and pos_profile:
            print_format = frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "custom_default_print_format"
            ) or frappe.db.get_value(
                "POS Profile",
                pos_profile,
                "print_format"
            )
        
        # Default to Standard if still no format
        if not print_format:
            print_format = "Standard"
        
        # Generate PDF using Frappe's built-in function
        from frappe.utils.print_format import download_pdf
        
        # This will set frappe.local.response for file download
        download_pdf(
            doctype="Sales Invoice",
            name=invoice_name,
            format=print_format,
            doc=doc
        )
        
        return {
            "status": "success",
            "message": _("PDF download initiated")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Download Invoice PDF Failed")
        frappe.throw(_("Failed to download invoice PDF: {0}").format(str(e)))


@frappe.whitelist()
def validate_contact_info(contact, channel):
    """
    Validate contact information format.
    
    Args:
        contact: Contact information (phone/email)
        channel: Communication channel (whatsapp, sms, email)
        
    Returns:
        dict: Validation result
    """
    try:
        import re
        
        if channel in ["whatsapp", "sms"]:
            # Validate phone number
            # Basic validation: should contain only digits, +, -, (), spaces
            phone_pattern = r'^[\d\s\+\-\(\)]+$'
            if not re.match(phone_pattern, contact):
                return {
                    "valid": False,
                    "message": _("Invalid phone number format. Use format: +1234567890")
                }
            
            # Remove formatting
            cleaned = re.sub(r'[\s\-\(\)]', '', contact)
            
            # Should have at least 10 digits
            if len(re.findall(r'\d', cleaned)) < 10:
                return {
                    "valid": False,
                    "message": _("Phone number should have at least 10 digits")
                }
            
        elif channel == "email":
            # Validate email
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, contact):
                return {
                    "valid": False,
                    "message": _("Invalid email address format")
                }
        
        return {
            "valid": True,
            "message": _("Valid contact information")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Validate Contact Info Error")
        return {
            "valid": False,
            "message": str(e)
        }


# Helper functions


