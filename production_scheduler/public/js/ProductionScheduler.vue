<template>
  <div class="kanban-board-container">
    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="filter-group">
        <label>Date</label>
        <input type="date" v-model="filterDate" class="filter-input" />
      </div>
      <div class="filter-group">
        <label>Party Code</label>
        <input
          type="text"
          v-model="filterPartyCode"
          placeholder="Search party..."
          class="filter-input"
        />
      </div>
      <div class="filter-group">
        <label>Unit</label>
        <select v-model="filterUnit" class="filter-input">
          <option value="">All Units</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Status</label>
        <select v-model="filterStatus" class="filter-input">
          <option value="">All</option>
          <option value="Draft">Draft</option>
          <option value="Finalized">Finalized</option>
        </select>
      </div>
      <button class="btn-clear" @click="clearFilters">Clear Filters</button>
    </div>

    <!-- Kanban Board -->
    <div class="kanban-board">
      <div
        v-for="unit in visibleUnits"
        :key="unit"
        class="kanban-column"
      >
        <div
          class="kanban-column-header"
          :style="{ borderTopColor: getHeaderColor(unit) }"
        >
          <div class="header-title">{{ unit }}</div>
          <div class="header-stats" :style="{ color: getHeaderColor(unit) }">
            {{ getUnitTotal(unit).toFixed(2) }}T / {{ limits[unit] }}T
          </div>
        </div>
        <div class="kanban-column-body" :data-unit="unit" ref="columnRefs">
          <div
            v-for="card in groupedCards[unit]"
            :key="card.name"
            class="kanban-card"
            :data-name="card.name"
            @click="openForm(card.name)"
          >
            <!-- Card Header: Customer + Status -->
            <div class="card-header-row">
              <span class="card-customer">{{ card.customer }}</span>
              <span
                class="card-status"
                :class="(card.planning_status || '').toLowerCase()"
              >
                {{ card.planning_status }}
              </span>
            </div>

            <!-- Party Code -->
            <div class="card-party">{{ card.party_code }}</div>

            <!-- Item Details Table -->
            <div class="card-items" v-if="card.items && card.items.length">
              <div
                v-for="(item, idx) in card.items"
                :key="idx"
                class="card-item-row"
              >
                <span class="item-quality">{{ item.quality }}</span>
                <span class="item-color">{{ item.color }}</span>
                <span class="item-gsm">{{ item.gsm }} GSM</span>
                <span class="item-qty">{{ item.qty }} Kg</span>
              </div>
            </div>

            <!-- Card Footer: Total Weight + Date -->
            <div class="card-footer-row">
              <span class="card-weight">
                {{ (card.total_weight / 1000).toFixed(3) }} T
              </span>
              <span class="card-date">{{ card.dod }}</span>
            </div>
          </div>
          <div v-if="!groupedCards[unit] || groupedCards[unit].length === 0" class="empty-column">
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
const columnRefs = ref(null);

// Filters
const filterDate = ref("");
const filterPartyCode = ref("");
const filterUnit = ref("");
const filterStatus = ref("");

const filteredCards = computed(() => {
  let result = cards.value;

  if (filterDate.value) {
    result = result.filter((c) => c.dod === filterDate.value);
  }

  if (filterPartyCode.value) {
    const search = filterPartyCode.value.toLowerCase();
    result = result.filter(
      (c) =>
        (c.party_code || "").toLowerCase().includes(search) ||
        (c.customer || "").toLowerCase().includes(search)
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
  const grouped = {};
  units.forEach((u) => (grouped[u] = []));
  filteredCards.value.forEach((c) => {
    if (grouped[c.unit]) grouped[c.unit].push(c);
  });
  return grouped;
});

const getUnitTotal = (unit) => {
  const totalKg = filteredCards.value
    .filter((c) => c.unit === unit)
    .reduce((sum, c) => sum + (c.total_weight || 0), 0);
  return totalKg / 1000;
};

const getHeaderColor = (unit) => {
  const total = getUnitTotal(unit);
  if (total > limits[unit]) return "#e24c4c";
  if (total > softLimits[unit]) return "#e8a317";
  return "#28a745";
};

const openForm = (name) => {
  frappe.set_route("Form", "Planning sheet", name);
};

const clearFilters = () => {
  filterDate.value = "";
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
    callback: (r) => {
      if (r.message) {
        cards.value = r.message;
      }
    },
  });
};

const initSortable = () => {
  if (typeof Sortable === "undefined") return;
  const columns = document.querySelectorAll(".kanban-column-body");
  columns.forEach((el) => {
    if (el._sortable) {
      el._sortable.destroy();
    }
    el._sortable = new Sortable(el, {
      group: "kanban",
      animation: 150,
      onEnd: (evt) => {
        const newUnit = evt.to.dataset.unit;
        const docName = evt.item.dataset.name;
        const oldUnit = evt.from.dataset.unit;
        if (newUnit === oldUnit) return;

        const card = cards.value.find((c) => c.name === docName);
        const cardDate = card ? card.dod : frappe.datetime.get_today();

        frappe.call({
          method: "production_scheduler.api.update_schedule",
          args: {
            doc_name: docName,
            unit: newUnit,
            date: cardDate,
          },
          error: () => fetchData(),
          callback: (r) => {
            if (r.exc) {
              fetchData();
            } else {
              if (card) card.unit = newUnit;
              frappe.show_alert({
                message: "Moved to " + newUnit,
                indicator: "green",
              });
            }
          },
        });
      },
    });
  });
};

watch([filteredCards, visibleUnits], () => {
  nextTick(() => initSortable());
});

onMounted(() => {
  fetchData();
  nextTick(() => initSortable());
  frappe.realtime.on("doc_update", (data) => {
    if (data.doctype === "Planning sheet") {
      fetchData();
    }
  });
});
</script>
