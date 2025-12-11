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
    Send invoice via WhatsApp with protected link (no expiry).
    Accepts frontend payload and sends invoice WhatsApp message with protected printview link.
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
        
        # Generate protected printview URL (no expiry for WhatsApp)
        protected_url = get_protected_printview_url(
            doctype="Sales Invoice",
            name=invoice_no,
            print_format=print_format,
            no_letterhead=1,
            lang="en",
            no_expiry=True
        )
        
        # Add link to message
        message_with_link = f"{message_text}\n\nView your invoice: {protected_url}"
        
        # Use WhatsApp utility function (similar to KLiK PoS)
        from pos_next.utils.whatsapp_utils import send_whatsapp_message
        
        # Send WhatsApp message with link (no PDF attachment)
        result = send_whatsapp_message(
            to_number=mobile,
            message_type="text",
            message_content=message_with_link,
            reference_doctype="Sales Invoice",
            reference_name=invoice_no,
            attach_document=False,
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
                "url": protected_url,
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
    Send invoice via Email with protected link (similar to KLiK PoS).
    Accepts frontend payload and sends invoice email with protected printview link.
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
        
        # Format invoice amount
        from frappe.utils import fmt_money
        invoice_amount = fmt_money(doc.rounded_total or doc.grand_total, currency=doc.currency)
        
        # Generate protected printview URL (with default expiry, typically 90 days)
        protected_url = get_protected_printview_url(
            doctype="Sales Invoice",
            name=invoice_no,
            print_format=print_format,
            no_letterhead=1,
            lang="en"
        )
        
        # Create email subject and message with link
        subject = _("Invoice {0} from {1}").format(doc.name, frappe.defaults.get_user_default('Company'))
        message = f"""
			<p>Dear {customer_name or 'Customer'},</p>
			<p>Please find your invoice <b>{doc.name}</b> at the link below.</p>
			<p>The total amount due is <b>{invoice_amount}</b>.</p>
			<p><a href="{protected_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">View Invoice</a></p>
			<p>Or copy this link: <br><a href="{protected_url}">{protected_url}</a></p>
			<p>Thank you for your business.</p>
			<br>
		"""
        
        # Send email synchronously (blocking) - not queued, no attachments
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message
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
            "url": protected_url,
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

def get_protected_printview_url(doctype, name, print_format="Standard", no_letterhead=1, lang="en", expires_in_days=None, no_expiry=False):
    """
    Generate a protected printview URL with document share key.
    
    Args:
        doctype: Document type (e.g., "Sales Invoice")
        name: Document name
        print_format: Print format name (default: "Standard")
        no_letterhead: Whether to exclude letterhead (default: 1)
        lang: Language code (default: "en")
        expires_in_days: Number of days until expiry (None for default, typically 90 days)
        no_expiry: If True, key never expires (default: False)
        
    Returns:
        str: Full protected printview URL with share key
    """
    try:
        doc = frappe.get_doc(doctype, name)
        
        # Generate share key (no expiry if requested)
        if no_expiry:
            key = doc.get_document_share_key(no_expiry=True)
        elif expires_in_days:
            expires_on = frappe.utils.add_days(None, expires_in_days)
            key = doc.get_document_share_key(expires_on=expires_on)
        else:
            # Use default expiry (typically 90 days)
            key = doc.get_document_share_key()
        
        frappe.db.commit()
        
        # Build printview URL
        base_url = get_url()
        url = f"{base_url}/printview?doctype={doctype}&name={name}&format={print_format}&no_letterhead={no_letterhead}&_lang={lang}&key={key}"
        
        return url
    except Exception as e:
        frappe.log_error(f"Error generating protected printview URL: {str(e)}", "Invoice Sharing")
        raise

