// Custom Script for Shaft Production Run form
frappe.ui.form.on('Shaft Production Run', {
    refresh: function(frm) {
        // Auto-fill production_plan if it's new and not already set
        if (frm.is_new() && !frm.doc.production_plan) {
            // Try to get from URL parameters or session
            const urlParams = new URLSearchParams(window.location.search);
            const pp_id = urlParams.get('pp_id') || frappe.session_context?.production_plan;
            
            if (pp_id) {
                frm.set_value('production_plan', pp_id);
            }
        }
        
        // Show WO popup when production_plan is set
        if (frm.doc.production_plan) {
            show_linked_work_orders(frm.doc.production_plan);
        }
    },
    
    production_plan: function(frm) {
        // When PP is changed/set, show WO popup
        if (frm.doc.production_plan) {
            show_linked_work_orders(frm.doc.production_plan);
        }
    }
});

function show_linked_work_orders(pp_id) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Work Order',
            filters: {
                'production_plan': pp_id,
                'docstatus': ['<', 2]  // Draft or Submitted (not Cancelled)
            },
            fields: [
                'name',
                'production_item',
                'qty',
                'produced_qty',
                'status',
                'docstatus'
            ],
            order_by: 'creation asc'
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                show_wo_status_popup(r.message, pp_id);
            }
        }
    });
}

function show_wo_status_popup(work_orders, pp_id) {
    // Build HTML table for WO list
    let table_html = `
        <table class="table table-striped table-sm">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th>WO #</th>
                    <th>Item</th>
                    <th>Status</th>
                    <th>Target Qty</th>
                    <th>Produced Qty</th>
                    <th>Pending Qty</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    let total_target = 0;
    let total_produced = 0;
    let total_pending = 0;
    
    work_orders.forEach(wo => {
        const target_qty = flt(wo.qty);
        const produced_qty = flt(wo.produced_qty);
        const pending_qty = target_qty - produced_qty;
        
        total_target += target_qty;
        total_produced += produced_qty;
        total_pending += pending_qty;
        
        const status_badge = get_wo_status_badge(wo.status);
        
        table_html += `
            <tr>
                <td><strong>${wo.name}</strong></td>
                <td>${wo.production_item || '-'}</td>
                <td>${status_badge}</td>
                <td class="text-right">${format_number(target_qty, 2)}</td>
                <td class="text-right">${format_number(produced_qty, 2)}</td>
                <td class="text-right"><strong>${format_number(pending_qty, 2)}</strong></td>
            </tr>
        `;
    });
    
    table_html += `
            </tbody>
            <tfoot>
                <tr style="background-color: #f0f0f0; font-weight: bold;">
                    <td colspan="3">TOTAL</td>
                    <td class="text-right">${format_number(total_target, 2)}</td>
                    <td class="text-right">${format_number(total_produced, 2)}</td>
                    <td class="text-right">${format_number(total_pending, 2)}</td>
                </tr>
            </tfoot>
        </table>
    `;
    
    // Show dialog
    let d = new frappe.ui.Dialog({
        title: `📋 Work Orders for PP: ${pp_id}`,
        width: 900,
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'wo_list',
                options: table_html
            }
        ],
        primary_action_label: 'Close',
        primary_action(dialog) {
            dialog.hide();
        }
    });
    
    d.show();
}

function get_wo_status_badge(status) {
    const status_map = {
        'Not Started': '<span class="badge badge-secondary">Not Started</span>',
        'In Progress': '<span class="badge badge-primary">In Progress</span>',
        'Completed': '<span class="badge badge-success">Completed</span>',
        'Cancelled': '<span class="badge badge-danger">Cancelled</span>'
    };
    return status_map[status] || `<span class="badge badge-light">${status}</span>`;
}

function format_number(num, decimals) {
    return (flt(num) || 0).toFixed(decimals);
}
