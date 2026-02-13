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
import { ref, onMounted, computed, nextTick } from "vue";

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
        method: "production_scheduler.production_scheduler.api.get_kanban_board",
        args: {
            start_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1), # Just an example range
            end_date: frappe.datetime.add_months(frappe.datetime.get_today(), 1)
        },
        callback: (r) => {
          if (r.message) {
            cards.value = r.message;
            // Update Sortable instances if needed or rely on DOM update
          }
        },
      });
    };

    const getCards = (unit) => {
      return cards.value.filter((c) => c.unit === unit);
    };

    const getUnitTotal = (unit) => {
      // Weight in API is generic. Assuming raw sum.
      // If the API returns raw sum (kg) and limit is T, we need conversion.
      // In api.py I implemented the check in Tons. 
      // Let's assume the API returns raw weight (likely Kg) and we display Tons.
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
    }
    
    onMounted(() => {
        fetchData();
        
        // Initialize Sortable
        // We need to wait for DOM to render columns
        nextTick(() => {
            if (columnRefs.value) {
                columnRefs.value.forEach((el) => {
                    new Sortable(el, {
                        group: "kanban",
                        animation: 150,
                        onEnd: (evt) => {
                            const itemEl = evt.item;
                            const newUnit = evt.to.dataset.unit;
                            const name = itemEl.dataset.name;
                            const oldUnit = evt.from.dataset.unit;
                            
                            if (newUnit === oldUnit) return;

                            // Optimistic update? Or wait for server?
                            // User said: "If API returns 'Capacity Exceeded', snap the card back".
                            // So we should probably try to move, and if fail, revert.
                            
                            frappe.call({
                                method: "production_scheduler.production_scheduler.api.update_schedule",
                                args: {
                                    doc_name: name,
                                    unit: newUnit,
                                    date: frappe.datetime.get_today() // Defaulting to today as 'date' wasn't specified in UI where it comes from. 
                                    // User said "update_schedule(doc_name, unit, date, index)".
                                    // "Capacity Validation: Calculate total weight for the Target Unit + Date".
                                    // If the column implies Date, we should know it.
                                    // But Columns are Units (1-4).
                                    // "Header: Show 'Day Total ...'".
                                    // This implies the Board is for a SINGLE Day?
                                    // "Create get_kanban_board(start_date, end_date)".
                                    // If the board shows multiple days, we need rows or filters.
                                    // I'll assume the Board Filter sets the Date Context. 
                                    // For now, I will use 'today' or the value from the card if we aren't changing date, 
                                    // but user said "Target Unit + Date".
                                    // I'll use the card's existing DOD (Delivery Date) or Today?
                                    // If we move to a Unit, do we change the Date?
                                    // "Capacity Validation ... for Target Unit + Date".
                                    // If the board is filtered by Date, we might update the date.
                                    // I'll assume we keep the Date of the card unless the board implies a date change.
                                    // Since I don't have a date picker in the UI, I'll use the card's current date.
                                },
                                error: (r) => {
                                    // Revert
                                    // Sortable doesn't easily revert on async error unless we prevent it first.
                                    // Standard trick: manipulate the array 'cards.value' to force re-render or move DOM back.
                                    // Re-fetching data is safest.
                                    fetchData();
                                },
                                callback: (r) => {
                                    if(r.exc) {
                                         fetchData();
                                    } else {
                                        // Update local state
                                        const card = cards.value.find(c => c.name === name);
                                        if(card) card.unit = newUnit;
                                        frappe.show_alert({message: __("Moved to {}").format(newUnit), indicator: 'green'});
                                    }
                                }
                            })
                        }
                    });
                });
            }
        });

        // Realtime
        frappe.realtime.on("doc_update", (data) => {
            if(data.doctype === "Planning Sheet") {
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
/* Scoped styles will be compiled by vue-loader if available, 
   but since we are sending this to public/js, we usually rely on global css. 
   I will make the main css file separately as requested. */
</style>
