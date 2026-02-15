
import frappe
from frappe.utils import getdate

def test_move_logic():
    # 1. Create Source Sheet
    source = frappe.new_doc("Planning sheet")
    source.ordered_date = getdate("2026-02-16")
    source.party_code = "TEST-PARTY"
    source.append("items", {
        "item_code": "ITEM-1",
        "qty": 2500,
        "unit": "Unit 4"
    })
    source.save()
    frappe.db.commit()
    print(f"Created Source: {source.name} with Item: {source.items[0].name}")

    item_name = source.items[0].name
    
    # 2. Simulate Move to Target (Partial Move logic)
    target_date = getdate("2026-02-15")
    target_unit = "Unit 1"
    
    # Find/Create Target
    target_sheet = frappe.new_doc("Planning sheet")
    target_sheet.ordered_date = target_date
    target_sheet.party_code = "TEST-PARTY"
    target_sheet.save()
    print(f"Created Target: {target_sheet.name}")

    # Move Item via SQL
    frappe.db.sql("""
        UPDATE `tabPlanning Sheet Item`
        SET parent = %s, idx = 1, unit = %s
        WHERE name = %s
    """, (target_sheet.name, target_unit, item_name))
    print("Executed SQL Update")

    # Reload and Save Target
    target_sheet.reload()
    print(f"Target Items after reload: {len(target_sheet.items)}")
    target_sheet.save()
    print("Saved Target")

    # Reload and Save Source
    source.reload()
    print(f"Source Items after reload: {len(source.items)}")
    source.save()
    print("Saved Source")
    
    # Verify Item Location
    item_doc = frappe.get_doc("Planning Sheet Item", item_name)
    print(f"Final Item Parent: {item_doc.parent}")
    print(f"Final Item Unit: {item_doc.unit}")
    
    if item_doc.parent != target_sheet.name:
        print("FAIL: Item did not move to target!")
    elif item_doc.unit != target_unit:
         print("FAIL: Item unit not updated!")
    else:
        print("SUCCESS: Item moved correctly.")

    # Cleanup
    frappe.delete_doc("Planning sheet", source.name)
    frappe.delete_doc("Planning sheet", target_sheet.name)

test_move_logic()
