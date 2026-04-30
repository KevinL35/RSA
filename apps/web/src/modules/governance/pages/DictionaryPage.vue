<template>
  <div v-loading="loading">
    <section class="config-block config-block--intro">
      <div class="intro-head">
        <h2 class="page-title">{{ t('governance.dictionaryTitle') }}</h2>
        <div class="intro-head-right">
          <el-select
            v-model="verticalId"
            class="dict-vertical-select"
            teleported
            placement="bottom-start"
            :fallback-placements="selectFallbackPlacementsBottom"
            :popper-options="selectPopperOptionsNoFlip"
            @change="onVerticalChange"
          >
            <el-option
              v-for="v in verticals"
              :key="v.id"
              :label="verticalLabel(v)"
              :value="v.id"
            />
          </el-select>
          <el-button type="primary" class="dict-modify-btn" @click="openDictionaryModify">
            {{ t('governance.dictionaryModify') }}
          </el-button>
        </div>
      </div>
      <p class="intro-text">{{ t('governance.dictionaryDesc') }}</p>
    </section>

    <el-empty v-if="!loading && (loadError || !preview)" :description="emptyDescription">
      <el-button type="primary" @click="retryDictionaryPage">{{ t('governance.dictionaryPreviewRetry') }}</el-button>
    </el-empty>

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
      v-model="dictionaryModifyVisible"
      :title="t('governance.dictionaryModify')"
      width="600px"
      class="dict-upload-dialog"
      destroy-on-close
      align-center
      @closed="resetDictionaryUploadForm"
    >
      <p class="dict-upload-intro">{{ t('governance.dictionaryModifyIntro') }}</p>

      <h4 class="dict-modify-section-title">{{ t('governance.dictionaryModifyDownloadSection') }}</h4>
      <p class="dict-modify-current-category">
        {{ t('governance.dictionaryModifyCurrentCategory', { name: currentVerticalDisplayName }) }}
      </p>
      <div class="dict-upload-form">
        <div
          class="upload-file-zone dict-download-zone"
          :class="{ 'dict-download-zone--loading': exportDownloadLoading }"
          role="button"
          tabindex="0"
          @click="onExportCurrentFromDialog"
          @keydown.enter.prevent="onExportCurrentFromDialog"
          @keydown.space.prevent="onExportCurrentFromDialog"
        >
          <div class="upload-file-trigger-row dict-download-trigger">
            <span
              class="upload-file-status"
              :class="{ 'upload-file-status--placeholder': !exportDownloadLoading }"
            >
              {{
                exportDownloadLoading
                  ? t('governance.dictionaryModifyDownloadLoading')
                  : t('governance.dictionaryModifyDownloadClick')
              }}
            </span>
          </div>
        </div>
        <p class="upload-file-hint">{{ t('governance.dictionaryModifyDownloadHint') }}</p>
      </div>

      <el-divider />

      <h4 class="dict-modify-section-title">{{ t('governance.dictionaryModifyUploadSection') }}</h4>
      <p class="dict-upload-subhint">{{ t('governance.dictionaryModifyUploadHint') }}</p>
      <div class="dict-upload-form">
        <div class="upload-file-zone">
          <el-upload
            ref="dictionaryExcelRef"
            class="upload-file-inner"
            :auto-upload="false"
            :limit="1"
            :show-file-list="false"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            :on-change="onDictionaryExcelChange"
            :on-exceed="onDictionaryExcelExceed"
          >
            <div class="upload-file-trigger-row">
              <span
                class="upload-file-status"
                :class="{ 'upload-file-status--placeholder': !dictionaryExcelFile }"
              >
                {{ dictionaryExcelDisplayName }}
              </span>
            </div>
          </el-upload>
        </div>
        <p class="upload-file-hint">{{ t('governance.dictionaryExcelFileHint') }}</p>
      </div>
      <template #footer>
        <el-button @click="dictionaryModifyVisible = false">{{ t('insight.dialogCancel') }}</el-button>
        <el-button type="primary" :loading="dictionaryImportSubmitting" @click="submitDictionaryImport">
          {{ t('governance.dictionaryExcelStartImport') }}
        </el-button>
      </template>
    </el-dialog>

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
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { genFileId } from 'element-plus'
import type { UploadFile, UploadInstance, UploadRawFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import type { DictionaryVerticalItem, TaxonomyPreviewEntry, TaxonomyPreviewResponse } from '../../dictionary/api'
import {
  fetchDictionaryVerticals,
  fetchTaxonomyPreview,
  postDictionaryImportExcel,
  postDictionaryRejectSynonym,
} from '../../dictionary/api'
import { downloadDictionaryAsExcel } from '../../../shared/utils/excelDownload'
import {
  SELECT_FALLBACK_PLACEMENTS_BOTTOM,
  selectPopperOptionsNoFlip,
} from '../../../shared/ui/elementSelectPlacement'

const { t, locale } = useI18n()

const selectFallbackPlacementsBottom = SELECT_FALLBACK_PLACEMENTS_BOTTOM

const loading = ref(true)
const loadError = ref(false)
const verticals = ref<DictionaryVerticalItem[]>([])
const verticalId = ref('electronics')
const preview = ref<TaxonomyPreviewResponse | null>(null)

const DICTIONARY_IMPORT_MAX_BYTES = 10 * 1024 * 1024

const dictionaryModifyVisible = ref(false)
const exportDownloadLoading = ref(false)
const dictionaryExcelFile = ref<File | null>(null)
const dictionaryExcelRef = ref<UploadInstance | null>(null)
const dictionaryImportSubmitting = ref(false)

const rejectDialogVisible = ref(false)
const rejectSubmitting = ref(false)
const pendingReject = ref<{
  dimension: string
  canonical: string
  alias: string
} | null>(null)

const emptyDescription = computed(() =>
  loadError.value ? t('governance.dictionaryLoadFail') : t('governance.dictionaryPreviewEmpty'),
)

const currentVerticalDisplayName = computed(() => {
  const v = verticals.value.find((x) => x.id === verticalId.value)
  return v ? verticalLabel(v) : verticalId.value
})

function openDictionaryModify() {
  dictionaryModifyVisible.value = true
}

async function retryDictionaryPage() {
  loadError.value = false
  preview.value = null
  await loadVerticals()
  await loadPreview()
}

const dimensionTitle = (dim: string) => {
  const key = `governance.dim_${dim}` as const
  const translated = t(key)
  return translated === key ? dim : translated
}

const dictionaryExcelDisplayName = computed(() =>
  dictionaryExcelFile.value?.name ?? t('insight.uploadFileClickToChoose'),
)

function resetDictionaryUploadForm() {
  dictionaryExcelFile.value = null
  dictionaryExcelRef.value?.clearFiles()
}

function onDictionaryExcelChange(uploadFile: UploadFile) {
  const raw = uploadFile.raw as UploadRawFile | undefined
  if (!raw) return
  if (raw.size > DICTIONARY_IMPORT_MAX_BYTES) {
    ElMessage.error(t('insight.uploadFileTooLarge'))
    dictionaryExcelRef.value?.clearFiles()
    dictionaryExcelFile.value = null
    return
  }
  const name = (raw.name || '').toLowerCase()
  if (!name.endsWith('.xlsx')) {
    ElMessage.error(t('governance.dictionaryExcelNeedFile'))
    dictionaryExcelRef.value?.clearFiles()
    dictionaryExcelFile.value = null
    return
  }
  dictionaryExcelFile.value = raw as File
}

function onDictionaryExcelExceed(files: File[]) {
  const f = files[0]
  if (!f) return
  dictionaryExcelRef.value?.clearFiles()
  const raw = f as UploadRawFile
  Object.assign(raw, { uid: genFileId() })
  dictionaryExcelRef.value?.handleStart(raw)
}

async function onExportCurrentFromDialog() {
  if (exportDownloadLoading.value) return
  const vid = verticalId.value
  exportDownloadLoading.value = true
  try {
    const p = await fetchTaxonomyPreview(vid)
    const v = verticals.value.find((x) => x.id === vid)
    const label = v ? verticalLabel(v) : vid
    const n = flattenEntryCount(p)
    await downloadDictionaryAsExcel(label, p)
    ElMessage.success(t('governance.dictionaryExcelExportOk', { n }))
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(msg)
  } finally {
    exportDownloadLoading.value = false
  }
}

function flattenEntryCount(p: TaxonomyPreviewResponse): number {
  let n = 0
  for (const dim of p.dimension_order) {
    n += p.dimensions[dim]?.entries?.length ?? 0
  }
  return n
}

async function submitDictionaryImport() {
  const f = dictionaryExcelFile.value
  if (!f) {
    ElMessage.warning(t('governance.dictionaryExcelNeedFile'))
    return
  }
  dictionaryImportSubmitting.value = true
  try {
    const res = await postDictionaryImportExcel(verticalId.value, f)
    const w = res.warnings?.filter(Boolean) ?? []
    if (w.length) {
      ElMessage.warning(w.slice(0, 3).join('；'))
    }
    ElMessage.success(t('governance.dictionaryExcelOk', { n: res.imported }))
    dictionaryModifyVisible.value = false
    resetDictionaryUploadForm()
    await loadPreview()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ElMessage.error(`${t('governance.dictionaryExcelFail')}: ${msg}`)
  } finally {
    dictionaryImportSubmitting.value = false
  }
}

function verticalLabel(v: DictionaryVerticalItem) {
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
.config-block {
  margin-bottom: 28px;
  padding: 18px 20px 20px;
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.config-block--intro {
  /* 与接口配置 ApiConfigPage 顶部模块一致 */
  padding: 16px 20px;
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
  /* 与评论洞察「添加商品」等默认按钮视觉宽度同档（约 90～110px） */
  --dict-head-control-width: 100px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 10px;
}

.dict-modify-btn {
  flex-shrink: 0;
  width: var(--dict-head-control-width);
  box-sizing: border-box;
}

.dict-modify-section-title {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.dict-modify-current-category {
  margin: 0 0 14px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
}

.dict-download-zone {
  cursor: pointer;
}

.dict-download-zone--loading {
  cursor: wait;
  pointer-events: none;
  opacity: 0.88;
}

.dict-download-trigger {
  min-height: 22px;
}

.dict-upload-subhint {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.dict-vertical-select {
  width: var(--dict-head-control-width);
  flex-shrink: 0;
}

.dict-vertical-select :deep(.el-select__wrapper) {
  width: 100%;
  box-sizing: border-box;
}

.intro-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
}

.dict-upload-intro {
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.dict-upload-form {
  margin-top: 4px;
}

.upload-file-section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
}

.upload-file-zone {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  padding: 8px 14px;
  background: var(--el-fill-color-blank);
  transition:
    border-color 0.28s ease,
    box-shadow 0.28s ease,
    background-color 0.28s ease;
}

.upload-file-zone:hover,
.upload-file-zone:focus-within {
  border-color: var(--el-color-primary-light-3);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
  background-color: var(--el-color-primary-light-9);
}

.upload-file-inner :deep(.el-upload) {
  display: block;
  width: auto;
}

.upload-file-trigger-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 10px;
  cursor: pointer;
  min-height: 22px;
}

.upload-file-status {
  font-size: 14px;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.upload-file-zone .upload-file-status--placeholder {
  color: var(--el-color-primary);
}

.upload-file-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
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
