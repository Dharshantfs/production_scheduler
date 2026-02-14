// Client Script for Planning Sheet
// This auto-fetches the order date from Sales Order when Sales Order field is filled

frappe.ui.form.on('Planning sheet', {
    sales_order: function (frm) {
        if (frm.doc.sales_order && !frm.doc.ordered_date) {
            // Fetch transaction_date from Sales Order
            frappe.db.get_value('Sales Order', frm.doc.sales_order, 'transaction_date', (r) => {
                if (r && r.transaction_date) {
                    frm.set_value('ordered_date', r.transaction_date);
                    frappe.show_alert({
                        message: 'Order Date auto-filled from Sales Order',
                        indicator: 'green'
                    });
                }
            });
        }
    },

    refresh: function (frm) {
        // Auto-fetch on form load if sales_order exists but ordered_date is empty
        if (frm.doc.sales_order && !frm.doc.ordered_date && !frm.is_new()) {
            frappe.db.get_value('Sales Order', frm.doc.sales_order, 'transaction_date', (r) => {
                if (r && r.transaction_date) {
                    frm.set_value('ordered_date', r.transaction_date);
                }
            });
        }
    }
});
