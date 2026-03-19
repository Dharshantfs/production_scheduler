import frappe
from production_scheduler.api import generate_plan_code, _strip_legacy_prefixes

def debug_plan(name):
    frappe.connect()
    doc = frappe.get_doc("Planning sheet", name)
    print(f"Sheet: {doc.name}, Date: {doc.custom_planned_date or doc.ordered_date}, Plan: {doc.custom_plan_name}")
    
    active_plan = doc.custom_plan_name or "Default"
    sheet_date = doc.custom_planned_date or doc.ordered_date
    
    for i, item in enumerate(doc.items):
        item_date = item.custom_item_planned_date or sheet_date
        item_unit = item.unit
        code = generate_plan_code(item_date, item_unit, active_plan)
        print(f"Item {i+1}: Unit='{item_unit}', Date='{item_date}', Code='{code}'")
        if not code:
            print(f"  Debug: date_str={bool(item_date)}, plan_name={bool(active_plan)}, unit_val='{item_unit}'")

if __name__ == "__main__":
    debug_plan("PLAN-2026-00838")
