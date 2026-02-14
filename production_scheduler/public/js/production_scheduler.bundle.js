import { createApp } from "vue";
import ProductionScheduler from "./ProductionScheduler.vue";
import ColorChart from "./ColorChart.vue";

frappe.provide("production_scheduler");

production_scheduler.Controller = class {
    constructor(wrapper) {
        const app = createApp(ProductionScheduler);
        app.mount(wrapper);
    }
};

production_scheduler.ColorChartController = class {
    constructor(wrapper) {
        const app = createApp(ColorChart);
        app.mount(wrapper);
    }
};
