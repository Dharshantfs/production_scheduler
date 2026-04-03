import frappe

def inspect():
    meta = frappe.get_meta("Planning Table")
    print("FIELDS FOR Planning Table:")
    for f in meta.fields:
        print(f"- {f.fieldname}: {f.label} ({f.fieldtype})")

if __name__ == "__main__":
    frappe.init(site="develop") # Adjusting for local environment if needed, but usually just frappe.connect()
    # Or just print via frappe call if this is a script
    inspect()
