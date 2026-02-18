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

import ConfirmedOrder from "./ConfirmedOrder.vue";
import ProductionPlan from "./ProductionPlan.vue";

production_scheduler.ConfirmedOrderController = class {
    constructor(wrapper) {
        const app = createApp(ConfirmedOrder);
        app.mount(wrapper);
    }
};

production_scheduler.ProductionPlanController = class {
    constructor(wrapper) {
        const app = createApp(ProductionPlan);
        app.mount(wrapper);
    }
};
