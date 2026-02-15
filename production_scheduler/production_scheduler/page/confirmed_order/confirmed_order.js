frappe.pages["confirmed-order"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Confirmed Order",
        single_column: true,
    });

    // Create the mount point for Vue
    $(page.body).html('<div id="confirmed-order-app"></div>');

    // Mount the Vue component
    new production_scheduler.ConfirmedOrderController(
        document.getElementById("confirmed-order-app")
    );
};
