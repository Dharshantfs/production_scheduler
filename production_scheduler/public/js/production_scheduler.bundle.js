import { createApp } from "vue";
import ProductionScheduler from "./ProductionScheduler.vue";

class ProductionSchedulerController {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.app = createApp(ProductionScheduler);
        this.mount();
    }

    mount() {
        this.app.mount(this.wrapper);
    }
}

frappe.provide("production_scheduler");
production_scheduler.Controller = ProductionSchedulerController;

// Helper to render it easily
production_scheduler.render = function (wrapper) {
    new ProductionSchedulerController(wrapper);
};
