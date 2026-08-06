<template>
  <div class="layout">
    <InstrumentSidebar
      v-model:keyword="keyword"
      :instruments="filteredInstruments"
      :selected="selected"
      :loading="loading"
      :is-admin="isAdmin"
      @refresh="loadInstruments"
      @select="selectInstrument"
      @delete="deleteInstrument"
    />

    <section class="content">
      <div v-if="isAdmin" class="admin-tools">
        <AdminInstrumentPanel
          :new-instrument="newInstrument"
          :loading="loading"
          @create-and-sync="createAndSync"
        />
        <AdminDataSourcePanel
          :data-source="dataSource"
          :data-source-form="dataSourceForm"
          :selected="selected"
          :loading="loading"
          @save="saveDataSource"
          @save-and-sync="saveAndSyncSelected"
        />
      </div>

      <div v-if="selected" class="instrument-detail">
        <InstrumentHeader
          v-model:freq="freq"
          :instrument="selected"
          :is-admin="isAdmin"
          :loading="loading"
          @load-bars="loadBars"
          @sync="syncSelected"
        />

        <OverviewStats :cards="overviewCards" />

        <div class="research-grid">
          <MarketChart
            v-model:price-layers="priceLayers"
            v-model:sub-chart="subChart"
            :bars="bars"
            :indicators="indicators"
          />
          <FactorPanel :groups="factorGroups" />
        </div>

        <div class="data-grid">
          <RecentBarsTable :bars="recentBars" />
        </div>
      </div>

      <EmptyDataState v-else />
    </section>
  </div>
</template>

<script setup>
import { toRef } from 'vue'
import AdminDataSourcePanel from './components/AdminDataSourcePanel.vue'
import AdminInstrumentPanel from './components/AdminInstrumentPanel.vue'
import EmptyDataState from './components/EmptyDataState.vue'
import FactorPanel from './components/FactorPanel.vue'
import InstrumentHeader from './components/InstrumentHeader.vue'
import InstrumentSidebar from './components/InstrumentSidebar.vue'
import MarketChart from './components/MarketChart.vue'
import OverviewStats from './components/OverviewStats.vue'
import RecentBarsTable from './components/RecentBarsTable.vue'
import { useDataCenter } from './composables/useDataCenter'

const props = defineProps({
  token: {
    type: String,
    required: true
  },
  user: {
    type: Object,
    default: null
  }
})

const {
  loading,
  selected,
  bars,
  indicators,
  dataSource,
  dataSourceForm,
  keyword,
  freq,
  priceLayers,
  subChart,
  newInstrument,
  isAdmin,
  filteredInstruments,
  recentBars,
  overviewCards,
  factorGroups,
  loadInstruments,
  selectInstrument,
  loadBars,
  createAndSync,
  syncSelected,
  deleteInstrument,
  saveDataSource,
  saveAndSyncSelected
} = useDataCenter(toRef(props, 'token'), toRef(props, 'user'))
</script>
