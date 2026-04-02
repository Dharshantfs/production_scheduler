frappe.pages["confirmed-order"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Confirmed Order",
        single_column: true,
    });

    // Create the mount point for Vue (Proven pattern from color_chart.js)
    $(page.body).html('<div id="confirmed-order-app"></div>');

    // Mount the Vue component
    const mountEl = document.getElementById("confirmed-order-app");
    try {
        if (!production_scheduler || !production_scheduler.ConfirmedOrderController) {
            throw new Error("production_scheduler.ConfirmedOrderController is not available");
        }
        new production_scheduler.ConfirmedOrderController(mountEl);
    } catch (e) {
        console.error("ConfirmedOrder mount failed:", e);
        if (mountEl) {
            mountEl.innerHTML =
                '<div style="padding:16px;color:#b91c1c;font-weight:700;">Confirmed Order failed to load. Check console.</div>';
        }
    }
};


