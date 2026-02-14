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
            <div class="cc-unit-controls">
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
          <div class="cc-col-stats">
            <span class="cc-stat-weight">{{ getUnitTotal(unit).toFixed(2) }}T</span>
            <span class="cc-stat-mix" v-if="getMixRollCount(unit) > 0">
              ⚠️ {{ getMixRollCount(unit) }} mix{{ getMixRollCount(unit) > 1 ? 'es' : '' }}
              ({{ getMixRollTotalWeight(unit) }} Kg)
            </span>
          </div>
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
import { ref, computed, onMounted, nextTick, watch } from "vue";

// Color groups for keyword-based matching
// Check MOST SPECIFIC (multi-word) first, then SINGLE-WORD catch-all groups
const COLOR_GROUPS = [
  // Multi-word specific matches (checked first)
  { keywords: ["WHITE MIX"], priority: 97, hex: "#f0f0f0" },
  { keywords: ["BLACK MIX"], priority: 98, hex: "#404040" },
  { keywords: ["COLOR MIX"], priority: 99, hex: "#c0c0c0" },
  { keywords: ["BEIGE MIX"], priority: 100, hex: "#e0d5c0" },
  { keywords: ["LEMON YELLOW"], priority: 3, hex: "#FFF44F" },
  { keywords: ["GOLDEN YELLOW"], priority: 4, hex: "#FFD700" },
  { keywords: ["SKY BLUE"], priority: 8, hex: "#87CEEB" },
  { keywords: ["LIGHT BLUE"], priority: 9, hex: "#ADD8E6" },
  { keywords: ["ROYAL BLUE"], priority: 10, hex: "#4169E1" },
  { keywords: ["PEACOCK BLUE"], priority: 11, hex: "#005F69" },
  { keywords: ["MEDICAL BLUE"], priority: 12, hex: "#0077B6" },
  { keywords: ["NAVY BLUE"], priority: 13, hex: "#000080" },
  { keywords: ["MEDICAL GREEN"], priority: 16, hex: "#00A86B" },
  { keywords: ["PARROT GREEN"], priority: 17, hex: "#7CFC00" },
  { keywords: ["RELIANCE GREEN"], priority: 18, hex: "#3CB371" },
  { keywords: ["PEACOCK GREEN"], priority: 19, hex: "#00827F" },
  { keywords: ["AQUA GREEN"], priority: 20, hex: "#00FFBF" },
  { keywords: ["APPLE GREEN"], priority: 21, hex: "#8DB600" },
  { keywords: ["MINT GREEN"], priority: 22, hex: "#98FF98" },
  { keywords: ["SEA GREEN"], priority: 23, hex: "#2E8B57" },
  { keywords: ["GRASS GREEN"], priority: 24, hex: "#7CFC00" },
  { keywords: ["BOTTLE GREEN"], priority: 25, hex: "#006A4E" },
  { keywords: ["POTHYS GREEN"], priority: 26, hex: "#2E5E4E" },
  { keywords: ["DARK GREEN"], priority: 27, hex: "#006400" },
  { keywords: ["OLIVE GREEN"], priority: 28, hex: "#808000" },
  { keywords: ["ARMY GREEN"], priority: 29, hex: "#4B5320" },
  { keywords: ["LIGHT BEIGE"], priority: 34, hex: "#F5DEB3" },
  { keywords: ["DARK BEIGE"], priority: 35, hex: "#D2B48C" },
  // Single-word catch-all groups (checked last)
  { keywords: ["WHITE"], priority: 1, hex: "#FFFFFF" },
  { keywords: ["IVORY"], priority: 2, hex: "#FFFFF0" },
  { keywords: ["YELLOW"], priority: 4, hex: "#FFD700" },
  { keywords: ["ORANGE"], priority: 5, hex: "#FF8C00" },
  { keywords: ["PINK"], priority: 6, hex: "#FF69B4" },
  { keywords: ["RED", "CRIMSON", "SCARLET"], priority: 7, hex: "#DC143C" },
  { keywords: ["VIOLET"], priority: 14, hex: "#8B00FF" },
  { keywords: ["PURPLE"], priority: 15, hex: "#800080" },
  { keywords: ["GREEN"], priority: 20, hex: "#00A86B" },
  { keywords: ["BLUE"], priority: 10, hex: "#4169E1" },
  { keywords: ["SILVER"], priority: 30, hex: "#C0C0C0" },
  { keywords: ["GREY", "GRAY"], priority: 31, hex: "#808080" },
  { keywords: ["MAROON"], priority: 32, hex: "#800000" },
  { keywords: ["BROWN"], priority: 33, hex: "#8B4513" },
  { keywords: ["BEIGE"], priority: 34, hex: "#F5DEB3" },
  { keywords: ["BLACK"], priority: 36, hex: "#1a1a1a" },
];

const GAP_THRESHOLD = 2; // any color group change triggers mix roll

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

// Auto-sort: Quality (per unit) → Color (manual) → GSM (manual)
function sortItems(unit, items) {
  items.sort((a, b) => {
    // Primary: Quality (per-unit priority, lower number first)
    let cmp = getQualityPriority(unit, a.quality) - getQualityPriority(unit, b.quality);
    
    if (cmp === 0) {
      const config = getUnitSortConfig(unit);
      
      if (config.priority === 'color') {
        // Option A: Color -> GSM
        const c = getColorPriority(a.color) - getColorPriority(b.color);
        cmp = config.color === 'asc' ? c : -c;
        
        if (cmp === 0) {
          const g = parseFloat(a.gsm || 0) - parseFloat(b.gsm || 0);
          cmp = config.gsm === 'asc' ? g : -g;
        }
      } else {
        // Option B: GSM -> Color
        const g = parseFloat(a.gsm || 0) - parseFloat(b.gsm || 0);
        cmp = config.gsm === 'asc' ? g : -g;
        
        if (cmp === 0) {
          const c = getColorPriority(a.color) - getColorPriority(b.color);
          cmp = config.color === 'asc' ? c : -c;
        }
      }
    }
    
    return cmp;
  });
  return items;
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
  config.color = config.color === 'asc' ? 'desc' : 'asc';
}

function toggleUnitGsm(unit) {
  const config = getUnitSortConfig(unit);
  config.gsm = config.gsm === 'asc' ? 'desc' : 'asc';
}

function toggleUnitPriority(unit) {
  const config = getUnitSortConfig(unit);
  config.priority = config.priority === 'color' ? 'gsm' : 'color';
}

// Group data by unit, sort, and insert mix markers
function getUnitEntries(unit) {
  const unitItems = filteredData.value.filter((d) => d.unit === unit);
  sortItems(unit, unitItems);

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
           const items = prevByUnit[unit];
           const config = getUnitSortConfig(unit);

           if (items && items.length > 0) {
              const lastItem = items[items.length - 1]; // sorted by creation
              
              // Color Logic
              const lastPri = getColorPriority(lastItem.color);
              if (lastPri > 20) {
                 config.color = 'desc'; // Ended Dark -> Start Dark->Light
              } else {
                 config.color = 'asc';
              }
              
              // GSM Logic
              const lastGsm = parseFloat(lastItem.gsm || 0);
              if (lastGsm > 50) {
                 config.gsm = 'desc'; // Ended High -> Start High->Low
              } else {
                 config.gsm = 'asc';
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
watch(filterOrderDate, () => {
  analyzePreviousFlow();
});

// Watch date to re-analyze flow
watch(filterOrderDate, () => {
  analyzePreviousFlow();
});

// ---- AUTO ALLOCATION (BIN PACKING) ----
const UNIT_CAPACITIES = {
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

    // Sort Units: Preference for Larger Capacity to facilitate grouping
    compatibleUnits.sort((a, b) => UNIT_CAPACITIES[b] - UNIT_CAPACITIES[a]);

    // Bin Packing Heuristic
    const items = [...groupItems];
    while (items.length > 0) {
      let bestUnit = null;
      let bestSubset = null;
      let bestEfficiency = -1;

      for (const u of compatibleUnits) {
        const cap = UNIT_CAPACITIES[u];
        const currentSubset = [];
        let currentW = 0;
        
        for (const item of items) {
          if (currentW + (item.width || 0) <= cap) {
            currentSubset.push(item);
            currentW += (item.width || 0);
          }
        }
        
        if (currentW > 0) {
            const efficiency = currentW / cap;
            // Prioritize higher efficiency
            if (efficiency > bestEfficiency) {
                bestEfficiency = efficiency;
                bestUnit = u;
                bestSubset = currentSubset;
            } else if (efficiency === bestEfficiency) {
                // Tie breaker: Prefer smaller unit for same efficiency? (Save big units)
                // Or Prefer larger unit?
                // User Example: 124" in 126" (98%) vs 63" in 63" (100%).
                // User picked 126". Why?
                // Maybe because 124 is MORE TOTAL WIDTH than 63?
                // Maximize Throughput?
                // Let's maximize TOTAL WIDTH used in this batch.
                // 124 > 63. So pick U3.
                if (currentW > (bestSubset ? bestSubset.reduce((s,i)=>s+(i.width||0),0) : 0)) {
                    bestUnit = u;
                    bestSubset = currentSubset;
                }
            }
        }
      }

      if (bestUnit && bestSubset) {
        bestSubset.forEach(item => {
           updates.push({ name: item.itemName, unit: bestUnit });
           const idx = items.indexOf(item);
           if (idx > -1) items.splice(idx, 1);
        });
      } else {
        // No fit? Assign to largest available?
        const item = items.shift();
        updates.push({ name: item.itemName, unit: compatibleUnits[0] || "Unit 2" });
      }
    }
  }

  // 3. Apply updates
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
              // 1. Optimistic update (find item in rawData and update unit)
              const item = rawData.value.find(d => d.itemName === itemName);
              if (item) {
                item.unit = newUnit;
                // Re-sort happens automatically via computed properties
              }
              
              // 2. API call to persist change
              await frappe.call({
                method: "production_scheduler.api.update_item_unit",
                args: { item_name: itemName, unit: newUnit }
              });
              
              frappe.show_alert({ message: `Moved to ${newUnit}`, indicator: "green" });
            } catch (e) {
              console.error(e);
              frappe.msgprint("Error updating unit");
              // Revert on error
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

onMounted(() => {
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
