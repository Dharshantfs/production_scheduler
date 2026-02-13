frappe.provide("production_scheduler");

production_scheduler.Controller = class {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.make();
    }

    make() {
        const app = frappe.createApp({
            name: "ProductionScheduler",
            data() {
                return {
                    units: ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
                    limits: {
                        "Unit 1": 4.4,
                        "Unit 2": 12.0,
                        "Unit 3": 9.0,
                        "Unit 4": 5.5,
                    },
                    softLimits: {
                        "Unit 1": 4.0,
                        "Unit 2": 9.0,
                        "Unit 3": 7.8,
                        "Unit 4": 4.0,
                    },
                    cards: [],
                };
            },
            computed: {
                groupedCards() {
                    const grouped = {};
                    this.units.forEach((u) => (grouped[u] = []));
                    this.cards.forEach((c) => {
                        if (grouped[c.unit]) grouped[c.unit].push(c);
                    });
                    return grouped;
                },
            },
            methods: {
                fetchData() {
                    frappe.call({
                        method: "production_scheduler.production_scheduler.api.get_kanban_board",
                        args: {
                            start_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
                            end_date: frappe.datetime.add_months(frappe.datetime.get_today(), 1),
                        },
                        callback: (r) => {
                            if (r.message) {
                                this.cards = r.message;
                                this.$nextTick(() => this.initSortable());
                            }
                        },
                    });
                },
                getUnitTotal(unit) {
                    const totalKg = this.cards
                        .filter((c) => c.unit === unit)
                        .reduce((sum, c) => sum + (c.total_weight || 0), 0);
                    return totalKg / 1000;
                },
                getHeaderColor(unit) {
                    const total = this.getUnitTotal(unit);
                    if (total > this.limits[unit]) return "#e24c4c";
                    if (total > this.softLimits[unit]) return "#e8a317";
                    return "#28a745";
                },
                openForm(name) {
                    frappe.set_route("Form", "Planning Sheet", name);
                },
                initSortable() {
                    if (typeof Sortable === "undefined") return;
                    this.$el.querySelectorAll(".kanban-column-body").forEach((el) => {
                        if (el._sortable) return;
                        el._sortable = new Sortable(el, {
                            group: "kanban",
                            animation: 150,
                            onEnd: (evt) => {
                                const newUnit = evt.to.dataset.unit;
                                const docName = evt.item.dataset.name;
                                const oldUnit = evt.from.dataset.unit;
                                if (newUnit === oldUnit) return;

                                const card = this.cards.find((c) => c.name === docName);
                                const cardDate = card ? card.dod : frappe.datetime.get_today();

                                frappe.call({
                                    method: "production_scheduler.production_scheduler.api.update_schedule",
                                    args: { doc_name: docName, unit: newUnit, date: cardDate },
                                    error: () => this.fetchData(),
                                    callback: (r) => {
                                        if (r.exc) {
                                            this.fetchData();
                                        } else {
                                            if (card) card.unit = newUnit;
                                            frappe.show_alert({ message: "Moved to " + newUnit, indicator: "green" });
                                        }
                                    },
                                });
                            },
                        });
                    });
                },
            },
            mounted() {
                this.fetchData();
                frappe.realtime.on("doc_update", (data) => {
                    if (data.doctype === "Planning Sheet") {
                        this.fetchData();
                    }
                });
            },
            template: `
                <div class="kanban-board-container">
                    <div class="kanban-board">
                        <div v-for="unit in units" :key="unit" class="kanban-column">
                            <div class="kanban-column-header" :style="{ borderTopColor: getHeaderColor(unit) }">
                                <div class="header-title">{{ unit }}</div>
                                <div class="header-stats" :style="{ color: getHeaderColor(unit) }">
                                    {{ getUnitTotal(unit).toFixed(2) }}T / {{ limits[unit] }}T
                                </div>
                            </div>
                            <div class="kanban-column-body" :data-unit="unit">
                                <div
                                    v-for="card in groupedCards[unit]"
                                    :key="card.name"
                                    class="kanban-card"
                                    :data-name="card.name"
                                    @click="openForm(card.name)"
                                >
                                    <div class="card-row">
                                        <span class="card-customer">{{ card.customer }}</span>
                                        <span class="card-status" :class="(card.planning_status || '').toLowerCase()">
                                            {{ card.planning_status }}
                                        </span>
                                    </div>
                                    <div class="card-row text-muted">
                                        <span>{{ card.quality }}</span>
                                        <span>{{ card.gsm }} GSM</span>
                                    </div>
                                    <div class="card-row">
                                        <span class="card-weight">{{ (card.total_weight / 1000).toFixed(3) }} T</span>
                                        <span class="text-muted">{{ card.dod }}</span>
                                    </div>
                                </div>
                                <div v-if="groupedCards[unit].length === 0" class="empty-column">
                                    No items
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `,
        });
        app.mount(this.wrapper);
    }
};
