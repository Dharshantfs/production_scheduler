<template>
  <div class="ps-container">
    <!-- Filter Bar -->
    <div class="ps-filters">
      <div class="ps-filter-item">
        <label>Delivery Date</label>
        <input type="date" v-model="filterDate" />
      </div>
      <div class="ps-filter-item">
        <label>Order Date</label>
        <input type="date" v-model="filterOrderDate" />
      </div>
      <div class="ps-filter-item">
        <label>Party Code</label>
        <input
          type="text"
          v-model="filterPartyCode"
          placeholder="Search party..."
        />
      </div>
      <div class="ps-filter-item">
        <label>Unit</label>
        <select v-model="filterUnit">
          <option value="">All Units</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
      </div>
      <div class="ps-filter-item">
        <label>Status</label>
        <select v-model="filterStatus">
          <option value="">All</option>
          <option value="Draft">Draft</option>
          <option value="Finalized">Finalized</option>
        </select>
      </div>
      <button class="ps-clear-btn" @click="clearFilters">✕ Clear</button>
    </div>

    <!-- Kanban Board -->
    <div class="ps-board">
      <div
        v-for="unit in visibleUnits"
        :key="unit"
        class="ps-column"
      >
        <div
          class="ps-col-header"
          :style="{ borderTopColor: getHeaderColor(unit) }"
        >
          <span class="ps-col-title">{{ unit }}</span>
          <span class="ps-col-stat" :style="{ color: getHeaderColor(unit) }">
            {{ getUnitTotal(unit).toFixed(2) }}T / {{ limits[unit] }}T
          </span>
        </div>
        <div class="ps-col-body" :data-unit="unit" ref="columnRefs">
          <div
            v-for="card in groupedCards[unit]"
            :key="card.name"
            class="ps-card"
            :data-name="card.name"
            @click="openForm(card.name)"
          >
            <div class="ps-card-top">
              <span class="ps-card-customer">{{ card.customer }}</span>
              <span
                class="ps-badge"
                :class="(card.planning_status || '').toLowerCase()"
              >{{ card.planning_status }}</span>
            </div>
            <div class="ps-card-party">{{ card.party_code }}</div>

            <table class="ps-item-table" v-if="card.items && card.items.length">
              <tr v-for="(item, idx) in card.items" :key="idx">
                <td class="ps-td-quality">{{ item.quality }}</td>
                <td class="ps-td-color">{{ item.color }}</td>
                <td class="ps-td-gsm">{{ item.gsm }} GSM</td>
                <td class="ps-td-qty">{{ item.qty }} Kg</td>
              </tr>
            </table>

            <div class="ps-card-bottom">
              <span class="ps-card-weight">{{ (card.total_weight / 1000).toFixed(3) }} T</span>
              <div class="ps-card-dates">
                <span v-if="card.ordered_date" class="ps-card-date-item">
                  <span class="ps-date-label">Order:</span> {{ card.ordered_date }}
                </span>
                <span class="ps-card-date-item">
                  <span class="ps-date-label">Delivery:</span> {{ card.dod }}
                </span>
              </div>
            </div>
          </div>
          <div v-if="!groupedCards[unit] || groupedCards[unit].length === 0" class="ps-empty">
            No items
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from "vue";

const units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4"];
const limits = { "Unit 1": 4.4, "Unit 2": 12.0, "Unit 3": 9.0, "Unit 4": 5.5 };
const softLimits = { "Unit 1": 4.0, "Unit 2": 9.0, "Unit 3": 7.8, "Unit 4": 4.0 };

const cards = ref([]);
const columnRefs = ref(null);
const filterDate = ref(frappe.datetime.get_today());
const filterOrderDate = ref("");
const filterPartyCode = ref("");
const filterUnit = ref("");
const filterStatus = ref("");

const filteredCards = computed(() => {
  let result = cards.value;
  if (filterDate.value) {
    result = result.filter((c) => c.dod === filterDate.value);
  }
  if (filterOrderDate.value) {
    result = result.filter((c) => c.ordered_date === filterOrderDate.value);
  }
  if (filterPartyCode.value) {
    const s = filterPartyCode.value.toLowerCase();
    result = result.filter(
      (c) => (c.party_code || "").toLowerCase().includes(s) ||
             (c.customer || "").toLowerCase().includes(s)
    );
  }
  if (filterStatus.value) {
    result = result.filter((c) => c.planning_status === filterStatus.value);
  }
  return result;
});

const visibleUnits = computed(() => {
  if (filterUnit.value) return [filterUnit.value];
  return units;
});

const groupedCards = computed(() => {
  const g = {};
  units.forEach((u) => (g[u] = []));
  filteredCards.value.forEach((c) => { if (g[c.unit]) g[c.unit].push(c); });
  return g;
});

const getUnitTotal = (unit) => {
  return filteredCards.value
    .filter((c) => c.unit === unit)
    .reduce((sum, c) => sum + (c.total_weight || 0), 0) / 1000;
};

const getHeaderColor = (unit) => {
  const t = getUnitTotal(unit);
  if (t > limits[unit]) return "#e24c4c";
  if (t > softLimits[unit]) return "#e8a317";
  return "#28a745";
};

const openForm = (name) => {
  frappe.set_route("Form", "Planning sheet", name);
};

const clearFilters = () => {
  filterDate.value = "";
  filterOrderDate.value = "";
  filterPartyCode.value = "";
  filterUnit.value = "";
  filterStatus.value = "";
};

const fetchData = () => {
  frappe.call({
    method: "production_scheduler.api.get_kanban_board",
    args: {
      start_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      end_date: frappe.datetime.add_months(frappe.datetime.get_today(), 1),
    },
    callback: (r) => { if (r.message) cards.value = r.message; },
  });
};

const initSortable = () => {
  if (typeof Sortable === "undefined") return;
  document.querySelectorAll(".ps-col-body").forEach((el) => {
    if (el._sortable) el._sortable.destroy();
    el._sortable = new Sortable(el, {
      group: "kanban",
      animation: 150,
      onEnd: (evt) => {
        const newUnit = evt.to.dataset.unit;
        const docName = evt.item.dataset.name;
        if (newUnit === evt.from.dataset.unit) return;
        const card = cards.value.find((c) => c.name === docName);
        
        // Prompt user for delivery date
        frappe.prompt(
          {
            label: "Delivery Date",
            fieldname: "delivery_date",
            fieldtype: "Date",
            default: card ? card.dod : frappe.datetime.get_today()
          },
          (values) => {
            frappe.call({
              method: "production_scheduler.api.update_schedule",
              args: { 
                doc_name: docName, 
                unit: newUnit, 
                date: values.delivery_date 
              },
              error: () => fetchData(),
              callback: (r) => {
                if (r.exc) { fetchData(); }
                else {
                  if (card) {
                    card.unit = newUnit;
                    card.dod = values.delivery_date;
                  }
                  frappe.show_alert({ message: "Moved to " + newUnit + " with delivery " + values.delivery_date, indicator: "green" });
                  fetchData();
                }
              },
            });
          },
          "Update Delivery Date",
          "Update"
        );
      },
    });
  });
};

watch([filteredCards, visibleUnits], () => { nextTick(() => initSortable()); });

onMounted(() => {
  fetchData();
  nextTick(() => initSortable());
  frappe.realtime.on("doc_update", (data) => {
    if (data.doctype === "Planning sheet") fetchData();
  });
});
</script>

<style scoped>
.ps-container {
  padding: 20px;
  height: calc(100vh - 100px);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* ---- FILTER BAR ---- */
.ps-filters {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  gap: 16px;
  padding: 14px 20px;
  margin-bottom: 20px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  flex-wrap: wrap;
}

.ps-filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ps-filter-item label {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ps-filter-item input,
.ps-filter-item select {
  padding: 7px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  background: #f8fafc;
  color: #1e293b;
  min-width: 140px;
  height: 36px;
  outline: none;
}

.ps-filter-item input:focus,
.ps-filter-item select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}

.ps-clear-btn {
  padding: 7px 16px;
  height: 36px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  white-space: nowrap;
}

.ps-clear-btn:hover {
  background: #e2e8f0;
  color: #334155;
}

/* ---- BOARD ---- */
.ps-board {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  height: calc(100% - 90px);
  padding-bottom: 10px;
}

/* ---- COLUMN ---- */
.ps-column {
  background: #f1f5f9;
  border-radius: 12px;
  width: 320px;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
}

.ps-col-header {
  padding: 12px 14px;
  background: #fff;
  border-top: 4px solid transparent;
  border-bottom: 1px solid #e2e8f0;
  border-radius: 12px 12px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ps-col-title {
  font-weight: 700;
  font-size: 14px;
  color: #1e293b;
}

.ps-col-stat {
  font-size: 13px;
  font-weight: 700;
}

.ps-col-body {
  padding: 10px;
  overflow-y: auto;
  flex-grow: 1;
  min-height: 200px;
}

.ps-col-body::-webkit-scrollbar { width: 4px; }
.ps-col-body::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

/* ---- CARD ---- */
.ps-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: grab;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: all 0.15s;
}

.ps-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}

.ps-card:active { cursor: grabbing; }

.ps-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}

.ps-card-customer {
  font-weight: 700;
  font-size: 13px;
  color: #1e293b;
}

.ps-badge {
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.ps-badge.draft { background: #fef3c7; color: #92400e; }
.ps-badge.finalized { background: #d1fae5; color: #065f46; }

.ps-card-party {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 8px;
  font-weight: 600;
}

/* ---- ITEM TABLE ---- */
.ps-item-table {
  width: 100%;
  border-collapse: collapse;
  border-top: 1px solid #f1f5f9;
  margin-bottom: 8px;
}

.ps-item-table tr {
  border-bottom: 1px dashed #f1f5f9;
}

.ps-item-table tr:last-child { border-bottom: none; }

.ps-item-table td {
  padding: 4px 2px;
  font-size: 11px;
  vertical-align: middle;
}

.ps-td-quality {
  font-weight: 600;
  color: #334155;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ps-td-color {
  color: #64748b;
  font-size: 10px;
  max-width: 70px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ps-td-gsm {
  color: #64748b;
  font-size: 10px;
  text-align: center;
  white-space: nowrap;
}

.ps-td-qty {
  font-weight: 700;
  color: #3b82f6;
  text-align: right;
  white-space: nowrap;
}

/* ---- CARD FOOTER ---- */
.ps-card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.ps-card-weight {
  font-weight: 800;
  font-size: 13px;
  color: #1e293b;
}

.ps-card-dates {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.ps-card-date-item {
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
}

.ps-date-label {
  font-weight: 600;
  color: #94a3b8;
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}


.ps-empty {
  text-align: center;
  color: #94a3b8;
  padding: 30px;
  font-size: 13px;
  font-style: italic;
}
</style>
