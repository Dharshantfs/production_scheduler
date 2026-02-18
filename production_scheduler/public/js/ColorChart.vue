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
        <input
          type="text"
          v-model="filterPartyCode"
          placeholder="Search party..."
        />
      </div>
      <div class="cc-filter-item">
        <label>Unit</label>
        <select v-model="filterUnit">
          <option value="">All Units</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
      </div>
      <div class="cc-filter-item">
        <label>Status</label>
        <select v-model="filterStatus">
          <option value="">All</option>
          <option value="Draft">Draft</option>
          <option value="Finalized">Finalized</option>
        </select>
      </div>
      <div class="cc-filter-item" style="flex-direction:row; align-items:flex-end; gap:4px; margin-left:auto;">
          <button 
            class="cc-view-btn" 
            :class="{ active: viewMode === 'kanban' }" 
            @click="viewMode = 'kanban'"
            title="Kanban Board View"
          >
            ðŸ“‹ Kanban
          </button>
          <button 
            class="cc-view-btn" 
            :class="{ active: viewMode === 'matrix' }" 
            @click="viewMode = 'matrix'"
            title="Matrix Pivot View"
          >
            ðŸ“Š Matrix
          </button>
      </div>
      
      <button class="cc-clear-btn" @click="clearFilters">âœ• Clear</button>
      <button class="cc-clear-btn" style="color: #2563eb; border-color: #2563eb; margin-left: 8px;" @click="autoAllocate" title="Auto-assign orders based on Width & Quality">
        ðŸª„ Auto Alloc
      </button>
      <button class="cc-clear-btn" style="color: #059669; border-color: #059669; margin-left: 8px;" @click="openPullOrdersDialog" title="Pull orders from a future date">
        📥 Pull Orders
      </button>
      <button v-if="isAdmin" class="cc-clear-btn" style="color: #dc2626; border-color: #dc2626; margin-left: 8px;" @click="openRescueDialog" title="Rescue lost or stuck orders">
        🚑 Rescue Orders
      </button>
    </div>

    <!-- Kanban View -->
    <div v-if="viewMode === 'kanban'" class="cc-board" :key="renderKey">
      <div
        v-for="unit in visibleUnits"
        :key="unit"
        class="cc-column"
        :data-unit="unit"
      >
        <div class="cc-col-header" :style="{ borderTopColor: headerColors[unit] }">
          <div class="cc-header-top">
            <span class="cc-col-title">{{ unit === 'Mixed' ? 'Unassigned' : unit }}</span>
            <!-- Sort Controls -->
            <div class="cc-unit-controls">
              <span style="font-size:10px; color:#64748b; margin-right:4px;">{{ getSortLabel(unit) }}</span>
              <button class="cc-mini-btn" @click="toggleUnitColor(unit)" :title="getUnitSortConfig(unit).color === 'asc' ? 'Light->Dark' : 'Dark->Light'">
                {{ getUnitSortConfig(unit).color === 'asc' ? 'â˜€ï¸' : 'ðŸŒ™' }}
              </button>
              <button class="cc-mini-btn" @click="toggleUnitGsm(unit)" :title="getUnitSortConfig(unit).gsm === 'desc' ? 'High->Low' : 'Low->High'">
                {{ getUnitSortConfig(unit).gsm === 'desc' ? 'â¬‡ï¸' : 'â¬†ï¸' }}
              </button>
              <button class="cc-mini-btn" @click="toggleUnitPriority(unit)" :title="getUnitSortConfig(unit).priority === 'color' ? 'Color Priority' : 'GSM Priority'">
                {{ getUnitSortConfig(unit).priority === 'color' ? 'ðŸŽ¨' : 'ðŸ“' }}
              </button>
            </div>
          </div>
            <span class="cc-stat-weight" :class="getUnitCapacityStatus(unit).class">
              {{ getUnitTotal(unit).toFixed(2) }} / {{ UNIT_TONNAGE_LIMITS[unit] }}T
              <span v-if="getHiddenWhiteTotal(unit) > 0" style="font-size:10px; font-weight:400; color:#64748b; display:block;">
                 (Inc. {{ getHiddenWhiteTotal(unit).toFixed(2) }}T White)
              </span>
            </span>
            <div v-if="getUnitCapacityStatus(unit).warning" class="text-xs text-red-600 font-bold">
              {{ getUnitCapacityStatus(unit).warning }}
            </div>
            <span class="cc-stat-mix" v-if="getMixRollCount(unit) > 0">
              âš ï¸ {{ getMixRollCount(unit) }} mix{{ getMixRollCount(unit) > 1 ? 'es' : '' }}
              ({{ getMixRollTotalWeight(unit) }} Kg)
            </span>
          </div>

        <div class="cc-col-body" :data-unit="unit" ref="columnRefs">
          <template v-for="(entry, idx) in getUnitEntries(unit)" :key="entry.uniqueKey">
            <!-- Mix Roll Marker -->
            <div v-if="entry.type === 'mix'" class="cc-mix-marker">
              <div class="cc-mix-line"></div>
              <span class="cc-mix-label" :class="entry.mixType.toLowerCase().replace(' ', '-')">
                {{ entry.mixType }} â€” ~{{ entry.qty }} Kg
              </span>
              <div class="cc-mix-line"></div>
            </div>
            <!-- Order Card -->
            <div
              v-else
              class="cc-card"
              :data-name="entry.name"
              :data-item-name="entry.itemName"
              :data-color="entry.color"
              :data-planning-sheet="entry.planningSheet"
              @click="openForm(entry.planningSheet)"
            >
              <div class="cc-card-left">
                <div
                  class="cc-color-swatch"
                  :style="{ backgroundColor: getHexColor(entry.color) }"
                  :title="entry.color"
                ></div>
                <div class="cc-card-info">
                  <div class="cc-card-color-name">{{ entry.color }}</div>
                  <div class="cc-card-customer">
                    <span style="font-weight:700; color:#111827;">{{ entry.partyCode }}</span>
                    <span v-if="entry.partyCode !== entry.customer" style="font-weight:400; color:#6b7280;"> Â· {{ entry.customer }}</span>
                  </div>
                  <div class="cc-card-details">
                    {{ entry.quality }} Â· {{ entry.gsm }} GSM
                  </div>
                </div>
              </div>
              <div class="cc-card-right">
                <span class="cc-card-qty">{{ (entry.qty / 1000).toFixed(3) }} T</span>
                <span class="cc-card-qty-kg">{{ entry.qty }} Kg</span>
              </div>
            </div>
          </template>

          <div v-if="!getUnitEntries(unit).length" class="cc-empty">
            No orders
          </div>
        </div>

        <!-- Unit Footer -->
        <div class="cc-col-footer">
          <span>Production: {{ getUnitProductionTotal(unit).toFixed(2) }}T</span>
          <span v-if="getMixRollTotalWeight(unit) > 0">
            Mix Waste: {{ (getMixRollTotalWeight(unit) / 1000).toFixed(3) }}T
          </span>
        </div>
      </div>
    </div>

    <!-- Matrix Pivot View -->
    <div v-if="viewMode === 'matrix'" class="cc-matrix-container">
        <div class="cc-matrix-scroll">
            <table class="cc-matrix-table">
                <thead>
                    <!-- Row 1: Order Date (Merged) -->
                    <tr>
                        <th class="matrix-sticky-col">DATE</th>
                        <template v-for="(h, i) in matrixData.dateHeaders" :key="'date-' + i">
                            <th :colspan="h.span" class="text-center" style="background:#f1f5f9; border-left:1px solid #cbd5e1;">
                                {{ h.date }}
                            </th>
                        </template>
                        <th class="matrix-total-col" rowspan="6">TOTAL</th>
                    </tr>
                    <!-- Row 2: Days -->
                    <tr>
                        <th class="matrix-sticky-col">DAYS</th>
                        <th v-for="col in matrixData.columns" :key="'days-'+col.id" class="text-center font-normal">
                            {{ col.days }}
                        </th>
                    </tr>
                    <!-- Row 3: Code (Draggable Header) -->
                    <tr ref="matrixHeaderRow">
                        <th class="matrix-sticky-col">CODE</th>
                        <th 
                            v-for="col in matrixData.columns" 
                            :key="'code-'+col.id" 
                            class="text-center matrix-col-header"
                            :data-id="col.id"
                            :data-date="col.date"
                        >
                            <div class="draggable-handle" style="cursor: grab;">{{ col.code }}</div>
                        </th>
                    </tr>
                    <!-- Row 4: GSM -->
                    <tr>
                        <th class="matrix-sticky-col">GSM TYPE</th>
                        <th v-for="col in matrixData.columns" :key="'gsm-'+col.id" class="text-center font-normal">
                            {{ col.gsm }}
                        </th>
                    </tr>
                    <!-- Row 5: Quality -->
                    <tr>
                        <th class="matrix-sticky-col">QUALITY</th>
                        <th v-for="col in matrixData.columns" :key="'qual-'+col.id" class="text-center">
                            {{ col.quality }}
                        </th>
                    </tr>
                    <!-- Row 6: Customer (Green Header) -->
                    <tr>
                        <th class="matrix-sticky-col" style="background:#dcfce7; color:#166534;">COLOURS</th>
                        <th v-for="col in matrixData.columns" :key="'cust-'+col.id" class="text-center" style="background:#dcfce7; color:#166534; font-size:10px;">
                            {{ col.customer }}
                        </th>
                    </tr>
                </thead>
                <tbody ref="matrixBody">
                    <tr 
                        v-for="row in matrixData.rows" 
                        :key="row.color"
                        :data-color="row.color"
                        class="matrix-row"
                    >
                        <td class="matrix-sticky-col matrix-row-header" style="cursor: grab;">
                            <div class="flex items-center">
                                <span class="w-3 h-3 rounded mr-2 border border-gray-300" :style="{backgroundColor: getHexColor(row.color)}"></span>
                                {{ row.color }}
                            </div>
                        </td>
                        <td 
                            v-for="col in matrixData.columns" 
                            :key="col.id" 
                            class="text-right"
                        >
                            {{ (row.cells[col.id] || 0) > 0 ? (row.cells[col.id]).toFixed(0) : '' }}
                        </td>
                        <td class="matrix-total-col text-right font-bold bg-gray-50">
                            {{ row.total.toFixed(0) }}
                        </td>
                    </tr>
                </tbody>
                <tfoot>
                    <tr>
                        <th class="matrix-sticky-col">TOTAL</th>
                        <th v-for="col in matrixData.columns" :key="col.id" class="text-right">
                            {{ matrixData.colTotals[col.id].toFixed(0) }}
                        </th>
                        <th class="matrix-total-col text-right">{{ matrixData.grandTotal.toFixed(0) }}</th>
                    </tr>
                </tfoot>
            </table>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch, reactive } from "vue";
import Sortable from "sortablejs";

// Color groups for keyword-based matching
// Check MOST SPECIFIC (multi-word) first, then SINGLE-WORD catch-all groups
const COLOR_GROUPS = [
  // 1. WHITE & OFF-WHITE (10-19)
  { keywords: ["WHITE MIX"], priority: 99, hex: "#f0f0f0" }, // Mixes at end
  { keywords: ["BLACK MIX"], priority: 99, hex: "#404040" },
  { keywords: ["COLOR MIX"], priority: 99, hex: "#c0c0c0" },
  { keywords: ["BEIGE MIX"], priority: 99, hex: "#e0d5c0" }, // Mixes 99
  
  { keywords: ["WHITE", "BRIGHT WHITE"], priority: 10, hex: "#FFFFFF" },
  { keywords: ["IVORY", "OFF WHITE", "CREAM"], priority: 11, hex: "#FFFFF0" },
  
  // 2. YELLOWS (20-29)
  { keywords: ["LEMON YELLOW"], priority: 20, hex: "#FFF44F" },
  { keywords: ["YELLOW"], priority: 21, hex: "#FFFF00" },
  { keywords: ["GOLDEN YELLOW", "GOLD"], priority: 22, hex: "#FFD700" },
  
  // 3. ORANGES & PEACH (30-39)
  { keywords: ["PEACH"], priority: 30, hex: "#FFDAB9" },
  { keywords: ["ORANGE", "BRIGHT ORANGE"], priority: 31, hex: "#FFA500" },
  
  // 4. PINKS (40-49)
  { keywords: ["BABY PINK", "LIGHT PINK"], priority: 40, hex: "#FFB6C1" },
  { keywords: ["PINK", "ROSE"], priority: 41, hex: "#FFC0CB" },
  { keywords: ["DARK PINK", "HOT PINK"], priority: 42, hex: "#FF69B4" },
  
  // 5. REDS & MAROONS (50-59)
  { keywords: ["RED", "BRIGHT RED"], priority: 50, hex: "#FF0000" },
  { keywords: ["CRIMSON", "SCARLET"], priority: 51, hex: "#DC143C" },
  { keywords: ["MAROON", "DARK RED", "BURGUNDY"], priority: 52, hex: "#800000" },
  
  // 6. PURPLES & VIOLETS (60-69)
  { keywords: ["LAVENDER", "LILAC"], priority: 60, hex: "#E6E6FA" },
  { keywords: ["VIOLET"], priority: 61, hex: "#EE82EE" },
  { keywords: ["PURPLE", "MAGENTA"], priority: 62, hex: "#800080" },
  
  // 7. BLUES (70-79) - Light to Dark
  { keywords: ["SKY BLUE", "LIGHT BLUE"], priority: 70, hex: "#87CEEB" },
  { keywords: ["MEDICAL BLUE"], priority: 71, hex: "#0077B6" },
  { keywords: ["BLUE", "ROYAL BLUE"], priority: 72, hex: "#4169E1" },
  { keywords: ["PEACOCK BLUE"], priority: 73, hex: "#005F69" },
  { keywords: ["NAVY BLUE", "DARK BLUE"], priority: 74, hex: "#000080" }, // Darkest Blue
  
  // 8. GREENS (80-89) - Light to Dark
  { keywords: ["MINT GREEN"], priority: 80, hex: "#98FF98" },
  { keywords: ["PARROT GREEN", "LIGHT GREEN"], priority: 81, hex: "#90EE90" },
  { keywords: ["APPLE GREEN", "LIME GREEN"], priority: 82, hex: "#32CD32" },
  { keywords: ["GREEN", "KELLY GREEN"], priority: 83, hex: "#008000" },
  { keywords: ["SEA GREEN"], priority: 84, hex: "#2E8B57" },
  { keywords: ["BOTTLE GREEN"], priority: 85, hex: "#006A4E" },
  { keywords: ["OLIVE GREEN"], priority: 86, hex: "#808000" },
  { keywords: ["ARMY GREEN"], priority: 87, hex: "#4B5320" },
  { keywords: ["DARK GREEN"], priority: 88, hex: "#006400" },

  // 10. GREYS & SILVER (95-97)
  { keywords: ["SILVER", "LIGHT GREY"], priority: 95, hex: "#C0C0C0" },
  { keywords: ["GREY", "GRAY", "DARK GREY"], priority: 96, hex: "#808080" },
  
  // 9. BROWNS & BEIGES (Moved to End as per Transition Rule)
  // Transition: Black -> Beige -> [Others]
  // So Beige must be > 98 (Black)? Or < 98?
  // User said: "aftere black complusary need any color in beige after biege order placed allowed to place other colors"
  // If sorting Ascending (Light -> Dark):
  // White (10) ... Black (98).
  // If Black is last, then Beige needs to be 99?
  // But wait, user said "after black... beige".
  // If we sort 10->98. Black is at bottom.
  // Then next cycle starts?
  // OR does user run Black -> Beige -> White?
  // "red blue ... black ... after black compulsory beige ... after beige other colors"
  // This implies a CYCLE: Light -> Dark (Black) -> Beige -> Light.
  // So Beige should be effectively "Priority 100" or handle a wrap-around.
  // Let's set Beige to 99 (after Black).
  { keywords: ["BEIGE", "LIGHT BEIGE", "CREAM", "OFF WHITE", "IVORY"], priority: 99, hex: "#F5F5DC" }, 
  { keywords: ["DARK BEIGE", "KHAKI", "SAND"], priority: 99, hex: "#C2B280" }, 
  { keywords: ["BROWN", "CHOCOLATE", "COFFEE"], priority: 90, hex: "#A52A2A" }, // Brown can stay normal?

  // 11. BLACK (98)
  { keywords: ["BLACK"], priority: 98, hex: "#000000" },
];

const GAP_THRESHOLD = 0; // any color priority difference triggers mix roll

const units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Mixed"];
const UNIT_TONNAGE_LIMITS = { "Unit 1": 4.4, "Unit 2": 12, "Unit 3": 9, "Unit 4": 5.5, "Mixed": 999 };
const headerColors = { "Unit 1": "#3b82f6", "Unit 2": "#10b981", "Unit 3": "#f59e0b", "Unit 4": "#8b5cf6", "Mixed": "#64748b" };

const filterOrderDate = ref(frappe.datetime.get_today());
const filterPartyCode = ref("");
const filterUnit = ref("");
const filterStatus = ref("");
// Per-unit sort configuration
const unitSortConfig = reactive({});
// Pre-initialize for all units
units.forEach(u => {
    unitSortConfig[u] = { mode: 'auto', color: 'asc', gsm: 'desc', priority: 'color' };
});
const viewMode = ref('kanban'); // 'kanban' | 'matrix'
const rawData = ref([]);
const columnRefs = ref(null);
const matrixHeaderRow = ref(null); // Ref for Matrix Column sorting
const matrixBody = ref(null);      // Ref for Matrix Row sorting
const customRowOrder = ref([]);    // Store user-defined row order (List of Colors)
const renderKey = ref(0); // Force re-render for drag revert

// Matrix View Helpers
const matrixData = computed(() => {
    if (viewMode.value !== 'matrix') return [];
    
    // 1. Prepare Columns (Orders / Planning Sheets/Items)
    // Group items by "Order Identity" -> (Date + Code/Sheet + Quality + Customer + GSM)?
    // User wants "Date, Days, Code, GSM, Quality, Customer" as headers.
    // Each COLUMN represents a unique "Production Run" or Order Context.
    
    // We need to group detailed items into columns.
    // If an order has multiple colors, do they share a column?
    // In the Excel, "Code A26192" has multiple colors below it (Ivory, Golden Yellow).
    // So distinct columns are determined by: CODE (and its attributes).
    
    const groups = {};
    
    filteredData.value.forEach(d => {
        // UNIT FILTER (Matrix View needs this explicitly as filteredData doesn't filter unit)
        if (filterUnit.value && (d.unit || "Mixed") !== filterUnit.value) return;

        // ID for the Column Group
        // Use Planning Sheet Name or Code? 
        // d.planningSheet might be "PS-001". d.name is "PS-001-1".
        // Let's use `planningSheet` as the Grouper?
        const code = d.planningSheet; // Or d.partyCode? Excel says "Code A26192". This looks like a Sales Order or Sheet ID.
        
        if (!groups[code]) {
            groups[code] = {
                id: code,
                date: d.ordered_date || d.order_date || "", // Date
                days: 0, // Calculate Diff?
                code: code,
                gsm: d.gsm || "",
                quality: d.quality || "",
                customer: d.customer || d.partyCode || "",
                items: [],
                // Sort key for checks
                idxSum: 0 
            };
            
            // Calculate Days (Diff from Today?)
            // If "Days Remaining" (DOD - Today):
            if (d.dod) {
               const d1 = new Date(d.dod);
               const today = new Date();
               const diffTime = d1 - today; 
               const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
               groups[code].days = diffDays + " DAYS";
            } else if (groups[code].date) {
               // Fallback: Age (Today - Ordered Date)
               const d1 = new Date(groups[code].date);
               const today = new Date();
               const diffTime = today - d1;
               const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)); 
               groups[code].days = diffDays + " DAYS";
            }
        }
        groups[code].items.push(d);
    });

    // Sort Groups (Columns) by Date then Code
    const sortedGroups = Object.values(groups).sort((a, b) => {
        if (a.date !== b.date) return new Date(a.date) - new Date(b.date);
        return a.code.localeCompare(b.code);
    });

    // 2. Prepare Rows (Unique Colors)
    const allColors = new Set();
    filteredData.value.forEach(d => {
        if (d.color) allColors.add(d.color);
    });
    
    let sortedColors = [];
    if (customRowOrder.value.length > 0) {
        // Sort by Custom Order first, then New colors by Priority
        const customSet = new Set(customRowOrder.value);
        // Gets colors present in Data OR Custom Order (to maintain gaps if needed? No, only show data)
        // Actually we only show colors present in Data.
        
        const presentColors = Array.from(allColors);
        
        const ordered = customRowOrder.value.filter(c => allColors.has(c));
        const others = presentColors.filter(c => !customSet.has(c)).sort((a,b) => compareColor({color: a}, {color: b}, 'asc'));
        
        sortedColors = [...ordered, ...others];
        sortedColors = [...ordered, ...others];
    } else {
        // Default: Use order of appearance in filteredData (which matches rawData / idx)
        sortedColors = Array.from(allColors);
    }

    const rows = sortedColors.map(color => {
        return {
            color: color,
            cells: {}, // Key = Group ID (Code)
            total: 0
        };
    });

    // 3. Fill Cells
    rows.forEach(row => {
        sortedGroups.forEach(group => {
            // Find item with this color in this group
            const match = group.items.find(i => i.color === row.color);
            if (match) {
                row.cells[group.id] = match.qty;
                row.total += match.qty;
            }
        });
    });
    
    // Group Columns by DATE for Merged Header
    const dateHeaders = [];
    let lastDate = null;
    let currentSpan = 0;
    
    sortedGroups.forEach((g, index) => {
         const d = g.date;
         if (d !== lastDate) {
             if (lastDate !== null) {
                 dateHeaders.push({ date: lastDate, span: currentSpan });
             }
             lastDate = d;
             currentSpan = 1;
         } else {
             currentSpan++;
         }
         
         if (index === sortedGroups.length - 1) {
             dateHeaders.push({ date: lastDate, span: currentSpan });
         }
    });

    // Column Totals
    const colTotals = {};
    sortedGroups.forEach(g => {
        colTotals[g.id] = rows.reduce((sum, r) => sum + (r.cells[g.id] || 0), 0);
    });
    
    const grandTotal = rows.reduce((sum, r) => sum + r.total, 0);

    return {
        dateHeaders,
        columns: sortedGroups,
        rows,
        colTotals,
        grandTotal
    };
});

const visibleUnits = computed(() =>
  filterUnit.value ? units.filter((u) => u === filterUnit.value) : units
);

const EXCLUDED_WHITES = [
  "WHITE", "BRIGHT WHITE", "SUNSHINE WHITE", "MILKY WHITE", 
  "SUPER WHITE", "BLEACH WHITE", "BLEACH WHITE 1.0", "BLEACH WHITE 2.0"
];

// As per user request: "APART FROM THIS U CAN BRING ALL COLOR IVORY"
// So IVORY, CREAM, OFF WHITE are kept.

// Filter data by party code and status
const filteredData = computed(() => {
  let data = rawData.value;
  
  data = data.filter(d => {
      // Normalize Unit for Display
      if (!d.unit) d.unit = "Mixed";

      const colorUpper = (d.color || "").toUpperCase();
      
      // Keep Ivory/Cream explicitly
      if (colorUpper.includes("IVORY") || colorUpper.includes("CREAM") || colorUpper.includes("OFF WHITE")) return true;
      
      // Remove Excluded Whites
      return !EXCLUDED_WHITES.some(ex => colorUpper.includes(ex));
  });

  if (filterPartyCode.value) {
    const search = filterPartyCode.value.toLowerCase();
    data = data.filter((d) =>
      (d.partyCode || "").toLowerCase().includes(search) ||
      (d.customer || "").toLowerCase().includes(search)
    );
  }
  if (filterStatus.value) {
    data = data.filter((d) => d.planningStatus === filterStatus.value);
  }
  return data;
});

function clearFilters() {
  filterOrderDate.value = frappe.datetime.get_today();
  filterPartyCode.value = "";
  filterUnit.value = "";
  filterStatus.value = "";
  // Reset all unit configs to default? Or keep them?
  // Let's keep them or reset them. User might want to clear filters but keep sort.
  // We'll leave unitSortConfig as is.
  fetchData();
}

// Find matching color group by checking if color name contains any keyword
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
  // Check custom order first (Sync with Matrix View)
  if (customRowOrder.value && customRowOrder.value.length > 0) {
      const idx = customRowOrder.value.indexOf(color);
      if (idx !== -1) {
          // Return a priority that overrides standard groups.
          // Lower number = higher priority. Standard groups are 10-99.
          return idx - 1000; 
      }
  }
  const group = findColorGroup(color);
  return group ? group.priority : 50;
}

function getHexColor(color) {
  const group = findColorGroup(color);
  return group ? group.hex : "#ccc";
}

// Mix roll qty: 100 Kg increments based on color gap
// Gap 1-3: 100 Kg (close colors)
// Gap 4-7: 200 Kg
// Gap 8-11: 300 Kg
// ...every +4 gap = +100 Kg
// Gap 35 (WHITE to BLACK): ~1000 Kg (max)
function getMixRollQty(gap) {
  const baseQty = 100;
  const increment = Math.floor(gap / 4) * 100;
  const totalQty = baseQty + increment;
  return Math.min(totalQty, 1000); // Cap at 1000 Kg
}

function determineMixType(fromColor, toColor) {
  const fromGroup = findColorGroup(fromColor);
  const toGroup = findColorGroup(toColor);
  const fromPri = fromGroup ? fromGroup.priority : 50;
  const toPri = toGroup ? toGroup.priority : 50;
  if (fromPri === 1 || toPri === 1) return "WHITE MIX";
  if (fromPri === 36 || toPri === 36) return "BLACK MIX";
  const from = (fromColor || "").toUpperCase();
  const to = (toColor || "").toUpperCase();
  if (from.includes("BEIGE") || to.includes("BEIGE")) return "BEIGE MIX";
  return "COLOR MIX";
}

// Per-unit quality priorities (lower number = higher priority)
const QUALITY_PRIORITY = {
  "Unit 1": { "PREMIUM": 1, "PLATINUM": 2, "SUPER PLATINUM": 3, "GOLD": 4, "SILVER": 5 },
  "Unit 2": { 
      "GOLD": 1, "SILVER": 2, "BRONZE": 3, "CLASSIC": 4, "SUPER CLASSIC": 5, 
      "LIFE STYLE": 6, "ECO SPECIAL": 7, "ECO GREEN": 8, "SUPER ECO": 9, "ULTRA": 10, "DELUXE": 11 
  },
  "Unit 3": { "PREMIUM": 1, "PLATINUM": 2, "SUPER PLATINUM": 3, "GOLD": 4, "SILVER": 5, "BRONZE": 6 },
  "Unit 4": { "PREMIUM": 1, "GOLD": 2, "SILVER": 3, "BRONZE": 4 },
};

function getQualityPriority(unit, quality) {
  const upper = (quality || "").toUpperCase().trim();
  const unitMap = QUALITY_PRIORITY[unit] || {};
  return unitMap[upper] || 99; // Unknown quality = lowest priority
}

// Helper Comparators
function compareQuality(unit, a, b) {
    return getQualityPriority(unit, a.quality) - getQualityPriority(unit, b.quality);
}

function compareColor(a, b, direction) {
    const pA = getColorPriority(a.color);
    const pB = getColorPriority(b.color);
    return direction === 'asc' ? pA - pB : pB - pA;
}

function compareGsm(a, b, direction) {
    const gA = parseFloat(a.gsm || 0);
    const gB = parseFloat(b.gsm || 0);
    return direction === 'asc' ? gA - gB : gB - gA;
}

// Visually display sort state
function getSortLabel(unit) {
    const config = getUnitSortConfig(unit);
    if (config.mode === 'manual') return 'Manual Sort';
    const p = config.priority === 'color' ? 'Color' : (config.priority === 'gsm' ? 'GSM' : 'Quality');
    const d = config.priority === 'color' ? config.color : (config.priority === 'gsm' ? config.gsm : 'ASC');
    return `${p} (${d.toUpperCase()})`; 
}

// Capacity Helper - Uses RAW DATA (Correct!) to include Hidden White Orders
function getUnitTotal(unit) {
  // Use rawData.value to ensure hidden orders (White) are counted in capacity
  return rawData.value
    .filter((d) => (d.unit || "Mixed") === unit)
    .reduce((sum, d) => sum + d.qty, 0) / 1000;
}

function getHiddenWhiteTotal(unit) {
  return rawData.value
    .filter((d) => {
        if ((d.unit || "Mixed") !== unit) return false;
        const colorUpper = (d.color || "").toUpperCase();
        // Check if it IS an excluded white
        if (colorUpper.includes("IVORY") || colorUpper.includes("CREAM") || colorUpper.includes("OFF WHITE")) return false;
        return EXCLUDED_WHITES.some(ex => colorUpper.includes(ex));
    })
    .reduce((sum, d) => sum + d.qty, 0) / 1000;
}



function getUnitCapacityStatus(unit) {
    const total = getUnitTotal(unit);
    const limit = UNIT_TONNAGE_LIMITS[unit] || 999;
    
    // STRICT Warning (Red) if over limit
    if (total > limit) {
        return { 
            class: 'text-red-600 font-bold', 
            warning: `âš ï¸ Over Limit (${(total - limit).toFixed(2)}T)!` 
        };
    }
    // Warning (Orange) if near limit (within 10%)
    if (total > limit * 0.9) {
        return { 
            class: 'text-orange-600 font-bold', 
            warning: `âš ï¸ Near Limit` 
        };
    }
    
    return { class: 'text-gray-600', warning: '' };
}

// ... (Mix Roll functions use getUnitEntries which uses filteredData - Correct for VISUALS) ...

async function initSortable() {
  if (!columnRefs.value) return;
  
  // Clear old instances
  columnRefs.value.forEach(col => {
      if (col._sortable) col._sortable.destroy();
  });
  if (matrixHeaderRow.value && matrixHeaderRow.value._sortable) matrixHeaderRow.value._sortable.destroy();
  if (matrixBody.value && matrixBody.value._sortable) matrixBody.value._sortable.destroy();

  // MATRIX VIEW SORTABLE
  if (viewMode.value === 'matrix') {
      // 1. COLUMNS (Headers)
      if (matrixHeaderRow.value) {
          matrixHeaderRow.value._sortable = new Sortable(matrixHeaderRow.value, {
             group: 'matrix-cols',
             animation: 150,
             handle: '.draggable-handle',
             draggable: '.matrix-col-header',
             ghostClass: 'cc-ghost',
             onEnd: async (evt) => {
                 const { newIndex, item } = evt;
                 const allCols = Array.from(matrixHeaderRow.value.querySelectorAll('.matrix-col-header'));
                 let targetDate = null;
                 const leftEl = allCols[newIndex - 1];
                 if (leftEl) {
                     targetDate = leftEl.dataset.date;
                 } else {
                     const rightEl = allCols[newIndex + 1];
                     if (rightEl) targetDate = rightEl.dataset.date;
                 }
                 
                 if (targetDate) {
                     const originalDate = item.dataset.date;
                     if (originalDate === targetDate) return;
                     
                     if (confirm(`Move Order to ${targetDate}?`)) {
                         const colId = item.dataset.id;
                         const group = matrixData.value.columns.find(c => c.id === colId);
                         if (group && group.items.length) {
                             const itemNames = group.items.map(i => i.itemName);
                             try {
                                 await frappe.call({
                                     method: "production_scheduler.api.move_orders_to_date",
                                     args: { item_names: itemNames, target_date: targetDate }
                                 });
                                 fetchData();
                             } catch(e) { console.error(e); renderKey.value++; }
                         }
                     } else { renderKey.value++; }
                 } else { renderKey.value++; }
             }
          });
      }

      // 2. ROWS (Colors)
      if (matrixBody.value) {
          matrixBody.value._sortable = new Sortable(matrixBody.value, {
              group: 'matrix-rows',
              animation: 150,
              handle: '.matrix-row-header',
              draggable: '.matrix-row',
              ghostClass: 'cc-ghost',
              onEnd: (evt) => {
                  const { oldIndex, newIndex } = evt;
                  if (oldIndex === newIndex) return;
                  const rows = Array.from(matrixBody.value.querySelectorAll('.matrix-row'));
                  customRowOrder.value = rows.map(r => r.dataset.color);
                  frappe.call({
                      method: "production_scheduler.api.save_color_order",
                      args: { order: customRowOrder.value },
                      callback: () => frappe.show_alert("Color Order Saved", 2)
                  });
              }
          });
      }
      return; 
  }

  // KANBAN VIEW SORTABLE
  columnRefs.value.forEach((colEl) => {
    if (!colEl) return;
    colEl._sortable = new Sortable(colEl, {
      group: "kanban",
      animation: 150,
      ghostClass: "cc-ghost",
      onEnd: async (evt) => {
        const { item, to, from, newIndex, oldIndex } = evt;
        const itemName = item.dataset.itemName;
        const newUnit = to.dataset.unit;
        if (!itemName || !newUnit) return;

        if (to !== from || newIndex !== oldIndex) {
             try {
                frappe.show_alert({ message: "Validating Capacity...", indicator: "orange" });
                
                const performMove = async (force=0, split=0) => {
                    return await frappe.call({
                        method: "production_scheduler.api.update_schedule",
                        args: {
                            item_name: itemName, 
                            unit: newUnit,
                            date: filterOrderDate.value,
                            index: newIndex + 1,
                            force_move: force,
                            perform_split: split
                        }
                    });
                };

                let res = await performMove();
                
                if (res.message && res.message.status === 'overflow') {
                     const avail = res.message.available;
                     const limit = res.message.limit;
                     const current = res.message.current_load;
                     const orderWt = res.message.order_weight;
                     
                     const d = new frappe.ui.Dialog({
                        title: 'âš ï¸ Capacity Full',
                        fields: [{
                             fieldtype: 'HTML', fieldname: 'msg',
                             options: `<div style="text-align:center; padding:10px;">
                                 <p class="text-lg font-bold text-red-600">Unit Capacity Exceeded!</p>
                                 <p>Unit Limit: <b>${limit}T</b> | Current: <b>${current.toFixed(2)}T</b></p>
                                 <p>Your Order: <b>${orderWt.toFixed(2)}T</b></p>
                                 <p class="mt-2 text-green-600 font-bold">Available Space: ${avail.toFixed(3)}T</p>
                             </div>`
                        }],
                        primary_action_label: 'Move to Next Day',
                        primary_action: async () => {
                            d.hide();
                            const res2 = await performMove(1, 0);
                            handleMoveSuccess(res2, newUnit);
                        },
                        secondary_action_label: 'Cancel',
                        secondary_action: () => { d.hide(); renderKey.value++; }
                     });
                     
                     d.add_custom_action('Split & Distribute', async () => {
                         d.hide();
                         if (avail < 0.1) {
                             frappe.msgprint("Space too small to split.");
                             renderKey.value++; return;
                         }
                         const res3 = await performMove(0, 1);
                         handleMoveSuccess(res3, newUnit);
                     }, 'btn-warning');
                     d.show();
                } else {
                     handleMoveSuccess(res, newUnit);
                }
             } catch (e) {
                 console.error(e);
                 frappe.msgprint("âŒ Move Failed");
                 renderKey.value++;
             }
        }
      },
    });
  });
}

async function handleMoveSuccess(res, newUnit) {
    if (res.message && res.message.status === 'success') {
        const movedTo = res.message.moved_to || { unit: newUnit, date: filterOrderDate.value };
        if (movedTo.date !== filterOrderDate.value) {
             frappe.msgprint(`Moved to ${movedTo.date}`);
        } else if (movedTo.unit !== newUnit) {
             frappe.msgprint(`Placed in ${movedTo.unit} (Capacity Full in ${newUnit})`);
        } else {
             frappe.show_alert({ message: "Moved successfully", indicator: "green" });
        }
        unitSortConfig[movedTo.unit].mode = 'manual';
        await fetchData(); 
    }
}

function getUnitSortConfig(unit) {
  if (!unitSortConfig[unit]) {
    unitSortConfig[unit] = { mode: 'auto', color: 'asc', gsm: 'desc', priority: 'color' };
  }
  return unitSortConfig[unit];
}

function toggleUnitColor(unit) {
  const config = getUnitSortConfig(unit);
  config.mode = 'auto'; 
  if (config.priority !== 'color') {
      config.priority = 'color';
      config.color = 'asc';
  } else {
      config.color = config.color === 'asc' ? 'desc' : 'asc';
  }
}

function toggleUnitGsm(unit) {
  const config = getUnitSortConfig(unit);
  config.mode = 'auto';
  if (config.priority !== 'gsm') {
      config.priority = 'gsm';
      config.gsm = 'asc';
  } else {
      config.gsm = config.gsm === 'asc' ? 'desc' : 'asc';
  }
}

function toggleUnitPriority(unit) {
  const config = getUnitSortConfig(unit);
  config.mode = 'auto';
  config.priority = config.priority === 'color' ? 'gsm' : 'color';
}

function sortItems(unit, items) {
  const config = getUnitSortConfig(unit);
  if (config.mode === 'manual') {
      return [...items].sort((a, b) => (a.idx || 0) - (b.idx || 0));
  }
  return [...items].sort((a, b) => {
      let diff = 0;
      if (config.priority === 'color') {
          diff = compareColor(a, b, config.color);
          if (diff === 0) diff = compareGsm(a, b, config.gsm);
      } else {
          diff = compareGsm(a, b, config.gsm);
          if (diff === 0) diff = compareColor(a, b, config.color);
      }
      if (diff === 0) diff = (a.idx || 0) - (b.idx || 0);
      return diff;
  });
}

// Group data by unit, sort, and insert mix markers
function getUnitEntries(unit) {
  let unitItems = filteredData.value.filter((d) => (d.unit || "Mixed") === unit);
  unitItems = sortItems(unit, unitItems); 

  const entries = [];
  for (let i = 0; i < unitItems.length; i++) {
    entries.push({ 
      type: "order", 
      ...unitItems[i],
      uniqueKey: unitItems[i].itemName
    });
    if (i < unitItems.length - 1) {
      const curPri = getColorPriority(unitItems[i].color);
      const nextPri = getColorPriority(unitItems[i + 1].color);
      if (curPri !== nextPri || unitItems[i].color !== unitItems[i+1].color) {
          const gap = Math.abs(curPri - nextPri);
          entries.push({
              type: "mix",
              mixType: determineMixType(unitItems[i].color, unitItems[i+1].color),
              unit: unit,
              fromColor: unitItems[i].color,
              toColor: unitItems[i+1].color,
              qty: getMixRollQty(gap),
              uniqueKey: `mix-${unitItems[i].itemName}-${unitItems[i+1].itemName}`
          });
      }
    }
  }
  return entries;
}

function getUnitProductionTotal(unit) {
  return rawData.value
    .filter((d) => (d.unit || "Mixed") === unit)
    .reduce((sum, d) => sum + (parseFloat(d.actual_qty) || 0), 0) / 1000;
}

function getMixRollCount(unit) {
  return getUnitEntries(unit).filter((e) => e.type === "mix").length;
}

function getMixRollTotalWeight(unit) {
  return getUnitEntries(unit)
    .filter((e) => e.type === "mix")
    .reduce((sum, e) => sum + e.qty, 0);
}

function toggleDirection() {
  direction.value = direction.value === "asc" ? "desc" : "asc";
}

function openForm(name) {
  frappe.set_route("Form", "Planning sheet", name);
}

async function analyzePreviousFlow() {
  if (!filterOrderDate.value) return;
  try {
    const prevDateArgs = await frappe.call({
      method: "production_scheduler.api.get_previous_production_date",
      args: { date: filterOrderDate.value }
    });
    const prevDate = prevDateArgs.message;
    
    if (prevDate) {
      const r = await frappe.call({
        method: "production_scheduler.api.get_color_chart_data",
        args: { date: prevDate }
      });
      const prevData = r.message || [];
      if (prevData.length > 0) {
        // Group previous data by unit
        const prevByUnit = {};
        units.forEach(u => prevByUnit[u] = []);
        prevData.forEach(item => {
           if (prevByUnit[item.unit]) prevByUnit[item.unit].push(item);
        });

         // Analyze each unit
         units.forEach(unit => {
            const prevItems = prevByUnit[unit];
            const config = getUnitSortConfig(unit);

            if (prevItems && prevItems.length > 0) {
               const lastItem = prevItems[prevItems.length - 1]; // sorted by idx
               
               // Color Logic (Existing)
               const lastPri = getColorPriority(lastItem.color);
               if (lastPri > 20) {
                  config.color = 'desc'; // Ended Dark -> Start Dark->Light
               } else {
                  config.color = 'asc';
               }
               
               // GSM Logic - Smart Gap Minimization
               const lastGsm = parseFloat(lastItem.gsm || 0);
               // Get Today's Items for this unit to find min/max
               const todayItems = filteredData.value.filter(d => d.unit === unit);
               
               if (todayItems.length > 0) {
                   const gsms = todayItems.map(d => parseFloat(d.gsm || 0));
                   const minGsm = Math.min(...gsms);
                   const maxGsm = Math.max(...gsms);
                   
                   const gapAsc = Math.abs(lastGsm - minGsm);  // If Start Low
                   const gapDesc = Math.abs(lastGsm - maxGsm); // If Start High
                   
                   // Choose direction with smaller gap
                   if (gapDesc < gapAsc) {
                       config.gsm = 'desc';
                   } else {
                       config.gsm = 'asc';
                   }
                   console.log(`Unit ${unit} Smart Sort: Last GSM ${lastGsm}. Today Min ${minGsm}, Max ${maxGsm}. Chose ${config.gsm}`);
               }
            }
         });
        
        
        frappe.show_alert("Updated sort based on previous day flow");
        // Force re-render of columns to ensure mix rolls are displayed correctly
        renderKey.value++;
      }
    }
  } catch (e) {
    console.error("Error analyzing previous flow", e);
  }
}

async function fetchData() {
  if (!filterOrderDate.value) return;
  try {
    const r = await frappe.call({
      method: "production_scheduler.api.get_color_chart_data",
      args: { date: filterOrderDate.value },
    });
    // Ensure idx is integer
    rawData.value = (r.message || []).map(d => ({
        ...d,
        idx: parseInt(d.idx || 0) || 9999
    }));
    // Load Custom Color Order (Sync)
    try {
        const orderRes = await frappe.call("production_scheduler.api.get_color_order");
        customRowOrder.value = orderRes.message || [];
    } catch(e) { console.error("Failed to load color order", e); }

    // Force Reactive UI Refresh
    renderKey.value++; 
    
    await nextTick();
    initSortable();
  } catch (e) {
    frappe.msgprint("Error loading color chart data");
    console.error(e);
  }
}

// Watch date to re-analyze flow
// Watch date to re-analyze flow
watch(filterOrderDate, async () => {
  await fetchData();
  await analyzePreviousFlow(); 
});

// ---- AUTO ALLOCATION (BIN PACKING) ----
const UNIT_WIDTHS = {
  "Unit 1": 63,
  "Unit 2": 126,
  "Unit 3": 126,
  "Unit 4": 90
};



async function autoAllocate() {
  if (!confirm("Auto-allocate visible orders based on Width & Quality? This will overwrite current unit assignments.")) return;

  const itemsToAlloc = filteredData.value; // Allocate currently filtered items
  if (itemsToAlloc.length === 0) return;

  // 1. Group by Quality + Color (assume same color/quality run together)
  const groups = {};
  const unallocated = []; // Track items that don't fit
  itemsToAlloc.forEach(item => {
    const key = `${item.quality}|${item.color}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  });

  const updates = [];

  // 2. Process each group
  for (const key in groups) {
    const groupItems = groups[key];
    const [quality, color] = key.split("|");
    
    // Sort items by width DESC (Best Fit Decreasing)
    groupItems.sort((a, b) => (b.width || 0) - (a.width || 0));

    // Find compatible units based on QUALITY_PRIORITY map
    // (If map exists for a unit, it lists supported qualities. If quality not in map, maybe not supported?)
    // But user said "Gold can run Unit 3". U3 map has Gold.
    let compatibleUnits = units.filter(u => {
      const priMap = QUALITY_PRIORITY[u];
      // If unit has no map (empty?), assume generic? No, strict check if map exists.
      // If unit has map, check if quality is in it.
      if (priMap) {
         // If map has entries, strict check.
         if (Object.keys(priMap).length > 0) {
             return priMap[quality] !== undefined;
         }
      }
      return true; // If no map, assume compatible
    });
    
    if (compatibleUnits.length === 0) {
        // Fallback: try all units if strict check fails (maybe 'General' quality?)
        compatibleUnits = [...units];
    }

    // Sort Units: Preference for Larger Width to facilitate grouping?
    // Actually, maybe sort by Remaining Tonnage Capacity?
    // For now, keep width logic but respect Tonnage.
    compatibleUnits.sort((a, b) => UNIT_WIDTHS[b] - UNIT_WIDTHS[a]);
    
    // Simulate current loads for this allocation session (since we are overwriting)
    // We need to know if we are appending or overwriting.
    // Alert says "overwrite current unit assignments". So we assume starting from 0 for these items.
    // But what about items NOT in this filter?
    // If we filter by "All Units", we re-allocate everything.
    // Ideally we should account for "Locked" or "Other" items.
    // For simplicity: We track load of items WE assign in this batch.
    // Realistically, we should check existing load of UNSOUCHED items.
    // But let's start with a local tracker.
    const batchLoads = {};
    units.forEach(u => batchLoads[u] = 0);

    for (const item of groupItems) {
        const itemWidth = parseFloat(item.width || 0);
        const itemTonnage = (item.qty || 0) / 1000;
        
        let bestUnit = null;
        let minWaste = Infinity;
        
        for (const unit of compatibleUnits) {
             const unitWidth = UNIT_WIDTHS[unit];
             const limit = UNIT_TONNAGE_LIMITS[unit];
             
             // Check 1: Width Fit
             if (unitWidth >= itemWidth) {
                 // Check 2: Tonnage Capacity
                 if (batchLoads[unit] + itemTonnage <= limit) {
                     const waste = unitWidth - itemWidth;
                     // Heuristic: Best Fit (Min Waste)
                     if (waste < minWaste) {
                         minWaste = waste;
                         bestUnit = unit;
                     }
                 }
             }
        }
        
        if (bestUnit) {
            updates.push({
                name: item.itemName,
                unit: bestUnit
            });
            batchLoads[bestUnit] += itemTonnage;
        } else {
            console.warn(`Could not allocate ${item.itemName}. Full or No Fit.`);
            unallocated.push(item);
        }
    }
  }

  // 3. Apply updates (Unit Changes)
  if (updates.length > 0) {
      try {
          // Optimistic update
          updates.forEach(upd => {
             const item = rawData.value.find(d => d.itemName === upd.name);
             if (item) item.unit = upd.unit;
          });

          // API Call
          await frappe.call({
            method: "production_scheduler.api.update_items_bulk",
            args: { items: updates }
          });
          
          frappe.show_alert({ message: `Auto-allocated ${updates.length} orders`, indicator: "green" });
      } catch (e) {
          console.error(e);
          frappe.msgprint("Error auto-allocating");
          fetchData(); 
      }
  }

  // 4. Handle Unallocated (Rollover)
  if (unallocated.length > 0) {
      const nextDate = frappe.datetime.add_days(filterOrderDate.value, 1);
      const totalUnallocated = unallocated.reduce((s, i) => s + (i.qty/1000), 0).toFixed(2);
      
      if (confirm(`${unallocated.length} orders (${totalUnallocated}T) could not fit in today's capacity.\n\nMove them to the Next Day (${nextDate})?`)) {
          console.log("Moving to next day:", nextDate, unallocated);
          const dateUpdates = unallocated.map(item => ({
              name: item.itemName,
              date: nextDate 
          }));
          
          try {
              await frappe.call({
                method: "production_scheduler.api.update_items_bulk",
                args: { items: dateUpdates }
              });
              frappe.show_alert({ message: `Moved ${unallocated.length} orders to ${nextDate}`, indicator: "orange" });
              
              // Remove from current view
              rawData.value = rawData.value.filter(d => !unallocated.find(u => u.itemName === d.itemName));
          } catch (e) {
              console.error(e);
              frappe.msgprint("Error moving items to next day");
          }
      }
  }
}



// ---- STATE PERSISTENCE (URL SYNC) ----
function updateUrlParams() {
  const url = new URL(window.location);
  if (filterOrderDate.value) url.searchParams.set('date', filterOrderDate.value);
  if (filterUnit.value) url.searchParams.set('unit', filterUnit.value);
  else url.searchParams.delete('unit');
  
  if (filterStatus.value) url.searchParams.set('status', filterStatus.value);
  else url.searchParams.delete('status');
  
  window.history.replaceState({}, '', url);
}

// Watchers to sync state
watch(filterOrderDate, () => {
    updateUrlParams();
    // fetchData called by existing watcher
});
watch(filterUnit, updateUrlParams);
watch(filterStatus, updateUrlParams);

// Re-init Sortable when renderKey changes (forced re-render)
watch(renderKey, () => {
    nextTick(() => {
        initSortable();
    });
});

onMounted(() => {
  // 1. Read URL Params
  const params = new URLSearchParams(window.location.search);
  const dateParam = params.get('date');
  const unitParam = params.get('unit');
  const statusParam = params.get('status');
  
  if (dateParam) {
      filterOrderDate.value = dateParam;
  } else {
      // Default to today if not provided
      // If filterOrderDate was already set in setup(), this is fine.
      if (!filterOrderDate.value) filterOrderDate.value = frappe.datetime.get_today();
  }
  
  if (unitParam) filterUnit.value = unitParam;
  if (statusParam) {
       // Ensure valid status
       if (["Draft", "Finalized"].includes(statusParam)) filterStatus.value = statusParam;
  }
  
  // 2. Fetch Data
  fetchData();
  analyzePreviousFlow();
});

// ---- SHARED ACTION ----
async function handleMoveOrders(items, date, unit, dialog) {
    // If unit is "Keep Original", passed as empty string
    try {
        // We use freeze:true to prevent UI interaction, but we settle generic errors manually to parse them
        const r = await frappe.call({
            method: "production_scheduler.api.move_orders_to_date",
            args: {
                item_names: items,
                target_date: date,
                target_unit: unit
            },
            freeze: true
        });
        
        if (r.message && r.message.status === 'success') {
            const currentFilterDate = filterOrderDate.value;
            const targetDate = date;
            
            const successMsg = `Successfully moved ${r.message.count} orders to ${targetDate}.`;
            frappe.show_alert({ message: successMsg, indicator: 'green' });
            
            // If moved to a date not currently viewed, show a more prominent message
            if (targetDate !== currentFilterDate) {
                frappe.msgprint({
                    title: __('Orders Moved'),
                    indicator: 'green',
                    primary_action: {
                        label: `Go to ${targetDate}`,
                        action: () => {
                            filterOrderDate.value = targetDate;
                            fetchData();
                        }
                    },
                    message: `Moved ${r.message.count} orders to <b>${targetDate}</b>.<br>They are no longer on this board.`
                });
            }
            
            if (dialog) dialog.hide();
            
            // Comprehensive Refresh
            await fetchData();
            await analyzePreviousFlow(); // Keep sorting consistent with flow
        }
    } catch (e) {
        console.error("Move failed", e);
        
        // Robust Error Extraction
        let msg = "";
        
        const cleanError = (raw) => {
            if (!raw) return "";
            
            // If it's a string, try to parse it (it might be double-encoded JSON)
            if (typeof raw === 'string') {
                const trimmed = raw.trim();
                if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
                    try {
                        return cleanError(JSON.parse(trimmed));
                    } catch (err) {
                        return raw;
                    }
                }
                // If it's HTML, try to strip tags or return as is
                if (raw.includes('<div') || raw.includes('<p')) {
                    const temp = document.createElement('div');
                    temp.innerHTML = raw;
                    return temp.textContent || temp.innerText || raw;
                }
                return raw;
            }
            
            // If it's an array, join its elements
            if (Array.isArray(raw)) {
                return raw.map(cleanError).filter(Boolean).join("\n");
            }
            
            // If it's an object, prioritize 'message' or 'error' property
            if (typeof raw === 'object') {
                if (raw.message) return cleanError(raw.message);
                if (raw.error) return cleanError(raw.error);
                // Last resort: stringify
                try {
                    return cleanError(JSON.stringify(raw));
                } catch (err) {
                    return String(raw);
                }
            }
            
            return String(raw);
        };

        const serverMsgs = e.server_messages || e._server_messages || (e.responseJSON && e.responseJSON._server_messages);
        msg = cleanError(serverMsgs || e.message || e.error || e.responseText || e);
        
        // Final trim and cleanup
        msg = msg.split('\n').map(s => s.trim()).filter(Boolean).join('\n');
        
        if (msg && msg.toLowerCase().includes("capacity exceeded")) {
             // Propose Next Day
             const nextDay = frappe.datetime.add_days(date, 1);
             frappe.confirm(
                 `<b>Capacity Limit Reached!</b><br>${msg}<br><br>Do you want to move these orders to <b>${nextDay}</b> instead?`,
                 () => {
                     handleMoveOrders(items, nextDay, unit, dialog);
                 },
                 () => {
                     // No / Cancel -> Revert UI
                     renderKey.value++;
                 }
             );
        } else {
             frappe.msgprint(msg || "An error occurred while moving orders.");
        }
    }
}

// ---- PULL ORDERS FROM FUTURE ----
function openPullOrdersDialog() {
    const nextDay = frappe.datetime.add_days(filterOrderDate.value, 1);
    
    // Create Dialog
    const d = new frappe.ui.Dialog({
        title: 'ðŸ“¥ Pull Orders from Date',
        fields: [
            {
                label: 'Source Date',
                fieldname: 'source_date',
                fieldtype: 'Date',
                default: nextDay,
                reqd: 1,
                onchange: () => loadOrders(d)
            },
            {
                label: 'Target Unit (Optional)',
                fieldname: 'target_unit',
                fieldtype: 'Select',
                options: [
                    { label: 'Keep Original Unit', value: '' },
                    ...units.map(u => ({ label: `Move to ${u}`, value: u }))
                ],
                default: '',
                description: 'If selected, all pulled orders will be assigned to this unit.'
            },
            {
                fieldtype: 'HTML',
                fieldname: 'preview_html'
            }
        ],
        primary_action_label: 'Move Selected to Today',
        primary_action: () => {
            const selected = d.calc_selected_items || [];
            if (selected.length === 0) {
                frappe.msgprint("Please select at least one order.");
                return;
            }
            const targetUnit = d.get_value('target_unit');
            handleMoveOrders(selected, filterOrderDate.value, targetUnit, d);
        }
    });
    
    d.show();
    // Initial Load
    loadOrders(d);
}

async function loadOrders(d) {
    const date = d.get_value('source_date');
    if (!date) return;
    
    d.set_value('preview_html', '<p class="text-gray-500 italic p-2">Loading...</p>');
    
    try {
        const r = await frappe.call({
            method: "production_scheduler.api.get_orders_for_date",
            args: { date: date }
        });
        
        const items = r.message || [];
        if (items.length === 0) {
            d.set_value('preview_html', '<p class="text-gray-500 italic p-2">No active orders found for this date.</p>');
            d.calc_selected_items = [];
            return;
        }
        
        // Modern List View using Flexbox/Grid
        let html = `
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff;">
                <div style="position: sticky; top: 0; background: #f8fafc; z-index: 10; padding: 10px 12px; border-bottom: 1px solid #e2e8f0; display: grid; grid-template-columns: 40px 80px 1fr 100px; gap: 8px; font-weight: 600; font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">
                    <div style="display:flex; align-items:center; justify-content:center;"><input type="checkbox" id="select-all-pull" style="cursor:pointer;" /></div>
                    <div>Unit</div>
                    <div>Order Details</div>
                    <div style="text-align:right;">Qty</div>
                </div>
                <div style="display: flex; flex-direction: column;">
        `;
        
        items.forEach(item => {
            // Quality Badge Color
            const q = (item.quality || '').toUpperCase();
            let qBadgeColor = '#e2e8f0';
            let qTextColor = '#475569';
            if (q.includes('PLATINUM')) { qBadgeColor = '#e0e7ff'; qTextColor = '#3730a3'; }
            else if (q.includes('GOLD')) { qBadgeColor = '#fef3c7'; qTextColor = '#92400e'; }
            else if (q.includes('PREMIUM')) { qBadgeColor = '#dcfce7'; qTextColor = '#166534'; }
            
            html += `
                <div class="pull-item-row" style="display: grid; grid-template-columns: 40px 80px 1fr 100px; gap: 8px; padding: 10px 12px; border-bottom: 1px solid #f1f5f9; align-items: center; transition: background 0.2s;">
                    <div style="display:flex; align-items:center; justify-content:center;">
                        <input type="checkbox" class="pull-item-cb" data-name="${item.name}" style="cursor:pointer; transform: scale(1.1);" />
                    </div>
                    
                    <!-- Unit -->
                    <div>
                        <span style="font-size: 11px; font-weight: 700; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">
                            ${item.unit || 'UNASSIGNED'}
                        </span>
                    </div>
                    
                    <!-- Details -->
                    <div style="display: flex; flex-direction: column; gap: 2px;">
                        <span style="font-size: 13px; font-weight: 600; color: #1e293b;">
                            ${item.item_name}
                            <span style="font-weight: 400; color: #94a3b8; font-size: 12px; margin-left: 4px;">
                                &bull; <span style="color: #0f172a;">${item.party_code || item.customer || '-'}</span>
                            </span>
                        </span>
                        
                        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 2px;">
                            <!-- Color Badge -->
                            <span style="display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e2e8f0; padding: 1px 6px; border-radius: 99px; font-size: 11px; background: #fff;">
                                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background-color: ${getHexColor(item.color)}; box-shadow: 0 0 0 1px rgba(0,0,0,0.1);"></span>
                                <span style="color: #334155; font-weight: 500;">${item.color || 'No Color'}</span>
                            </span>
                            
                            <!-- Quality Badge -->
                            <span style="font-size: 10px; font-weight: 600; background: ${qBadgeColor}; color: ${qTextColor}; padding: 1px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.3px;">
                                ${item.quality || 'STD'}
                            </span>
                            
                            <!-- GSM Badge -->
                            <span style="font-size: 10px; font-weight: 600; background: #f3f4f6; color: #4b5563; padding: 1px 6px; border-radius: 4px;">
                                ${item.gsm ? item.gsm + ' GSM' : 'N/A'}
                            </span>
                        </div>
                    </div>
                    
                    <!-- Qty -->
                    <div style="text-align: right;">
                        <span style="display: block; font-size: 14px; font-weight: 700; color: #0f172a;">${(item.qty/1000).toFixed(2)} T</span>
                    </div>
                </div>
            `;
        });
        
        html += `</div></div>`;
        
        // Summary
        html += `<div style="margin-top:8px; text-align:right; font-weight:600; font-size:12px; color:#64748b;">Total Orders: ${items.length}</div>`;
        
        d.set_value('preview_html', html);
        
        // Bind Events
        d.$wrapper.find('#select-all-pull').on('change', function() {
            const checked = $(this).prop('checked');
            d.$wrapper.find('.pull-item-cb').prop('checked', checked);
            updateSelection(d);
        });
        
        d.$wrapper.find('.pull-item-cb').on('change', function() {
            updateSelection(d);
        });
        
        // Initialize selection tracker
        d.calc_selected_items = [];
        
    } catch (e) {
        console.error(e);
        d.set_value('preview_html', '<p class="text-red-500">Error loading orders.</p>');
    }
}

function updateSelection(d) {
    const selected = [];
    d.$wrapper.find('.pull-item-cb:checked').each(function() {
        selected.push($(this).data('name'));
    });
    d.calc_selected_items = selected;
    d.get_primary_btn().text(`Move ${selected.length} to Today`);
}

// ---- ADMIN RESCUE ----
const isAdmin = computed(() => {
    const roles = frappe.boot.user.roles || [];
    return roles.includes('System Manager') || roles.includes('Administrator');
});

function openRescueDialog() {
    const d = new frappe.ui.Dialog({
        title: 'ðŸš‘ Rescue / Re-Queue Orders',
        fields: [
            {
                label: 'Source Planning Sheet',
                fieldname: 'sheet',
                fieldtype: 'Link',
                options: 'Planning sheet',
                reqd: 1,
                description: 'Select the sheet containing the lost/stuck orders.',
                onchange: () => loadRescueItems(d)
            },
            {
                label: 'Target Unit (Optional)',
                fieldname: 'target_unit',
                fieldtype: 'Select',
                options: [
                    { label: 'Keep Original Unit', value: '' },
                    ...units.map(u => ({ label: `Move to ${u}`, value: u }))
                ],
                default: '',
                description: 'If selected, all rescued orders will be assigned to this unit.'
            },
            {
                fieldtype: 'HTML',
                fieldname: 'rescue_html'
            }
        ],
        primary_action_label: 'Rescue Selected',
        primary_action: () => {
            const selected = d.calc_selected_rescue || [];
            if (selected.length === 0) {
                frappe.msgprint("Select at least one order to rescue.");
                return;
            }
            const targetUnit = d.get_value('target_unit');
            handleMoveOrders(selected, filterOrderDate.value, targetUnit, d);
        }
    });
    d.show();
}

async function loadRescueItems(d) {
    const sheet = d.get_value('sheet');
    if (!sheet) return;
    
    d.set_value('rescue_html', 'Loading...');
    
    try {
        const r = await frappe.call({
            method: "production_scheduler.api.get_items_by_sheet",
            args: { sheet_name: sheet }
        });
        
        const items = r.message || [];
        if (items.length === 0) {
            d.set_value('rescue_html', 'No items found in this sheet.');
            return;
        }
        
        // Simple List for Rescue
        let html = `
            <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ccc; margin-top:10px;">
                <table class="table table-bordered table-sm" style="margin:0;">
                    <thead>
                        <tr style="background:#f0f0f0;">
                            <th width="30"><input type="checkbox" id="select-all-rescue"></th>
                            <th>Item</th>
                            <th>Unit</th>
                            <th>Qty</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        items.forEach(item => {
            html += `
                <tr>
                    <td><input type="checkbox" class="rescue-cb" data-name="${item.name}"></td>
                    <td>${item.item_name} <br> <span class="text-muted" style="font-size:10px;">${item.name}</span></td>
                    <td>${item.unit || '-'}</td>
                    <td>${item.qty}</td>
                    <td>${item.docstatus === 0 ? 'Draft' : item.docstatus === 1 ? 'Submitted' : 'Cancelled'}</td>
                </tr>
            `;
        });
        
        html += `</tbody></table></div>`;
        d.set_value('rescue_html', html);
        
        // Bind Logic
        d.$wrapper.find('#select-all-rescue').on('change', function() {
            d.$wrapper.find('.rescue-cb').prop('checked', $(this).prop('checked'));
            updateRescueSelection(d);
        });
        
        d.$wrapper.find('.rescue-cb').on('change', () => updateRescueSelection(d));
        
        d.calc_selected_rescue = [];
        
    } catch (e) {
        d.set_value('rescue_html', 'Error loading items.');
    }
}

function updateRescueSelection(d) {
    const s = [];
    d.$wrapper.find('.rescue-cb:checked').each(function() {
        s.push($(this).data('name'));
    });
    d.calc_selected_rescue = s;
    d.get_primary_btn().text(`Rescue ${s.length} Orders`);
}
</script>

<style scoped>
/* ---- LAYOUT ---- */
.cc-container {
  padding: 16px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f1f5f9;
  min-height: 100vh;
}

.cc-filters {
  display: flex;
  gap: 14px;
  align-items: flex-end;
  margin-bottom: 18px;
  padding: 14px 18px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  flex-wrap: wrap;
}

.cc-filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cc-filter-item label {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.cc-filter-item input,
.cc-filter-item select {
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  background: #f8fafc;
}

.cc-direction-btn {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  background: #f8fafc;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.cc-direction-btn:hover {
  background: #e2e8f0;
}

.cc-clear-btn {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  background: #fff;
  cursor: pointer;
  color: #ef4444;
  font-weight: 600;
  transition: all 0.2s;
}

.cc-clear-btn:hover {
  background: #fef2f2;
  border-color: #ef4444;
}

/* ---- BOARD ---- */
.cc-board {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 20px;
}

.cc-column {
  flex: 0 0 280px;
  background: #f8fafc;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 180px);
}

.cc-col-header {
  padding: 12px 14px;
  background: #fff;
  border-top: 4px solid transparent;
  border-bottom: 1px solid #e2e8f0;
  border-radius: 12px 12px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cc-header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cc-unit-controls {
  display: flex;
  gap: 4px;
}

.cc-mini-btn {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  cursor: pointer;
  padding: 2px 6px;
  font-size: 12px;
  color: #4a5568;
  transition: all 0.2s;
  display: flex; 
  align-items: center;
  justify-content: center;
  min-width: 24px;
}

.cc-mini-btn:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
}

.cc-col-title {
  font-weight: 700;
  font-size: 14px;
  color: #1e293b;
}

.cc-col-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.cc-stat-weight {
  font-size: 13px;
  font-weight: 700;
  color: #3b82f6;
}

.cc-stat-mix {
  font-size: 10px;
  font-weight: 600;
  color: #f59e0b;
}

.cc-col-body {
  padding: 10px;
  overflow-y: auto;
  flex-grow: 1;
  min-height: 200px;
}

.cc-col-body::-webkit-scrollbar { width: 4px; }
.cc-col-body::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

.cc-col-footer {
  padding: 10px 14px;
  background: #fff;
  border-top: 1px solid #e2e8f0;
  border-radius: 0 0 12px 12px;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

/* ---- ORDER CARD ---- */
.cc-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 6px;
  cursor: grab;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  transition: all 0.15s;
}

.cc-card:hover {
  box-shadow: 0 3px 10px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}

.cc-card:active { cursor: grabbing; }

.cc-card-locked {
  opacity: 0.8;
  cursor: not-allowed !important;
  background-color: #f9fafb !important;
  border: 1px dashed #d1d5db !important;
}

.cc-lock-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  background: #fefce8;
  border: 1px solid #fde047;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  z-index: 10;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

.cc-card-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.cc-color-swatch {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 2px solid #e2e8f0;
  flex-shrink: 0;
}

.cc-card-info {
  min-width: 0;
}

.cc-card-color-name {
  font-weight: 700;
  font-size: 12px;
  color: #1e293b;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.cc-card-customer {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cc-card-details {
  font-size: 10px;
  color: #94a3b8;
}

.cc-card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
}

.cc-card-qty {
  font-weight: 700;
  font-size: 13px;
  color: #1e293b;
}

.cc-card-qty-kg {
  font-size: 10px;
  color: #94a3b8;
}

/* ---- MIX ROLL MARKER ---- */
.cc-mix-marker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
  padding: 0 4px;
}

.cc-mix-line {
  flex: 1;
  height: 2px;
  background: #fbbf24;
}

.cc-mix-label {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 4px 10px;
  border-radius: 12px;
  white-space: nowrap;
  border: 1px solid rgba(0,0,0,0.1);
}

.cc-mix-label.white-mix {
  background: #fef3c7;
  color: #92400e;
}

.cc-mix-label.black-mix {
  background: #374151;
  color: #f9fafb;
}

.cc-mix-label.color-mix {
  background: #dbeafe;
  color: #1e40af;
}

.cc-mix-label.beige-mix {
  background: #fde8cd;
  color: #92400e;
}

.cc-empty {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
  font-size: 13px;
  font-style: italic;
}
</style>

<style scoped>
/* ---- MATRIX VIEW ---- */
.cc-view-btn {
    background: white;
    border: 1px solid #d1d5db;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    color: #4b5563;
    cursor: pointer;
    font-weight: 500;
}
.cc-view-btn.active {
    background: #eff6ff;
    border-color: #3b82f6;
    color: #1d4ed8;
    font-weight: 600;
}

.cc-matrix-container {
    flex: 1;
    overflow: hidden;
    padding: 16px;
    display: flex;
    flex-direction: column;
}

.cc-matrix-scroll {
    flex: 1;
    overflow: auto;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: white;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.cc-matrix-table {
    width: 100%;
    border-collapse: separate; /* Required for sticky headers */
    border-spacing: 0;
    font-size: 12px;
}

.cc-matrix-table th, 
.cc-matrix-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #e5e7eb;
    border-right: 1px solid #e5e7eb;
}

.cc-matrix-table thead th {
    background: #f8fafc;
    font-weight: 700;
    color: #334155;
    position: sticky;
    top: 0;
    z-index: 20;
    border-bottom: 2px solid #e2e8f0;
}

.cc-matrix-table tbody tr:hover td {
    background: #f8fafc;
}

.matrix-sticky-col {
    position: sticky;
    left: 0;
    z-index: 10;
    background: #f8fafc;
    border-right: 2px solid #e2e8f0;
}

.cc-matrix-table thead th.matrix-sticky-col {
    z-index: 30; /* Higher than normal headers and normal sticky cols */
}

.matrix-row-header {
    font-weight: 600;
    color: #1e293b;
    min-width: 150px;
}

.matrix-highlight {
    background-color: #dcfce7 !important; /* Green-100 */
    color: #166534;
    font-weight: 700;
}

.matrix-total-col {
    background: #f1f5f9;
    font-weight: 700;
}

/* Drag & Drop Visuals */
.cc-ghost {
    opacity: 0.5;
    background: #e2e8f0;
    border: 2px dashed #94a3b8;
}

.draggable-handle {
    cursor: grab;
}
.draggable-handle:active {
    cursor: grabbing;
}
</style>
