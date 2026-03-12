<template>
  <div class="sequence-approval-container">
    <div class="dashboard-header">
      <div class="header-left">
        <h2>Arrangement Approvals Dashboard</h2>
        <p class="text-muted">Review, reorder, and approve color sequences by unit and plan.</p>
      </div>
      <div class="header-right">
        <button class="btn btn-primary btn-sm" @click="fetchApprovals">
          <i class="fa fa-refresh"></i> Refresh
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-3">Fetching pending approvals...</p>
    </div>

    <div v-else-if="approvals.length === 0" class="empty-state">
      <div class="empty-icon">📂</div>
      <h3>No Pending Approvals</h3>
      <p>All arrangements are currently up to date.</p>
    </div>

    <div v-else class="approval-layout">
      <!-- Sidebar: List of pending items -->
      <div class="approval-sidebar">
        <div class="sidebar-header">
          <span class="badge badge-pill badge-info">{{ approvals.length }} Pending</span>
        </div>
        <div 
          v-for="app in approvals" 
          :key="app.name" 
          :class="['approval-card', { active: selectedApproval?.name === app.name }]"
          @click="selectApproval(app)"
        >
          <div class="card-title">
            <span class="plan-badge">{{ app.plan_name }}</span>
            <span class="unit-badge">{{ app.unit }}</span>
          </div>
          <div class="card-details">
            <span class="date">{{ formatDate(app.date) }}</span>
            <span class="requester-mini"><i class="fa fa-user mr-1"></i>{{ app.owner }}</span>
            <span :class="['status-badge', app.status.toLowerCase().replace(' ', '-')]">
              {{ app.status }}
            </span>
          </div>
        </div>
      </div>

      <!-- Main: Arrangement Editor -->
      <div class="approval-editor" v-if="selectedApproval">
        <div class="editor-header">
          <div>
            <h3>{{ selectedApproval.plan_name }} | {{ selectedApproval.unit }}</h3>
            <p class="mb-0 text-muted">
              {{ formatDate(selectedApproval.date) }} • 
              <span class="text-info font-weight-bold">
                <i class="fa fa-user-circle mr-1"></i>Requested By: {{ selectedApproval.owner }}
              </span>
            </p>
          </div>
          <div class="editor-actions">
            <button class="btn btn-primary btn-lg" @click="saveAndApprove" :disabled="isSaving">
              {{ isSaving ? 'Processing...' : '✅ Approve Arrangement' }}
            </button>
          </div>
        </div>

        <div class="editor-info">
          <i class="fa fa-info-circle mr-2"></i>
          <span>Drag items below to finalize the production sequence before approving.</span>
        </div>

        <div class="sequence-list">
          <div class="list-header">
            <div class="col-drag"></div>
            <div class="col-idx">#</div>
            <div class="col-party">Party Code</div>
            <div class="col-color">Color</div>
            <div class="col-quality">Quality</div>
            <div class="col-qty text-right">Qty (Kg)</div>
          </div>
          <div class="draggable-container" ref="dragContainer">
            <div v-for="(item, index) in items" :key="item.name" class="sequence-item" :data-id="item.name">
              <div class="col-drag draggable-handle">⠿</div>
              <div class="col-idx">{{ index + 1 }}</div>
              <div class="col-party"><b>{{ item.party_code }}</b></div>
              <div class="col-color">{{ item.color }}</div>
              <div class="col-quality">{{ item.quality }}</div>
              <div class="col-qty text-right font-weight-bold">{{ formatQty(item.qty) }}</div>
            </div>
          </div>
          <div class="list-footer" v-if="items.length > 0">
            <div class="col-total-label">Total Weight</div>
            <div class="col-total-val text-right">{{ formatQty(totalWeight) }} Kg</div>
          </div>
        </div>
      </div>

      <div class="editor-placeholder" v-else>
        <div class="placeholder-content">
          <i class="fa fa-mouse-pointer mb-3" style="font-size: 40px; color: #cbd5e1;"></i>
          <p>Select an arrangement from the sidebar to review and approve.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';

const approvals = ref([]);
const loading = ref(false);
const isSaving = ref(false);
const selectedApproval = ref(null);
const items = ref([]);
const dragContainer = ref(null);
let sortableInstance = null;

const totalWeight = computed(() => {
  return items.value.reduce((sum, item) => sum + (parseFloat(item.qty) || 0), 0);
});

async function fetchApprovals() {
  loading.value = true;
  try {
    const r = await frappe.call({
      method: "production_scheduler.api.get_pending_approvals"
    });
    approvals.value = r.message || [];
    if (approvals.value.length > 0) {
      // Keep selection if it still exists in results, otherwise pick first
      const stillPending = selectedApproval.value ? approvals.value.find(a => a.name === selectedApproval.value.name) : null;
      if (stillPending) {
        selectApproval(stillPending);
      } else {
        selectApproval(approvals.value[0]);
      }
    } else {
      selectedApproval.value = null;
    }
  } finally {
    loading.value = false;
  }
}

async function selectApproval(app) {
  selectedApproval.value = app;
  const itemNames = JSON.parse(app.sequence_data || "[]");
  
  if (itemNames.length > 0) {
    const r = await frappe.call({
      method: "production_scheduler.api.get_items_by_name",
      args: {
        names: itemNames
      }
    });
    const fetchedItems = r.message || [];
    // Sort items according to the saved sequence
    items.value = itemNames.map(name => fetchedItems.find(i => i.name === name)).filter(Boolean);
    
    // Initialize Sortable after DOM update
    nextTick(() => {
        initSortable();
    });
  } else {
    items.value = [];
  }
}

function initSortable() {
    if (sortableInstance) sortableInstance.destroy();
    
    if (dragContainer.value) {
        sortableInstance = new Sortable(dragContainer.value, {
            animation: 150,
            handle: '.draggable-handle',
            ghostClass: 'ghost-item',
            chosenClass: 'chosen-item',
            onEnd: () => {
                // Update local items array based on new DOM order
                const newOrder = Array.from(dragContainer.value.querySelectorAll('.sequence-item'))
                                     .map(el => el.dataset.id);
                const reorderedItems = newOrder.map(name => items.value.find(i => i.name === name));
                items.value = reorderedItems;
                
                // Track that sequence was changed (optional: can show "Unsaved Changes" if we want a separate save button)
                // For now, we save on Approve.
            }
        });
    }
}

async function saveAndApprove() {
  if (!selectedApproval.value) return;
  
  frappe.confirm('Are you sure you want to approve this arrangement? Any reordering will be saved.', async () => {
    isSaving.value = true;
    try {
      // 1. Save new sequence first
      const currentItemNames = items.value.map(i => i.name);
      await frappe.call({
        method: "production_scheduler.api.save_color_sequence",
        args: {
          date: selectedApproval.value.date,
          unit: selectedApproval.value.unit,
          plan_name: selectedApproval.value.plan_name,
          sequence_data: currentItemNames
        }
      });

      // 2. Approve
      await frappe.call({
        method: "production_scheduler.api.approve_sequence",
        args: {
          date: selectedApproval.value.date,
          unit: selectedApproval.value.unit,
          plan_name: selectedApproval.value.plan_name
        }
      });

      frappe.show_alert({ message: 'Arrangement Approved & Saved', indicator: 'green' });
      selectedApproval.value = null;
      await fetchApprovals();
    } catch (e) {
      console.error(e);
      frappe.msgprint("Error during approval process.");
    } finally {
      isSaving.value = false;
    }
  });
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return frappe.datetime.str_to_user(dateStr);
}

function formatQty(qty) {
  return parseFloat(qty || 0).toLocaleString();
}

onMounted(fetchApprovals);
</script>

<style scoped>
.sequence-approval-container {
  padding: 24px;
  background: #f1f5f9;
  min-height: calc(100vh - 80px);
  font-family: 'Inter', sans-serif;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.dashboard-header h2 {
  margin: 0;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.approval-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 180px);
}

.approval-sidebar {
  width: 320px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.sidebar-header {
    padding: 8px 4px 12px;
    border-bottom: 1px solid #f1f5f9;
    margin-bottom: 8px;
}

.approval-card {
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.approval-card:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  transform: translateY(-1px);
}

.approval-card.active {
  background: #eff6ff;
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.card-title {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.plan-badge {
  font-size: 10px;
  font-weight: 800;
  background: #dbeafe;
  color: #1e40af;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.unit-badge {
  font-size: 10px;
  font-weight: 800;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.card-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.requester-mini {
    color: #64748b;
    font-size: 9px;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.list-footer {
  display: flex;
  padding: 16px 0;
  border-top: 2px solid #0f172a;
  margin-top: 8px;
  font-weight: 800;
  color: #0f172a;
}

.col-total-label {
    flex: 1;
    padding-left: 80px;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.col-total-val {
    width: 120px;
    font-size: 16px;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 20px;
  font-weight: 800;
  font-size: 9px;
  text-transform: uppercase;
}

.status-badge.pending-approval { background: #fefce8; color: #854d0e; border: 1px solid #fef08a; }
.status-badge.draft { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }

.approval-editor {
  flex: 1;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.editor-header {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.editor-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.editor-info {
  padding: 10px 24px;
  background: #f0f9ff;
  color: #0369a1;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.sequence-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px;
}

.list-header {
  display: flex;
  padding: 12px 0;
  border-bottom: 2px solid #f1f5f9;
  font-size: 10px;
  font-weight: 800;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.sequence-item {
  display: flex;
  padding: 14px 0;
  border-bottom: 1px solid #f8fafc;
  align-items: center;
  font-size: 14px;
  transition: background 0.2s;
}

.sequence-item:hover {
    background: #f8fafc;
}

.col-drag { width: 40px; text-align: center; color: #cbd5e1; cursor: grab; font-size: 18px; }
.col-drag:active { cursor: grabbing; }
.col-idx { width: 40px; text-align: center; color: #94a3b8; font-weight: 700; font-size: 12px; }
.col-party { width: 120px; color: #1e40af; font-weight: 700; }
.col-color { flex: 2; color: #0f172a; }
.col-quality { flex: 2; color: #64748b; font-size: 13px; }
.col-qty { width: 100px; color: #0f172a; }

.ghost-item { opacity: 0.4; background: #eff6ff !important; border: 1px dashed #3b82f6; }
.chosen-item { background: #f8fafc; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }

.loading-state, .empty-state, .editor-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  color: #64748b;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.empty-icon { font-size: 56px; margin-bottom: 16px; opacity: 0.5; }
.text-right { text-align: right; }
</style>
