<template>
  <div class="page" v-loading="loading">
    <section class="config-block config-block--intro">
      <div class="intro-head">
        <h2 class="page-title">{{ t('governance.dictionaryTitle') }}</h2>
        <div class="intro-head-right">
          <el-select
            v-model="verticalId"
            class="dict-vertical-select"
            :teleported="true"
            @change="onVerticalChange"
          >
            <el-option
              v-for="v in verticals"
              :key="v.id"
              :label="verticalLabel(v)"
              :value="v.id"
            />
          </el-select>
        </div>
      </div>
      <p class="intro-text">{{ t('governance.dictionaryDesc') }}</p>
    </section>

    <el-empty
      v-if="!loading && loadError"
      :description="t('governance.dictionaryLoadFail')"
    />

    <template v-else-if="preview">
      <section
        v-for="dim in preview.dimension_order"
        :key="dim"
        class="config-block"
      >
        <div class="block-head">
          <div class="block-head-left">
            <h3 class="block-title">{{ dimensionTitle(dim) }}</h3>
            <el-tag size="small" type="info" class="dim-count-tag">
              {{ preview.dimensions[dim]?.count ?? 0 }}
            </el-tag>
          </div>
        </div>
        <el-table
          :data="preview.dimensions[dim]?.entries ?? []"
          stripe
          class="block-table"
          :empty-text="t('insight.tableEmpty')"
        >
          <el-table-column
            :label="t('governance.dictionaryColKeyword')"
            prop="canonical"
            min-width="200"
            show-overflow-tooltip
          />
          <el-table-column :label="t('governance.dictionaryColSynonyms')" min-width="360">
            <template #default="{ row }">
              <div class="synonym-chips">
                <button
                  v-for="(al, idx) in aliasList(row)"
                  :key="idx"
                  type="button"
                  class="synonym-chip"
                  @click="openRejectDialog(dim, row, al)"
                >
                  {{ al }}
                </button>
                <span v-if="aliasList(row).length === 0" class="synonym-empty">—</span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <el-dialog
      v-model="rejectDialogVisible"
      :title="t('governance.rejectSynonymTitle')"
      width="480px"
      align-center
      destroy-on-close
      @closed="pendingReject = null"
    >
      <p class="reject-dialog-text">
        {{ t('governance.rejectSynonymBody', { keyword: pendingReject?.canonical ?? '', synonym: pendingReject?.alias ?? '' }) }}
      </p>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">{{ t('governance.rejectSynonymCancel') }}</el-button>
        <el-button type="danger" :loading="rejectSubmitting" @click="confirmReject">
          {{ t('governance.rejectSynonymConfirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import type { DictionaryVerticalItem, TaxonomyPreviewEntry, TaxonomyPreviewResponse } from '../../dictionary/api'
import {
  fetchDictionaryVerticals,
  fetchTaxonomyPreview,
  postDictionaryRejectSynonym,
} from '../../dictionary/api'

const { t, locale } = useI18n()

const loading = ref(false)
const loadError = ref(false)
const verticals = ref<DictionaryVerticalItem[]>([])
const verticalId = ref('general')
const preview = ref<TaxonomyPreviewResponse | null>(null)

const rejectDialogVisible = ref(false)
const rejectSubmitting = ref(false)
const pendingReject = ref<{
  dimension: string
  canonical: string
  alias: string
} | null>(null)

const dimensionTitle = (dim: string) => {
  const key = `governance.dim_${dim}` as const
  const translated = t(key)
  return translated === key ? dim : translated
}

function verticalLabel(v: DictionaryVerticalItem) {
  if (v.id === 'general') {
    return locale.value === 'zh-CN' ? '默认词典' : 'Default dictionary'
  }
  return locale.value === 'zh-CN' ? v.label_zh : v.label_en
}

function aliasList(row: TaxonomyPreviewEntry): string[] {
  const a = row.aliases
  if (!Array.isArray(a)) return []
  return a.map((x) => String(x).trim()).filter(Boolean)
}

function openRejectDialog(dimension: string, row: TaxonomyPreviewEntry, alias: string) {
  const kw = String(row.canonical ?? '').trim()
  if (!kw) return
  pendingReject.value = { dimension, canonical: kw, alias: String(alias).trim() }
  rejectDialogVisible.value = true
}

async function confirmReject() {
  const p = pendingReject.value
  if (!p) return
  rejectSubmitting.value = true
  try {
    await postDictionaryRejectSynonym({
      vertical_id: verticalId.value,
      dimension_6way: p.dimension,
      canonical: p.canonical,
      alias: p.alias,
    })
    ElMessage.success(t('governance.rejectSynonymOk'))
    rejectDialogVisible.value = false
    pendingReject.value = null
    await loadPreview()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.rejectSynonymFail')}: ${msg}`)
  } finally {
    rejectSubmitting.value = false
  }
}

async function loadVerticals() {
  try {
    const res = await fetchDictionaryVerticals()
    verticals.value = res.items ?? []
    if (!verticals.value.some((x) => x.id === verticalId.value) && verticals.value.length) {
      verticalId.value = verticals.value[0]!.id
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.dictionaryLoadFail')}: ${msg}`)
    verticals.value = []
    loadError.value = true
  }
}

async function loadPreview() {
  loading.value = true
  loadError.value = false
  try {
    preview.value = await fetchTaxonomyPreview(verticalId.value)
  } catch (e) {
    preview.value = null
    loadError.value = true
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.dictionaryLoadFail')}: ${msg}`)
  } finally {
    loading.value = false
  }
}

function onVerticalChange() {
  void loadPreview()
}

onMounted(async () => {
  await loadVerticals()
  await loadPreview()
})
</script>

<style scoped>
.page {
  max-width: 960px;
}

.config-block {
  margin-bottom: 28px;
  padding: 18px 20px 20px;
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.config-block--intro {
  padding: 16px 20px 18px;
}

.intro-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.35;
  flex: 1;
  min-width: 0;
}

.intro-head-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.dict-vertical-select {
  width: 160px;
}

.intro-text {
  margin: 0 0 14px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.block-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.block-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.dim-count-tag {
  flex-shrink: 0;
}

.block-table {
  width: 100%;
}

.synonym-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.synonym-chip {
  margin: 0;
  padding: 4px 10px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 6px;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.synonym-chip:hover {
  background: var(--el-color-primary-light-7);
  border-color: var(--el-color-primary-light-3);
}

.synonym-empty {
  color: var(--el-text-color-placeholder);
  font-size: 14px;
}

.reject-dialog-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--el-text-color-regular);
}
</style>
