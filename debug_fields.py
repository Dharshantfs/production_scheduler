import frappe

def debug_split(item_name):
    frappe.init(site="develop")
    frappe.connect()
    
    # Get the original document
    doc = frappe.get_doc("Planning Table", item_name)
    print(f"DEBUG: Fields for {item_name}:")
    
    # List all fields and values to find the "Source PS" ID
    fields_found = []
    for d in doc.as_dict():
        val = doc.get(d)
        if val == doc.parent or (isinstance(val, str) and val.startswith("ag")):
            print(f"!!! FOUND POTENTIAL LINK: {d} = {val}")
        fields_found.append(f"{d}: {val}")
    
    # Just print the first 10 for overview
    for f in fields_found[:20]:
        print(f"  {f}")

if __name__ == "__main__":
    # Usually we would pass an actual item name from your screenshot, e.g. 'ag4983js-1'
    # But I can also just find any row in Planning Table
    rows = frappe.get_all("Planning Table", limit=1)
    if rows:
        debug_split(rows[0].name)
    else:
        print("No rows found in Planning Table")
