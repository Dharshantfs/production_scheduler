frappe.pages["production-plan"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Production Plan",
        single_column: true,
    });

    // Create the mount point for Vue
    $(page.body).html('<div id="production-plan-app"></div>');

    // Mount the Vue component
    new production_scheduler.ProductionPlanController(
        document.getElementById("production-plan-app")
    );
};
