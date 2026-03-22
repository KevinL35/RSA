<template>
  <div>
    <section class="config-block config-block--intro">
      <h2 class="page-title">{{ t('governance.painAuditTitle') }}</h2>
      <p class="intro-text">{{ t('governance.painAuditIntro') }}</p>
    </section>

    <section class="config-block">
      <el-table :data="rows" stripe class="audit-table" :empty-text="t('governance.painAuditEmpty')">
        <el-table-column :label="t('governance.painAuditColKeyword')" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="kw">{{ row.canonical }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.painAuditColType')" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.kind === 'new_discovery' ? 'warning' : 'success'" size="small">
              {{ row.kind === 'new_discovery' ? t('governance.painAuditTypeNew') : t('governance.painAuditTypeExisting') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.painAuditColSynonyms')" min-width="320">
          <template #default="{ row }">
            <div class="synonym-row">
              <el-tag
                v-for="(s, idx) in row.synonyms"
                :key="`${row.id}-${idx}-${s}`"
                class="syn-tag"
                closable
                @close="removeSynonym(row, idx)"
              >
                {{ s }}
              </el-tag>
              <span v-if="row.synonyms.length === 0" class="syn-empty">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.painAuditColAction')" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <div class="audit-actions">
              <el-button type="primary" size="small" :disabled="row.synonyms.length === 0" @click="openApprove(row)">
                {{ t('governance.painAuditApprove') }}
              </el-button>
              <el-button type="primary" size="small" @click="openEdit(row)">
                {{ t('governance.painAuditEdit') }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="approveVisible"
      :title="t('governance.painAuditApproveTitle')"
      width="480px"
      align-center
      destroy-on-close
      @closed="pendingRow = null"
    >
      <template v-if="pendingRow">
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.painAuditColKeyword') }}</span>
          <span class="dlg-value">{{ pendingRow.canonical }}</span>
        </div>
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.painAuditColSynonyms') }}</span>
          <div class="dlg-tags">
            <el-tag v-for="(s, i) in pendingRow.synonyms" :key="i" size="small" class="dlg-tag">{{ s }}</el-tag>
          </div>
        </div>
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.painAuditCategory') }}</span>
          <el-select
            v-model="approveVerticalIds"
            class="dlg-select"
            multiple
            collapse-tags
            collapse-tags-tooltip
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
            :placeholder="t('governance.painAuditCategoryPh')"
          >
            <el-option
              v-for="v in verticals"
              :key="v.id"
              :label="verticalLabel(v)"
              :value="v.id"
            />
          </el-select>
        </div>
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.painAuditDimension') }}</span>
          <el-select
            v-model="approveDimension"
            class="dlg-select"
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
            :placeholder="t('governance.painAuditPickDim')"
          >
            <el-option v-for="d in SIX_DIMENSIONS" :key="d" :label="dimensionLabel(d)" :value="d" />
          </el-select>
        </div>
      </template>
      <template #footer>
        <el-button @click="approveVisible = false">{{ t('governance.painAuditCancel') }}</el-button>
        <el-button
          type="primary"
          :disabled="!canConfirmApprove"
          :loading="approveSubmitting"
          @click="confirmApprove"
        >
          {{ t('governance.painAuditConfirmApprove') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="editVisible"
      :title="t('governance.painAuditEditTitle')"
      width="520px"
      align-center
      destroy-on-close
      @closed="onEditDialogClosed"
    >
      <p class="edit-hint">{{ t('governance.painAuditEditHint') }}</p>
      <el-form label-position="top" class="edit-form">
        <el-form-item :label="t('governance.painAuditEditKeyword')" required>
          <el-input v-model="editCanonical" clearable maxlength="512" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('governance.painAuditEditSynonyms')" required>
          <el-input
            v-model="editSynonymsText"
            type="textarea"
            :rows="6"
            :placeholder="t('governance.painAuditEditSynonymsPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">{{ t('governance.painAuditCancel') }}</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="saveEdit">
          {{ t('governance.painAuditEditSave') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import type { DictionaryReviewQueueItem, DictionaryVerticalItem } from '../../dictionary/api'
import {
  deleteDictionaryReviewQueue,
  fetchDictionaryReviewQueue,
  fetchDictionaryVerticals,
  patchDictionaryReviewQueue,
  postDictionaryApproveEntry,
} from '../../dictionary/api'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'
import type { PainAuditRow, SixDimension } from '../painAuditTypes'
import { SIX_DIMENSIONS } from '../painAuditTypes'

const { t, locale } = useI18n()

const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM

const rows = ref<PainAuditRow[]>([])
const verticals = ref<DictionaryVerticalItem[]>([])

const approveVisible = ref(false)
const pendingRow = ref<PainAuditRow | null>(null)

const editVisible = ref(false)
const editingRowId = ref<string | null>(null)
const editCanonical = ref('')
const editSynonymsText = ref('')
const editSubmitting = ref(false)
const approveVerticalIds = ref<string[]>([])
const approveDimension = ref<SixDimension | ''>('')
const approveSubmitting = ref(false)

const canConfirmApprove = computed(
  () =>
    !!pendingRow.value &&
    !!approveDimension.value &&
    approveVerticalIds.value.length > 0,
)

function verticalLabel(v: DictionaryVerticalItem) {
  if (v.id === 'general') {
    return locale.value === 'zh-CN' ? '默认词典' : 'Default dictionary'
  }
  return locale.value === 'zh-CN' ? v.label_zh : v.label_en
}

function dimensionLabel(d: SixDimension) {
  const key = `governance.dim_${d}` as const
  const translated = t(key)
  return translated === key ? d : translated
}

function parseSynonymsFromTextarea(raw: string): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const part of raw.split(/[\n,，]+/)) {
    const s = part.trim()
    if (!s) continue
    const key = s.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(s)
  }
  return out
}

function openEdit(row: PainAuditRow) {
  editingRowId.value = row.id
  editCanonical.value = row.canonical
  editSynonymsText.value = row.synonyms.length ? row.synonyms.join('\n') : ''
  editVisible.value = true
}

function onEditDialogClosed() {
  editingRowId.value = null
  editCanonical.value = ''
  editSynonymsText.value = ''
}

async function saveEdit() {
  const id = editingRowId.value
  const c = editCanonical.value.trim()
  if (!c) {
    ElMessage.warning(t('governance.painAuditEditNeedKeyword'))
    return
  }
  const syns = parseSynonymsFromTextarea(editSynonymsText.value)
  if (syns.length === 0) {
    ElMessage.warning(t('governance.painAuditEditNeedSynonym'))
    return
  }
  const row = rows.value.find((r) => r.id === id)
  if (!row) {
    editVisible.value = false
    return
  }
  editSubmitting.value = true
  try {
    await patchDictionaryReviewQueue(row.id, { canonical: c, synonyms: syns })
    row.canonical = c
    row.synonyms = syns
    editVisible.value = false
    ElMessage.success(t('governance.painAuditEditSavedOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.painAuditQueueSyncFail')}: ${msg}`)
  } finally {
    editSubmitting.value = false
  }
}

async function removeSynonym(row: PainAuditRow, index: number) {
  const next = row.synonyms.filter((_, i) => i !== index)
  if (next.length === 0) {
    try {
      await deleteDictionaryReviewQueue(row.id)
      rows.value = rows.value.filter((r) => r.id !== row.id)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      ElMessage.error(`${t('governance.painAuditQueueSyncFail')}: ${msg}`)
    }
    return
  }
  try {
    await patchDictionaryReviewQueue(row.id, { canonical: row.canonical, synonyms: next })
    row.synonyms = next
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.painAuditQueueSyncFail')}: ${msg}`)
  }
}

function openApprove(row: PainAuditRow) {
  if (row.synonyms.length === 0) return
  pendingRow.value = row
  const vid = row.vertical_id || 'general'
  approveVerticalIds.value = [vid]
  approveDimension.value = row.kind === 'existing' && row.dimension_6way ? row.dimension_6way : ''
  approveVisible.value = true
}

async function confirmApprove() {
  const row = pendingRow.value
  const dim = approveDimension.value
  if (!row || !dim || approveVerticalIds.value.length === 0) return
  approveSubmitting.value = true
  try {
    await postDictionaryApproveEntry({
      vertical_ids: [...approveVerticalIds.value],
      dimension_6way: dim,
      canonical: row.canonical,
      aliases: [...row.synonyms],
      batch_id: row.batch_id ?? null,
      source_topic_id: row.source_topic_id ?? null,
      review_queue_id: row.id,
    })
    rows.value = rows.value.filter((r) => r.id !== row.id)
    approveVisible.value = false
    pendingRow.value = null
    ElMessage.success(t('governance.painAuditApprovedOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.painAuditApproveFail')}: ${msg}`)
  } finally {
    approveSubmitting.value = false
  }
}

async function loadVerticals() {
  try {
    const res = await fetchDictionaryVerticals()
    verticals.value = res.items ?? []
  } catch {
    verticals.value = []
    ElMessage.warning(t('governance.painAuditVerticalsLoadFail'))
  }
}

function mapQueueItem(raw: DictionaryReviewQueueItem): PainAuditRow {
  const dimRaw = raw.dimension_6way
  const dimension_6way =
    dimRaw && (SIX_DIMENSIONS as readonly string[]).includes(dimRaw) ? (dimRaw as SixDimension) : undefined
  return {
    id: String(raw.id),
    kind: raw.kind === 'existing' ? 'existing' : 'new_discovery',
    canonical: String(raw.canonical ?? '').trim(),
    synonyms: Array.isArray(raw.synonyms) ? raw.synonyms.map((s) => String(s).trim()).filter(Boolean) : [],
    vertical_id: String(raw.vertical_id ?? 'general').trim() || 'general',
    dimension_6way,
    batch_id: raw.batch_id ?? undefined,
    source_topic_id: raw.source_topic_id ?? undefined,
    quality_score: typeof raw.quality_score === 'number' ? raw.quality_score : undefined,
  }
}

async function loadReviewQueue() {
  try {
    const res = await fetchDictionaryReviewQueue()
    rows.value = (res.items ?? []).map(mapQueueItem).filter((r) => r.canonical.length > 0)
  } catch {
    rows.value = []
    ElMessage.warning(t('governance.painAuditQueueLoadFail'))
  }
}

onMounted(async () => {
  await loadVerticals()
  await loadReviewQueue()
})
</script>

<style scoped>
.config-block {
  margin-bottom: 28px;
  padding: 18px 20px 20px;
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.config-block--intro {
  padding: 16px 20px;
}

.page-title {
  margin: 0 0 10px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.35;
}

.intro-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
}

.audit-table {
  width: 100%;
}

.kw {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.synonym-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.syn-tag {
  margin: 0;
}

.syn-empty {
  color: var(--el-text-color-placeholder);
  font-size: 14px;
}

.audit-actions {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

.dlg-field {
  margin-bottom: 14px;
}

.dlg-field:last-of-type {
  margin-bottom: 0;
}

.dlg-label {
  display: block;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

.dlg-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.dlg-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dlg-tag {
  margin: 0;
}

.dlg-select {
  width: 100%;
}

.edit-hint {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.edit-form {
  margin-top: 4px;
}
</style>
