<template>
  <div class="kanban-board-container">
    <div class="kanban-board">
      <div
        v-for="unit in units"
        :key="unit"
        class="kanban-column"
      >
        <div class="column-header" :style="{ borderTopColor: getHeaderColor(unit) }">
          <div class="header-title">{{ unit }}</div>
          <div class="header-stats" :style="{ color: getHeaderColor(unit) }">
            {{ getUnitTotal(unit).toFixed(2) }}T / {{ limits[unit] }}T
          </div>
        </div>
        <div
          class="column-body"
          ref="columnRefs"
          :data-unit="unit"
        >
          <div
            v-for="card in getCards(unit)"
            :key="card.name"
            class="kanban-card"
            :data-name="card.name"
            @click="openForm(card.name)"
          >
            <div class="card-row">
              <span class="card-title">{{ card.customer }}</span>
              <span class="card-status status-indicator" :class="card.planning_status.toLowerCase()">{{ card.planning_status }}</span>
            </div>
            <div class="card-row text-muted">
              <span>{{ card.quality }}</span>
              <span>{{ card.gsm }} GSM</span>
            </div>
            <div class="card-row">
              <span class="font-bold">{{ (card.total_weight / 1000).toFixed(3) }} T</span>
              <span class="text-muted">{{ card.dod }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick } from "vue";

export default {
  name: "ProductionScheduler",
  setup() {
    const units = ref(["Unit 1", "Unit 2", "Unit 3", "Unit 4"]);
    const limits = {
      "Unit 1": 4.4,
      "Unit 2": 12.0,
      "Unit 3": 9.0,
      "Unit 4": 5.5,
    };
    const softLimits = {
      "Unit 1": 4.0,
      "Unit 2": 9.0,
      "Unit 3": 7.8,
      "Unit 4": 4.0,
    };

    const cards = ref([]);
    const columnRefs = ref([]);

    const fetchData = () => {
      frappe.call({
        method: "production_scheduler.api.get_kanban_board",
        args: {
          start_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
          end_date: frappe.datetime.add_months(frappe.datetime.get_today(), 1)
        },
        callback: (r) => {
          if (r.message) {
            cards.value = r.message;
          }
        },
      });
    };

    const getCards = (unit) => {
      return cards.value.filter((c) => c.unit === unit);
    };

    const getUnitTotal = (unit) => {
      const totalKg = cards.value
        .filter((c) => c.unit === unit)
        .reduce((sum, c) => sum + (c.total_weight || 0), 0);
      return totalKg / 1000;
    };

    const getHeaderColor = (unit) => {
      const total = getUnitTotal(unit);
      if (total > limits[unit]) return "var(--red-500)";
      if (total > softLimits[unit]) return "var(--orange-500)";
      return "var(--green-500)";
    };

    const openForm = (name) => {
      frappe.set_route("Form", "Planning Sheet", name);
    };

    onMounted(() => {
      fetchData();

      // Initialize Sortable after DOM renders
      nextTick(() => {
        if (columnRefs.value) {
          columnRefs.value.forEach((el) => {
            new Sortable(el, {
              group: "kanban",
              animation: 150,
              onEnd: (evt) => {
                const itemEl = evt.item;
                const newUnit = evt.to.dataset.unit;
                const docName = itemEl.dataset.name;
                const oldUnit = evt.from.dataset.unit;

                if (newUnit === oldUnit) return;

                // Find the card to get its current date
                const card = cards.value.find((c) => c.name === docName);
                const cardDate = card ? card.dod : frappe.datetime.get_today();

                frappe.call({
                  method: "production_scheduler.api.update_schedule",
                  args: {
                    doc_name: docName,
                    unit: newUnit,
                    date: cardDate
                  },
                  error: () => {
                    // Revert on error by re-fetching
                    fetchData();
                  },
                  callback: (r) => {
                    if (r.exc) {
                      fetchData();
                    } else {
                      // Update local state
                      if (card) card.unit = newUnit;
                      frappe.show_alert({
                        message: "Moved to " + newUnit,
                        indicator: "green"
                      });
                    }
                  }
                });
              }
            });
          });
        }
      });

      // Realtime updates
      frappe.realtime.on("doc_update", (data) => {
        if (data.doctype === "Planning Sheet") {
          fetchData();
        }
      });
    });

    return {
      units,
      limits,
      columnRefs,
      getCards,
      getUnitTotal,
      getHeaderColor,
      openForm
    };
  },
};
</script>

<style scoped>
/* Styles are in production_scheduler.css */
</style>
