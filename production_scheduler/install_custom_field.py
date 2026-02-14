"""
Custom field installation for Production Scheduler
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """
    Creates custom field for order date tracking in Planning Sheet
    """
    custom_fields = {
        "Planning sheet": [
            {
                "fieldname": "custom_order_date",
                "label": "Order Date",
                "fieldtype": "Date",
                "insert_after": "dod",
                "description": "Date when the order was received",
                "allow_on_submit": 0,
                "search_index": 1,
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
    print("Custom field 'custom_order_date' created successfully for Planning sheet")
