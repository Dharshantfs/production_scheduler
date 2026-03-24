<template>
  <div class="cc-container">
    <!-- Filter Bar -->
    <div class="cc-filters">
      <div class="cc-filter-item">
        <label>View Scope</label>
        <select v-model="viewScope" @change="toggleViewScope" style="font-weight: bold; color: #4f46e5;">
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
      
      <div class="cc-filter-item" v-if="viewScope === 'daily'">
        <label>Planned Date</label>
        <input type="date" v-model="filterOrderDate" @change="fetchData" />
      </div>
      <div class="cc-filter-item" v-else-if="viewScope === 'weekly'">
        <label>Select Week</label>
        <input type="week" v-model="filterWeek" @change="fetchData" />
      </div>
      <div class="cc-filter-item" v-else-if="viewScope === 'monthly'">
        <label>Select Month</label>
        <input type="month" v-model="filterMonth" @change="fetchData" />
      </div>
      <div class="cc-filter-item">
        <label>Party Code</label>
        <input type="text" v-model="filterPartyCode" placeholder="Search party..." @input="fetchData" />
      </div>
      <div class="cc-filter-item">
        <label>Customer</label>
        <input type="text" v-model="filterCustomer" placeholder="Search customer..." @input="fetchData" />
      </div>
      <div class="cc-filter-item">
        <label>Unit</label>
        <select v-model="filterUnit" @change="fetchData">
          <option value="">All Units</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
      </div>
      <button class="cc-clear-btn" @click="fetchData">🔄 Refresh</button>
      <button class="cc-maint-btn" @click="openMaintenanceDialog" title="Manage equipment maintenance schedules">⚙️ Maintenance</button>
      
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
                        <th style="width: 120px;">PLAN CODE</th>
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
                      <!-- Maintenance Row (shown once for the date group, even if no orders) -->
                      <tr v-if="getMaintenanceForDate(dateGroup.date, unitGroup.unit)" style="background-color: #fee2e2; border: 2px solid #dc2626;">
                        <td colspan="11" style="padding: 8px 12px; font-weight: 700; color: #991b1b; display: flex; justify-content: space-between; align-items: center;">
                          <span>🔧 MAINTENANCE: {{ getMaintenanceForDate(dateGroup.date, unitGroup.unit)[0].type }} ({{ getMaintenanceForDate(dateGroup.date, unitGroup.unit)[0].startDate }} - {{ getMaintenanceForDate(dateGroup.date, unitGroup.unit)[0].endDate }})</span>
                          <button @click="deleteMaintenanceRecord(getMaintenanceForDate(dateGroup.date, unitGroup.unit)[0].name)" style="background: #dc2626; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 11px;">Remove</button>
                        </td>
                      </tr>

                      <template v-if="dateGroup.items.length">
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
                            <td class="cell-center font-mono font-bold" style="font-size:11px; color:#4f46e5;">{{ item.planCode }}</td>
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

                      <tr v-else>
                        <td class="cell-center font-bold">{{ formatDate(dateGroup.date) }}</td>
                        <td class="cell-center">{{ getDayName(dateGroup.date) }}</td>
                        <td colspan="7" style="text-align:center; color:#94a3b8; font-style:italic;">No orders (maintenance day)</td>
                        <td class="cell-center font-bold bg-yellow-50">0</td>
                        <td class="cell-center">-</td>
                      </tr>
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
import { ref, computed, onMounted, nextTick, watch, reactive } from "vue";

// ===== MAINTENANCE DATA =====
const maintenanceRecords = ref([]);
const maintenanceData = ref({});

async function fetchMaintenanceRecords() {
	try {
		const res = await frappe.call({
			method: "production_scheduler.api.get_all_equipment_maintenance"
		});
		if (res.message) {
			maintenanceRecords.value = res.message;
			// Map by date and unit for quick lookup
			maintenanceData.value = {};
			res.message.forEach(rec => {
				const startD = new Date(rec.start_date);
				const endD = new Date(rec.end_date);
				for (let d = new Date(startD); d <= endD; d.setDate(d.getDate() + 1)) {
					const dateStr = d.toISOString().split('T')[0];
          if (!maintenanceData.value[dateStr]) maintenanceData.value[dateStr] = {};
          if (!maintenanceData.value[dateStr][rec.unit]) maintenanceData.value[dateStr][rec.unit] = [];
          maintenanceData.value[dateStr][rec.unit].push({
						name: rec.name,
						type: rec.maintenance_type,
						startDate: rec.start_date,
						endDate: rec.end_date,
						status: rec.status
					});
				}
			});
		}
	} catch (e) {
		console.error("Failed to fetch maintenance records", e);
	}
}

async function deleteMaintenanceRecord(recordName) {
  if (!confirm('Remove this maintenance record? Orders moved for this maintenance will be restored to original dates.')) return;
	try {
		const res = await frappe.call({
			method: "production_scheduler.api.delete_maintenance_and_cascade",
			args: { maintenance_record_name: recordName }
		});
		if (res.message && res.message.status === 'success') {
			frappe.show_alert({ message: `${res.message.message}`, indicator: 'green' });
			await fetchMaintenanceRecords();
			await fetchData();
		} else if (res.message && res.message.status === 'error') {
			frappe.msgprint(res.message.message || "Error deleting maintenance record");
		}
	} catch (e) {
		frappe.msgprint("Error deleting maintenance record");
		console.error(e);
	}
}

function getMaintenanceForDate(date, unit) {
  if (!date || !maintenanceData.value[date]) return null;
  return maintenanceData.value[date][unit];
}

function getCurrentScopeDateRange() {
  if (viewScope.value === 'monthly') {
    if (!filterMonth.value) return null;
    const [year, month] = filterMonth.value.split('-').map(v => parseInt(v, 10));
    const start = new Date(year, month - 1, 1);
    const end = new Date(year, month, 0);
    return { start, end };
  }

  if (viewScope.value === 'weekly') {
    if (!filterWeek.value) return null;
    const [yearStr, weekStr] = filterWeek.value.split('-W');
    const year = parseInt(yearStr, 10);
    const week = parseInt(weekStr, 10);
    const simple = new Date(year, 0, 1 + (week - 1) * 7);
    const dow = simple.getDay();
    const start = new Date(simple);
    if (dow <= 4) start.setDate(simple.getDate() - dow + 1);
    else start.setDate(simple.getDate() + 8 - dow);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    return { start, end };
  }

  if (!filterOrderDate.value) return null;
  const d = new Date(filterOrderDate.value);
  return { start: d, end: d };
}

function getScopeMaintenanceDates(unit) {
  const range = getCurrentScopeDateRange();
  if (!range) return [];

  const out = [];
  const cur = new Date(range.start);
  while (cur <= range.end) {
    const y = cur.getFullYear();
    const m = String(cur.getMonth() + 1).padStart(2, '0');
    const d = String(cur.getDate()).padStart(2, '0');
    const dateStr = `${y}-${m}-${d}`;
    if (getMaintenanceForDate(dateStr, unit)) out.push(dateStr);
    cur.setDate(cur.getDate() + 1);
  }

  return out;
}

async function openMaintenanceDialog() {
	const d = new frappe.ui.Dialog({
		title: "⚙️ Equipment Maintenance Management",
		fields: [
			{
				fieldtype: "Section Break",
				label: "Add New Maintenance"
			},
			{
				fieldtype: "Select",
				fieldname: "new_unit",
				label: "Unit",
				options: "Unit 1\nUnit 2\nUnit 3\nUnit 4",
				reqd: 1
			},
			{
				fieldtype: "Select",
				fieldname: "maint_type",
				label: "Maintenance Type",
				options: "Mesh Change\nDie Change",
				reqd: 1
			},
			{
				fieldtype: "Date",
				fieldname: "start_date",
				label: "Start Date",
				reqd: 1
			},
			{
				fieldtype: "Date",
				fieldname: "end_date",
				label: "End Date",
				reqd: 1
			},
			{
				fieldtype: "Small Text",
				fieldname: "notes",
				label: "Notes"
			},
			{
				fieldtype: "Section Break",
				label: "Existing Maintenance Records"
			},
			{
				fieldtype: "HTML",
				fieldname: "records_display",
				options: getMaintenanceRecordsHTML()
			}
		],
		primary_action_label: "Add Maintenance",
		primary_action: async (vals) => {
			if (!vals.new_unit || !vals.maint_type || !vals.start_date || !vals.end_date) {
				frappe.msgprint("Please fill all required fields");
				return;
			}
			try {
				const res = await frappe.call({
					method: "production_scheduler.api.add_equipment_maintenance",
					args: {
						unit: vals.new_unit,
						maintenance_type: vals.maint_type,
						start_date: vals.start_date,
						end_date: vals.end_date,
						notes: vals.notes || ""
					}
				});
				if (res.message && res.message.status === 'success') {
					frappe.show_alert({ message: res.message.message, indicator: 'green' });
					await fetchMaintenanceRecords();
          await fetchData();
          d.hide();
				}
			} catch (e) {
				frappe.msgprint("Error adding maintenance record");
				console.error(e);
			}
		}
	});
	d.show();
	await fetchMaintenanceRecords();
}

function getMaintenanceRecordsHTML() {
	if (!maintenanceRecords.value || maintenanceRecords.value.length === 0) {
		return '<p style="color: #999; text-align: center;">No maintenance records scheduled</p>';
	}
	
	let html = '<table style="width:100%; border-collapse: collapse; font-size: 12px;"><tr style="background: #f1f5f9; font-weight: 600;">';
	html += '<th style="border: 1px solid #ddd; padding: 6px;">Unit</th>';
	html += '<th style="border: 1px solid #ddd; padding: 6px;">Type</th>';
	html += '<th style="border: 1px solid #ddd; padding: 6px;">Start</th>';
	html += '<th style="border: 1px solid #ddd; padding: 6px;">End</th>';
	html += '<th style="border: 1px solid #ddd; padding: 6px;">Status</th>';
	html += '</tr>';
	
	maintenanceRecords.value.forEach(rec => {
		html += `<tr style="border: 1px solid #ddd;">`;
		html += `<td style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: 600;">${rec.unit}</td>`;
		html += `<td style="border: 1px solid #ddd; padding: 6px; text-align: center;">${rec.maintenance_type}</td>`;
		html += `<td style="border: 1px solid #ddd; padding: 6px; text-align: center;">${rec.start_date}</td>`;
		html += `<td style="border: 1px solid #ddd; padding: 6px; text-align: center;">${rec.end_date}</td>`;
		html += `<td style="border: 1px solid #ddd; padding: 6px; text-align: center;">`;
		const statusColor = rec.status === 'Completed' ? '#10b981' : rec.status === 'In Progress' ? '#f59e0b' : '#999';
		html += `<span style="background: ${statusColor}20; color: ${statusColor}; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${rec.status}</span>`;
		html += `</td>`;
		html += `</tr>`;
	});
	
	html += '</table>';
	return html;
}

// Color groups for keyword-based matching
// Check MOST SPECIFIC (multi-word) first, then SINGLE-WORD catch-all groups
const COLOR_GROUPS = [
  // ── 1. WHITES (Priority 0) ───────────────────────────────────
  { keywords: ["BRIGHT WHITE", "SUNSHINE WHITE", "MILKY WHITE", "SUPER WHITE",
               "BLEACH WHITE", "OPTICAL WHITE"], priority: 0, hex: "#FFFFFF" },
  { keywords: ["WHITE"], priority: 0, hex: "#FFFFFF" },

  // ── 2. BABY PINK (Priority 1) ───────────────────────────────────
  { keywords: ["BABY PINK"], priority: 1, hex: "#FFB6C1" },

  // ── 3. MEDICAL BLUE (Priority 2) ───────────────────────────────────
  { keywords: ["MEDICAL BLUE"],          priority: 2, hex: "#0096FF" },

  // ── 4. MEDICAL GREEN (Priority 3) ───────────────────────────────────
  { keywords: ["MEDICAL GREEN"],         priority: 3, hex: "#00A36C" },

  // ── 5. IVORY / CREAM / OFF WHITE (Priority 4) ──────────────────
  { keywords: ["BRIGHT IVORY", "IVORY", "OFF WHITE", "CREAM"], priority: 4, hex: "#FFFFF0" },

  // ── 6. YELLOWS (Priority 5-6): Lemon → Yellow → Golden
  { keywords: ["LEMON YELLOW"],          priority: 5, hex: "#FFF44F" },
  { keywords: ["GOLDEN YELLOW", "GOLD"], priority: 6, hex: "#FFD700" },
  { keywords: ["YELLOW"],                priority: 5, hex: "#FFEA00" },

  // ── 7. ORANGES (Priority 7)
  { keywords: ["LIGHT ORANGE", "PEACH", "BRIGHT ORANGE", "ORANGE"], priority: 7, hex: "#FF8C00" },

  // ── 8. PINKS (Priority 8)
  { keywords: ["DARK PINK"],             priority: 8, hex: "#C71585" },
  { keywords: ["PINK", "PINK 1.0", "PINK 2.0", "PINK 3.0", "PINK 5.0", "HOT PINK"], priority: 8, hex: "#FFC0CB" },

  // ── 9. REDS / MAROONS (Priority 9)
  { keywords: ["BRIGHT RED", "SCARLET", "CRIMSON", "RED"],  priority: 9, hex: "#D32F2F" },
  { keywords: ["MAROON", "BURGUNDY", "DARK RED"],  priority: 9, hex: "#800000" },

  // ── 10. BLUES (Priority 10-12): Peacock → Royal → Navy
  { keywords: ["LIGHT PEACOCK BLUE", "PEACOCK BLUE"], priority: 10, hex: "#008B8B" },
  { keywords: ["SKY BLUE", "LIGHT BLUE"], priority: 11, hex: "#87CEEB" },
  { keywords: ["ROYAL BLUE", "BLUE"], priority: 11, hex: "#2962FF" },
  { keywords: ["NAVY BLUE", "DARK BLUE"], priority: 12, hex: "#1A237E" },

  // ── 11. VIOLET / PURPLE (Priority 13)
  { keywords: ["VIOLET", "VOILET", "PURPLE"], priority: 13, hex: "#8B00FF" },

  // ── 12. GREENS (Priority 14-17): Reliance / Parrot / Sea / Army
  { keywords: ["GREEN 1.0 MINT", "MEDICAL GREEN"], priority: 14, hex: "#00897B" },
  { keywords: ["PARROT GREEN", "RELIANCE GREEN", "GREEN"], priority: 15, hex: "#228B22" },
  { keywords: ["SEA GREEN"],             priority: 16, hex: "#2E8B57" },
  { keywords: ["ARMY GREEN", "ARMY"],    priority: 17, hex: "#4B5320" },

  // ── 13. GREYS / SILVERS (Priority 18)
  { keywords: ["SILVER", "LIGHT GREY", "GREY", "GRAY", "DARK GREY"], priority: 18, hex: "#808080" },

  // ── 14. BROWNS (Priority 19)
  { keywords: ["BROWN", "CHOCOLATE"], priority: 19, hex: "#8B4513" },

  // ── 15. BLACK (Priority 20)
  { keywords: ["BLACK"],                 priority: 20, hex: "#000000" },

  // ── 16. BEIGES (Priority 21-22) ── Transition Rule: Run last to recover machine
  { keywords: ["DARK BEIGE"], priority: 21, hex: "#C2B280" },
  { keywords: ["LIGHT BEIGE", "BEIGE"], priority: 22, hex: "#F5F5DC" },

  // ── MIX MARKERS (priority 199) ──
  { keywords: ["WHITE MIX", "BLACK MIX", "COLOR MIX", "BEIGE MIX"], priority: 199, hex: "#c0c0c0" },
  { keywords: ["NO COLOR"], priority: 999, hex: "#e5e7eb" },
];

function findColorGroup(color) {
  const upper = (color || "").toUpperCase().trim();
  for (const group of COLOR_GROUPS) {
    for (const keyword of group.keywords) {
      if (upper.includes(keyword)) return group;
    }
  }
  return null;
}

function getColorPriority(color) {
  const group = findColorGroup(color);
  return group ? group.priority : 50;
}

function compareColor(a, b, direction) {
  const pA = getColorPriority(a.color);
  const pB = getColorPriority(b.color);
  return direction === 'asc' ? pA - pB : pB - pA;
}

function compareGsm(a, b, direction) {
  const gsmA = parseFloat(a.gsm) || 0;
  const gsmB = parseFloat(b.gsm) || 0;
  return direction === 'asc' ? gsmA - gsmB : gsmB - gsmA;
}

// Track saved sequences from 'Color Sequence Approval' to match Board order exactly
const unitSequenceStore = reactive({});

function sortItems(unit, items, date) {
  // 1. If we have a saved sequence (Manual Sort / Approved Sequence) for this unit/date, use it primarily
  const key = `${unit}-${date}`;
  const savedSeq = unitSequenceStore[key]?.sequence;
  if (savedSeq && savedSeq.length) {
      const seqMap = {};
      savedSeq.forEach((name, i) => seqMap[name] = i);
      
      return [...items].sort((a, b) => {
          const nameA = a.itemName || a.name;
          const nameB = b.itemName || b.name;
          
          const idxA = seqMap[nameA] !== undefined ? seqMap[nameA] : 9999 + parseInt(a.idx || 0);
          const idxB = seqMap[nameB] !== undefined ? seqMap[nameB] : 9999 + parseInt(b.idx || 0);
          
          if (idxA !== idxB) return idxA - idxB;
          
          // Fallback if not in sequence map
          const pA = getColorPriority(a.color);
          const pB = getColorPriority(b.color);
          if (pA !== pB) return pA - pB;
          return (parseFloat(b.gsm) || 0) - (parseFloat(a.gsm) || 0);
      });
  }

  // 2. Default Auto Sort (Matches Board's default when no manual sequence): 
  // Color Priority (Asc) -> GSM (Desc) -> DB Index
  return [...items].sort((a, b) => {
    // A. Color Priority
    const pA = getColorPriority(a.color);
    const pB = getColorPriority(b.color);
    if (pA !== pB) return pA - pB;

    // B. GSM Descending (Heuristic: heavier first to minimize gaps)
    const gsmA = parseFloat(a.gsm) || 0;
    const gsmB = parseFloat(b.gsm) || 0;
    if (gsmB !== gsmA) return gsmB - gsmA;

    // C. Database Index (Initial Sequence)
    const idxA = parseInt(a.idx || 0);
    const idxB = parseInt(b.idx || 0);
    return idxA - idxB;
  });
}
// ─────────────────────────────────────────────────────────────────────────────

const units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Mixed"];
const filterOrderDate = ref(frappe.datetime.get_today());
const filterWeek = ref("");
const filterMonth = ref("");
const viewScope = ref("daily");

const filterPartyCode = ref("");
const filterCustomer = ref("");
const filterUnit = ref("");
const rawData = ref([]);

const visibleUnits = computed(() => {
  if (!filterUnit.value) return units;
  return units.filter((u) => u === filterUnit.value);
});

const filteredData = computed(() => {
  let data = rawData.value || [];
  
  // Only show items that have been pushed to Production Board
  data = data.filter(d => !!d.plannedDate);

  // Exclude missing parameters and NO COLOR
  data = data.filter(d => {

      if (!d.quality || !d.color || !d.unit || d.unit === "Mixed" || d.unit === "Unassigned") return false;
      const colorUpper = d.color.toUpperCase().trim();
      if (colorUpper === "NO COLOR") return false;
      return true;
  });
  
  data = data.map(d => ({ ...d, unit: d.unit || "Mixed" }));

  if (filterPartyCode.value) {
    const search = filterPartyCode.value.toLowerCase();
    data = data.filter((d) =>
      (d.partyCode || "").toLowerCase().includes(search)
    );
  }
  if (filterCustomer.value) {
    const search = filterCustomer.value.toLowerCase();
    data = data.filter((d) =>
      (d.customer || "").toLowerCase().includes(search)
    );
  }
  return data;
});

const tableData = computed(() => {
    return visibleUnits.value.map(unit => {
        let items = filteredData.value.filter(d => (d.unit || "Mixed") === unit);
        
        const dateGroupsObj = {};
        items.forEach(item => {
            const d = item.plannedDate || "No Date";
            if (!dateGroupsObj[d]) dateGroupsObj[d] = { date: d, items: [], dailyTotal: 0 };
            dateGroupsObj[d].items.push(item);
            dateGroupsObj[d].dailyTotal += (item.qty || 0);
        });

    // Ensure maintenance dates are visible even when there are zero orders on those dates.
    for (const maintenanceDate of getScopeMaintenanceDates(unit)) {
      if (!dateGroupsObj[maintenanceDate]) {
        dateGroupsObj[maintenanceDate] = { date: maintenanceDate, items: [], dailyTotal: 0 };
      }
    }
        
        const dates = Object.values(dateGroupsObj).sort((a, b) => new Date(a.date) - new Date(b.date));
        
        // Sort each date group individually using Board's exact queuing for that day
        dates.forEach(group => {
            group.items = sortItems(unit, group.items, group.date);
        });

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

function toggleViewScope() {
    if (viewScope.value === 'monthly' && !filterMonth.value) {
        filterMonth.value = frappe.datetime.get_today().substring(0, 7);
    } else if (viewScope.value === 'weekly' && !filterWeek.value) {
        const d = new Date();
        const dStart = new Date(d.getFullYear(), 0, 1);
        const days = Math.floor((d - dStart) / (24 * 60 * 60 * 1000));
        const weekNum = Math.ceil(days / 7);
        filterWeek.value = `${d.getFullYear()}-W${String(weekNum).padStart(2,'0')}`;
    }
    fetchData();
}

let fetchTimeout = null;

async function fetchData() {
  return new Promise((resolve) => {
    if (fetchTimeout) clearTimeout(fetchTimeout);
    fetchTimeout = setTimeout(async () => {
      try {
        let args = { party_code: filterPartyCode.value };
        
        if (viewScope.value === 'monthly') {
            if (!filterMonth.value) return resolve();
            const startDate = `${filterMonth.value}-01`;
            const [year, month] = filterMonth.value.split("-");
            const lastDay = new Date(year, month, 0).getDate();
            const endDate = `${filterMonth.value}-${lastDay}`;
            args.start_date = startDate;
            args.end_date = endDate;
        } else if (viewScope.value === 'weekly') {
            if (!filterWeek.value) return resolve();
            const [yearStr, weekStr] = filterWeek.value.split('-W');
            const y = parseInt(yearStr);
            const w = parseInt(weekStr);
            const simple = new Date(y, 0, 1 + (w - 1) * 7);
            const dow = simple.getDay();
            const ISOweekStart = new Date(simple);
            if (dow <= 4) ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1);
            else ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay());
            
            const ISOweekEnd = new Date(ISOweekStart);
            ISOweekEnd.setDate(ISOweekEnd.getDate() + 6);
            
            const format = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
            args.start_date = format(ISOweekStart);
            args.end_date = format(ISOweekEnd);
        } else {
            args.date = filterOrderDate.value;
        }

        args.plan_name = "__all__";
        args.planned_only = 1;

    const r = await frappe.call({
      method: "production_scheduler.api.get_color_chart_data",
      args: args,
    });
    rawData.value = (r.message || []).map(d => ({
      ...d,
      plannedDate: d.plannedDate || d.planned_date || "",
      partyCode: d.partyCode || d.party_code || "",
      itemName: d.itemName || d.item_name || "",
      orderDate: d.orderDate || d.ordered_date || "",
      planCode: d.custom_plan_code || "",
    }));

    // After loading raw data, fetch the exact sequence for the range 
    // to match the Production Board's exact queuing flow for each day.
    if (args.start_date && args.end_date) {
        try {
            const seqRes = await frappe.call({
                method: "production_scheduler.api.get_color_sequences_range",
                args: { 
                    start_date: args.start_date, 
                    end_date: args.end_date, 
                    unit: filterUnit.value || "All Units",
                    plan_name: "__all__" 
                }
            });
            if (seqRes.message) {
                Object.assign(unitSequenceStore, seqRes.message);
            }
        } catch (e) {
            console.warn(`Failed to fetch sequence range`, e);
        }
    } else if (args.date) {
        // Single day case
        for (const unit of units) {
            try {
                const seqRes = await frappe.call({
                    method: "production_scheduler.api.get_color_sequence",
                    args: { date: args.date, unit, plan_name: "__all__" }
                });
                if (seqRes.message && seqRes.message.sequence) {
                    unitSequenceStore[`${unit}-${args.date}`] = seqRes.message;
                }
            } catch (e) {}
        }
    }
      } catch (e) {
        frappe.msgprint("Error loading plan data");
        console.error(e);
      }
      resolve();
    }, 150);
  });
}

function updateUrlParams() {
    let query = {};
    if (viewScope.value === 'daily') query.date = filterOrderDate.value;
    if (viewScope.value === 'weekly') query.week = filterWeek.value;
    if (viewScope.value === 'monthly') query.month = filterMonth.value;
    query.scope = viewScope.value;
    
    const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?' + new URLSearchParams(query).toString();
    window.history.replaceState({path: newUrl}, '', newUrl);
}

watch(viewScope, updateUrlParams);
watch(filterOrderDate, updateUrlParams);
watch(filterWeek, updateUrlParams);
watch(filterMonth, updateUrlParams);

onMounted(() => {
  const params = new URLSearchParams(window.location.search);
  const scopeParam = params.get('scope');
  const dateParam = params.get('date');
  const weekParam = params.get('week');
  const monthParam = params.get('month');
  
  if (scopeParam) viewScope.value = scopeParam;
  if (dateParam) filterOrderDate.value = dateParam;
  if (weekParam) filterWeek.value = weekParam;
  if (monthParam) filterMonth.value = monthParam;
  
  fetchMaintenanceRecords();
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
.cc-maint-btn {
    padding: 8px 16px;
    background-color: #f97316;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
}
.cc-maint-btn:hover {
    background-color: #ea580c;
    box-shadow: 0 2px 4px rgba(249, 115, 22, 0.3);
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