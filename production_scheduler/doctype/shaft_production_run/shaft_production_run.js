// Custom Script for Shaft Production Run form
frappe.ui.form.on('Shaft Production Run', {
    refresh: function(frm) {
        const forcedPopup = !!(frappe.route_options && cint(frappe.route_options.show_wo_popup));

        // Auto-fill production_plan if it's new and not already set
        if (frm.is_new() && !frm.doc.production_plan) {
            // Try to get from URL parameters or session
            const urlParams = new URLSearchParams(window.location.search);
            const pp_id = urlParams.get('pp_id') || frappe.session_context?.production_plan;
            
            if (pp_id) {
                frm.set_value('production_plan', pp_id);
            }
        }

        // If PP already exists on a new form, ensure Available Jobs are pulled from PP shaft details.
        if (frm.doc.production_plan) {
            load_available_jobs_from_pp(frm, { force: false });
        }
        
        // Show WO popup when production_plan is set
        if (frm.doc.production_plan) {
            show_linked_work_orders(frm.doc.production_plan);

            // Explicitly support redirected flow from Production Table -> Stock Entry -> SPR open.
            if (forcedPopup) {
                setTimeout(() => {
                    show_linked_work_orders(frm.doc.production_plan);
                }, 250);
                frappe.route_options = null;
            }
        }
    },
    
    production_plan: function(frm) {
        // When PP is changed/set, pull shaft details and show WO popup.
        if (frm.doc.production_plan) {
            load_available_jobs_from_pp(frm, { force: true });
            show_linked_work_orders(frm.doc.production_plan);
        } else if (frm.doc.shaft_jobs && frm.doc.shaft_jobs.length) {
            frm.clear_table('shaft_jobs');
            frm.refresh_field('shaft_jobs');
        }
    }
});

function should_skip_auto_fill(frm, force) {
    if (!frm.doc.production_plan) {
        return true;
    }

    if (frm.__spr_jobs_loading) {
        return true;
    }

    // Do not overwrite existing rows unless explicitly forced.
    if (!force && frm.doc.shaft_jobs && frm.doc.shaft_jobs.length > 0) {
        return true;
    }

    return false;
}

function load_available_jobs_from_pp(frm, opts = {}) {
    const force = !!opts.force;
    if (should_skip_auto_fill(frm, force)) {
        return;
    }

    frm.__spr_jobs_loading = true;

    frappe.call({
        method: 'production_scheduler.api.get_spr_shaft_jobs_from_pp',
        args: {
            pp_id: frm.doc.production_plan
        },
        freeze: false,
        callback: function(r) {
            frm.__spr_jobs_loading = false;
            const payload = r.message || {};

            if (payload.status !== 'ok') {
                if (payload.message) {
                    frappe.show_alert({
                        indicator: 'orange',
                        message: payload.message
                    }, 5);
                }
                return;
            }

            const jobs = Array.isArray(payload.jobs) ? payload.jobs : [];
            if (!jobs.length) {
                return;
            }

            frm.clear_table('shaft_jobs');

            jobs.forEach((job, idx) => {
                const row = frm.add_child('shaft_jobs');
                row.job_id = job.job_id || String(idx + 1);
                row.gsm = job.gsm || '';
                row.combination = job.combination || '';
                row.total_width = flt(job.total_width || 0);
                row.meter_roll_mtrs = flt(job.meter_roll_mtrs || 0);
                row.no_of_shafts = cint(job.no_of_shafts || 0);
                row.net_weight_shaft_kgs = flt(job.net_weight_shaft_kgs || 0);
                row.total_weight_kgs = flt(job.total_weight_kgs || 0);
            });

            frm.refresh_field('shaft_jobs');
            frm.__spr_jobs_loaded_pp = frm.doc.production_plan;

            if (!frm.doc.customer && payload.customer) {
                frm.set_value('customer', payload.customer);
            }

            if (!frm.doc.custom_order_code && payload.order_code) {
                frm.set_value('custom_order_code', payload.order_code);
            }
        },
        error: function() {
            frm.__spr_jobs_loading = false;
        }
    });
}

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
