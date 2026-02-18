<template>
  <div class="cc-container">
    <!-- Filter Bar -->
    <div class="cc-filters">
      <div class="cc-filter-item">
        <label>Order Date</label>
        <input type="date" v-model="filterOrderDate" @change="fetchData" />
      </div>
      <div class="cc-filter-item">
        <label>Party Code</label>
        <input type="text" v-model="filterPartyCode" placeholder="Search party..." @input="fetchData" />
      </div>
      <div class="cc-filter-item">
        <label>Unit</label>
        <select v-model="filterUnit" @change="fetchData">
          <option value="">All Units</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
      </div>
      <button class="cc-clear-btn" @click="fetchData">🔄 Refresh</button>
      
      <div class="cc-filter-item" style="margin-left: auto;">
          <button class="cc-view-btn" @click="goToBoard">📊 Back to Board</button>
      </div>
    </div>

    <!-- Table View (Always Visible in this page) -->
    <div class="cc-table-container">
        <div v-for="unitGroup in tableData" :key="unitGroup.unit" class="cc-table-unit-block">
            <!-- Unit Header -->
            <div class="cc-table-unit-header" :style="{ backgroundColor: getUnitHeaderColor(unitGroup.unit) }">
                {{ unitGroup.unit.toUpperCase() }} (06:00 am to 06:00 am) - Total: {{ unitGroup.totalWeight.toFixed(2) }} T
            </div>
            
            <table class="cc-prod-table">
                <thead>
                    <tr>
                        <th style="width: 80px;">DATE</th>
                        <th style="width: 80px;">DAY</th>
                        <th style="width: 100px;">PARTY CODE</th>
                        <th style="width: 150px;">PARTY NAME</th>
                        <th style="width: 80px;">QUALITY</th>
                        <th style="width: 100px;">COLOUR</th>
                        <th style="width: 80px;">GSM</th>
                        <th style="width: 80px;">WEIGHT (Kg)</th>
                        <th style="width: 80px;">ACTUAL PROD</th>
                        <th style="width: 100px;">DESPATCH STATUS</th>
                    </tr>
                </thead>
                <tbody>
                    <template v-for="dateGroup in unitGroup.dates" :key="dateGroup.date">
                        <template v-for="(item, idx) in dateGroup.items" :key="item.itemName">
                            <tr>
                                <td v-if="idx === 0" :rowspan="dateGroup.items.length" class="cell-center font-bold">
                                    {{ formatDate(dateGroup.date) }}
                                </td>
                                <td v-if="idx === 0" :rowspan="dateGroup.items.length" class="cell-center">
                                    {{ getDayName(dateGroup.date) }}
                                </td>
                                
                                <td class="cell-center">{{ item.partyCode }}</td>
                                <td>{{ item.customer }}</td>
                                <td class="cell-center">{{ item.quality }}</td>
                                <td class="cell-center font-bold">{{ item.color }}</td>
                                <td class="cell-center">{{ item.gsm }}</td>
                                <td class="cell-right font-bold">{{ item.qty }}</td>
                                
                                <td v-if="idx === 0" :rowspan="dateGroup.items.length" class="cell-center font-bold bg-yellow-50">
                                    {{ dateGroup.dailyTotal.toFixed(0) }}
                                </td>
                                
                                <td class="cell-center">
                                    <span class="status-badge" :class="getDispatchStatusClass(item.delivery_status)">
                                        {{ formatDispatchStatus(item.delivery_status) }}
                                    </span>
                                </td>
                            </tr>
                        </template>
                    </template>
                    <tr v-if="unitGroup.dates.length === 0">
                        <td colspan="10" style="text-align:center; padding: 20px; color:#999;">No production planned for this unit</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from "vue";

const units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Mixed"];
const filterOrderDate = ref(frappe.datetime.get_today());
const filterPartyCode = ref("");
const filterUnit = ref("");
const rawData = ref([]);

const visibleUnits = computed(() => {
  if (!filterUnit.value) return units;
  return units.filter((u) => u === filterUnit.value);
});

const filteredData = computed(() => {
  let data = rawData.value || [];
  data = data.map(d => ({ ...d, unit: d.unit || "Mixed" }));

  if (filterPartyCode.value) {
    const search = filterPartyCode.value.toLowerCase();
    data = data.filter((d) =>
      (d.partyCode || "").toLowerCase().includes(search) ||
      (d.customer || "").toLowerCase().includes(search)
    );
  }
  return data;
});

const tableData = computed(() => {
    return visibleUnits.value.map(unit => {
        let items = filteredData.value.filter(d => (d.unit || "Mixed") === unit);
        
        // Sort items by idx (sequence)
        items = [...items].sort((a, b) => (a.idx || 0) - (b.idx || 0));

        const dateGroupsObj = {};
        items.forEach(item => {
            const d = item.ordered_date || "No Date";
            if (!dateGroupsObj[d]) dateGroupsObj[d] = { date: d, items: [], dailyTotal: 0 };
            dateGroupsObj[d].items.push(item);
            dateGroupsObj[d].dailyTotal += (item.qty || 0);
        });
        
        const dates = Object.values(dateGroupsObj).sort((a, b) => new Date(a.date) - new Date(b.date));
        const totalWeight = items.reduce((s, i) => s + (i.qty || 0), 0) / 1000;

        return { unit, dates, totalWeight };
    });
});

function formatDate(dateStr) {
    if (!dateStr || dateStr === 'No Date') return '-';
    const d = new Date(dateStr);
    return `${d.getDate()}/${d.getMonth()+1}/${d.getFullYear()}`;
}

function getDayName(dateStr) {
    if (!dateStr || dateStr === 'No Date') return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { weekday: 'long' }).toUpperCase();
}

function getUnitHeaderColor(unit) {
    return "#fcd34d"; 
}

function formatDispatchStatus(status) {
    if (!status || status === 'Not Delivered') return 'NOT DESPATCHED';
    if (status === 'Fully Delivered') return 'DESPATCHED';
    if (status === 'Partly Delivered') return 'PARTLY DESPATCHED';
    return status.toUpperCase();
}

function getDispatchStatusClass(status) {
    if (!status || status === 'Not Delivered') return 'bg-red-100 text-red-800';
    if (status === 'Fully Delivered') return 'bg-green-100 text-green-800';
    if (status === 'Partly Delivered') return 'bg-orange-100 text-orange-800';
    return 'bg-gray-100 text-gray-800';
}

function goToBoard() {
    frappe.set_route("production-board");
}

async function fetchData() {
  try {
    const r = await frappe.call({
      method: "production_scheduler.api.get_color_chart_data",
      args: { 
          date: filterOrderDate.value,
          party_code: filterPartyCode.value
      },
    });
    rawData.value = r.message || [];
  } catch (e) {
    frappe.msgprint("Error loading plan data");
  }
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.cc-container {
  display: flex;
  flex-direction: column;
  padding: 16px;
  background-color: #f3f4f6;
  min-height: 100vh;
}
.cc-filters {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  gap: 12px;
}
.cc-filter-item {
  display: flex;
  flex-direction: column;
}
.cc-filter-item label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 2px;
}
.cc-filter-item input,
.cc-filter-item select {
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}
.cc-clear-btn, .cc-view-btn {
  padding: 8px 16px;
  background-color: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  font-weight: 500;
}
.cc-view-btn {
    background-color: #3b82f6;
    color: white;
    border: none;
}

.cc-table-container {
    display: flex;
    flex-direction: column;
    gap: 30px;
}
.cc-table-unit-header {
    padding: 10px 15px;
    font-weight: 800;
    font-size: 14px;
    border-radius: 8px 8px 0 0;
    border: 1px solid #e5e7eb;
    border-bottom: none;
}
.cc-prod-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    font-size: 12px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.cc-prod-table th {
    background: #f8fafc;
    padding: 10px;
    border: 1px solid #e5e7eb;
    text-align: center;
    font-weight: 700;
}
.cc-prod-table td {
    padding: 8px;
    border: 1px solid #e5e7eb;
}
.cell-center { text-align: center; }
.cell-right { text-align: right; }
.font-bold { font-weight: 700; }
.bg-yellow-50 { background-color: #fefce8; }

.status-badge {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
}
.bg-red-100 { background: #fee2e2; color: #991b1b; }
.bg-green-100 { background: #dcfce7; color: #166534; }
.bg-orange-100 { background: #ffedd5; color: #9a3412; }
.bg-gray-100 { background: #f3f4f6; color: #374151; }
</style>
