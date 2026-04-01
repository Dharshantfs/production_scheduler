import frappe


def execute():
    required = {
        "parent": "VARCHAR(140)",
        "parenttype": "VARCHAR(140)",
        "parentfield": "VARCHAR(140)",
        "idx": "INT NOT NULL DEFAULT 0",
    }

    doctypes = frappe.get_all("DocType", filters={"istable": 1}, pluck="name") or []
    for dt in doctypes:
        existing = set(frappe.db.get_table_columns(dt) or [])
        for col, ddl in required.items():
            if col not in existing:
                frappe.db.sql(f"ALTER TABLE `tab{dt}` ADD COLUMN `{col}` {ddl}")

    frappe.db.commit()
