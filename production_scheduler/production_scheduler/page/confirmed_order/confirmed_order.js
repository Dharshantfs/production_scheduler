frappe.pages["confirmed-order"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Confirmed Order",
        single_column: true,
    });

    // Mount the Vue component
    new production_scheduler.ConfirmedOrderController(
        page.body.querySelector("#confirmed-order-app")
    );
};

