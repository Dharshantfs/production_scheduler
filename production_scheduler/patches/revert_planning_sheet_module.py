import frappe

def execute():
    """Revert Planning Sheet and Planning Sheet Item module back to Manufacturing.

    The module was accidentally changed to 'Production Planning', which broke
    visibility and routing for the Planning Sheet doctype.
    """
    # 1. Fix Planning Sheet module
    if frappe.db.exists("DocType", "Planning Sheet"):
        frappe.db.set_value("DocType", "Planning Sheet", "module", "Manufacturing")
        frappe.logger().info("Reverted Planning Sheet module to Manufacturing")

    # Also check lowercase variant used in some installations
    if frappe.db.exists("DocType", "Planning sheet"):
        frappe.db.set_value("DocType", "Planning sheet", "module", "Manufacturing")
        frappe.logger().info("Reverted Planning sheet module to Manufacturing")

    # 2. Fix Planning Sheet Item module
    if frappe.db.exists("DocType", "Planning Sheet Item"):
        frappe.db.set_value("DocType", "Planning Sheet Item", "module", "Manufacturing")
        frappe.logger().info("Reverted Planning Sheet Item module to Manufacturing")

    # 3. Clear caches so the change takes effect immediately
    frappe.clear_cache(doctype="Planning Sheet")
    frappe.clear_cache(doctype="Planning sheet")
    frappe.clear_cache(doctype="Planning Sheet Item")
    frappe.db.commit()

    frappe.logger().info("Planning Sheet module revert patch completed successfully")
