<template>
  <div class="cc-container">
    <!-- Filter Bar -->
    <div class="cc-filters">
      <div class="cc-filter-item">
        <label>Date</label>
        <input type="date" v-model="filterDate" @change="fetchData" />
      </div>
      <div class="cc-filter-item">
        <label>Unit</label>
        <select v-model="filterUnit">
          <option value="">All Units</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
      </div>
      <div class="cc-filter-item">
        <label>Direction</label>
        <button class="cc-direction-btn" @click="toggleDirection">
          {{ direction === 'asc' ? '☀️ Light → Dark' : '🌙 Dark → Light' }}
        </button>
      </div>
    </div>

    <!-- Color Chart Board -->
    <div class="cc-board">
      <div
        v-for="unit in visibleUnits"
        :key="unit"
        class="cc-column"
      >
        <div class="cc-col-header" :style="{ borderTopColor: headerColors[unit] }">
          <span class="cc-col-title">{{ unit }}</span>
          <div class="cc-col-stats">
            <span class="cc-stat-weight">{{ getUnitTotal(unit).toFixed(2) }}T</span>
            <span class="cc-stat-mix" v-if="getMixRollCount(unit) > 0">
              ⚠️ {{ getMixRollCount(unit) }} mix{{ getMixRollCount(unit) > 1 ? 'es' : '' }}
            </span>
          </div>
        </div>
        <div class="cc-col-body" :data-unit="unit" ref="columnRefs">
          <template v-for="(entry, idx) in getUnitEntries(unit)" :key="idx">
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
          <span v-if="getMixRollWeight(unit) > 0">
            Mix Waste: {{ (getMixRollWeight(unit) / 1000).toFixed(3) }}T
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
// This way "BRIGHT WHITE" matches WHITE group, "CRIMSON RED" matches RED group, etc.
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
  // "BRIGHT WHITE", "SUPER WHITE", etc. all match here
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

const MIX_ROLL_QTY = 100; // kg per mix roll
const GAP_THRESHOLD = 5; // color priority gap to trigger mix roll

const units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4"];
const headerColors = { "Unit 1": "#3b82f6", "Unit 2": "#10b981", "Unit 3": "#f59e0b", "Unit 4": "#8b5cf6" };

const filterDate = ref(frappe.datetime.get_today());
const filterUnit = ref("");
const direction = ref("asc"); // asc = light to dark, desc = dark to light
const rawData = ref([]);
const columnRefs = ref(null);

const visibleUnits = computed(() =>
  filterUnit.value ? units.filter((u) => u === filterUnit.value) : units
);

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
  return group ? group.priority : 50; // unknown colors get middle priority
}

function getHexColor(color) {
  const group = findColorGroup(color);
  return group ? group.hex : "#ccc";
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

// Group raw data by unit, sort by color, insert mix markers
function getUnitEntries(unit) {
  const unitItems = rawData.value.filter((d) => d.unit === unit);

  // Sort by color priority
  unitItems.sort((a, b) => {
    const pa = getColorPriority(a.color);
    const pb = getColorPriority(b.color);
    return direction.value === "asc" ? pa - pb : pb - pa;
  });

  // Insert mix roll markers where color gap is large
  const entries = [];
  for (let i = 0; i < unitItems.length; i++) {
    entries.push({ type: "order", ...unitItems[i] });
    if (i < unitItems.length - 1) {
      const gap = Math.abs(
        getColorPriority(unitItems[i].color) - getColorPriority(unitItems[i + 1].color)
      );
      if (gap > GAP_THRESHOLD) {
        entries.push({
          type: "mix",
          mixType: determineMixType(unitItems[i].color, unitItems[i + 1].color),
          qty: MIX_ROLL_QTY,
        });
      }
    }
  }
  return entries;
}

function getUnitTotal(unit) {
  return rawData.value
    .filter((d) => d.unit === unit)
    .reduce((sum, d) => sum + d.qty, 0) / 1000;
}

function getUnitProductionTotal(unit) {
  const production = rawData.value
    .filter((d) => d.unit === unit)
    .reduce((sum, d) => sum + d.qty, 0);
  const mixWeight = getMixRollWeight(unit);
  return (production + mixWeight) / 1000;
}

function getMixRollCount(unit) {
  return getUnitEntries(unit).filter((e) => e.type === "mix").length;
}

function getMixRollWeight(unit) {
  return getMixRollCount(unit) * MIX_ROLL_QTY;
}

function toggleDirection() {
  direction.value = direction.value === "asc" ? "desc" : "asc";
}

function openForm(name) {
  frappe.set_route("Form", "Planning sheet", name);
}

async function fetchData() {
  if (!filterDate.value) return;
  try {
    const r = await frappe.call({
      method: "production_scheduler.api.get_color_chart_data",
      args: { date: filterDate.value },
    });
    rawData.value = r.message || [];
  } catch (e) {
    frappe.msgprint("Error loading color chart data");
    console.error(e);
  }
  await nextTick();
  initSortable();
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
      onEnd: (evt) => {
        // Reorder is visual only for now
        frappe.show_alert({ message: "Sequence updated", indicator: "blue" });
      },
    });
  });
}

onMounted(fetchData);
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
  justify-content: space-between;
  align-items: center;
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
