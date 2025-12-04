# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
Communication Gateway Wrappers - WhatsApp, SMS, and Email
"""

import frappe
from frappe import _
from frappe.utils import cint


def send_whatsapp_message(mobile_no, message, attachment=None, reference_doctype=None, reference_name=None):
    """
    Send WhatsApp message using configured gateway (similar to KLiK PoS).
    
    Args:
        mobile_no: Recipient mobile number with country code
        message: Message text
        attachment: Optional file dict with 'fname' and 'fcontent' (deprecated, use reference_doctype/name)
        reference_doctype: Reference doctype (e.g., "Sales Invoice")
        reference_name: Reference document name
        
    Returns:
        dict: Success status and message/error
    """
    try:
        # Check if WhatsApp is configured
        if not _is_whatsapp_configured():
            return {
                "success": False,
                "error": _("WhatsApp gateway is not configured. Please configure WhatsApp Setup in POS Next.")
            }
        
        # Use WhatsApp utility function (similar to KLiK PoS)
        from pos_next.utils.whatsapp_utils import send_whatsapp_message as send_whatsapp
        
        # Determine if we should attach document
        attach_document = bool(reference_doctype and reference_name)
        
        # Send WhatsApp message
        result = send_whatsapp(
            to_number=mobile_no,
            message_type="text",
            message_content=message,
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            attach_document=attach_document,
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": _("WhatsApp message sent successfully"),
                "message_id": result.get("message_id")
            }
        else:
            return {
                "success": False,
                "error": result.get("error", _("Failed to send WhatsApp message"))
            }
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Send Error")
        return {
            "success": False,
            "error": str(e)
        }


def send_sms_message(mobile_no, message):
    """
    Send SMS using configured gateway.
    
    Args:
        mobile_no: Recipient mobile number
        message: Message text
        
    Returns:
        dict: Success status and message/error
    """
    try:
        # Check if SMS Settings are configured
        if not _is_sms_configured():
            return {
                "success": False,
                "error": _("SMS gateway is not configured. Please configure SMS Settings in ERPNext.")
            }
        
        # Use Frappe's SMS integration
        try:
            from frappe.core.doctype.sms_settings.sms_settings import send_sms
            
            # Send SMS
            result = send_sms([mobile_no], message)
            
            if result:
                return {
                    "success": True,
                    "message": _("SMS sent successfully")
                }
            else:
                return {
                    "success": False,
                    "error": _("Failed to send SMS")
                }
                
        except ImportError:
            # SMS Settings not available
            return {
                "success": False,
                "error": _("SMS functionality is not available. Please install SMS integration.")
            }
        except Exception as e:
            frappe.log_error(f"SMS send error: {str(e)}", "SMS Gateway")
            return {
                "success": False,
                "error": str(e)
            }
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "SMS Send Error")
        return {
            "success": False,
            "error": str(e)
        }


def send_email_with_attachment(email, subject, message, attachments=None):
    """
    Send email with PDF attachment.
    
    Args:
        email: Recipient email address
        subject: Email subject
        message: Email body (HTML or plain text)
        attachments: List of file dicts with 'fname' and 'fcontent'
        
    Returns:
        dict: Success status and message/error
    """
    try:
        if not attachments:
            attachments = []
        
        # Use frappe.sendmail
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message,
            attachments=attachments,
            now=True
        )
        
        return {
            "success": True,
            "message": _("Email sent successfully")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Email Send Error")
        return {
            "success": False,
            "error": str(e)
        }


# Helper functions

def _is_whatsapp_configured():
    """Check if WhatsApp gateway is configured (using WhatsApp Setup doctype)."""
    try:
        # Check if WhatsApp Setup doctype exists (similar to KLiK PoS)
        if frappe.db.exists("WhatsApp Setup", "WhatsApp Setup"):
            settings = frappe.get_doc("WhatsApp Setup", "WhatsApp Setup")
            if not cint(settings.enabled):
                return False
            
            # Check if required fields are configured
            token = settings.get_password("token")
            if not token:
                return False
            if not settings.url or not settings.version or not settings.phone_id:
                return False
            
            return True
        
        return False
        
    except Exception:
        return False


def _is_sms_configured():
    """Check if SMS gateway is configured."""
    try:
        # Check SMS Settings
        if frappe.db.exists("DocType", "SMS Settings"):
            settings = frappe.get_single("SMS Settings")
            # Check if any gateway is configured
            if settings.sms_gateway_url:
                return True
        
        return False
        
    except Exception:
        return False

