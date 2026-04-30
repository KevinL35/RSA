<template>
  <div>
    <section class="config-block">
      <h2 class="page-title">{{ t('governance.smartMiningTitle') }}</h2>
      <p class="intro-text">{{ t('governance.smartMiningDesc') }}</p>
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button :type="activeList === 'new' ? 'primary' : 'default'" @click="activeList = 'new'">
            {{ t('governance.smartMiningNewDirection') }}
          </el-button>
          <el-button :type="activeList === 'rejected' ? 'primary' : 'default'" @click="activeList = 'rejected'">
            {{ t('governance.smartMiningRejectedList') }}
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-button
            :type="miningRunning ? 'success' : 'primary'"
            :loading="miningStartingOrCancelling"
            @click="onToggleMining"
          >
            {{ miningRunning ? t('governance.topicMiningCancel') : t('governance.topicMiningStart') }}
          </el-button>
          <el-button type="primary" @click="onAddTopic">{{ t('governance.addTopic') }}</el-button>
          <el-button
            class="toolbar-refresh-square"
            :icon="Refresh"
            @click="onRefresh"
            :title="t('governance.refresh')"
          />
        </div>
      </div>
      <el-table :data="filteredRows" stripe class="audit-table" :empty-text="t('governance.smartMiningEmpty')">
        <el-table-column :label="t('governance.smartMiningCategory')" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ verticalNameById(row.vertical_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.smartMiningColKeyword')" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="kw">{{ row.canonical }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.smartMiningColSynonyms')" min-width="320">
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
        <el-table-column :label="t('governance.smartMiningColAction')" min-width="280" align="center" fixed="right">
          <template #default="{ row }">
            <div class="audit-actions">
              <el-button type="primary" size="small" :disabled="row.synonyms.length === 0" @click="openApprove(row)">
                {{ t('governance.smartMiningApprove') }}
              </el-button>
              <el-button type="primary" size="small" @click="openEdit(row)">
                {{ t('governance.smartMiningEdit') }}
              </el-button>
              <el-button
                type="danger"
                size="small"
                :loading="deletingQueueId === row.id"
                @click="onDeleteQueueRow(row)"
              >
                {{ t('governance.smartMiningDelete') }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="config-block agent-review-block">
      <h3 class="agent-review-title">{{ t('governance.agentReviewPanelTitle') }}</h3>
      <p class="agent-review-intro">{{ t('governance.agentReviewPanelIntro') }}</p>
      <div class="toolbar agent-review-toolbar">
        <div class="toolbar-left"></div>
        <div class="toolbar-right">
          <el-button type="primary" :loading="agentReviewing" @click="onAgentReview">
            {{ t('governance.agentReviewStart') }}
          </el-button>
          <el-button
            class="toolbar-refresh-square"
            :icon="Refresh"
            @click="onRefresh"
            :title="t('governance.refresh')"
          />
        </div>
      </div>
      <el-table
        :data="agentGroupedRows"
        stripe
        class="audit-table"
        :empty-text="t('governance.reviewRecordsEmpty')"
        :span-method="agentDimSpanMethod"
      >
        <el-table-column :label="t('governance.smartMiningCategory')" min-width="150" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            {{ verticalNameById(row.vertical_id) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.smartMiningDimension')" min-width="130" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.dimension_6way ? dimensionLabel(row.dimension_6way) : '—' }}
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.smartMiningColKeyword')" min-width="320" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="synonym-row">
              <el-popover
                v-for="kw in keywordsByGroup[groupKey(row)] || [row.canonical]"
                :key="`${groupKey(row)}-${kw}`"
                trigger="click"
                placement="top"
                :width="320"
              >
                <template #reference>
                  <el-tag
                    class="syn-tag"
                    closable
                    @close="removeKeywordByGroup(row.vertical_id, row.dimension_6way, kw)"
                  >
                    {{ kw }}
                  </el-tag>
                </template>
                <div class="kw-popover">
                  <div class="kw-popover-title">{{ t('governance.smartMiningColSynonyms') }}</div>
                  <div class="kw-popover-content">
                    <template v-if="synonymsByKeyword(row.vertical_id, row.dimension_6way, kw).length">
                      <el-tag
                        v-for="syn in synonymsByKeyword(row.vertical_id, row.dimension_6way, kw)"
                        :key="`${groupKey(row)}-${kw}-${syn}`"
                        class="syn-tag"
                        closable
                        @close="removeSynonymByKeyword(row.vertical_id, row.dimension_6way, kw, syn)"
                      >
                        {{ syn }}
                      </el-tag>
                    </template>
                    <span v-else>—</span>
                  </div>
                </div>
              </el-popover>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('governance.agentRecordActions')" width="300" align="center" fixed="right">
          <template #default="{ row, $index }">
            <div v-if="isAgentGroupActionRow(row, $index)" class="audit-actions">
              <el-button
                type="primary"
                size="small"
                :loading="smartMergeLoadingKey === groupKey(row)"
                :disabled="agentGroupQueueIds(row).length === 0"
                @click="onSmartMergeGroup(row)"
              >
                {{ t('governance.agentSmartMerge') }}
              </el-button>
              <el-button
                type="danger"
                size="small"
                :loading="deletingAgentGroupKey === groupKey(row)"
                :disabled="agentGroupQueueIds(row).length === 0"
                @click="onDeleteAgentGroup(row)"
              >
                {{ t('governance.smartMiningDelete') }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="approveVisible"
      :title="t('governance.smartMiningApproveTitle')"
      width="480px"
      align-center
      destroy-on-close
      @closed="pendingRow = null"
    >
      <template v-if="pendingRow">
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.smartMiningColKeyword') }}</span>
          <span class="dlg-value">{{ pendingRow.canonical }}</span>
        </div>
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.smartMiningColSynonyms') }}</span>
          <div class="dlg-tags">
            <el-tag v-for="(s, i) in pendingRow.synonyms" :key="i" size="small" class="dlg-tag">{{ s }}</el-tag>
          </div>
        </div>
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.smartMiningCategory') }}</span>
          <span class="dlg-value">{{ pendingRow ? verticalNameById(pendingRow.vertical_id) : '' }}</span>
        </div>
        <div class="dlg-field">
          <span class="dlg-label">{{ t('governance.smartMiningDimension') }}</span>
          <span class="dlg-value">
            {{ approveDimension ? dimensionLabel(approveDimension) : t('governance.smartMiningNoAgentDimension') }}
          </span>
        </div>
      </template>
      <template #footer>
        <el-button @click="approveVisible = false">{{ t('governance.smartMiningCancel') }}</el-button>
        <el-button
          type="primary"
          :disabled="!canConfirmApprove"
          :loading="approveSubmitting"
          @click="confirmApprove"
        >
          {{ t('governance.smartMiningConfirmApprove') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="editVisible"
      :title="t('governance.smartMiningEditTitle')"
      width="520px"
      align-center
      destroy-on-close
      @closed="onEditDialogClosed"
    >
      <p class="edit-hint">{{ t('governance.smartMiningEditHint') }}</p>
      <el-form label-position="top" class="edit-form">
        <el-form-item :label="t('governance.smartMiningEditKeyword')" required>
          <el-input v-model="editCanonical" clearable maxlength="512" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('governance.smartMiningEditSynonyms')" required>
          <el-input
            v-model="editSynonymsText"
            type="textarea"
            :rows="6"
            :placeholder="t('governance.smartMiningEditSynonymsPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">{{ t('governance.smartMiningCancel') }}</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="saveEdit">
          {{ t('governance.smartMiningEditSave') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="addTopicVisible"
      :title="t('governance.addTopic')"
      width="520px"
      align-center
      destroy-on-close
      @closed="resetAddTopicForm"
    >
      <el-form label-position="top" class="edit-form">
        <el-form-item :label="t('governance.smartMiningCategory')" required>
          <el-select
            v-model="addTopicVerticalId"
            class="dlg-select"
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
            :placeholder="t('governance.addTopicPickVertical')"
          >
            <el-option
              v-for="v in verticals"
              :key="v.id"
              :label="verticalLabel(v)"
              :value="v.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('governance.smartMiningEditKeyword')" required>
          <el-input v-model="addTopicCanonical" clearable maxlength="512" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('governance.smartMiningEditSynonyms')" required>
          <el-input
            v-model="addTopicSynonymsText"
            type="textarea"
            :rows="6"
            :placeholder="t('governance.smartMiningEditSynonymsPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addTopicVisible = false">{{ t('governance.smartMiningCancel') }}</el-button>
        <el-button type="primary" :loading="addTopicSubmitting" @click="submitAddTopic">
          {{ t('governance.addTopicSave') }}
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import type { DictionaryReviewQueueItem, DictionaryVerticalItem } from '../../dictionary/api'
import {
  deleteDictionaryReviewQueue,
  fetchDictionaryReviewRecords,
  fetchDictionaryReviewQueue,
  fetchDictionaryVerticals,
  patchDictionaryReviewQueue,
  postDictionaryAgentReview,
  postDictionaryApproveEntry,
  postDictionaryReviewQueue,
  postDictionarySmartMerge,
} from '../../dictionary/api'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'
import type { SmartMiningRow, SixDimension } from '../smartMiningTypes'
import { SIX_DIMENSIONS } from '../smartMiningTypes'
import {
  cancelTopicDiscoveryGlobal,
  fetchTopicDiscoveryGlobalLatest,
  postTopicDiscoveryGlobal,
} from '../../insight/api'
import { onBeforeUnmount } from 'vue'

const { t, locale } = useI18n()

const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM

const rows = ref<SmartMiningRow[]>([])
const verticals = ref<DictionaryVerticalItem[]>([])

const approveVisible = ref(false)
const pendingRow = ref<SmartMiningRow | null>(null)

const editVisible = ref(false)
const editingRowId = ref<string | null>(null)
const editCanonical = ref('')
const editSynonymsText = ref('')
const editSubmitting = ref(false)
const addTopicVisible = ref(false)
const addTopicVerticalId = ref('')
const addTopicCanonical = ref('')
const addTopicSynonymsText = ref('')
const addTopicSubmitting = ref(false)
const deletingQueueId = ref<string | null>(null)
const approveDimension = ref<SixDimension | ''>('')
const approveSubmitting = ref(false)
const activeList = ref<'new' | 'rejected'>('new')

const canConfirmApprove = computed(() => !!pendingRow.value && !!approveDimension.value)

const agentReviewIds = ref<string[]>([])
const displayRows = computed(() =>
  rows.value.filter((row) => !agentReviewIds.value.includes(row.id)),
)
const filteredRows = computed(() =>
  activeList.value === 'rejected'
    ? displayRows.value.filter((row) => row.kind === 'rejected')
    : displayRows.value.filter((row) => row.kind !== 'rejected'),
)
const _dimOrder = SIX_DIMENSIONS as readonly string[]
const agentGroupedRows = computed(() =>
  rows.value
    .filter((r) => agentReviewIds.value.includes(r.id))

    .filter((r) => !!r.dimension_6way)
    .slice()
    .sort((a, b) => {
      const avv = (a.vertical_id || '').trim()
      const bvv = (b.vertical_id || '').trim()
      if (avv !== bvv) return avv.localeCompare(bvv)
      const ai = _dimOrder.indexOf((a.dimension_6way || '') as string)
      const bi = _dimOrder.indexOf((b.dimension_6way || '') as string)
      const av = ai === -1 ? 999 : ai
      const bv = bi === -1 ? 999 : bi
      if (av !== bv) return av - bv
      return a.canonical.localeCompare(b.canonical)
    }),
)
const keywordsByGroup = computed<Record<string, string[]>>(() => {
  const out: Record<string, string[]> = {}
  const seen: Record<string, Set<string>> = {}
  for (const r of agentGroupedRows.value) {
    const key = groupKey(r)
    if (!seen[key]) seen[key] = new Set<string>()
    seen[key].add(r.canonical)
  }
  for (const [key, set] of Object.entries(seen)) {
    out[key] = Array.from(set)
  }
  return out
})

function groupKey(row: Pick<SmartMiningRow, 'vertical_id' | 'dimension_6way'>): string {
  const vid = (row.vertical_id || '__none__').trim() || '__none__'
  const dim = row.dimension_6way || '__none__'
  return `${vid}::${dim}`
}

function isAgentGroupActionRow(row: SmartMiningRow, $index: number): boolean {
  const data = agentGroupedRows.value
  if ($index <= 0) return true
  const prev = data[$index - 1]
  if (!prev) return true
  return groupKey(prev) !== groupKey(row)
}

function agentGroupQueueIds(row: SmartMiningRow): string[] {
  const vid = (row.vertical_id || '').trim()
  const dim = row.dimension_6way || ''
  if (!dim) return []

  return rows.value
    .filter((r) => agentReviewIds.value.includes(r.id))
    .filter((r) => (r.vertical_id || '').trim() === vid)
    .filter((r) => (r.dimension_6way || '') === dim)
    .map((r) => r.id)
}

async function onSmartMergeGroup(row: SmartMiningRow) {
  const dim = row.dimension_6way
  if (!dim) {
    ElMessage.warning(t('governance.agentSmartMergeNeedDim'))
    return
  }
  const ids = agentGroupQueueIds(row)
  if (!ids.length) return
  const k = groupKey(row)
  smartMergeLoadingKey.value = k
  try {
    await postDictionarySmartMerge({
      vertical_id: (row.vertical_id || 'electronics').trim() || 'electronics',
      dimension_6way: dim,
      queue_ids: ids,
    })
    await loadReviewQueue()
    ElMessage.success(t('governance.agentSmartMergeOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.agentSmartMergeFail')}: ${msg}`)
  } finally {
    smartMergeLoadingKey.value = ''
  }
}

async function onDeleteAgentGroup(row: SmartMiningRow) {
  const ids = agentGroupQueueIds(row)
  if (!ids.length) return
  const dimLabel = row.dimension_6way ? dimensionLabel(row.dimension_6way) : '—'
  try {
    await ElMessageBox.confirm(
      `确定删除该分组的待审记录吗？（词典：${verticalNameById(row.vertical_id)}，维度：${dimLabel}，共 ${ids.length} 条）`,
      t('governance.smartMiningDelete'),
      {
        type: 'warning',
        confirmButtonText: t('governance.smartMiningDelete'),
        cancelButtonText: t('governance.smartMiningCancel'),
      },
    )
  } catch {
    return
  }
  const key = groupKey(row)
  deletingAgentGroupKey.value = key
  try {
    await Promise.all(ids.map((id) => deleteDictionaryReviewQueue(id)))
    rows.value = rows.value.filter((r) => !ids.includes(r.id))
    agentReviewIds.value = agentReviewIds.value.filter((id) => !ids.includes(id))
    ElMessage.success(t('governance.smartMiningDeletedOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.smartMiningDeleteFail')}: ${msg}`)
  } finally {
    deletingAgentGroupKey.value = ''
  }
}

function verticalLabel(v: DictionaryVerticalItem) {
  return locale.value === 'zh-CN' ? v.label_zh : v.label_en
}

function dimensionLabel(d: SixDimension) {
  const key = `governance.dim_${d}` as const
  const translated = t(key)
  return translated === key ? d : translated
}

function resetAddTopicForm() {
  addTopicVerticalId.value = verticals.value[0]?.id ?? 'electronics'
  addTopicCanonical.value = ''
  addTopicSynonymsText.value = ''
}

function onAddTopic() {
  resetAddTopicForm()
  addTopicVisible.value = true
}

async function submitAddTopic() {
  const c = addTopicCanonical.value.trim()
  if (c.length < 2) {
    ElMessage.warning(t('governance.smartMiningEditNeedKeyword'))
    return
  }
  const syns = parseSynonymsFromTextarea(addTopicSynonymsText.value)
  const kwLower = c.toLowerCase()
  const filtered = syns.filter((s) => s.toLowerCase() !== kwLower)
  if (filtered.length === 0) {
    ElMessage.warning(t('governance.smartMiningEditNeedSynonym'))
    return
  }
  const vid = (addTopicVerticalId.value || '').trim()
  if (!vid) {
    ElMessage.warning(t('governance.addTopicPickVertical'))
    return
  }
  addTopicSubmitting.value = true
  try {
    await postDictionaryReviewQueue({ canonical: c, synonyms: filtered, vertical_id: vid })
    await loadReviewQueue()
    addTopicVisible.value = false
    resetAddTopicForm()
    ElMessage.success(t('governance.addTopicOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.addTopicFail')}: ${msg}`)
  } finally {
    addTopicSubmitting.value = false
  }
}

function onUploadReviews() {
  ElMessage.info(t('governance.featureComingSoon'))
}

const miningRunning = ref(false)
const miningStartingOrCancelling = ref(false)
const activeMiningJobId = ref<string>('')
const agentReviewing = ref(false)

const smartMergeLoadingKey = ref('')

const deletingAgentGroupKey = ref('')
let miningPoller: number | null = null

function stopMiningPoll() {
  if (miningPoller != null) {
    window.clearInterval(miningPoller)
    miningPoller = null
  }
}

async function pollLatestJob() {
  try {
    const res = await fetchTopicDiscoveryGlobalLatest()
    const job = res.job
    if (!job) {
      miningRunning.value = false
      activeMiningJobId.value = ''
      stopMiningPoll()
      return
    }
    activeMiningJobId.value = job.id
    if (job.status === 'pending' || job.status === 'running') {
      miningRunning.value = true
      return
    }
    miningRunning.value = false
    stopMiningPoll()
    if (job.status === 'success') {
      ElMessage.success(t('governance.topicMiningOk'))
      await onRefresh()
    } else if (job.status === 'cancelled') {
      ElMessage.warning(t('governance.topicMiningCancelled'))
    } else {
      const detail = job.error_message ? `: ${job.error_message}` : ''
      ElMessage.error(`${t('governance.topicMiningFailed')}${detail}`)
    }
  } catch (e) {

    console.warn('[topic-discovery] poll failed', e)
  }
}

function startMiningPoll() {
  stopMiningPoll()
  void pollLatestJob()
  miningPoller = window.setInterval(() => void pollLatestJob(), 2500)
}

async function onToggleMining() {
  if (miningRunning.value) {
    const jid = activeMiningJobId.value
    if (!jid) return
    miningStartingOrCancelling.value = true
    try {
      await cancelTopicDiscoveryGlobal(jid)
      ElMessage.warning(t('governance.topicMiningCancelled'))
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      ElMessage.error(`${t('governance.topicMiningCancelFail')}: ${msg}`)
    } finally {
      miningStartingOrCancelling.value = false
      void pollLatestJob()
    }
    return
  }
  miningStartingOrCancelling.value = true
  try {
    const res = await postTopicDiscoveryGlobal({ embedding_model: 'ml/all-MiniLM-L6-v2' })
    activeMiningJobId.value = res.job.id
    miningRunning.value = true
    ElMessage.info(t('governance.topicMiningRunningTip'))
    startMiningPoll()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.topicMiningFailed')}: ${msg}`)
  } finally {
    miningStartingOrCancelling.value = false
  }
}

async function onAgentReview() {
  agentReviewing.value = true
  try {
    const res = await postDictionaryAgentReview(20)
    await loadReviewQueue()
    const reviewedIds = (res.items ?? [])
      .map((x) => String(x.id || '').trim())
      .filter((x) => x.length > 0)
    if (reviewedIds.length) {
      const merged = new Set([...agentReviewIds.value, ...reviewedIds])
      agentReviewIds.value = Array.from(merged)
    }
    ElMessage.success(
      t('governance.agentReviewOk', {
        reviewed: res.reviewed ?? 0,
        updated: res.updated ?? 0,
      }),
    )
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.agentReviewFail')}: ${msg}`)
  } finally {
    agentReviewing.value = false
  }
}

function verticalNameById(verticalId?: string) {
  const id = (verticalId || 'electronics').trim() || 'electronics'
  const v = verticals.value.find((x) => x.id === id)
  if (!v) return id
  return verticalLabel(v)
}

function agentDimSpanMethod({
  row,
  rowIndex,
  columnIndex,
}: {
  row: SmartMiningRow
  rowIndex: number
  columnIndex: number
}) {
  if (columnIndex !== 0 && columnIndex !== 1 && columnIndex !== 2 && columnIndex !== 3) {
    return { rowspan: 1, colspan: 1 }
  }
  const data = agentGroupedRows.value
  const key = groupKey(row)
  if (rowIndex > 0) {
    const prev = data[rowIndex - 1]
    if (groupKey(prev) === key) return { rowspan: 0, colspan: 0 }
  }
  let span = 1
  for (let i = rowIndex + 1; i < data.length; i++) {
    if (groupKey(data[i]) !== key) break
    span += 1
  }
  return { rowspan: span, colspan: 1 }
}

async function onDeleteQueueRow(row: SmartMiningRow) {
  try {
    await ElMessageBox.confirm(
      t('governance.smartMiningDeleteConfirm', { keyword: row.canonical }),
      t('governance.smartMiningDelete'),
      {
        type: 'warning',
        confirmButtonText: t('governance.smartMiningDelete'),
        cancelButtonText: t('governance.smartMiningCancel'),
      },
    )
  } catch {
    return
  }
  deletingQueueId.value = row.id
  try {
    await deleteDictionaryReviewQueue(row.id)
    rows.value = rows.value.filter((r) => r.id !== row.id)
    agentReviewIds.value = agentReviewIds.value.filter((id) => id !== row.id)
    ElMessage.success(t('governance.smartMiningDeletedOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.smartMiningDeleteFail')}: ${msg}`)
  } finally {
    deletingQueueId.value = null
  }
}

async function onCancelAgentRecord(row: SmartMiningRow) {
  try {
    await deleteDictionaryReviewQueue(row.id)
    rows.value = rows.value.filter((r) => r.id !== row.id)
    agentReviewIds.value = agentReviewIds.value.filter((id) => id !== row.id)
    ElMessage.success(t('governance.smartMiningCancelledOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.smartMiningCancelFail')}: ${msg}`)
  }
}

async function removeKeywordByGroup(
  verticalId: string | undefined,
  dimension: SixDimension | undefined,
  keyword: string,
) {
  const target = rows.value.find(
    (r) =>
      (r.vertical_id || undefined) === (verticalId || undefined) &&
      (r.dimension_6way || undefined) === (dimension || undefined) &&
      r.canonical === keyword,
  )
  if (!target) return
  try {
    await deleteDictionaryReviewQueue(target.id)
    rows.value = rows.value.filter((r) => r.id !== target.id)
    ElMessage.success(t('governance.smartMiningCancelledOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.smartMiningCancelFail')}: ${msg}`)
  }
}

function synonymsTextByKeyword(
  verticalId: string | undefined,
  dimension: SixDimension | undefined,
  keyword: string,
) {
  const target = rows.value.find(
    (r) =>
      (r.vertical_id || undefined) === (verticalId || undefined) &&
      (r.dimension_6way || undefined) === (dimension || undefined) &&
      r.canonical === keyword,
  )
  if (!target || !target.synonyms.length) return '—'
  return target.synonyms.join(' / ')
}

function synonymsByKeyword(
  verticalId: string | undefined,
  dimension: SixDimension | undefined,
  keyword: string,
) {
  const target = rows.value.find(
    (r) =>
      (r.vertical_id || undefined) === (verticalId || undefined) &&
      (r.dimension_6way || undefined) === (dimension || undefined) &&
      r.canonical === keyword,
  )
  return target?.synonyms ?? []
}

async function removeSynonymByKeyword(
  verticalId: string | undefined,
  dimension: SixDimension | undefined,
  keyword: string,
  synonym: string,
) {
  const target = rows.value.find(
    (r) =>
      (r.vertical_id || undefined) === (verticalId || undefined) &&
      (r.dimension_6way || undefined) === (dimension || undefined) &&
      r.canonical === keyword,
  )
  if (!target) return
  const idx = target.synonyms.findIndex((s) => s === synonym)
  if (idx < 0) return
  await removeSynonym(target, idx)
}

async function bootstrapMiningStateOnMount() {
  try {
    const res = await fetchTopicDiscoveryGlobalLatest()
    const job = res.job
    if (job && (job.status === 'pending' || job.status === 'running')) {
      activeMiningJobId.value = job.id
      miningRunning.value = true
      startMiningPoll()
    }
  } catch {
    
  }
}

onBeforeUnmount(() => {
  stopMiningPoll()
})

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

function openEdit(row: SmartMiningRow) {
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
    ElMessage.warning(t('governance.smartMiningEditNeedKeyword'))
    return
  }
  const syns = parseSynonymsFromTextarea(editSynonymsText.value)
  if (syns.length === 0) {
    ElMessage.warning(t('governance.smartMiningEditNeedSynonym'))
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
    ElMessage.success(t('governance.smartMiningEditSavedOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.smartMiningQueueSyncFail')}: ${msg}`)
  } finally {
    editSubmitting.value = false
  }
}

async function removeSynonym(row: SmartMiningRow, index: number) {
  const next = row.synonyms.filter((_, i) => i !== index)
  if (next.length === 0) {
    try {
      await deleteDictionaryReviewQueue(row.id)
      rows.value = rows.value.filter((r) => r.id !== row.id)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      ElMessage.error(`${t('governance.smartMiningQueueSyncFail')}: ${msg}`)
    }
    return
  }
  try {
    await patchDictionaryReviewQueue(row.id, { canonical: row.canonical, synonyms: next })
    row.synonyms = next
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.smartMiningQueueSyncFail')}: ${msg}`)
  }
}

function queueRowVerticalId(row: SmartMiningRow): string {
  const v = (row.vertical_id || '').trim()
  return v || 'electronics'
}

function openApprove(row: SmartMiningRow) {
  if (row.synonyms.length === 0) return
  pendingRow.value = row

  approveDimension.value = row.dimension_6way ?? ''
  approveVisible.value = true
}

async function confirmApprove() {
  const row = pendingRow.value
  const dim = approveDimension.value
  if (!row || !dim) return
  if (!row.dimension_6way) {
    ElMessage.warning(t('governance.smartMiningNeedAgentDimension'))
    return
  }
  approveSubmitting.value = true
  try {
    await postDictionaryApproveEntry({
      vertical_ids: [queueRowVerticalId(row)],
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
    ElMessage.success(t('governance.smartMiningApprovedOk'))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.smartMiningApproveFail')}: ${msg}`)
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
    ElMessage.warning(t('governance.smartMiningVerticalsLoadFail'))
  }
}

function normalizeKind(raw: unknown): SmartMiningRow['kind'] {
  const s = String(raw ?? '').trim().toLowerCase()
  if (s === 'existing') return 'existing'
  if (s === 'rejected') return 'rejected'
  return 'new_discovery'
}

function smartMiningTypeTag(kind: SmartMiningRow['kind']): 'warning' | 'success' | 'danger' {
  if (kind === 'existing') return 'success'
  if (kind === 'rejected') return 'danger'
  return 'warning'
}

function smartMiningTypeLabel(kind: SmartMiningRow['kind']): string {
  if (kind === 'existing') return t('governance.smartMiningTypeExisting')
  if (kind === 'rejected') return t('governance.smartMiningTypeRejected')
  return t('governance.smartMiningTypeNew')
}

function mapQueueItem(raw: DictionaryReviewQueueItem): SmartMiningRow {
  const dimRaw = raw.dimension_6way
  const dimension_6way =
    dimRaw && (SIX_DIMENSIONS as readonly string[]).includes(dimRaw) ? (dimRaw as SixDimension) : undefined
  return {
    id: String(raw.id),
    kind: normalizeKind(raw.kind),
    canonical: String(raw.canonical ?? '').trim(),
    synonyms: Array.isArray(raw.synonyms) ? raw.synonyms.map((s) => String(s).trim()).filter(Boolean) : [],
    vertical_id: String(raw.vertical_id ?? 'electronics').trim() || 'electronics',
    dimension_6way,
    batch_id: raw.batch_id ?? undefined,
    source_topic_id: raw.source_topic_id ?? undefined,
    quality_score: typeof raw.quality_score === 'number' ? raw.quality_score : undefined,
    created_at: raw.created_at ?? undefined,
    updated_at: raw.updated_at ?? undefined,
  }
}

async function loadReviewQueue() {
  try {
    const [res, records] = await Promise.all([
      fetchDictionaryReviewQueue(),
      fetchDictionaryReviewRecords(300),
    ])
    rows.value = (res.items ?? []).map(mapQueueItem).filter((r) => r.canonical.length > 0)
    const currentIds = new Set(rows.value.map((r) => r.id))
    const reviewedIds = (records.items ?? [])
      .map((x) => String(x.review_queue_id || '').trim())
      .filter((id) => id.length > 0 && currentIds.has(id))
    agentReviewIds.value = Array.from(new Set(reviewedIds)).filter((id) => {
      const r = rows.value.find((x) => x.id === id)
      return !!r && r.kind !== 'rejected'
    })
  } catch {
    rows.value = []
    agentReviewIds.value = []
    ElMessage.warning(t('governance.smartMiningQueueLoadFail'))
  }
}

async function onRefresh() {
  await loadVerticals()
  await loadReviewQueue()
  ElMessage.success(t('governance.refreshed'))
}

onMounted(async () => {
  await loadVerticals()
  await loadReviewQueue()
  void bootstrapMiningStateOnMount()
})
</script>

<style scoped>
.config-block {
  padding: 18px 20px 20px;
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.agent-review-block {
  margin-top: 14px;
}

.agent-review-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.3;
}

.agent-review-intro {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  line-height: 1.55;
}

.agent-review-toolbar {
  margin-top: 14px;
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

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-right :deep(.el-button) {
  margin-inline: 0;
}

.toolbar-left :deep(.el-button) {
  margin-inline: 0;
}

.toolbar-refresh-square {
  width: var(--el-component-size);
  min-width: var(--el-component-size);
  height: var(--el-component-size);
  padding: 0;
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

.kw-popover-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.kw-popover-content {
  line-height: 1.5;
  color: var(--el-text-color-primary);
  word-break: break-word;
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
