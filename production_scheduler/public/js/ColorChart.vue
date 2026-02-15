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
      <button class="cc-clear-btn" @click="clearFilters">✕ Clear</button>
      <button class="cc-clear-btn" style="color: #2563eb; border-color: #2563eb; margin-left: 8px;" @click="autoAllocate" title="Auto-assign orders based on Width & Quality">
        🪄 Auto Alloc
      </button>
    </div>

    <!-- Color Chart Board -->
    <div class="cc-board">
      <div
        v-for="unit in visibleUnits"
        :key="unit"
        class="cc-column"
      >
        <div class="cc-col-header" :style="{ borderTopColor: headerColors[unit] }">
          <div class="cc-header-top">
            <span class="cc-col-title">{{ unit }}</span>
            <!-- Sort Controls -->
            <div class="cc-unit-controls">
              <span style="font-size:10px; color:#64748b; margin-right:4px;">{{ getSortLabel(unit) }}</span>
              <button class="cc-mini-btn" @click="toggleUnitColor(unit)" :title="getUnitSortConfig(unit).color === 'asc' ? 'Light->Dark' : 'Dark->Light'">
                {{ getUnitSortConfig(unit).color === 'asc' ? '☀️' : '🌙' }}
              </button>
              <button class="cc-mini-btn" @click="toggleUnitGsm(unit)" :title="getUnitSortConfig(unit).gsm === 'desc' ? 'High->Low' : 'Low->High'">
                {{ getUnitSortConfig(unit).gsm === 'desc' ? '⬇️' : '⬆️' }}
              </button>
              <button class="cc-mini-btn" @click="toggleUnitPriority(unit)" :title="getUnitSortConfig(unit).priority === 'color' ? 'Color Priority' : 'GSM Priority'">
                {{ getUnitSortConfig(unit).priority === 'color' ? '🎨' : '📏' }}
              </button>
            </div>
          </div>
            <span class="cc-stat-weight" :class="getUnitCapacityStatus(unit).class">
              {{ getUnitTotal(unit).toFixed(2) }}T
            </span>
            <div v-if="getUnitCapacityStatus(unit).warning" class="text-xs text-red-600 font-bold">
              {{ getUnitCapacityStatus(unit).warning }}
            </div>
            <span class="cc-stat-mix" v-if="getMixRollCount(unit) > 0">
              ⚠️ {{ getMixRollCount(unit) }} mix{{ getMixRollCount(unit) > 1 ? 'es' : '' }}
              ({{ getMixRollTotalWeight(unit) }} Kg)
            </span>
          </div>

        <div class="cc-col-body" :data-unit="unit" ref="columnRefs">
          <template v-for="(entry, idx) in getUnitEntries(unit)" :key="entry.uniqueKey">
            <!-- Mix Roll Marker -->
            <div v-if="entry.type === 'mix'" class="cc-mix-marker">
              <div class="cc-mix-line"></div>
              <span class="cc-mix-label" :class="entry.mixType.toLowerCase().replace(' ', '-')">
                {{ entry.mixType }} — ~{{ entry.qty }} Kg
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
                  <div class="cc-card-customer">{{ entry.customer }} — {{ entry.partyCode }}</div>
                  <div class="cc-card-details">
                    {{ entry.quality }} · {{ entry.gsm }} GSM
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch, reactive } from "vue";

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

  // 9. BROWNS & BEIGES (90-94) -> Beige is light, wait.
  // Beige is usually light (like Ivory). Should be near 15?
  // But user had Beige near Brown (34).
  // "Light Beige" (34).
  // If Beige is "Sand", it's light.
  // I'll move Beige to 15 (After Ivory).
  { keywords: ["BEIGE", "LIGHT BEIGE", "CREAM"], priority: 15, hex: "#F5F5DC" },
  { keywords: ["DARK BEIGE", "KHAKI", "SAND"], priority: 90, hex: "#C2B280" }, // Darker beige
  { keywords: ["BROWN", "CHOCOLATE", "COFFEE"], priority: 91, hex: "#A52A2A" },
  
  // 10. GREYS & SILVER (95-97)
  { keywords: ["SILVER", "LIGHT GREY"], priority: 95, hex: "#C0C0C0" },
  { keywords: ["GREY", "GRAY", "DARK GREY"], priority: 96, hex: "#808080" },
  
  // 11. BLACK (98)
  { keywords: ["BLACK"], priority: 98, hex: "#000000" },
];

const GAP_THRESHOLD = 0; // any color priority difference triggers mix roll

const units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4"];
const headerColors = { "Unit 1": "#3b82f6", "Unit 2": "#10b981", "Unit 3": "#f59e0b", "Unit 4": "#8b5cf6" };

const filterOrderDate = ref(frappe.datetime.get_today());
const filterPartyCode = ref("");
const filterUnit = ref("");
const filterStatus = ref("");
// Per-unit sort configuration
const unitSortConfig = reactive({});
const rawData = ref([]);
const columnRefs = ref(null);

const visibleUnits = computed(() =>
  filterUnit.value ? units.filter((u) => u === filterUnit.value) : units
);

// Filter data by party code and status
const filteredData = computed(() => {
  let data = rawData.value;
  
  // Exclude Specific WHITE variants as per user request
  // "BRIGHT WHITE", "SUNSHINE WHITE", "MILKY WHITE", "SUPER WHITE", "BLEACH WHITE 1.0", "BLEACH WHITE 2.0"
  // And "WHITE" generally? "DONT BRING THIS COLOR IN COLOR CHART APART FROM THIS U CAN BRING ALL COLOR IVORY"
  // So keep Ivory. Remove "White" and variants.
  const EXCLUDED_WHITES = [
      "WHITE", "BRIGHT WHITE", "SUNSHINE WHITE", "MILKY WHITE", 
      "SUPER WHITE", "BLEACH WHITE", "BLEACH WHITE 1.0", "BLEACH WHITE 2.0"
  ];

  data = data.filter(d => {
      const colorUpper = (d.color || "").toUpperCase();
      // Check if color matches any excluded keyword
      // User says "APART FROM THIS U CAN BRING ALL COLOR IVORY"
      // So if color is IVORY, Keep.
      if (colorUpper.includes("IVORY") || colorUpper.includes("CREAM") || colorUpper.includes("OFF WHITE")) return true;
      
      // If color contains excluded keyword, remove
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
  "Unit 1": {
    "SUPER PLATINUM": 1,
    "PLATINUM": 2,
    "PREMIUM": 3,
    "GOLD": 4,
    "SUPER CLASSIC": 5,
  },
  "Unit 2": {
    "GOLD": 1,
    "SILVER": 2,
    "BRONZE": 3,
    "CLASSIC": 4,
    "ECO SPECIAL": 5,
    "ECO SPL": 6,
  },
  "Unit 3": {
    "SUPER PLATINUM": 1,
    "PLATINUM": 2,
    "PREMIUM": 3,
    "GOLD": 4,
    "SILVER": 5,
    "BRONZE": 6,
  },
  "Unit 4": {
    "PREMIUM": 1,
    "GOLD": 2,
    "SILVER": 3,
    "BRONZE": 4,
  },
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
    const p = config.priority === 'color' ? 'Color' : (config.priority === 'gsm' ? 'GSM' : 'Quality');
    const d = config.priority === 'color' ? config.color : (config.priority === 'gsm' ? config.gsm : 'ASC');
    return `${p} (${d.toUpperCase()})`; 
}

// Auto-sort: Dynamically based on config.priority
function sortItems(unit, items) {
  const config = getUnitSortConfig(unit);
  const pri = config.priority || 'quality'; 

  // Create a Shallow Copy to ensure Vue detects change (New Array Reference)
  return [...items].sort((a, b) => {
    let cmp = 0;

    // 1. Primary Sort
    if (pri === 'color') {
        cmp = compareColor(a, b, config.color);
    } else if (pri === 'gsm') {
        cmp = compareGsm(a, b, config.gsm);
    } else {
        // Default: Quality
        cmp = compareQuality(unit, a, b);
    }

    if (cmp !== 0) return cmp;

    // 2. Secondary/Tertiary Sort (Tie-Breakers)
    if (pri === 'color') {
        // Color -> Quality -> GSM
        cmp = compareQuality(unit, a, b);
        if (cmp === 0) cmp = compareGsm(a, b, config.gsm);
    } else if (pri === 'gsm') {
        // GSM -> Quality -> Color
        cmp = compareQuality(unit, a, b);
        if (cmp === 0) cmp = compareColor(a, b, config.color);
    } else {
        // Quality -> Color -> GSM
        cmp = compareColor(a, b, config.color);
        if (cmp === 0) cmp = compareGsm(a, b, config.gsm);
    }
    
    return cmp;
  });
}

// Helper to get/init config
function getUnitSortConfig(unit) {
  if (!unitSortConfig[unit]) {
    unitSortConfig[unit] = { color: 'asc', gsm: 'desc', priority: 'color' };
  }
  return unitSortConfig[unit];
}

function toggleUnitColor(unit) {
  const config = getUnitSortConfig(unit);
  // If not already sorting by color, switch to color and reset to asc
  if (config.priority !== 'color') {
      config.priority = 'color';
      config.color = 'asc';
  } else {
      config.color = config.color === 'asc' ? 'desc' : 'asc';
  }
  console.log(`Unit ${unit} Sort: Color ${config.color}, Priority: ${config.priority}`);
}

function toggleUnitGsm(unit) {
  const config = getUnitSortConfig(unit);
  if (config.priority !== 'gsm') {
      config.priority = 'gsm';
      config.gsm = 'asc'; // Default to ASC (Low to High)? Or DESC? Usually Low to High.
  } else {
      config.gsm = config.gsm === 'asc' ? 'desc' : 'asc';
  }
  console.log(`Unit ${unit} Sort: GSM ${config.gsm}, Priority: ${config.priority}`);
}

function toggleUnitPriority(unit) {
  const config = getUnitSortConfig(unit);
  config.priority = config.priority === 'color' ? 'gsm' : 'color';
  console.log(`Unit ${unit} Priority swapped to: ${config.priority}`);
}

// Group data by unit, sort, and insert mix markers
function getUnitEntries(unit) {
  let unitItems = filteredData.value.filter((d) => d.unit === unit);
  unitItems = sortItems(unit, unitItems); // Capture sorted result

  // Insert mix roll markers where color GROUP changes
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
      const gap = Math.abs(curPri - nextPri);
      // Only add mix marker if colors are in different groups (gap > 0)
      if (gap > GAP_THRESHOLD) {
        entries.push({
          type: "mix",
          mixType: determineMixType(unitItems[i].color, unitItems[i + 1].color),
          qty: getMixRollQty(gap),
          uniqueKey: `mix-${unitItems[i].itemName}-${unitItems[i + 1].itemName}`
        });
      }
    }
  }
  return entries;
}

function getUnitTotal(unit) {
  return filteredData.value
    .filter((d) => d.unit === unit)
    .reduce((sum, d) => sum + d.qty, 0) / 1000;
}

function getUnitProductionTotal(unit) {
  const production = filteredData.value
    .filter((d) => d.unit === unit)
    .reduce((sum, d) => sum + d.qty, 0);
  const mixWeight = getMixRollTotalWeight(unit);
  return (production + mixWeight) / 1000;
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
    rawData.value = r.message || [];
    console.log("Fetched Data:", rawData.value);
    if (rawData.value.length > 0) {
        console.log("Sample Item Width:", rawData.value[0].width, rawData.value[0]);
    }
  } catch (e) {
    frappe.msgprint("Error loading color chart data");
    console.error(e);
  }
  await nextTick();
  initSortable();
  // We analyze previous flow on mount or date change, but maybe do it separately to avoid blocking render?
  // Called safely at end of fetchData or in watcher
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

const UNIT_TONNAGE_LIMITS = {
  "Unit 1": 5.0,
  "Unit 2": 12.0,
  "Unit 3": 9.0,
  "Unit 4": 5.5
};

function getUnitCapacityStatus(unit) {
    const total = getUnitTotal(unit);
    const limit = UNIT_TONNAGE_LIMITS[unit] || 999;
    return total > limit ? { class: 'text-red-600 font-bold', warning: `⚠️ Over Limit (${limit}T)` } : {};
}

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

function initSortable() {
  if (!columnRefs.value) return;
  const els = Array.isArray(columnRefs.value) ? columnRefs.value : [columnRefs.value];
  els.forEach((el) => {
    if (!el) return;
    if (el._sortable) el._sortable.destroy();
    el._sortable = new Sortable(el, {
      group: "color-chart",
      animation: 150,
      filter: ".cc-mix-marker",
      draggable: ".cc-card",
      onEnd: async (evt) => {
        const itemEl = evt.item;
        const newUnitEl = evt.to;
        const oldUnitEl = evt.from;
        
        // If moved to a different unit
        if (newUnitEl !== oldUnitEl) {
          const itemName = itemEl.dataset.itemName;
          const newUnit = newUnitEl.dataset.unit;
          
          if (itemName && newUnit) {
            try {
              // 1. Check Capacity BEFORE moving
              const item = rawData.value.find(d => d.itemName === itemName);
              if (item) {
                  const itemTonnage = (item.qty || 0) / 1000;
                  const currentLoad = getUnitTotal(newUnit); // Helper
                  const limit = UNIT_TONNAGE_LIMITS[newUnit] || 999;
                  
                  if (currentLoad + itemTonnage > limit) {
                      const nextDate = frappe.datetime.add_days(filterOrderDate.value, 1);
                      if (confirm(`Unit ${newUnit} is Full! (${limit}T Limit)\n\nMove this order to Next Day (${nextDate})?`)) {
                          // Move to Next Day
                          await frappe.call({
                            method: "production_scheduler.api.update_items_bulk",
                            args: { items: [{ name: itemName, date: nextDate }] }
                          });
                          frappe.show_alert({ message: `Moved to ${nextDate}`, indicator: "orange" });
                          
                          // Remove from view
                          rawData.value = rawData.value.filter(d => d.itemName !== itemName);
                          // Clean up DOM (Sortable already moved it)
                          if (itemEl && itemEl.parentNode) itemEl.parentNode.removeChild(itemEl);
                          return; // Stop processing
                      } else {
                          // Standard Revert
                          fetchData();
                          return;
                      }
                  }
              }

              // 2. Optimistic update (Capacity OK)
              if (item) {
                // Remove the element moved by Sortable so Vue can re-render it cleanly from state
                if (itemEl && itemEl.parentNode) {
                    itemEl.parentNode.removeChild(itemEl);
                }
                item.unit = newUnit;
              }
              
              // 3. API call to persist change
              await frappe.call({
                method: "production_scheduler.api.update_item_unit",
                args: { item_name: itemName, unit: newUnit }
              });
              
              frappe.show_alert({ message: `Moved to ${newUnit}`, indicator: "green" });
            } catch (e) {
              console.error(e);
              frappe.msgprint("Error updating unit");
              fetchData();
            }
          }
        } else {
            // Reorder within same unit is visual only (auto-sort enforces order)
            // We could trigger a force re-render or just show alert
            frappe.show_alert({ message: "Sequence updated", indicator: "blue" });
        }
      },
    });
  });
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
  height: 1px;
  background: #fbbf24;
}

.cc-mix-label {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 3px 8px;
  border-radius: 10px;
  white-space: nowrap;
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
