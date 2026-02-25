<template>
  <div class="cc-container">
    <!-- Filter Bar -->
    <div class="cc-filters">
      <div class="cc-filter-item">
        <label>{{ viewScope === 'daily' ? 'Order Date' : 'Select Month' }}</label>
        <div style="display:flex; gap:4px;">
            <input v-if="viewScope === 'daily'" type="date" v-model="filterOrderDate" @change="fetchData" />
            <input v-else type="month" v-model="filterMonth" @change="fetchData" />
            
            <button class="cc-mini-btn" @click="toggleViewScope" :title="viewScope === 'daily' ? 'Switch to Monthly View' : 'Switch to Daily View'">
                {{ viewScope === 'daily' ? '📅 Month' : '📆 Day' }}
            </button>
        </div>
      </div>
      <div class="cc-filter-item">
        <label>Party Code</label>
        <input
          type="text"
          v-model="filterPartyCode"
          placeholder="Search party..."
          @input="fetchData"
        />
      </div>
      <div class="cc-filter-item">
        <label>Customer</label>
        <input
          type="text"
          v-model="filterCustomer"
          placeholder="Search customer..."
          @input="fetchData"
        />
      </div>
      <div class="cc-filter-item">
        <label>Plan</label>
        <div style="display:flex; gap:4px; align-items:center;">
            <select v-model="selectedPlan" @change="fetchData">
                <option v-for="p in plans" :key="p.name" :value="p.name">{{ p.locked ? '🔒 ' : '' }}{{ p.name }}</option>
            </select>
            <button v-if="selectedPlan" class="cc-mini-btn" @click="togglePlanLock" :title="isCurrentPlanLocked ? 'Unlock Plan' : 'Lock Plan'" style="margin-right:2px; padding: 2px 4px;font-size: 14px;">
                {{ isCurrentPlanLocked ? '🔒' : '🔓' }}
            </button>
            <button class="cc-mini-btn" @click="createNewPlan" title="Create New Plan Tab" style="color:#2563eb; font-weight:bold;">
                ➕ New
            </button>
            <button v-if="selectedPlan !== 'Default'" class="cc-mini-btn" @click="deletePlan" title="Delete this Plan" style="color:#dc2626; font-weight:bold;">
                🗑️
            </button>
        </div>
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
            📋 Kanban
          </button>
          <button 
            class="cc-view-btn" 
            :class="{ active: viewMode === 'matrix' }" 
            @click="viewMode = 'matrix'"
            title="Matrix Pivot View"
          >
            📊 Matrix
          </button>
      </div>
      
      <button class="cc-clear-btn" @click="clearFilters">✕ Clear</button>
      <button class="cc-clear-btn" style="color: #6366f1; border-color: #6366f1; margin-left: 8px;" @click="showGlobalSortInfo" title="View Color Hierarchy Rules">
        🎨 Sort Info
      </button>
      <button class="cc-clear-btn" style="color: #2563eb; border-color: #2563eb; margin-left: 8px;" @click="autoAllocate" title="Auto-assign orders based on Width & Quality">
        🪄 Auto Alloc
      </button>
      <button class="cc-clear-btn" style="color: #059669; border-color: #059669; margin-left: 8px;" @click="openPullOrdersDialog" title="Pull orders from a future date">
        📥 Pull Orders
      </button>
      <button class="cc-clear-btn" style="color: #7c3aed; border-color: #7c3aed; margin-left: 8px; font-weight:600;" @click="pushToProductionBoard" title="Push visible orders to Production Board plan">
        📤 Push to Board
      </button>
      <button class="cc-clear-btn" style="color: #ca8a04; border-color: #ca8a04; margin-left: 8px; font-weight:600;" @click="openMovePlanDialog" title="Move visible orders to another Color Chart plan">
        📥 Move to Plan
      </button>
      <button v-if="isAdmin" class="cc-clear-btn" style="color: #dc2626; border-color: #dc2626; margin-left: 8px;" @click="openRescueDialog" title="Rescue lost or stuck orders">
        🚑 Rescue Orders
      </button>
    </div>

    <!-- Kanban View -->
    <div v-if="viewMode === 'kanban'" class="cc-board" :key="renderKey">
      
      <!-- DAILY VIEW -->
      <template v-if="viewScope === 'daily'">
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
                <button class="cc-mini-btn" @click="toggleUnitColor(unit)" :title="getUnitSortConfig(unit).color === 'asc' ? 'Currently: Light→Dark (click for Dark→Light)' : 'Currently: Dark→Light (click for Light→Dark)'">
                    {{ getUnitSortConfig(unit).color === 'asc' ? '☀️→🌙' : '🌙→☀️' }}
                </button>
                <button class="cc-mini-btn" @click="toggleUnitGsm(unit)" :title="getUnitSortConfig(unit).gsm === 'desc' ? 'GSM: High→Low (click to reverse)' : 'GSM: Low→High (click to reverse)'">
                    {{ getUnitSortConfig(unit).gsm === 'desc' ? '⬇️' : '⬆️' }}
                </button>
                <button class="cc-mini-btn" @click="toggleUnitPriority(unit)" :title="getUnitSortConfig(unit).priority === 'color' ? 'Priority: Color (click for GSM)' : 'Priority: GSM (click for Color)'">
                    {{ getUnitSortConfig(unit).priority === 'color' ? '🎨' : '📏' }}
                </button>
                <button class="cc-mini-btn" @click="showSortInfo(unit)" title="Show Sorting & Mixing Rules">
                    ℹ️
                </button>
                </div>
            </div>
            <div class="cc-header-stats">
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
                        <span v-if="entry.partyCode !== entry.customer" style="font-weight:400; color:#6b7280;"> · {{ entry.customer }}</span>
                    </div>
                    <div class="cc-card-details" style="display:flex; align-items:center;">
                        {{ entry.quality }} · {{ entry.gsm }} GSM
                        <span v-if="entry.has_wo" style="font-size:9px; padding:1px 4px; background:#dcfce7; color:#166534; border-radius:3px; margin-left:4px; font-weight:bold; border:1px solid #bbf7d0;" title="Work Order Created">WO</span>
                        <span v-else-if="entry.has_pp" style="font-size:9px; padding:1px 4px; background:#dbeafe; color:#1e40af; border-radius:3px; margin-left:4px; font-weight:bold; border:1px solid #bfdbfe;" title="Production Plan Created">PP</span>
                        <span v-else style="font-size:9px; padding:1px 4px; background:#fef3c7; color:#92400e; border-radius:3px; margin-left:4px; font-weight:bold; border:1px solid #fde68a;" title="Planning Sheet">PS</span>
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
      </template>

      <!-- MONTHLY VIEW -->
      <div v-else class="cc-monthly-container">
          <!-- Header Row -->
          <div class="cc-monthly-header">
              <div class="cc-monthly-corner">Week / Unit</div>
              <div v-for="unit in visibleUnits" :key="unit" class="cc-monthly-col-header" :style="{ borderTopColor: headerColors[unit] }">
                  <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                      <span>{{ unit }}</span>
                      <!-- Removed Info Button -->
                  </div>
                  <span class="text-xs text-gray-500 block font-normal">
                      {{ getUnitProductionTotal(unit).toFixed(2) }}T
                  </span>
              </div>
          </div>

          <!-- Week Rows -->
          <div v-for="week in weeks" :key="week.id" class="cc-monthly-row-group">
              
              <!-- Week Label Header (Optional, if we want to separate weeks) -->
              <!-- <div class="cc-week-header">{{ week.label }} ({{ week.dateRange }})</div> -->

              <!-- Iterate Days in Week -->
              <div v-for="day in getDaysInWeek(week)" :key="day.date" class="cc-matrix-row" style="display:flex; border-bottom:1px solid #e5e7eb;">
                  
                  <!-- Date Column (Fixed Width & Centered) -->
                  <div class="cc-matrix-date-col" style="width:120px; flex-shrink:0; padding:8px; background:#f9fafb; border-right:1px solid #e5e7eb; font-weight:bold; color:#374151; font-size:12px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
                      {{ day.label }}
                      <div class="text-[10px] text-gray-500 font-normal mt-1">{{ week.label }}</div>
                  </div>

                  <!-- Unit Columns -->
                  <div v-for="unit in visibleUnits" :key="unit" class="cc-matrix-cell" ref="monthlyCellRefs" :data-date="day.date" :data-unit="unit" :style="{ flex:1, borderRight:'1px solid #e5e7eb', padding:'4px', minHeight:'60px', display:'flex', flexDirection:'column', gap:'4px' }">
                      
                      <!-- Items for this Day/Unit -->
                      <div 
                          v-for="entry in getItemsForDay(day.date, unit)" 
                          :key="entry.uniqueKey"
                          class="cc-card cc-card-mini"
                          :data-name="entry.name"
                          :data-item-name="entry.itemName"
                          :data-color="entry.color"
                          :data-planning-sheet="entry.planningSheet"
                          :data-unit="unit"
                          :data-date="day.date"
                          @click="openForm(entry.planningSheet)"
                      >
                          <div class="cc-card-left" style="width: 100%;">
                              <div class="cc-color-swatch-mini" :style="{ backgroundColor: getHexColor(entry.color) }"></div>
                              <div class="cc-card-info" style="display:flex; flex-direction:column; justify-content:center; width: 100%;">
                                  <div class="cc-card-color-name text-xs truncate font-bold" style="line-height:1.2;">{{ entry.color }}</div>
                                  <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                                      <div style="display:flex; flex-direction:column; max-width:65%;">
                                          <div class="text-[10px] text-gray-800 truncate" style="line-height:1.1;" :title="entry.customer">
                                              <b>{{ entry.partyCode || entry.customer }}</b>
                                          </div>
                                          <div class="text-[9px] text-gray-500 truncate" style="line-height:1.1; display:flex; align-items:center; gap:3px;">
                                              <span>{{ entry.quality }}</span>
                                              <span v-if="entry.has_wo" style="font-size:8px; padding:0px 3px; background:#dcfce7; color:#166534; border-radius:2px; font-weight:bold;" title="Work Order Created">WO</span>
                                              <span v-else-if="entry.has_pp" style="font-size:8px; padding:0px 3px; background:#dbeafe; color:#1e40af; border-radius:2px; font-weight:bold;" title="Production Plan Created">PP</span>
                                              <span v-else style="font-size:8px; padding:0px 3px; background:#fef3c7; color:#92400e; border-radius:2px; font-weight:bold;" title="Planning Sheet">PS</span>
                                          </div>
                                      </div>
                                      <div class="text-[10px] font-bold text-gray-700" style="white-space:nowrap;">
                                          {{ formatWeight(entry.qty / 1000) }}
                                      </div>
                                  </div>
                              </div>
                          </div>
                      </div>
                  </div>
              </div>
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
                        <th class="matrix-total-col" rowspan="9">TOTAL</th>
                    </tr>
                    <!-- Row 2: Days (Merged by Sheet) -->
                    <tr>
                        <th class="matrix-sticky-col">DAYS</th>
                        <template v-for="(sh, si) in matrixData.sheetHeaders" :key="'days-sh-'+si">
                            <th :colspan="sh.span" class="text-center font-normal" style="border-left:1px solid #cbd5e1;">
                                {{ sh.days }}
                            </th>
                        </template>
                    </tr>
                    <!-- Row 3: Planning Sheet (Merged by Sheet, Clickable) -->
                    <tr>
                        <th class="matrix-sticky-col">PLANNING SHEET</th>
                        <template v-for="(sh, si) in matrixData.sheetHeaders" :key="'sheet-sh-'+si">
                            <th :colspan="sh.span" class="text-center font-normal" style="font-size:10px; border-left:1px solid #cbd5e1;">
                                <a href="javascript:void(0)" @click.stop="openForm(sh.code)" style="color:#2563eb; text-decoration:underline; cursor:pointer; font-weight:600;">{{ sh.code }}</a>
                            </th>
                        </template>
                    </tr>
                    <!-- Row 4: Customer (Merged by Sheet) -->
                    <tr>
                        <th class="matrix-sticky-col">CUSTOMER</th>
                        <template v-for="(sh, si) in matrixData.sheetHeaders" :key="'cust2-sh-'+si">
                            <th :colspan="sh.span" class="text-center font-normal" style="font-size:10px; border-left:1px solid #cbd5e1;">
                                {{ sh.customer }}
                            </th>
                        </template>
                    </tr>
                    <!-- Row 5: Party Code (Merged by Sheet) -->
                    <tr ref="matrixHeaderRow">
                        <th class="matrix-sticky-col">CODE</th>
                        <template v-for="(sh, si) in matrixData.sheetHeaders" :key="'code-sh-'+si">
                            <th :colspan="sh.span" class="text-center matrix-col-header" style="border-left:1px solid #cbd5e1;">
                                <div class="draggable-handle" style="cursor: grab;">{{ sh.partyCode }}</div>
                            </th>
                        </template>
                    </tr>
                    <!-- Row 5: Unit (Per Column) -->
                    <tr>
                        <th class="matrix-sticky-col">UNIT</th>
                        <th v-for="col in matrixData.columns" :key="'unit-'+col.id" class="text-center font-normal" style="font-size:10px;">
                            {{ col.unit }}
                        </th>
                    </tr>
                    <!-- Row 6: GSM -->
                    <tr>
                        <th class="matrix-sticky-col">GSM TYPE</th>
                        <th v-for="col in matrixData.columns" :key="'gsm-'+col.id" class="text-center font-normal">
                            {{ col.gsm }}
                        </th>
                    </tr>
                    <!-- Row 7: Quality -->
                    <tr>
                        <th class="matrix-sticky-col">QUALITY</th>
                        <th v-for="col in matrixData.columns" :key="'qual-'+col.id" class="text-center">
                            {{ col.quality }}
                        </th>
                    </tr>
                    <!-- Row 8: Customer (Merged by Sheet, Green Header) -->
                    <tr>
                        <th class="matrix-sticky-col" style="background:#dcfce7; color:#166534;">COLOURS</th>
                        <template v-for="(sh, si) in matrixData.sheetHeaders" :key="'cust-sh-'+si">
                            <th :colspan="sh.span" class="text-center" style="background:#dcfce7; color:#166534; font-size:10px; border-left:1px solid #cbd5e1;">
                                {{ sh.customer }}
                            </th>
                        </template>
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
                                <button v-if="row.isPushed" 
                                    style="margin-left:8px; background: #16a34a; color:white; border:none; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:700; cursor:default; box-shadow: 0 2px 4px rgba(22,163,74,0.3);"
                                    title="All orders for this color are pushed"
                                >
                                    ✅ {{ row.pushedPlanName || 'Pushed' }}
                                </button>
                                <button v-else-if="row.total >= 800" 
                                    @click.stop="openPushColorDialog(row.color)"
                                    style="margin-left:8px; background: linear-gradient(135deg, #3b82f6, #2563eb); color:white; border:none; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:700; cursor:pointer; box-shadow: 0 2px 4px rgba(37,99,235,0.3); transition: all 0.2s;"
                                    onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 4px 8px rgba(37,99,235,0.4)'"
                                    onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 2px 4px rgba(37,99,235,0.3)'"
                                >
                                    📤 Push
                                </button>
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
                        <th class="matrix-sticky-col" style="background:#ffeb3b; color:#000;">TOTAL</th>
                        <th v-for="col in matrixData.columns" :key="col.id" class="text-right" style="background:#ffeb3b; color:#000;">
                            {{ matrixData.colTotals[col.id] > 0 ? matrixData.colTotals[col.id].toFixed(0) : '' }}
                        </th>
                        <th class="matrix-total-col text-right" style="background:#ffeb3b; color:#000;">{{ matrixData.grandTotal.toFixed(0) }}</th>
                    </tr>
                    <!-- Whites Section -->
                    <tr 
                        v-for="row in matrixData.whiteRows" 
                        :key="'w-' + row.color"
                        class="matrix-row"
                    >
                        <td class="matrix-sticky-col bg-white">
                            <div class="flex items-center">
                                <span class="w-3 h-3 rounded mr-2 border border-gray-300" :style="{backgroundColor: getHexColor(row.color)}"></span>
                                {{ row.color }}
                                <button v-if="row.isPushed" 
                                    style="margin-left:8px; background: #16a34a; color:white; border:none; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:700; cursor:default; box-shadow: 0 2px 4px rgba(22,163,74,0.3);"
                                    title="White orders auto-pushed"
                                >
                                    ✅ {{ row.pushedPlanName || 'Default' }}
                                </button>
                            </div>
                        </td>
                        <td 
                            v-for="col in matrixData.columns" 
                            :key="'w-' + col.id" 
                            class="text-right bg-white"
                        >
                            {{ (row.cells[col.id] || 0) > 0 ? (row.cells[col.id]).toFixed(0) : '' }}
                        </td>
                        <td class="matrix-total-col text-right font-bold bg-gray-50">
                            {{ row.total.toFixed(0) }}
                        </td>
                    </tr>
                </tfoot>
            </table>
        </div>
    </div>
    
    <!-- MIX ROLL Manual Entry Section -->
    <div v-if="viewMode === 'matrix' && mixRolls && mixRolls.length > 0" class="mt-8 bg-white p-4 rounded-lg shadow border border-gray-200" style="margin-bottom: 30px;">
        <h3 class="text-sm font-bold mb-4 text-gray-800 flex items-center">
            <span class="mr-2">♻️</span> MIX ROLL AREA (Manual Entry)
        </h3>
        <table class="w-full text-xs text-left border-collapse border border-gray-200">
            <thead class="bg-gray-100 text-gray-700">
                <tr>
                    <th class="p-2 border">UNIT</th>
                    <th class="p-2 border">COLOR 1</th>
                    <th class="p-2 border">COLOR 2</th>
                    <th class="p-2 border">MIX NAME</th>
                    <th class="p-2 border">GSM</th>
                    <th class="p-2 border">WIDTH</th>
                    <th class="p-2 border w-32">WEIGHT (Kg)</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(mix, idx) in mixRolls" :key="idx" class="border-b hover:bg-gray-50">
                    <td class="p-2 border font-semibold text-gray-600">{{ mix.unit }}</td>
                    <td class="p-2 border font-bold" :style="{ color: getHexColor(mix.color1) !== '#FFFFFF' ? getHexColor(mix.color1) : '#000' }">{{ mix.color1 }}</td>
                    <td class="p-2 border font-bold" :style="{ color: getHexColor(mix.color2) !== '#FFFFFF' ? getHexColor(mix.color2) : '#000' }">{{ mix.color2 }}</td>
                    <td class="p-2 border">
                        <input type="text" class="w-full border p-1 rounded outline-none focus:border-blue-500 font-bold uppercase text-gray-800" v-model="mix.mixName" />
                    </td>
                    <td class="p-2 border">
                        <input type="text" class="w-full border p-1 rounded outline-none focus:border-blue-500 text-center font-semibold text-gray-600" v-model="mix.gsm" />
                    </td>
                    <td class="p-2 border">
                        <input type="number" class="w-full border p-1 rounded outline-none focus:border-blue-500 text-center" v-model="mix.width" />
                    </td>
                    <td class="p-2 border text-center">
                         <input type="number" class="w-full border p-1 rounded outline-none focus:border-blue-500 text-right font-mono" placeholder="0.0" v-model="mix.kg" />
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch, reactive } from "vue";
import Sortable from "sortablejs";

// Color groups for keyword-based matching
// Check MOST SPECIFIC (multi-word) first, then SINGLE-WORD catch-all groups
const COLOR_GROUPS = [
  // ── MIX MARKERS (always at end, priority 199) ──────────────────
  { keywords: ["WHITE MIX"],  priority: 199, hex: "#f0f0f0" },
  { keywords: ["BLACK MIX"],  priority: 199, hex: "#404040" },
  { keywords: ["COLOR MIX"],  priority: 199, hex: "#c0c0c0" },
  { keywords: ["BEIGE MIX"],  priority: 199, hex: "#e0d5c0" },
  
  // ── NO COLOR (Handling Unassigned/Empty Colors) ─────────────────
  // High priority to push to end, or 0 to push to start? 
  // User didn't specify sort order for these, let's put them at END (999) 
  // so they don't interrupt the refined flow.
  { keywords: ["NO COLOR"], priority: 999, hex: "#e5e7eb" }, // Grey-200

  // ── WHITES (priority 5 — excluded by filter anyway) ─────────────
  // IMPORTANT: multi-word phrases FIRST so "BRIGHT WHITE" matches here, not "WHITE"
  { keywords: ["BRIGHT WHITE", "SUNSHINE WHITE", "MILKY WHITE", "SUPER WHITE",
               "BLEACH WHITE", "OPTICAL WHITE"], priority: 5, hex: "#FFFFFF" },
  { keywords: ["WHITE"], priority: 5, hex: "#FFFFFF" },

  // ── 1. IVORY / CREAM / OFF WHITE (4) — User Req: Beige -> Ivory -> White 
  { keywords: ["IVORY", "OFF WHITE", "CREAM"], priority: 4, hex: "#FFFFF0" },

  // ── 2. YELLOWS (20-22): Lemon → Yellow → Golden ─────────────────
  { keywords: ["LEMON YELLOW"],          priority: 20, hex: "#FFF44F" },
  { keywords: ["GOLDEN YELLOW"],         priority: 22, hex: "#FFD700" }, // before YELLOW & GOLD
  { keywords: ["GOLD"],                  priority: 22, hex: "#FFD700" }, // before YELLOW
  { keywords: ["YELLOW"],               priority: 21, hex: "#FFFF00" },

  // ── 3. ORANGES (28-31): Light → Orange → Bright → Peach ─────────
  { keywords: ["LIGHT ORANGE"],          priority: 28, hex: "#FFD580" },
  { keywords: ["PEACH"],                 priority: 28, hex: "#FFDAB9" },
  { keywords: ["BRIGHT ORANGE"],         priority: 31, hex: "#FF8C00" }, // before ORANGE
  { keywords: ["ORANGE"],               priority: 30, hex: "#FFA500" },

  // ── 4. PINKS (39-42): Baby → Light → Pink → Dark → Hot ──────────
  { keywords: ["BABY PINK"],             priority: 39, hex: "#FFB6C1" },
  { keywords: ["LIGHT PINK"],            priority: 39, hex: "#FFB6C1" },
  { keywords: ["DARK PINK"],             priority: 42, hex: "#FF1493" }, // before PINK
  { keywords: ["HOT PINK"],              priority: 42, hex: "#FF69B4" }, // before PINK
  { keywords: ["ROSE", "PINK"],          priority: 40, hex: "#FFC0CB" },

  // ── 5. REDS (50-51) ──────────────────────────────────────────────
  { keywords: ["BRIGHT RED"],            priority: 50, hex: "#FF2400" }, // before RED
  { keywords: ["SCARLET", "CRIMSON"],    priority: 50, hex: "#DC143C" },
  { keywords: ["RED"],                   priority: 50, hex: "#FF0000" },

  // ── 6. BLUES (55-59): Sky→Light→Royal→Peacock→Medical→Navy ──────
  // IMPORTANT: multi-word specific names BEFORE generic "BLUE"
  { keywords: ["SKY BLUE"],              priority: 55, hex: "#87CEEB" },
  { keywords: ["LIGHT BLUE"],            priority: 55, hex: "#ADD8E6" },
  { keywords: ["ROYAL BLUE"],            priority: 56, hex: "#4169E1" },
  { keywords: ["PEACOCK BLUE"],          priority: 57, hex: "#005F69" },
  { keywords: ["MEDICAL BLUE"],          priority: 58, hex: "#0077B6" },
  { keywords: ["NAVY BLUE", "DARK BLUE"],priority: 59, hex: "#000080" },
  { keywords: ["BLUE"],                  priority: 56, hex: "#0000FF" }, // generic → Royal Blue level

  // ── 7. VIOLETS & PURPLES (60-61) ────────────────────────────────
  { keywords: ["LAVENDER", "LILAC"],     priority: 60, hex: "#E6E6FA" },
  { keywords: ["VIOLET"],               priority: 60, hex: "#EE82EE" },
  { keywords: ["PURPLE", "MAGENTA"],     priority: 61, hex: "#800080" },

  // ── 8. GREENS (65-79): exact user order ──────────────────────────
  // Medical → Parrot → Reliance → Peacock → Aqua → Apple → Mint
  // → Sea → Grass → Bottle → Pothys → Dark → Olive → Army
  // IMPORTANT: all specific names BEFORE generic "GREEN"
  { keywords: ["MEDICAL GREEN"],         priority: 65, hex: "#00897B" },
  { keywords: ["PARROT GREEN"],          priority: 66, hex: "#57C84D" },
  { keywords: ["LIGHT GREEN"],           priority: 66, hex: "#90EE90" }, // ≈ Parrot Green
  { keywords: ["RELIANCE GREEN"],        priority: 67, hex: "#228B22" },
  { keywords: ["PEACOCK GREEN"],         priority: 68, hex: "#00A693" },
  { keywords: ["AQUA GREEN", "AQUA"],    priority: 69, hex: "#00FFFF" },
  { keywords: ["APPLE GREEN"],           priority: 70, hex: "#32CD32" },
  { keywords: ["LIME GREEN"],            priority: 70, hex: "#32CD32" },
  { keywords: ["MINT GREEN", "MINT"],    priority: 71, hex: "#98FF98" },
  { keywords: ["SEA GREEN"],             priority: 72, hex: "#2E8B57" },
  { keywords: ["GRASS GREEN"],           priority: 73, hex: "#7CFC00" },
  { keywords: ["BOTTLE GREEN"],          priority: 74, hex: "#006A4E" },
  { keywords: ["POTHYS GREEN"],          priority: 75, hex: "#1A5C38" },
  { keywords: ["DARK GREEN"],            priority: 76, hex: "#006400" },
  { keywords: ["OLIVE GREEN", "OLIVE"],  priority: 77, hex: "#808000" },
  { keywords: ["ARMY GREEN", "ARMY"],    priority: 78, hex: "#4B5320" },
  { keywords: ["KELLY GREEN", "GREEN"],  priority: 67, hex: "#008000" }, // generic → Reliance level

  // ── 9. SILVER & GREY (80-82) ────────────────────────────────────
  { keywords: ["SILVER", "LIGHT GREY", "LIGHT GRAY"], priority: 80, hex: "#C0C0C0" },
  { keywords: ["DARK GREY", "DARK GRAY"],             priority: 82, hex: "#696969" },
  { keywords: ["GREY", "GRAY"],                       priority: 81, hex: "#808080" },

  // ── 10. MAROON & BROWN (85-86) — after greens, per user spec ────
  { keywords: ["DARK RED"],              priority: 85, hex: "#8B0000" }, // before RED match
  { keywords: ["MAROON", "BURGUNDY"],    priority: 85, hex: "#800000" },
  { keywords: ["DARK BROWN"],            priority: 86, hex: "#5C4033" },
  { keywords: ["BROWN", "CHOCOLATE", "COFFEE"], priority: 86, hex: "#A52A2A" },

  // ── 11. BLACK (92) — heaviest dark color ───────────────────────
  { keywords: ["BLACK"],                 priority: 92, hex: "#000000" },

  // ── 12. BEIGE (95-96) — mandatory AFTER BLACK ────────────────────
  // Machine MUST run BEIGE after BLACK (and other heavy dark colors)
  // to recover/transition before next cycle. BEIGE is the last step.
  { keywords: ["LIGHT BEIGE"],           priority: 95, hex: "#F5F5DC" },
  { keywords: ["DARK BEIGE"],            priority: 96, hex: "#C2B280" }, // before BEIGE
  { keywords: ["KHAKI", "SAND"],         priority: 96, hex: "#C2B280" },
  { keywords: ["BEIGE"],                 priority: 95, hex: "#F5F5DC" },
];

const GAP_THRESHOLD = 0; // any color priority difference triggers mix roll

const units = ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Mixed"];
const UNIT_TONNAGE_LIMITS = { "Unit 1": 4.4, "Unit 2": 12, "Unit 3": 9, "Unit 4": 5.5, "Mixed": 999 };
const headerColors = { "Unit 1": "#3b82f6", "Unit 2": "#10b981", "Unit 3": "#f59e0b", "Unit 4": "#8b5cf6", "Mixed": "#64748b" };

const filterOrderDate = ref(frappe.datetime.get_today());
const viewScope = ref('daily');
const filterMonth = ref(frappe.datetime.get_today().substring(0, 7));
const filterPartyCode = ref("");
const filterCustomer = ref("");
const filterUnit = ref("");
const filterStatus = ref("");
const selectedPlan = ref("Default");

const isCurrentPlanLocked = computed(() => {
    const p = plans.value.find(p => p.name === selectedPlan.value);
    return p ? p.locked : 0;
});

async function togglePlanLock() {
    if (!selectedPlan.value) return;
    const p = plans.value.find(p => p.name === selectedPlan.value);
    if (!p) return;
    
    const newLock = p.locked ? 0 : 1;
    try {
        await frappe.call({
            method: "production_scheduler.api.toggle_plan_lock",
            args: { plan_type: "color_chart", name: selectedPlan.value, locked: newLock }
        });
        p.locked = newLock;
        frappe.show_alert({ message: newLock ? `Plan '${selectedPlan.value}' Locked` : `Plan '${selectedPlan.value}' Unlocked`, indicator: 'green' });
    } catch(e) { console.error("Error toggling lock", e); }
}
const plans = ref(["Default"]);
// Per-unit sort configuration
const unitSortConfig = reactive({});
// Pre-initialize for all units
units.forEach(u => {
    unitSortConfig[u] = { mode: 'auto', color: 'asc', gsm: 'desc', priority: 'color' };
});
const viewMode = ref('matrix'); // 'kanban' | 'matrix'
const rawData = ref([]);
const columnRefs = ref(null);
const monthlyCellRefs = ref(null);
const matrixHeaderRow = ref(null); // Ref for Matrix Column sorting
const matrixBody = ref(null);      // Ref for Matrix Row sorting
const customRowOrder = ref([]);    // Store user-defined row order (List of Colors)
const renderKey = ref(0); // Force re-render for drag revert
const matrixSortableInstances = []; // Track matrix sortable instances for cleanup
let matrixInitTimer = null; // Track pending matrix sortable init timeout

// Matrix View Helpers
const matrixData = computed(() => {
    const emptyResult = { dateHeaders: [], sheetHeaders: [], columns: [], rows: [], whiteRows: [], colTotals: {}, grandTotal: 0, whiteColTotals: {}, whiteGrandTotal: 0 };
    if (viewMode.value !== 'matrix') return emptyResult;
    
    // We need Whites in the matrix view, but separated.
    // baseData = only the selected plan's items (for columns)
    const baseData = rawData.value.filter(d => {
        // ---- PLAN FILTER (columns show only selected plan) ----
        if (selectedPlan.value && selectedPlan.value !== 'Default') {
            if (d.planName !== selectedPlan.value) return false;
        } else {
            // Default plan: include items with no plan or explicit Default
            if (d.planName && d.planName !== '' && d.planName !== 'Default') return false;
        }

        // UNIT FILTER
        if (filterUnit.value && (d.unit || "Mixed") !== filterUnit.value) return false;
        
        // STATUS FILTER
        if (filterStatus.value && d.planningStatus !== filterStatus.value) return false;

        // PARTY CODE FILTER
        if (filterPartyCode.value) {
            const search = filterPartyCode.value.toLowerCase();
            const pCode = (d.partyCode || "").toLowerCase();
            if (!pCode.includes(search)) return false;
        }
        // CUSTOMER FILTER
        if (filterCustomer.value) {
            const search = filterCustomer.value.toLowerCase();
            const cust = (d.customer || "").toLowerCase();
            if (!cust.includes(search)) return false;
        }

        // Hide NO COLOR completely
        const colorUpper = (d.color || "").toUpperCase();
        if (colorUpper === "NO COLOR") return false;

        return true;
    });

    const groups = {};
    
    baseData.forEach(d => {
        const sheetCode = d.planningSheet || "Unassigned";
        const gsm = d.gsm || "-";
        const quality = d.quality || "-";
        const compositeKey = `${sheetCode}|${gsm}|${quality}`;
        
        if (!groups[compositeKey]) {
            groups[compositeKey] = {
                id: compositeKey,
                date: d.ordered_date || d.order_date || "", // Date
                days: 0,
                code: sheetCode,
                partyCode: d.partyCode || d.customer || "",
                gsm: gsm,
                quality: quality,
                customer: d.customer || d.partyCode || "",
                unit: d.unit || "Mixed",
                items: [],
                idxSum: 0 
            };
            
            // Calculate Days
            if (d.dod) {
               const d1 = new Date(d.dod);
               const today = new Date();
               const diffTime = d1 - today; 
               const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
               groups[compositeKey].days = diffDays + " DAYS";
            } else if (groups[compositeKey].date) {
               const d1 = new Date(groups[compositeKey].date);
               const today = new Date();
               const diffTime = today - d1;
               const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)); 
               groups[compositeKey].days = diffDays + " DAYS";
            }
        }
        groups[compositeKey].items.push(d);
    });

    // Sort Groups (Columns) by Date then Code
    const sortedGroups = Object.values(groups).sort((a, b) => {
        if (a.date !== b.date) return new Date(a.date) - new Date(b.date);
        return a.code.localeCompare(b.code);
    });

    // 2. Prepare Rows (Unique Colors and Whites)
    // ✅ IMPROVEMENT: Use rawData (All Plans) to seed the vertical legend
    // This ensures that when you create a new plan, the color names from the Default plan 
    // are still visible in the legend/rows.
    const allColors = new Set();
    const allWhites = new Set();
    
    rawData.value.forEach(d => {
        if (!d.color) return;
        const colorUpper = d.color.toUpperCase();
        
        // Skip NO COLOR for legend
        if (colorUpper === "NO COLOR") return;

        let isWhite = false;
        if (!colorUpper.includes("IVORY") && !colorUpper.includes("CREAM") && !colorUpper.includes("OFF WHITE")) {
            if (EXCLUDED_WHITES.some(ex => colorUpper.includes(ex))) {
                isWhite = true;
            }
        }
        
        if (isWhite) allWhites.add(d.color);
        else allColors.add(d.color);
    });
    
    let sortedColors = [];
    if (customRowOrder.value.length > 0) {
        const customSet = new Set(customRowOrder.value);
        const presentColors = Array.from(allColors);
        const ordered = customRowOrder.value.filter(c => allColors.has(c));
        const others = presentColors.filter(c => !customSet.has(c)).sort((a,b) => compareColor({color: a}, {color: b}, 'asc'));
        sortedColors = [...ordered, ...others];
    } else {
        sortedColors = Array.from(allColors).sort((a,b) => compareColor({color: a}, {color: b}, 'asc'));
    }

    const rows = sortedColors.map(color => {
        return { color: color, cells: {}, total: 0 };
    });
    
    // Sort whites
    const sortedWhites = Array.from(allWhites).sort((a,b) => compareColor({color: a}, {color: b}, 'asc'));
    const whiteRows = sortedWhites.map(color => {
        return { color: color, cells: {}, total: 0 };
    });

    // 3. Fill Cells
    const processRows = (rowArray) => {
        rowArray.forEach(row => {
            let pushedPlanNames = new Set();
            let allPushed = true;
            let hasItems = false;
            
            sortedGroups.forEach(group => {
                const matchs = group.items.filter(i => i.color === row.color);
                matchs.forEach(m => {
                    hasItems = true;
                    if (m.plannedDate) pushedPlanNames.add(m.plannedDate);
                    else allPushed = false;
                });
                
                const sumQty = matchs.reduce((sum, item) => sum + (item.qty || 0), 0);
                if (sumQty > 0) {
                    row.cells[group.id] = sumQty;
                    row.total += sumQty;
                }
            });
            
            if (hasItems && allPushed) {
                row.isPushed = true;
                row.pushedPlanName = Array.from(pushedPlanNames).join(', ') || 'Pushed';
            } else {
                row.isPushed = false;
            }
        });
    };
    
    processRows(rows);
    processRows(whiteRows);
    
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

    // Group Columns by Planning Sheet for Merged Headers (DAYS, SHEET, CODE, COLOURS)
    const sheetHeaders = [];
    let lastSheetCode = null;
    let sheetSpan = 0;
    let sheetData = null;

    sortedGroups.forEach((g, index) => {
        if (g.code !== lastSheetCode) {
            if (lastSheetCode !== null) {
                sheetHeaders.push(sheetData);
            }
            lastSheetCode = g.code;
            sheetSpan = 1;
            sheetData = { code: g.code, partyCode: g.partyCode, days: g.days, customer: g.customer, span: 1 };
        } else {
            sheetSpan++;
            sheetData.span = sheetSpan;
        }
        if (index === sortedGroups.length - 1) {
            sheetHeaders.push(sheetData);
        }
    });

    // Column Totals (Main Colors Only)
    const colTotals = {};
    sortedGroups.forEach(g => {
        colTotals[g.id] = rows.reduce((sum, r) => sum + (r.cells[g.id] || 0), 0);
    });
    const grandTotal = rows.reduce((sum, r) => sum + r.total, 0);
    
    // Column Totals (Whites Only)
    const whiteColTotals = {};
    sortedGroups.forEach(g => {
        whiteColTotals[g.id] = whiteRows.reduce((sum, r) => sum + (r.cells[g.id] || 0), 0);
    });
    const whiteGrandTotal = whiteRows.reduce((sum, r) => sum + r.total, 0);

    return {
        dateHeaders,
        sheetHeaders,
        columns: sortedGroups,
        rows,
        whiteRows,
        colTotals,
        grandTotal,
        whiteColTotals,
        whiteGrandTotal
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
  
  // Step 1: Normalize unit, exclude specific whites
  data = data.filter(d => {
      if (!d.unit) d.unit = "Mixed";

      const colorUpper = (d.color || "").toUpperCase();
      
      // Keep Ivory/Cream explicitly
      if (colorUpper.includes("IVORY") || colorUpper.includes("CREAM") || colorUpper.includes("OFF WHITE")) return true;
      
      // Remove Excluded Whites
      if (EXCLUDED_WHITES.some(ex => colorUpper.includes(ex))) return false;

      // Hide "NO COLOR" items visually (User request: "dont show here")
      // They remain in rawData so capacity calculation remains accurate.
      if (colorUpper === "NO COLOR") return false;

      return true;
  });

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
  if (filterUnit.value) {
    data = data.filter((d) => d.unit === filterUnit.value);
  }
  if (filterStatus.value) {
    data = data.filter((d) => d.planningStatus === filterStatus.value);
  }
  
  if (selectedPlan.value && selectedPlan.value !== "Default") {
      data = data.filter((d) => d.planName === selectedPlan.value);
  }

  return data;
});

// Calculate Mix Rolls Based on Current Filters
const mixRolls = computed(() => {
    let data = filteredData.value || [];
    const results = [];
    
    // Use the actual visible units
    const unitsList = visibleUnits.value;
    
    // Simple unit sort helper
    function sortUnitItems(items) {
        return items.sort((a, b) => {
            const pA = a.color ? getColorPriority(a.color) : 999;
            const pB = b.color ? getColorPriority(b.color) : 999;
            if (pA !== pB) return pA - pB;
            const gsmA = parseFloat(a.gsm) || 0;
            const gsmB = parseFloat(b.gsm) || 0;
            if (gsmA !== gsmB) return gsmB - gsmA;
            return (a.idx || 0) - (b.idx || 0);
        });
    }

    unitsList.forEach(unit => {
        let uItems = data.filter(d => (d.unit || "Mixed") === unit);
        if (uItems.length === 0) return;
        uItems = sortUnitItems(uItems);

        for (let i = 0; i < uItems.length - 1; i++) {
            const cur = uItems[i];
            const next = uItems[i+1];
            if ((cur.color || "").toUpperCase() !== (next.color || "").toUpperCase()) {
                let mixName = "RECYCLE"; // Default
                const q = (cur.quality || "").toUpperCase();
                if (q && q !== "RECYCLE") mixName = `GPKL - ${q} MIX`;
                else if (!q) mixName = "COLOURMIX";
                
                // Just as a UI feature, provide empty kg ref
                results.push(reactive({
                    unit: unit,
                    color1: (cur.color || "").toUpperCase(),
                    color2: (next.color || "").toUpperCase(),
                    mixName: mixName,
                    gsm: cur.gsm || next.gsm || "",
                    width: cur.width || next.width || "",
                    kg: ""
                }));
            }
        }
    });
    
    return results;
});

function clearFilters() {
  filterOrderDate.value = frappe.datetime.get_today();
  filterPartyCode.value = "";
  filterCustomer.value = "";
  filterUnit.value = "";
  filterStatus.value = "";
  selectedPlan.value = "Default";
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

// Pure group priority — ALWAYS uses COLOR_GROUPS only, ignores customRowOrder.
// Use this for Kanban light/dark sorting so Matrix drag order doesn't interfere.
function getGroupPriority(color) {
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
    // Use getGroupPriority (not getColorPriority) so Matrix customRowOrder
    // does NOT interfere with Kanban light/dark sorting
    const pA = getGroupPriority(a.color);
    const pB = getGroupPriority(b.color);
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
    if (config.priority === 'color') {
        return config.color === 'asc' ? 'Color (Light→Dark)' : 'Color (Dark→Light)';
    } else if (config.priority === 'gsm') {
        return config.gsm === 'desc' ? 'GSM (High→Low)' : 'GSM (Low→High)';
    }
    return 'Color Sort';
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
            warning: `⚠️ Over Limit (${(total - limit).toFixed(2)}T)!` 
        };
    }
    // Warning (Orange) if near limit (within 10%)
    if (total > limit * 0.9) {
        return { 
            class: 'text-orange-600 font-bold', 
            warning: `⚠️ Near Limit` 
        };
    }
    
    return { class: 'text-gray-600', warning: '' };
}

// ... (Mix Roll functions use getUnitEntries which uses filteredData - Correct for VISUALS) ...

async function initSortable() {
  if (!columnRefs.value && !monthlyCellRefs.value) return;

  // Cancel any pending matrix init — prevents race condition
  if (matrixInitTimer !== null) {
      clearTimeout(matrixInitTimer);
      matrixInitTimer = null;
  }
  
  // Clear old kanban instances
  if (columnRefs.value) {
    columnRefs.value.forEach(col => {
        if (col && col._sortable) { try { col._sortable.destroy(); } catch(e) {} }
    });
  }
  
  // Clear old monthly instances
  if (monthlyCellRefs.value) {
    monthlyCellRefs.value.forEach(col => {
        if (col && col._sortable) { try { col._sortable.destroy(); } catch(e) {} }
    });
  }

  // Clear old matrix instances
  while (matrixSortableInstances.length > 0) {
      try { matrixSortableInstances.pop().destroy(); } catch(e) {}
  }

  // MATRIX VIEW
  if (viewMode.value === 'matrix') {
      matrixInitTimer = setTimeout(() => {
          matrixInitTimer = null;
          if (viewMode.value !== 'matrix') return;

          const headerRowEl = matrixHeaderRow.value;
          if (headerRowEl) {
              const colSortable = new Sortable(headerRowEl, {
                 group: 'matrix-cols',
                 animation: 150,
                 handle: '.draggable-handle',
                 draggable: '.matrix-col-header',
                 ghostClass: 'cc-ghost',
                 onEnd: async (evt) => {
                      const { newIndex, item } = evt;
                      setTimeout(async () => {
                          const allCols = Array.from(headerRowEl.querySelectorAll('.matrix-col-header'));
                          let targetDate = null;
                          const leftEl = allCols[newIndex - 1];
                          if (leftEl) targetDate = leftEl.dataset.date;
                          else {
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
                                          item.style.display = 'none';
                                          fetchData();
                                      } catch(e) { console.error(e); }
                                  }
                              } else {
                                  fetchData();
                              }
                          }
                      }, 50);
                  }
              });
              matrixSortableInstances.push(colSortable);
          }

          const bodyEl = matrixBody.value;
          if (bodyEl) {
              const rowSortable = new Sortable(bodyEl, {
                  group: 'matrix-rows',
                  animation: 250,
                  handle: '.matrix-row-header',
                  draggable: '.matrix-row',
                  ghostClass: 'cc-ghost',
                  dragClass: 'cc-drag',
                  chosenClass: 'cc-chosen',
                  onEnd: (evt) => {
                      const { oldIndex, newIndex } = evt;
                      if (oldIndex === newIndex) return;
                      setTimeout(() => {
                          const rows = Array.from(bodyEl.querySelectorAll('.matrix-row'));
                          customRowOrder.value = rows.map(r => r.dataset.color);
                          frappe.call({
                              method: "production_scheduler.api.save_color_order",
                              args: { order: customRowOrder.value },
                              callback: () => frappe.show_alert("Color Order Saved", 2)
                          });
                      }, 50);
                  }
              });
              matrixSortableInstances.push(rowSortable);
          }
      }, 150);
      return; 
  }

  // MONTHLY VIEW KANBAN
  if (viewScope.value === 'monthly' && monthlyCellRefs.value) {
     monthlyCellRefs.value.forEach(cellEl => {
         if (!cellEl) return;
         const monthlySortable = new Sortable(cellEl, {
             group: "monthly-kanban",
             animation: 250,
             forceFallback: false, /* Native is smoother if optimized */
             fallbackClass: "cc-ghost",
             ghostClass: "cc-ghost",
             dragClass: "cc-drag",
             chosenClass: "cc-chosen",
             onEnd: async (evt) => {
                const { item, to, newIndex } = evt;
                const itemName = item.dataset.itemName;
                const newUnit = to.dataset.unit;
                const newDate = to.dataset.date;
                
                if (!itemName || !newUnit || !newDate) return;

                setTimeout(async () => {
                    try {
                        await frappe.call({
                            method: "production_scheduler.api.update_schedule",
                            args: {
                                item_name: itemName,
                                unit: newUnit,
                                date: newDate,
                                index: newIndex + 1,
                                force_move: 1
                            }
                        });
                        frappe.show_alert("Order moved successfully", 2);
                        fetchData();
                    } catch (e) {
                        console.error("Failed to move order", e);
                        frappe.msgprint("Failed to move order");
                        fetchData(); 
                    }
                }, 10);
             }
         });
         cellEl._sortable = monthlySortable;
     });
     return;
  }

  // DAILY VIEW KANBAN
  if (columnRefs.value) {
    columnRefs.value.forEach((colEl) => {
        if (!colEl) return;
        const kanbanSortable = new Sortable(colEl, {
        group: "kanban",
        animation: 250, // Smoother transition
        ghostClass: "cc-ghost",
        dragClass: "cc-drag",
        chosenClass: "cc-chosen",
        forceFallback: false,
        fallbackTolerance: 3, 
        onEnd: async (evt) => {
            const { item, to, from, newIndex, oldIndex } = evt;
            const itemName = item.dataset.itemName;
            const newUnit = to.dataset.unit;
            const isSameUnit = (to === from);
            if (!itemName || !newUnit) return;

            if (!isSameUnit || newIndex !== oldIndex) {
                 setTimeout(async () => {
                 try {
                    const performMove = async (force=0, split=0) => {
                        return await frappe.call({
                            method: "production_scheduler.api.update_schedule",
                            args: {
                                item_name: itemName, 
                                unit: newUnit,
                                date: filterOrderDate.value,
                                index: newIndex + 1,
                                force_move: force,
                                perform_split: split,
                                plan_name: selectedPlan.value
                            }
                        });
                    };

                    let res = await performMove();
                    
                    if (res.message && res.message.status === 'overflow') {
                         const showOverflowDialog = (overflowData, moveDate, moveUnit) => {
                             const avail = overflowData.available;
                             const limit = overflowData.limit;
                             const current = overflowData.current_load;
                             const orderWt = overflowData.order_weight;
                             const extraMsg = overflowData.message || '';
                             
                             const d = new frappe.ui.Dialog({
                                title: '⚠️ Capacity Full',
                                fields: [{
                                     fieldtype: 'HTML', fieldname: 'msg',
                                     options: `<div style="text-align:center; padding:10px;">
                                         <p class="text-lg font-bold text-red-600">Unit Capacity Exceeded!</p>
                                         ${extraMsg ? `<p style="color:#b45309; font-weight:600; margin-bottom:8px;">${extraMsg}</p>` : ''}
                                         <p>Unit Limit: <b>${limit}T</b> | Current: <b>${current.toFixed(2)}T</b></p>
                                         <p>Your Order: <b>${orderWt.toFixed(2)}T</b></p>
                                         <p class="mt-2 text-green-600 font-bold">Available Space: ${avail.toFixed(3)}T</p>
                                     </div>`
                                }],
                                primary_action_label: '🧠 Smart Move',
                                primary_action: async () => {
                                    d.hide();
                                    const res2 = await frappe.call({
                                        method: "production_scheduler.api.update_schedule",
                                        args: { item_name: itemName, unit: moveUnit, date: moveDate, index: newIndex + 1, force_move: 1, plan_name: selectedPlan.value }
                                    });
                                    if (res2.message && res2.message.status === 'success') {
                                        const dest = res2.message.moved_to;
                                        frappe.show_alert(`Placed in ${dest.unit} (${dest.date})`, 5);
                                    }
                                    fetchData();
                                },
                                secondary_action_label: 'Cancel',
                                secondary_action: () => { d.hide(); renderKey.value++; }
                             });
                             
                             // Move to Next Day button (strict — same unit, next day)
                             d.add_custom_action('📅 Next Day', async () => {
                                 d.hide();
                                 const res3 = await frappe.call({
                                     method: "production_scheduler.api.update_schedule",
                                     args: { item_name: itemName, unit: moveUnit, date: moveDate, index: 0, strict_next_day: 1 }
                                 });
                                 if (res3.message && res3.message.status === 'overflow') {
                                     // Next day also full — show dialog again for that date
                                     showOverflowDialog(res3.message, res3.message.target_date, res3.message.target_unit);
                                 } else if (res3.message && res3.message.status === 'success') {
                                     const dest = res3.message.moved_to;
                                     frappe.show_alert(`Moved to ${dest.unit} on ${dest.date}`, 5);
                                     fetchData();
                                 }
                             }, 'btn-info');
                             
                             // Split & Distribute button
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
                         };
                         
                         showOverflowDialog(res.message, filterOrderDate.value, newUnit);
                    } else {
                         // Fix 3: Re-fetch data instead of silent splice for same-unit resequence
                         if (isSameUnit && res.message && res.message.status === 'success') {
                             frappe.show_alert({ message: "Order resequenced", indicator: "green" });
                             unitSortConfig[newUnit].mode = 'manual';
                             // Re-fetch to get correct order from server
                             fetchData();
                         } else {
                             handleMoveSuccess(res, newUnit);
                         }
                    }
                 } catch (e) {
                     console.error(e);
                     frappe.msgprint("❌ Move Failed");
                     renderKey.value++;
                 }
                 }, 50);
            }
        },
        });
        colEl._sortable = kanbanSortable;
    });
  }
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
  renderKey.value++; // Force re-render so cards re-sort immediately
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
  renderKey.value++; // Force re-render so cards re-sort immediately
}

// ---- MONTHLY VIEW HELPERS ----


const weeks = computed(() => {
    try {
        if (viewScope.value !== 'monthly' || !filterMonth.value) return [];
        
        // Strict 7-Day Logic (User Request: "Accurate Date")
        // Week 1: Day 1-7
        // Week 2: Day 8-14
        // Week 3: Day 15-21
        // Week 4: Day 22-28
        // Week 5: Day 29-End
        
        let year, month;
        if (filterMonth.value.includes('-')) {
             [year, month] = filterMonth.value.split('-').map(Number);
        } else { return []; }

        const lastDayOfMonth = new Date(year, month, 0).getDate();
        const weekList = [];
        
        const ranges = [
            { start: 1, end: 7 },
            { start: 8, end: 14 },
            { start: 15, end: 21 },
            { start: 22, end: 28 },
            { start: 29, end: lastDayOfMonth }
        ];

        ranges.forEach((range, idx) => {
            if (range.start > lastDayOfMonth) return;
            
            const effectiveEnd = Math.min(range.end, lastDayOfMonth);
            
            // Format Dates YYYY-MM-DD
            const startStr = `${year}-${String(month).padStart(2, '0')}-${String(range.start).padStart(2, '0')}`;
            const endStr = `${year}-${String(month).padStart(2, '0')}-${String(effectiveEnd).padStart(2, '0')}`;
            
            const MONTH_ABBRS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            const monthAbbr = MONTH_ABBRS[month-1];
            
            weekList.push({
                id: `w-${idx+1}-${startStr}`,
                label: `Week ${idx+1}`,
                dateRange: `${range.start} ${monthAbbr} - ${effectiveEnd} ${monthAbbr}`,
                startDay: range.start,
                endDay: effectiveEnd,
                start: startStr,
                end: endStr
            });
        });
        
        return weekList;
    } catch (e) {
        console.error("Error computing weeks:", e);
        return [];
    }
});

function showGlobalSortInfo() {
    // Build Color Order List
    const colorOrder = COLOR_GROUPS
        .map(g => {
             // Use first keyword as label
             const label = g.keywords[0];
             return { label, priority: g.priority };
        })
        .sort((a,b) => a.priority - b.priority)
        .map(g => `<li style="font-size:11px; margin-bottom:2px;">${g.priority}. <b>${g.label}</b></li>`)
        .join("");

    const d = new frappe.ui.Dialog({
        title: `🎨 Global Sort & Mix Rules`,
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'info',
            options: `
                <div style="padding:10px;">
                    <div style="margin-bottom:15px; padding:8px; background:#f3f4f6; border-radius:4px;">
                        <p style="font-weight:bold; margin-bottom:4px;">Global Sorting Strategy</p>
                        <p>All views enforce <b>Light → Dark</b> and <b>Low → High GSM</b> sorting by default.</p>
                    </div>
                    
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                        <div>
                            <p style="font-weight:bold; border-bottom:1px solid #ddd; margin-bottom:5px;">Color Sequence (Light→Dark)</p>
                            <ul style="list-style:none; padding:0; height:200px; overflow-y:auto; border:1px solid #eee;">
                                ${colorOrder}
                            </ul>
                        </div>
                        <div>
                            <p style="font-weight:bold; border-bottom:1px solid #ddd; margin-bottom:5px;">Mixing Rules</p>
                            <div style="font-size:11px;">
                                <p><b>Gap Calculation:</b> Difference in Color Priority.</p>
                                <ul style="list-style:disc; padding-left:15px; margin-top:5px;">
                                    <li>Gap 0 (Same Color): <b>0 Kg</b></li>
                                    <li>Gap 1-5 (Similar): <b>10 Kg</b></li>
                                    <li>Gap > 20 (Contrast): <b>50 Kg+</b></li>
                                </ul>
                                <p style="margin-top:8px; font-style:italic; color:#666;">
                                    *High gaps create significant waste. Try to group similar colors!
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            `
        }]
    });
    d.show();
}

function showSortInfo(unit) {
    const config = getUnitSortConfig(unit);
    const isColor = config.priority === 'color';
    const direction = isColor ? config.color : config.gsm;
    
// Build Color Order List (Corrected Iteration)
    const colorOrder = COLOR_GROUPS
        .map(g => {
             // Use first keyword as label
             const label = g.keywords[0];
             return { label, priority: g.priority };
        })
        .sort((a,b) => a.priority - b.priority)
        .map(g => `<li style="font-size:11px; margin-bottom:2px;">${g.priority}. <b>${g.label}</b></li>`)
        .join("");

    const d = new frappe.ui.Dialog({
        title: `ℹ️ Sort & Mix Rules: ${unit}`,
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'info',
            options: `
                <div style="padding:10px;">
                    <div style="margin-bottom:15px; padding:8px; background:#f3f4f6; border-radius:4px;">
                        <p style="font-weight:bold; margin-bottom:4px;">Current Strategy:</p>
                        <p>Priority: <b>${isColor ? 'Color' : 'GSM'}</b></p>
                        <p>Direction: <b>${direction === 'asc' ? (isColor ? 'Light → Dark' : 'Low → High') : (isColor ? 'Dark → Light' : 'High → Low')}</b></p>
                    </div>
                    
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                        <div>
                            <p style="font-weight:bold; border-bottom:1px solid #ddd; margin-bottom:5px;">Color Sequence (Light→Dark)</p>
                            <ul style="list-style:none; padding:0; height:200px; overflow-y:auto; border:1px solid #eee;">
                                ${colorOrder}
                            </ul>
                        </div>
                        <div>
                            <p style="font-weight:bold; border-bottom:1px solid #ddd; margin-bottom:5px;">Mixing Rules</p>
                            <div style="font-size:11px;">
                                <p><b>Gap Calculation:</b> Difference in Color Priority.</p>
                                <ul style="list-style:disc; padding-left:15px; margin-top:5px;">
                                    <li>Gap 0 (Same Color): <b>0 Kg</b></li>
                                    <li>Gap 1-5 (Similar): <b>10 Kg</b></li>
                                    <li>Gap > 20 (Contrast): <b>50 Kg+</b></li>
                                </ul>
                                <p style="margin-top:8px; font-style:italic; color:#666;">
                                    *High gaps create significant waste. Try to group similar colors!
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            `
        }]
    });
    d.show();
}

function getMonthlyCellTotal(week, unit) {
    try {
        const entries = getMonthlyCellEntries(week, unit);
        const total = entries.reduce((sum, e) => sum + (parseFloat(e.qty) || 0), 0);
        return (total / 1000).toFixed(2);
    } catch (e) {
        return "0.00";
    }
}

function getMonthlyCellDays(week, unit) {
    if (!week || !week.start || !week.end) return [];
    if (!filteredData.value) return [];

    try {
        // Filter by Unit
        let items = filteredData.value.filter(d => (d.unit || "Mixed") === unit);
        
        // Filter by Date Range
        items = items.filter(d => d.orderDate >= week.start && d.orderDate <= week.end);

        // Group by Date
        const itemsByDate = {};
        items.forEach(item => {
            const d = item.orderDate;
            if (!itemsByDate[d]) itemsByDate[d] = [];
            itemsByDate[d].push(item);
        });

        // Create Day Objects (Sorted Chronologically)
        const days = Object.keys(itemsByDate).sort().map(dateStr => {
           let dayItems = itemsByDate[dateStr];
           
           // Sort Items within Day (Light -> Dark)
           // Use existing logic for priority
           const config = getUnitSortConfig(unit);
           dayItems.sort((a, b) => {
                  let diff = 0;
                  if (config.priority === 'color') {
                      diff = compareColor(a, b, 'asc');
                      if (diff === 0) diff = compareGsm(a, b, 'asc');
                  } else {
                      diff = compareGsm(a, b, 'asc');
                      if (diff === 0) diff = compareColor(a, b, 'asc');
                  }
                  if (diff === 0) diff = (a.idx || 0) - (b.idx || 0);
                  return diff;
           });

           // Format Date Label (e.g., "2026-02-18" -> "18 Feb")
           const [y, m, d] = dateStr.split('-');
           const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
           const label = `${parseInt(d)} ${monthNames[parseInt(m)-1]}`;

           return {
               date: dateStr,
               label: label,
               items: dayItems.map(d => ({
                   ...d,
                   type: 'order',
                   uniqueKey: d.itemName
               }))
           };
        });

        return days;
    } catch (e) {
        console.error("Error grouping monthly days:", e);
        return [];
    }
}

function getMonthlyCellEntries(week, unit) {
    if (!week || !week.start || !week.end) return [];
    if (!filteredData.value) return [];
    
    try {
        // Filter by Unit
        let items = filteredData.value.filter(d => (d.unit || "Mixed") === unit);
        
        // Filter by Date Range
        items = items.filter(d => d.orderDate >= week.start && d.orderDate <= week.end);
        
        // --- DAILY-ASCENDING SORT [DATE -> COLOR] ---
        // 1. Group by Date (Locking Principle)
        const itemsByDate = {};
        items.forEach(item => {
            const d = item.orderDate;
            if (!itemsByDate[d]) itemsByDate[d] = [];
            itemsByDate[d].push(item);
        });
        
        // 2. Sort Dates Chronologically
        const distinctDates = Object.keys(itemsByDate).sort();
        
        // 3. Sort Items within Date (Always Light -> Dark)
        let finalSortedItems = [];
        distinctDates.forEach(date => {
             const dayItems = itemsByDate[date];
             
             // ALWAYS Sort Light -> Dark (Ascending)
             // This ensures Beige (96) is at End of Day 1
             // And White/Ivory (4/5) is at Start of Day 2
             const config = getUnitSortConfig(unit);
             
             dayItems.sort((a, b) => {
                  let diff = 0;
                  if (config.priority === 'color') {
                      diff = compareColor(a, b, 'asc'); // Force ASC
                      if (diff === 0) diff = compareGsm(a, b, 'asc');
                  } else {
                      diff = compareGsm(a, b, 'asc');
                      if (diff === 0) diff = compareColor(a, b, 'asc');
                  }
                  if (diff === 0) diff = (a.idx || 0) - (b.idx || 0);
                  return diff;
             });
             
             finalSortedItems = finalSortedItems.concat(dayItems);
        });
        
        return finalSortedItems.map(d => ({
            ...d,
            type: 'order',
            uniqueKey: d.itemName
        }));
    } catch (e) {
        console.error("Error getting monthly entries:", e);
        return [];
    }
}

// --- MATRIX LAYOUT HELPERS ---
function getDaysInWeek(week) {
    if (!filterMonth.value || !week) return [];
    
    try {
        let year, month;
        if (filterMonth.value.includes('-')) {
             [year, month] = filterMonth.value.split('-').map(Number);
        } else { return []; }

        const days = [];
        
        for (let d = week.startDay; d <= week.endDay; d++) {
             // Create date string manually: YYYY-MM-DD
             const yyyy = year;
             const mm = String(month).padStart(2, '0');
             const dd = String(d).padStart(2, '0');
             const dateStr = `${yyyy}-${mm}-${dd}`;
             
             // Label: "22 Feb"
             const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
             const label = `${d} ${monthNames[month-1]}`;
             
             days.push({
                 date: dateStr,
                 label: label,
                 dayNum: d
             });
        }
        return days;
    } catch (e) {
        console.error("Error generating days:", e);
        return [];
    }
}

function getItemsForDay(dateStr, unit) {
    if (!filteredData.value) return [];
    
    try {
       // Filter by Unit and Exact Date
       // Handle "Mixed" unit as well
       let dayItems = filteredData.value.filter(d => 
           (d.unit || "Mixed") === unit && 
           d.orderDate === dateStr
       );
       
       // Force sorting to ALWAYS strictly be Light -> Dark 
       const config = getUnitSortConfig(unit);
       dayItems.sort((a, b) => {
              let diff = 0;
              if (config.priority === 'color') {
                  diff = compareColor(a, b, 'asc');
                  if (diff === 0) diff = compareGsm(a, b, 'asc');
              } else {
                  diff = compareGsm(a, b, 'asc');
                  if (diff === 0) diff = compareColor(a, b, 'asc');
              }
              if (diff === 0) diff = (a.idx || 0) - (b.idx || 0);
              return diff;
       });
       
       return dayItems.map(d => ({
           ...d,
           type: 'order',
           uniqueKey: d.itemName
       }));
    } catch (e) {
        console.error("Error fetching items for day:", e);
        return [];
    }
}

function toggleUnitPriority(unit) {
  const config = getUnitSortConfig(unit);
  config.mode = 'auto';
  config.priority = config.priority === 'color' ? 'gsm' : 'color';
  renderKey.value++; // Force re-render so cards re-sort immediately
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
    .reduce((sum, d) => sum + (parseFloat(d.qty) || 0), 0) / 1000;
}

function formatWeight(tonnage) {
  // Input is in Tons
  if (tonnage >= 1) {
      // If integer (e.g. 10.00), return "10 T"
      if (Number.isInteger(tonnage)) return tonnage.toFixed(0) + " T";
      // Else return with decimals, e.g. "1.23 T" or "1.20 T"
      // User said "remove 2 digit make it whole" for 10.00 -> 10T
      // Let's use clean logic:
      return parseFloat(tonnage.toFixed(3)) + " T"; 
  } else {
      // Less than 1 Ton -> Show Kg
      // 0.469 T -> 469 Kg
      return (tonnage * 1000).toFixed(0) + " Kg";
  }
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
               // Sort yesterday's items the same way they would have been displayed
               // (by their stored idx — the actual run order saved to DB)
               const sorted = [...prevItems].sort((a, b) => (a.idx || 0) - (b.idx || 0));
               const lastItem = sorted[sorted.length - 1];
               
               // DARK/LIGHT threshold:
               // Dark = priority >= 50 (Red, Maroon, Purple, Blue, Green, Grey, Brown, Black)
               // Light = priority < 50 (White, Ivory, Yellow, Orange, Pink)
               // Use getGroupPriority — NOT getColorPriority — so Matrix customRowOrder
               // does not affect this decision
               const lastPri = getGroupPriority(lastItem.color);
               
               // Rule (as stated by user):
               // Yesterday ended LIGHT (pri < 50)  → today start LIGHT → DARK ('asc')
               // Yesterday ended DARK  (pri >= 50) → today start DARK  → LIGHT ('desc')
               if (lastPri >= 50) {
                  config.color = 'desc'; // Ended Dark  → today: Dark → Light
               } else {
                  config.color = 'asc';  // Ended Light → today: Light → Dark
               }
               config.mode = 'auto';
               config.priority = 'color';
               
               console.log(`Unit ${unit}: Yesterday last color="${lastItem.color}" (pri=${lastPri}) → today sort: ${config.color}`);
               
               // GSM Logic - Smart Gap Minimization
               const lastGsm = parseFloat(lastItem.gsm || 0);
               const todayItems = filteredData.value.filter(d => d.unit === unit);
               
               if (todayItems.length > 0) {
                   const gsms = todayItems.map(d => parseFloat(d.gsm || 0));
                   const minGsm = Math.min(...gsms);
                   const maxGsm = Math.max(...gsms);
                   
                   const gapAsc = Math.abs(lastGsm - minGsm);  // Start Low
                   const gapDesc = Math.abs(lastGsm - maxGsm); // Start High
                   
                   config.gsm = gapDesc < gapAsc ? 'desc' : 'asc';
                   console.log(`Unit ${unit} GSM: Last=${lastGsm} Min=${minGsm} Max=${maxGsm} → ${config.gsm}`);
               }
            } else {
               // No data yesterday for this unit — default to Light→Dark
               config.color = 'asc';
               config.mode = 'auto';
               config.priority = 'color';
            }
         });
        
        
        frappe.show_alert({ message: "Sort updated from previous day", indicator: "blue" }, 3);
        // Only force re-render for kanban — matrix is already reactive via rawData
        if (viewMode.value !== 'matrix') {
            renderKey.value++;
        }
      }
    }
  } catch (e) {
    console.error("Error analyzing previous flow", e);
  }
}

// View Scope Logic
async function toggleViewScope() {
  if (viewScope.value === 'daily') {
      viewScope.value = 'monthly';
      if (!filterMonth.value) {
          filterMonth.value = frappe.datetime.get_today().substring(0, 7);
      }
  } else {
      viewScope.value = 'daily';
      if (!filterOrderDate.value) {
          filterOrderDate.value = frappe.datetime.get_today();
      }
  }
  await fetchData();
}

async function fetchPlans(args) {
    try {
        const planArgs = { ...args };
        if (planArgs.date && !planArgs.start_date) {
            const [year, month] = planArgs.date.split("-");
            const lastDay = new Date(year, month, 0).getDate();
            planArgs.start_date = `${year}-${month}-01`;
            planArgs.end_date = `${year}-${month}-${lastDay}`;
            delete planArgs.date;
        }
        
        const r = await frappe.call({
            method: "production_scheduler.api.get_monthly_plans",
            args: planArgs
        });
        plans.value = r.message || [{name: "Default", locked: 0}];
        // If the currently selected plan is not returned (e.g. new plan with no sheets yet),
        // keep it in the dropdown instead of silently falling back to Default.
        if (selectedPlan.value && !plans.value.find(p => p.name === selectedPlan.value)) {
            // Insert as an unlocked empty plan so user stays on it
            plans.value.push({ name: selectedPlan.value, locked: 0 });
        }
    } catch(e) { console.error("Error fetching plans", e); }
}

function createNewPlan() {
    frappe.prompt({
        label: 'New Plan Name',
        fieldname: 'plan_name',
        fieldtype: 'Data',
        reqd: 1
    }, async (values) => {
        if (!plans.value.find(p => p.name === values.plan_name)) {
            plans.value.push({name: values.plan_name, locked: 0});
            // Persist the new plan so it survives refresh
            frappe.call({
                method: "production_scheduler.api.add_persistent_plan",
                args: { plan_type: "color_chart", name: values.plan_name }
            });
        }
        
        const newPlan = values.plan_name;
        
        frappe.show_alert({ message: `Created new empty Plan '${newPlan}'`, indicator: 'green' });
        
        selectedPlan.value = newPlan;
        fetchData();
    }, 'Create New Plan Tab', 'Create');
}

function deletePlan() {
    const planName = selectedPlan.value;
    if (!planName || planName === 'Default') {
        frappe.msgprint('Cannot delete the Default plan.');
        return;
    }
    frappe.confirm(
        `Delete plan "<b>${planName}</b>"? This will permanently remove all Planning Sheets under this plan for the current ${viewScope.value === 'daily' ? 'date' : 'month'}.`,
        async () => {
            let deleteArgs = { plan_name: planName };
            if (viewScope.value === 'daily') {
                deleteArgs.date = filterOrderDate.value;
            } else {
                const [year, month] = filterMonth.value.split("-");
                const lastDay = new Date(year, month, 0).getDate();
                deleteArgs.start_date = `${year}-${month}-01`;
                deleteArgs.end_date = `${year}-${month}-${lastDay}`;
            }
            try {
                const r = await frappe.call({
                    method: "production_scheduler.api.delete_plan",
                    args: deleteArgs
                });
                const count = (r.message && r.message.deleted_count) || 0;
                frappe.show_alert({ message: `Deleted plan "${planName}" (${count} sheet${count !== 1 ? 's' : ''} removed)`, indicator: 'green' });
                // Remove from dropdown and switch to Default
                plans.value = plans.value.filter(p => p.name !== planName);
                selectedPlan.value = 'Default';
                fetchData();
            } catch (e) {
                console.error('Failed to delete plan', e);
                frappe.msgprint('Error deleting plan.');
            }
        }
    );
}

// ---- PUSH TO PRODUCTION BOARD ----
async function pushToProductionBoard() {
    const items = filteredData.value || [];
    if (items.length === 0) {
        frappe.msgprint('No orders visible to push. Apply filters first.');
        return;
    }

    // Collect item names from current view
    const allItemNames = [...new Set(items.map(d => d.itemName).filter(Boolean))];
    if (allItemNames.length === 0) {
        frappe.msgprint('No valid items to push.');
        return;
    }

    // State for the dialog
    let smartSequenceActive = false;
    let currentSequence = allItemNames.map((n, i) => {
        const d = items.find(it => it.itemName === n) || {};
        return {
            name: n,
            color: d.color || '',
            quality: d.quality || d.custom_quality || '',
            gsm: d.gsm || '',
            unit: d.unit || '',
            qty: d.qty || '',
            customer: d.customer || d.partyCode || '',
            phase: '',
            is_seed_bridge: false,
            sequence_no: i + 1,
            checked: true
        };
    });

    function getPhaseColor(phase) {
        if (phase === 'white') return '#e8f5e9';
        if (phase === 'color') return '#fff8e1';
        return '#f5f5f5';
    }

    function renderTable(seq) {
        let lastUnit = null;
        const rows = seq.map((item, i) => {
            let unitDivider = '';
            if (smartSequenceActive && item.unit !== lastUnit) {
                lastUnit = item.unit;
                unitDivider = `<tr style="background:#1565c0;color:white;font-size:11px;font-weight:bold;">
                    <td colspan="7" style="padding:4px 8px;">📦 ${item.unit || 'Mixed'}</td>
                </tr>`;
            }
            const bridge = item.is_seed_bridge ? ' 🔗' : '';
            const rowBg = smartSequenceActive ? getPhaseColor(item.phase) : '#fff';
            const checked = item.checked !== false;
            return `${unitDivider}<tr style="background:${rowBg};border-bottom:1px solid #eee;">
                <td style="padding:4px 6px;text-align:center;">
                    <input type="checkbox" data-idx="${i}" ${checked ? 'checked' : ''} style="cursor:pointer;">
                </td>
                <td style="padding:4px 6px;font-weight:bold;color:#555;font-size:12px;">${item.sequence_no}${bridge}</td>
                <td style="padding:4px 6px;font-size:12px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${item.color}">${item.color || '—'}</td>
                <td style="padding:4px 6px;font-size:12px;">${item.quality || '—'}</td>
                <td style="padding:4px 6px;font-size:12px;">${item.gsm || '—'}</td>
                <td style="padding:4px 6px;font-size:12px;">${item.unit || '—'}</td>
                <td style="padding:4px 6px;font-size:12px;color:#666;">${item.customer || '—'}</td>
            </tr>`;
        }).join('');

        return `<div style="max-height:380px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;">
            <table style="width:100%;border-collapse:collapse;font-family:sans-serif;">
                <thead style="background:#2196f3;color:white;position:sticky;top:0;z-index:1;">
                    <tr>
                        <th style="padding:6px;width:32px;">✓</th>
                        <th style="padding:6px;">#</th>
                        <th style="padding:6px;">Color</th>
                        <th style="padding:6px;">Quality</th>
                        <th style="padding:6px;">GSM</th>
                        <th style="padding:6px;">Unit</th>
                        <th style="padding:6px;">Party</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
    }

    function buildDialogHtml(seq) {
        const total = seq.filter(i => i.checked !== false).length;
        const smartBtnStyle = smartSequenceActive
            ? 'background:#1b5e20;color:white;border:none;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;'
            : 'background:#e8f5e9;color:#1b5e20;border:1px solid #81c784;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;';
        return `
        <div style="margin-bottom:10px;display:flex;align-items:center;gap:10px;">
            <button id="smart_seq_btn" style="${smartBtnStyle}">
                ${smartSequenceActive ? '🔗 Smart Sequence ON' : '🔗 Smart Sequence'}
            </button>
            <span style="font-size:12px;color:#666;">${total} item(s) selected</span>
            ${smartSequenceActive ? '<span style="font-size:11px;color:#1b5e20;">✅ Sequenced by white → color chain</span>' : ''}
        </div>
        ${renderTable(seq)}`;
    }

    const d = new frappe.ui.Dialog({
        title: '🚀 Push to Production Board',
        fields: [
            {
                fieldname: 'sequence_html',
                fieldtype: 'HTML',
                options: buildDialogHtml(currentSequence)
            }
        ],
        primary_action_label: 'Push',
        primary_action: async (values) => {
            const pbPlanName = 'Default';

            const checkedItems = currentSequence.filter(i => i.checked !== false);
            if (checkedItems.length === 0) { frappe.msgprint('No items selected.'); return; }

            const itemNamesToSend = checkedItems.map(i => i.name);

            d.hide();
            frappe.show_alert({ message: `Pushing ${itemNamesToSend.length} items...`, indicator: 'blue' });

            try {
                const r = await frappe.call({
                    method: "production_scheduler.api.push_to_pb",
                    args: {
                        item_names: JSON.stringify(itemNamesToSend),
                        pb_plan_name: pbPlanName
                    }
                });
                if (r.message && r.message.status === 'success') {
                    frappe.show_alert({
                        message: `✅ Pushed ${r.message.updated_count} sheet(s) to Production Board`,
                        indicator: 'green'
                    });
                    fetchData();
                } else {
                    frappe.msgprint(r.message?.message || 'Push failed.');
                }
            } catch (e) {
                console.error('Push to PB failed', e);
                frappe.msgprint('Error pushing to Production Board.');
            }
        }
    });

    d.show();

    // Wire up checkbox events
    function wireCheckboxes() {
        const container = d.wrapper.querySelector('#sequence_html') || d.wrapper;
        container.querySelectorAll('input[type=checkbox]').forEach(cb => {
            cb.addEventListener('change', function() {
                const idx = parseInt(this.dataset.idx);
                currentSequence[idx].checked = this.checked;
                // Update count label
                const total = currentSequence.filter(i => i.checked !== false).length;
                const countEl = d.wrapper.querySelector('span[style*="fontSize"]') ||
                    d.wrapper.querySelector('span');
                if (countEl && countEl.textContent.includes('item(s)')) {
                    countEl.textContent = `${total} item(s) selected`;
                }
            });
        });
    }

    // Wire Smart Sequence button
    function wireSmartBtn() {
        const btn = d.wrapper.querySelector('#smart_seq_btn');
        if (!btn) return;
        btn.onclick = async () => {
            if (smartSequenceActive) {
                // Toggle off — restore original order
                smartSequenceActive = false;
                currentSequence = allItemNames.map((n, i) => {
                    const existing = currentSequence.find(c => c.name === n) || {};
                    const dItem = items.find(it => it.itemName === n) || {};
                    return {
                        ...existing,
                        name: n,
                        color: dItem.color || existing.color || '',
                        quality: dItem.quality || dItem.custom_quality || existing.quality || '',
                        gsm: dItem.gsm || existing.gsm || '',
                        unit: dItem.unit || existing.unit || '',
                        qty: dItem.qty || existing.qty || '',
                        customer: dItem.customer || dItem.partyCode || existing.customer || '',
                        phase: '',
                        is_seed_bridge: false,
                        sequence_no: i + 1,
                        checked: existing.checked !== false
                    };
                });
                d.fields_dict.sequence_html.$wrapper.html(buildDialogHtml(currentSequence));
                setTimeout(() => { wireCheckboxes(); wireSmartBtn(); }, 100);
            } else {
                // Toggle on — fetch smart sequence
                btn.textContent = '⏳ Sequencing...';
                btn.disabled = true;
                try {
                    const r = await frappe.call({
                        method: 'production_scheduler.api.get_smart_push_sequence',
                        args: { item_names: JSON.stringify(allItemNames) }
                    });
                    const smartSeq = r.message || [];
                    if (smartSeq.length > 0) {
                        smartSequenceActive = true;
                        currentSequence = smartSeq.map(s => ({
                            name: s.name,
                            color: s.color || '',
                            quality: s.quality || s.custom_quality || '',
                            gsm: s.gsm || s.gsmVal || '',
                            unit: s.unit || s.unitKey || '',
                            qty: s.qty || '',
                            customer: s.customer || s.partyCode || '',
                            phase: s.phase || '',
                            is_seed_bridge: !!s.is_seed_bridge,
                            sequence_no: s.sequence_no,
                            checked: (() => {
                                const existing = currentSequence.find(c => c.name === s.name);
                                return existing ? existing.checked !== false : true;
                            })()
                        }));
                        d.fields_dict.sequence_html.$wrapper.html(buildDialogHtml(currentSequence));
                        setTimeout(() => { wireCheckboxes(); wireSmartBtn(); }, 100);
                    } else {
                        frappe.show_alert({ message: 'No sequence data returned', indicator: 'orange' });
                        d.fields_dict.sequence_html.$wrapper.html(buildDialogHtml(currentSequence));
                        setTimeout(() => { wireCheckboxes(); wireSmartBtn(); }, 100);
                    }
                } catch (e) {
                    console.error('Smart sequence error', e);
                    frappe.show_alert({ message: 'Smart sequence failed', indicator: 'red' });
                    d.fields_dict.sequence_html.$wrapper.html(buildDialogHtml(currentSequence));
                    setTimeout(() => { wireCheckboxes(); wireSmartBtn(); }, 100);
                }
            }
        };
    }

    setTimeout(() => { wireCheckboxes(); wireSmartBtn(); }, 300);
}


// ---- MOVE TO PLAN ----
async function openMovePlanDialog() {
    // 1. Get ALL items from the current plan (rawData filtered by plan)
    const allItems = rawData.value.filter(d => {
        const planOk = selectedPlan.value === 'Default'
            ? (!d.planName || d.planName === '' || d.planName === 'Default')
            : d.planName === selectedPlan.value;
        return planOk;
    });

    if (allItems.length === 0) {
        frappe.msgprint('No orders in this plan to move.');
        return;
    }

    // 2. Get available target plans (excluding current, non-locked)
    const targetPlans = plans.value
        .filter(p => p.name !== selectedPlan.value && !p.locked)
        .map(p => p.name);

    if (targetPlans.length === 0) {
        frappe.msgprint('No other unlocked plans available. Create a new plan first using the "+" button.');
        return;
    }

    // 3. Separate items: moveable (no WO) vs locked (has WO)
    const moveableItems = allItems.filter(i => !i.has_wo);
    const lockedItems   = allItems.filter(i => i.has_wo);

    // 4. Sort moveable items: Color (Light→Dark), then Unit, then GSM
    const sorted = [...moveableItems].sort((a, b) => {
        const pA = getGroupPriority(a.color), pB = getGroupPriority(b.color);
        if (pA !== pB) return pA - pB;
        const uOrder = ['Unit 1','Unit 2','Unit 3','Unit 4','Mixed'];
        const uA = uOrder.indexOf(a.unit||'Mixed'), uB = uOrder.indexOf(b.unit||'Mixed');
        if (uA !== uB) return uA - uB;
        return (parseFloat(a.gsm)||0) - (parseFloat(b.gsm)||0);
    });

    // 5. Build HTML table
    const buildTable = () => {
        const unitBadge = u => {
            const c = u==='Unit 1'?'#3b82f6':u==='Unit 2'?'#10b981':u==='Unit 3'?'#f59e0b':u==='Unit 4'?'#8b5cf6':'#64748b';
            return `<span style="background:${c};color:#fff;padding:2px 6px;border-radius:10px;font-size:10px;font-weight:600;">${u||'Mixed'}</span>`;
        };

        // Moveable rows
        const moveRows = sorted.map(item => {
            const hex = getHexColor(item.color);
            const wt = ((item.qty||0)/1000).toFixed(3);
            return `<tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:5px 6px;text-align:center;">
                    <input type="checkbox" class="mtp-check" data-name="${item.itemName}" checked style="cursor:pointer;width:14px;height:14px;">
                </td>
                <td style="padding:5px 6px;">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span style="width:12px;height:12px;background:${hex};border-radius:2px;border:1px solid #ccc;flex-shrink:0;display:inline-block;"></span>
                        <b style="font-size:11px;">${item.color||'N/A'}</b>
                    </div>
                </td>
                <td style="padding:5px 6px;">${unitBadge(item.unit)}</td>
                <td style="padding:5px 6px;font-size:11px;color:#555;">${item.quality||'-'}</td>
                <td style="padding:5px 6px;font-size:11px;text-align:center;">${item.gsm||'-'}</td>
                <td style="padding:5px 6px;font-size:11px;text-align:right;font-weight:600;">${wt} T</td>
                <td style="padding:5px 6px;font-size:11px;color:#888;">${item.partyCode||item.customer||'-'}</td>
                <td style="padding:5px 6px;text-align:center;"><span style="color:#16a34a;font-size:10px;font-weight:600;">✓ FREE</span></td>
            </tr>`;
        }).join('');

        // Locked rows (WO exists — stays in original plan)
        const lockRows = lockedItems.map(item => {
            const hex = getHexColor(item.color);
            const wt = ((item.qty||0)/1000).toFixed(3);
            return `<tr style="border-bottom:1px solid #f1f5f9;opacity:0.5;background:#fef9c3;">
                <td style="padding:5px 6px;text-align:center;">—</td>
                <td style="padding:5px 6px;">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span style="width:12px;height:12px;background:${hex};border-radius:2px;border:1px solid #ccc;flex-shrink:0;display:inline-block;"></span>
                        <b style="font-size:11px;">${item.color||'N/A'}</b>
                    </div>
                </td>
                <td style="padding:5px 6px;">${unitBadge(item.unit)}</td>
                <td style="padding:5px 6px;font-size:11px;color:#555;">${item.quality||'-'}</td>
                <td style="padding:5px 6px;font-size:11px;text-align:center;">${item.gsm||'-'}</td>
                <td style="padding:5px 6px;font-size:11px;text-align:right;font-weight:600;">${wt} T</td>
                <td style="padding:5px 6px;font-size:11px;color:#888;">${item.partyCode||item.customer||'-'}</td>
                <td style="padding:5px 6px;text-align:center;"><span style="color:#dc2626;font-size:10px;font-weight:600;">🔒 WO</span></td>
            </tr>`;
        }).join('');

        const totalMoveT = (sorted.reduce((s,i)=>s+(i.qty||0),0)/1000).toFixed(2);
        const totalLockT = (lockedItems.reduce((s,i)=>s+(i.qty||0),0)/1000).toFixed(2);

        return `<div style="font-family:-apple-system,sans-serif;">
            <!-- Source/Target Header -->
            <div style="display:flex;gap:12px;margin-bottom:10px;align-items:center;background:#f8fafc;padding:10px 14px;border-radius:8px;border:1px solid #e2e8f0;">
                <div>
                    <div style="font-size:10px;color:#64748b;margin-bottom:2px;">SOURCE PLAN</div>
                    <div style="font-weight:700;color:#0f172a;font-size:13px;">📋 ${selectedPlan.value}</div>
                </div>
                <div style="font-size:20px;color:#94a3b8;padding:0 6px;">→</div>
                <div>
                    <div style="font-size:10px;color:#64748b;margin-bottom:2px;">TARGET PLAN</div>
                    <select id="mtp-target-plan" style="font-weight:700;border:1px solid #7c3aed;padding:5px 8px;border-radius:6px;font-size:12px;color:#7c3aed;background:#faf5ff;">
                        ${targetPlans.map(p=>`<option value="${p}">${p}</option>`).join('')}
                    </select>
                </div>
            </div>

            <!-- Summary badges -->
            <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;flex-wrap:wrap;">
                <span style="background:#dcfce7;color:#16a34a;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">✓ ${sorted.length} moveable (${totalMoveT} T)</span>
                ${lockedItems.length>0?`<span style="background:#fef9c3;color:#b45309;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">🔒 ${lockedItems.length} WO locked — stays in ${selectedPlan.value} (${totalLockT} T)</span>`:''}
                <button onclick="document.querySelectorAll('.mtp-check').forEach(c=>c.checked=true)" style="font-size:10px;padding:3px 8px;cursor:pointer;border:1px solid #10b981;color:#10b981;background:#f0fdf4;border-radius:4px;margin-left:auto;">✅ All</button>
                <button onclick="document.querySelectorAll('.mtp-check').forEach(c=>c.checked=false)" style="font-size:10px;padding:3px 8px;cursor:pointer;border:1px solid #ef4444;color:#ef4444;background:#fef2f2;border-radius:4px;">❌ None</button>
            </div>

            <!-- Table -->
            <div style="max-height:400px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:8px;">
                <table style="width:100%;border-collapse:collapse;font-size:12px;">
                    <thead style="position:sticky;top:0;background:#f1f5f9;z-index:1;">
                        <tr>
                            <th style="padding:6px;width:30px;text-align:center;"><input type="checkbox" id="mtp-check-all" onclick="document.querySelectorAll('.mtp-check').forEach(c=>c.checked=this.checked)" style="cursor:pointer;"></th>
                            <th style="padding:6px;text-align:left;">Color</th>
                            <th style="padding:6px;text-align:left;">Unit</th>
                            <th style="padding:6px;text-align:left;">Quality</th>
                            <th style="padding:6px;text-align:center;">GSM</th>
                            <th style="padding:6px;text-align:right;">Weight</th>
                            <th style="padding:6px;text-align:left;">Party</th>
                            <th style="padding:6px;text-align:center;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${moveRows}
                        ${lockRows}
                    </tbody>
                </table>
            </div>
            ${lockedItems.length>0?`<p style="font-size:10px;color:#b45309;margin-top:6px;padding:6px 10px;background:#fef9c3;border-radius:4px;">⚠️ Yellow rows have Work Orders — they will <b>remain in "${selectedPlan.value}"</b> on the same date after the move.</p>`:''}
        </div>`;
    };

    const d = new frappe.ui.Dialog({
        title: `📥 Move Orders to Another Plan`,
        fields: [{ fieldtype: 'HTML', fieldname: 'move_table', options: buildTable() }],
        primary_action_label: '🚀 Move Selected',
        primary_action: async () => {
            const targetPlan = document.getElementById('mtp-target-plan')?.value;
            if (!targetPlan) { frappe.msgprint('Select a target plan.'); return; }

            const checkedNames = [...document.querySelectorAll('.mtp-check:checked')]
                .map(c => c.dataset.name).filter(Boolean);
            if (checkedNames.length === 0) { frappe.msgprint('No items selected.'); return; }

            d.hide();
            frappe.show_alert({ message: `Moving ${checkedNames.length} items to "${targetPlan}"...`, indicator: 'blue' });

            try {
                const daysInView = (() => {
                    if (viewScope.value === 'weekly') return 7;
                    if (viewScope.value === 'monthly' && filterMonth.value) {
                        const [y, m] = filterMonth.value.split('-');
                        return new Date(y, m, 0).getDate();
                    }
                    return 1;
                })();
                const isAggregateView = viewScope.value === 'monthly' || viewScope.value === 'weekly';

                const r = await frappe.call({
                    method: 'production_scheduler.api.move_items_to_plan',
                    args: {
                        item_names: JSON.stringify(checkedNames),
                        target_plan: targetPlan,
                        days_in_view: daysInView,
                        force_move: isAggregateView ? 1 : 0,
                        ...dateArgs
                    }
                });

                if (r.message) {
                    const { moved, errors, skipped } = r.message;
                    if (moved > 0) frappe.show_alert({ message: `✅ Moved ${moved} items to "${targetPlan}"`, indicator: 'green' });
                    if (skipped?.length > 0) {
                        console.warn('Skipped (cancelled SO):', skipped);
                    }
                    if (errors?.length > 0) {
                        frappe.msgprint({
                            title: '⚠️ Some items blocked',
                            message: `<ul>${errors.map(e=>`<li>${e}</li>`).join('')}</ul>`,
                            indicator: 'orange'
                        });
                    }
                    fetchData();
                }

            } catch (e) {
                console.error('Move to plan failed', e);
                frappe.msgprint('❌ Error moving orders.');
            }
        },
        secondary_action_label: 'Cancel',
        secondary_action: () => d.hide()
    });

    d.show();
    d.$wrapper.find('.modal-dialog').css('max-width', '720px');
}


async function fetchData() {

  let args = {};
  
  if (viewScope.value === 'monthly') {
      if (!filterMonth.value) return;
      const [year, month] = filterMonth.value.split("-");
      const startDate = `${filterMonth.value}-01`;
      // Get last day of month
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${filterMonth.value}-${lastDay}`;
      
      args = { start_date: startDate, end_date: endDate };
      
  } else {
      if (!filterOrderDate.value) return;
      args = { date: filterOrderDate.value };
  }
  
  // ✅ IMPROVEMENT: Fetch ALL plans for the date range
  // This allows the Matrix View to maintain a consistent color legend 
  // even if the currently selected plan is empty.
  await fetchPlans(args); // Load plan names for the dropdown
  args.plan_name = "__all__"; 

  try {
    const r = await frappe.call({
      method: "production_scheduler.api.get_color_chart_data",
      args: args,
    });
    
    // Ensure idx is integer
    rawData.value = (r.message || []).map(d => ({
        ...d,
        idx: parseInt(d.idx || 0) || 9999,
        // Ensure date is parsed for monthly grouping
        orderDate: d.ordered_date || ""
    }));
    
    // Load Custom Color Order (Sync)
    try {
        const orderRes = await frappe.call("production_scheduler.api.get_color_order");
        customRowOrder.value = orderRes.message || [];
    } catch(e) { console.error("Failed to load color order", e); }

    // Re-init sortable for fresh DOM (all view modes)
    await nextTick();
    // Small delay ensures monthly refs are ready
    setTimeout(() => initSortable(), 200);
  } catch (e) {
    frappe.msgprint("Error loading color chart data");
    console.error(e);
  }
}

// Watch date to re-analyze flow
watch(filterOrderDate, async () => {
    if (viewScope.value === 'daily') {
        await fetchData();
        await analyzePreviousFlow(); 
    }
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
  
  if (selectedPlan.value && selectedPlan.value !== "Default") url.searchParams.set('plan', selectedPlan.value);
  else url.searchParams.delete('plan');
  
  // Persist view state
  url.searchParams.set('view', viewMode.value);
  url.searchParams.set('scope', viewScope.value);
  if (viewScope.value === 'monthly' && filterMonth.value) url.searchParams.set('month', filterMonth.value);
  else url.searchParams.delete('month');
  
  window.history.replaceState({}, '', url);
}

// Watchers to sync state
watch(filterOrderDate, () => {
    updateUrlParams();
    // fetchData called by existing watcher
});
watch(filterUnit, updateUrlParams);
watch(filterStatus, updateUrlParams);
watch(selectedPlan, updateUrlParams);

// Re-init Sortable when renderKey changes (forced re-render)
// Skip if matrix — matrix init is handled by its own 150ms timer inside initSortable()
watch(renderKey, () => {
    nextTick(() => {
        if (viewMode.value !== 'matrix') {
            initSortable();
        }
    });
});

// Re-init sortable when switching between kanban/matrix views
watch(viewMode, async () => {
    updateUrlParams();
    await nextTick();
    initSortable();
});
watch(viewScope, updateUrlParams);
watch(filterMonth, updateUrlParams);

onMounted(async () => {
  // 1. Read URL Params
  const params = new URLSearchParams(window.location.search);
  const dateParam = params.get('date');
  const unitParam = params.get('unit');
  const statusParam = params.get('status');
  const viewParam = params.get('view');
  const scopeParam = params.get('scope');
  const monthParam = params.get('month');
  
  // Restore view mode and scope FIRST (before data fetch)
  if (viewParam && ['kanban', 'matrix'].includes(viewParam)) viewMode.value = viewParam;
  if (scopeParam && ['daily', 'monthly'].includes(scopeParam)) viewScope.value = scopeParam;
  if (monthParam) filterMonth.value = monthParam;
  
  if (dateParam) {
      filterOrderDate.value = dateParam;
  } else {
      if (!filterOrderDate.value) filterOrderDate.value = frappe.datetime.get_today();
  }
  
  if (unitParam) filterUnit.value = unitParam;
  if (statusParam) {
       if (["Draft", "Finalized"].includes(statusParam)) filterStatus.value = statusParam;
  }
  
  if (params.get('plan')) selectedPlan.value = params.get('plan');
  
  // Create Plan Name custom field if not exist
  try {
      await frappe.call("production_scheduler.api.create_plan_name_field");
  } catch (e) {
      console.log(e);
  }
  
  // 2. Fetch Data
  await fetchData();
  analyzePreviousFlow();
});

const NO_RULE_WHITES = ["BRIGHT WHITE", "MILKY WHITE", "SUPER WHITE", "SUNSHINE WHITE", "BLEACH WHITE 1.0", "BLEACH WHITE 2.0"];
function isWhiteExempt(color) {
    if (!color) return false;
    return NO_RULE_WHITES.includes(color.toUpperCase().trim());
}

// ---- SHARED ACTION ----
async function handleMoveOrders(items, date, unit, plan, dialog) {
    try {
        const args = {
            item_names: items,
            target_date: date,
            target_unit: unit || ""
        };
        if (plan) args.plan_name = plan;

        const r = await frappe.call({
            method: "production_scheduler.api.move_orders_to_date",
            args: args,
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
         }
    }
}

async function openPushColorDialog(color) {
    // Hide items already pushed
    const items = rawData.value.filter(d => {
        if (d.plannedDate) return false; 
        if ((d.color || "").toUpperCase().trim() !== color.toUpperCase().trim()) return false;
        
        // Exclude White colors from being pushed manually
        const colorUpper = (d.color || "").toUpperCase().trim();
        if (colorUpper === "WHITE" || colorUpper === "BRIGHT WHITE") return false;
        
        if (filterUnit.value && (d.unit || "Mixed") !== filterUnit.value) return false;
        if (filterStatus.value && d.planningStatus !== filterStatus.value) return false;
        return true;
    });

    if (!items.length) {
        frappe.msgprint("No eligible items found. (Note: White orders are auto-allocated and do not need to be pushed manually, and already-pushed items are hidden.)");
        return;
    }

    const d = new frappe.ui.Dialog({
        title: `📤 Push ${color} to Production Board`,
        fields: [
            { fieldname: "target_date", label: "Target Date", fieldtype: "Date", reqd: 1, default: filterOrderDate.value || frappe.datetime.get_today(),
              onchange: () => loadCapacityPreview(d)
            },
            { fieldname: "capacity_info", label: "", fieldtype: "HTML" },
            { fieldname: "items_info", label: "Order Selection", fieldtype: "HTML" }
        ],
        primary_action_label: "Push to Production Board",
        primary_action: () => {
             const selected = d.calc_selected_items || [];
             if (!selected.length) { frappe.msgprint("Please select at least one order."); return; }
             
             const targetDate = d.get_value("target_date");
             const pbPlan = "Default";
             
             // Build payload
             const payload = selected.map(s => ({ name: s.name, target_unit: s.target_unit, target_date: targetDate }));
             
             // Define strictly inside primary_action to avoid ReferenceError
             const executePush = async (finalPayload) => {
                 d.get_primary_btn().prop("disabled", true).text("Pushing...");
                 try {
                     const r = await frappe.call({
                         method: "production_scheduler.api.push_items_to_pb",
                         args: {
                             items_data: JSON.stringify(finalPayload),
                             pb_plan_name: pbPlan
                         },
                         freeze: true
                     });
                     if (r.message && r.message.status === 'success') {
                         frappe.show_alert({ message: `✅ Pushed ${r.message.moved_items} order(s) to Plan "${r.message.plan_name}"`, indicator: 'green' });
                         d.hide();
                         fetchData();
                     } else {
                         frappe.msgprint(r.message?.message || "Push failed");
                         d.get_primary_btn().prop("disabled", false).text("Push to Production Board");
                     }
                 } catch(e) {
                     console.error("Push Error", e);
                     frappe.msgprint("Error pushing to Production Board.");
                     d.get_primary_btn().prop("disabled", false).text("Push to Production Board");
                 }
             };

             if (d.capacityExceeded) {
                  const nextDay = frappe.datetime.add_days(targetDate, 1);
                  frappe.confirm(
                      `<b>Capacity Limit Reached!</b><br>One or more selected units will exceed capacity on ${targetDate}.<br><br>Do you want to override and push to <b>${targetDate}</b> anyway?<br><br><i>Click 'Yes' to override limit, or 'No' to cancel.</i>`,
                      () => { executePush(payload); }, // Yes = Force override
                      () => { d.get_primary_btn().prop("disabled", false).text("Push to Production Board"); } // No = Cancel
                  );
             } else {
                  executePush(payload);
             }
        }
    });

    // Generate HTML for item selection (checkbox list with per-item unit dropdown)
    let html = `
        <div style="max-height: 320px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff;">
            <div style="position: sticky; top: 0; background: #f8fafc; z-index: 10; padding: 10px; border-bottom: 1px solid #e2e8f0; display:flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 12px; color: #64748b;">
                <div>
                   <input type="checkbox" checked class="push-select-all" /> Select All
                </div>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                <tbody>
    `;

    items.forEach(item => {
        // Auto-suggest unit from items existing unit if available
        let unit = item.unit || "Unit 1";
        if (unit === "Mixed" || unit === "Unassigned") unit = "Unit 1";
        
        html += `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 10px 8px; text-align:center; width:30px;">
                    <input type="checkbox" class="push-chk" value="${item.itemName}" checked />
                </td>
                <td style="padding: 10px 8px;">
                    <div><b style="color:#1e293b;">${item.partyCode}</b></div>
                    <div style="color:#64748b; font-size:10px; margin-top:2px;">${item.quality} · ${item.gsm} GSM</div>
                </td>
                <td style="padding: 10px 8px; width: 110px;">
                    <select class="push-unit-sel" data-item="${item.itemName}" style="width:100%; padding:4px; font-size:11px; border:1px solid #cbd5e1; border-radius:4px; background:#fff; cursor:pointer;">
                        <option value="Unit 1" ${unit === 'Unit 1' ? 'selected' : ''}>Unit 1</option>
                        <option value="Unit 2" ${unit === 'Unit 2' ? 'selected' : ''}>Unit 2</option>
                        <option value="Unit 3" ${unit === 'Unit 3' ? 'selected' : ''}>Unit 3</option>
                        <option value="Unit 4" ${unit === 'Unit 4' ? 'selected' : ''}>Unit 4</option>
                    </select>
                </td>
                <td style="padding: 10px 8px; text-align:right; width:80px;">
                    <b>${item.qty} Kg</b>
                </td>
            </tr>
        `;
    });

    html += `</tbody></table></div>`;
    d.set_value("items_info", html);

    // Track selections and trigger capacity preview
    window.updatePushSelection = () => {
        const selected = [];
        // Important: Only select checkboxes inside the CURRENT dialog to prevent duplication from old hidden dialogs
        d.fields_dict.items_info.$wrapper.find('.push-chk').each(function() {
            if (this.checked) {
                const itemName = this.value;
                const sel = d.fields_dict.items_info.$wrapper.find(`.push-unit-sel[data-item="${itemName}"]`);
                selected.push({ name: itemName, target_unit: sel.length ? sel.val() : "Unit 1" });
            }
        });
        d.calc_selected_items = selected;
        loadCapacityPreview(d);
    };

    async function loadCapacityPreview(dialog) {
        const date = dialog.get_value("target_date");
        if (!date) return;
        
        const limits = { "Unit 1": 4.4, "Unit 2": 12, "Unit 3": 9, "Unit 4": 5.5 };
        
        try {
            const r = await frappe.call({
                method: "production_scheduler.api.get_color_chart_data",
                args: { date: date }
            });
            const allItems = r.message || [];
            
            // Calculate pushed weight per unit for checked items
            const pushLoads = {};
            const selected = dialog.calc_selected_items || [];
            selected.forEach(sel => {
                const i = items.find(it => it.itemName === sel.name);
                if (i) {
                    pushLoads[sel.target_unit] = (pushLoads[sel.target_unit] || 0) + (i.qty || 0)/1000;
                }
            });
            
            let capHtml = `<div style="display:flex; flex-direction:column; gap:6px;">`;
            let capacityExceeded = false;
            let unitsPrinted = 0;
            
            ["Unit 1", "Unit 2", "Unit 3", "Unit 4"].forEach(u => {
                const pushWeight = pushLoads[u] || 0;
                if (pushWeight > 0) {
                    unitsPrinted++;
                    // Calculate existing order loads on this unit on this date
                    // EXCLUDE items that we are currently pushing so we don't double count!
                    const pushingNames = selected.map(s => s.name);
                    const existingU = allItems.filter(i => i.unit === u && i.plannedDate && !pushingNames.includes(i.itemName)); 
                    const currentLoad = existingU.reduce((s, i) => s + (i.qty || 0), 0) / 1000;
                    
                    const afterPush = currentLoad + pushWeight;
                    const limit = limits[u];
                    const isOver = afterPush > limit;
                    
                    if (isOver) capacityExceeded = true;
                    
                    capHtml += `
                        <div style="padding: 6px 10px; border-radius: 6px; border: 1px solid ${isOver ? '#fda4af' : '#bbf7d0'}; background: ${isOver ? '#fff1f2' : '#f0fdf4'}; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div style="font-weight:700; font-size:12px; color:${isOver ? '#dc2626' : '#16a34a'};">${u}: ${currentLoad.toFixed(2)} / ${limit}T</div>
                                <div style="font-size:10px; color:#475569; margin-top:2px;">After push: <b>${afterPush.toFixed(2)}T</b> <span style="color:#64748b;">(+${pushWeight.toFixed(2)}T)</span></div>
                            </div>
                            ${isOver ? '<span style="font-size:16px;" title="Capacity Exceeded">⚠️</span>' : '<span style="font-size:16px;">✅</span>'}
                        </div>`;
                }
            });
            
            if (unitsPrinted === 0) {
                capHtml += `<div style="font-size:11px; color:#64748b; font-style:italic;">Select items above to see capacity footprint.</div>`;
            }
            
            capHtml += `</div>`;
            dialog.set_value("capacity_info", capHtml);
            dialog.capacityExceeded = capacityExceeded;
        } catch(e) {
            console.error(e);
        }
    }
    
    // Initial load - wait for DOM to mount elements so Selectors work
    setTimeout(() => {
        // Bind events strictly to THIS dialog instance
        const wrapper = d.fields_dict.items_info.$wrapper;
        const selectAll = wrapper.find('.push-select-all');
        const checkboxes = wrapper.find('.push-chk');
        const selects = wrapper.find('.push-unit-sel');
        
        selectAll.on('change', function() {
            checkboxes.prop('checked', this.checked);
            window.updatePushSelection();
        });
        
        checkboxes.on('change', function() {
            selectAll.prop('checked', checkboxes.length === checkboxes.filter(':checked').length);
            window.updatePushSelection();
        });
        
        selects.on('change', function() {
            window.updatePushSelection();
        });
        
        window.updatePushSelection();
    }, 200);

    d.show();
}

// ---- PULL ORDERS FROM FUTURE ----
function openPullOrdersDialog() {
    const nextDay = frappe.datetime.add_days(filterOrderDate.value, 1);
    
    // Create Dialog
    const d = new frappe.ui.Dialog({
        title: '📥 Pull Orders from Date',
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
            method: "production_scheduler.api.get_color_chart_data",
            args: { date: date, mode: 'pull' }
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
                        <input type="checkbox" class="pull-item-cb" data-name="${item.itemName}" style="cursor:pointer; transform: scale(1.1);" />
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
                            ${item.color || 'No Color'}
                            <span style="font-weight: 400; color: #94a3b8; font-size: 12px; margin-left: 4px;">
                                &bull; <span style="color: #0f172a;">${item.partyCode || item.customer || '-'}</span>
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
        title: '🚑 Rescue / Re-Queue Orders',
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

.cc-card-party {
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
    border: 1px solid #d1d5db;
}

.cc-matrix-table thead th {
    background: #f8fafc;
    font-weight: 700;
    color: #334155;
    position: sticky;
    top: 0;
    z-index: 20;
    border-bottom: 2px solid #94a3b8;
}

.cc-matrix-table tbody tr:hover td {
    background: #f8fafc;
}

.matrix-sticky-col {
    position: sticky;
    left: 0;
    z-index: 10;
    background: #f8fafc;
    border-right: 2px solid #94a3b8 !important;
    min-width: 130px;
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
  opacity: 0.4;
  background: #c7d2fe !important;
  border: 2px dashed #6366f1 !important;
}

.cc-drag {
  opacity: 0;
}

.cc-chosen {
  background-color: #e0e7ff !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
}

.draggable-handle {
    cursor: grab;
}
.draggable-handle:active {
    cursor: grabbing;
}
</style>

<style scoped>
/* ---- MONTHLY VIEW ---- */
.cc-monthly-container {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow-y: auto;
    overflow-x: auto;
    padding: 10px;
    gap: 10px;
}

.cc-monthly-header {
    display: flex;
    min-width: 1000px;
}

.cc-monthly-corner {
    min-width: 150px;
    width: 150px;
    padding: 10px;
    font-weight: bold;
    background: #f1f5f9;
    border-right: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: center;
    position: sticky;
    left: 0;
    z-index: 10;
}

.cc-monthly-col-header {
    flex: 1;
    min-width: 250px;
    padding: 10px;
    text-align: center;
    font-weight: bold;
    border-top: 4px solid transparent;
    background: white;
    border-right: 1px solid #f1f5f9;
    border-bottom: 2px solid #e2e8f0;
}

.cc-monthly-row {
    display: flex;
    border-bottom: 1px solid #e2e8f0;
    min-height: 150px;
    min-width: 1000px;
}

.cc-monthly-row-label {
    min-width: 150px;
    width: 150px;
    padding: 10px;
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: sticky;
    left: 0;
    z-index: 5;
}

.cc-monthly-cell {
    flex: 1;
    min-width: 250px;
    border-right: 1px solid #f1f5f9;
    padding: 4px;
    display: flex;
    flex-direction: column;
    background: #fff;
}

.cc-cell-header-tiny {
    font-size: 10px;
    font-weight: bold;
    text-align: right;
    color: #94a3b8;
    margin-bottom: 4px;
    padding-right: 4px;
}

.cc-cell-body {
    flex: 1;
    display: flex;
    flex-wrap: wrap;
    align-content: flex-start;
    gap: 6px;
    min-height: 80px;
    background: #fafafa; /* Slight tint to show droppable area */
    border-radius: 4px;
    padding: 4px;
}

.cc-card-mini {
    width: 100%; /* Full width in cell */
    padding: 4px 6px; /* Reduced vertical padding for compact view */
    margin-bottom: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    cursor: grab;
}

.cc-color-swatch-mini {
    width: 12px;
    height: 12px;
    border-radius: 4px;
    margin-right: 6px;
    border: 1px solid rgba(0,0,0,0.1);
    flex-shrink: 0;
}
</style>