import frappe

def execute():
    """Fix Planning Sheet module back to Manufacturing.
    
    The module was accidentally changed to 'Production Planning' which doesn't
    exist in any installed app, causing ImportError when creating Planning Sheets.
    Uses raw SQL to guarantee the fix works regardless of controller state.
    """
    # Raw SQL - guaranteed to work in patch context, no controller import needed
    frappe.db.sql("UPDATE `tabDocType` SET module='Manufacturing' WHERE name='Planning Sheet'")
    frappe.db.sql("UPDATE `tabDocType` SET module='Manufacturing' WHERE name='Planning sheet'")
    frappe.db.sql("UPDATE `tabDocType` SET module='Manufacturing' WHERE name='Planning Sheet Item'")
    frappe.db.sql("UPDATE `tabDocType` SET module='Manufacturing' WHERE name='Planning sheet Item'")
    frappe.db.commit()
    frappe.clear_cache()
