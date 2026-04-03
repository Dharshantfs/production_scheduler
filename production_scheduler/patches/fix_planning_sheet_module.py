import frappe

def execute():
    """Fix Planning Sheet module back to Manufacturing.
    
    The module was accidentally changed to 'Production Planning'.
    Uses db_set to bypass validation and commit immediately.
    Handles both name variants (capital and lowercase S).
    """
    fixed = []

    for name in ["Planning Sheet", "Planning sheet"]:
        if frappe.db.exists("DocType", name):
            doc = frappe.get_doc("DocType", name)
            if doc.module != "Manufacturing":
                doc.db_set("module", "Manufacturing")
                fixed.append(name)

    for name in ["Planning Sheet Item", "Planning sheet Item"]:
        if frappe.db.exists("DocType", name):
            doc = frappe.get_doc("DocType", name)
            if doc.module != "Manufacturing":
                doc.db_set("module", "Manufacturing")
                fixed.append(name)

    if fixed:
        frappe.clear_cache()
    
    print(f"Fixed module for: {fixed}")
