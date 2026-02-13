import { createApp } from "vue";
import ProductionScheduler from "./ProductionScheduler.vue";

frappe.provide("production_scheduler");

production_scheduler.Controller = class {
    constructor(wrapper) {
        const app = createApp(ProductionScheduler);
        app.mount(wrapper);
    }
};
