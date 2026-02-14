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

// Color priority map: lower = lighter
const COLOR_PRIORITY = {
  "WHITE": 1,
  "IVORY": 2,
  "LEMON YELLOW": 3,
  "GOLDEN YELLOW": 4,
  "ORANGE": 5,
  "PINK": 6,
  "RED": 7,
  "SKY BLUE": 8,
  "LIGHT BLUE": 9,
  "ROYAL BLUE": 10,
  "PEACOCK BLUE": 11,
  "MEDICAL BLUE": 12,
  "NAVY BLUE": 13,
  "VIOLET": 14,
  "PURPLE": 15,
  "MEDICAL GREEN": 16,
  "PARROT GREEN": 17,
  "RELIANCE GREEN": 18,
  "PEACOCK GREEN": 19,
  "AQUA GREEN": 20,
  "APPLE GREEN": 21,
  "MINT GREEN": 22,
  "SEA GREEN": 23,
  "GRASS GREEN": 24,
  "BOTTLE GREEN": 25,
  "POTHYS GREEN": 26,
  "DARK GREEN": 27,
  "OLIVE GREEN": 28,
  "ARMY GREEN": 29,
  "SILVER": 30,
  "GREY": 31,
  "MAROON": 32,
  "BROWN": 33,
  "LIGHT BEIGE": 34,
  "DARK BEIGE": 35,
  "BLACK": 36,
  "WHITE MIX": 97,
  "BLACK MIX": 98,
  "COLOR MIX": 99,
  "BEIGE MIX": 100,
};

// Hex color map for swatches
const COLOR_HEX = {
  "WHITE": "#FFFFFF",
  "IVORY": "#FFFFF0",
  "LEMON YELLOW": "#FFF44F",
  "GOLDEN YELLOW": "#FFD700",
  "ORANGE": "#FF8C00",
  "PINK": "#FF69B4",
  "RED": "#DC143C",
  "SKY BLUE": "#87CEEB",
  "LIGHT BLUE": "#ADD8E6",
  "ROYAL BLUE": "#4169E1",
  "PEACOCK BLUE": "#005F69",
  "MEDICAL BLUE": "#0077B6",
  "NAVY BLUE": "#000080",
  "VIOLET": "#8B00FF",
  "PURPLE": "#800080",
  "MEDICAL GREEN": "#00A86B",
  "PARROT GREEN": "#7CFC00",
  "RELIANCE GREEN": "#3CB371",
  "PEACOCK GREEN": "#00827F",
  "AQUA GREEN": "#00FFBF",
  "APPLE GREEN": "#8DB600",
  "MINT GREEN": "#98FF98",
  "SEA GREEN": "#2E8B57",
  "GRASS GREEN": "#7CFC00",
  "BOTTLE GREEN": "#006A4E",
  "POTHYS GREEN": "#2E5E4E",
  "DARK GREEN": "#006400",
  "OLIVE GREEN": "#808000",
  "ARMY GREEN": "#4B5320",
  "SILVER": "#C0C0C0",
  "GREY": "#808080",
  "MAROON": "#800000",
  "BROWN": "#8B4513",
  "LIGHT BEIGE": "#F5DEB3",
  "DARK BEIGE": "#D2B48C",
  "BLACK": "#1a1a1a",
  "WHITE MIX": "#f0f0f0",
  "BLACK MIX": "#404040",
  "COLOR MIX": "#c0c0c0",
  "BEIGE MIX": "#e0d5c0",
};

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

function getColorPriority(color) {
  const upper = (color || "").toUpperCase().trim();
  return COLOR_PRIORITY[upper] || 50; // unknown colors get middle priority
}

function getHexColor(color) {
  const upper = (color || "").toUpperCase().trim();
  return COLOR_HEX[upper] || "#ccc";
}

function determineMixType(fromColor, toColor) {
  const from = (fromColor || "").toUpperCase().trim();
  const to = (toColor || "").toUpperCase().trim();
  if (from === "WHITE" || to === "WHITE") return "WHITE MIX";
  if (from === "BLACK" || to === "BLACK") return "BLACK MIX";
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
