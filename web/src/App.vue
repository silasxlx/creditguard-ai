<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  ApiError,
  createCase,
  createRun,
  exportReport,
  getCase,
  getFacts,
  getReport,
  getResults,
  getRun,
  health,
  listCases,
  retryRun,
  seedDemo,
  submitFactReview,
  submitReportReview,
  uploadDocument,
} from './api'
import type {
  CaseDetail,
  CaseSummary,
  DemoRole,
  DocumentType,
  FactReviewView,
  ReportResponse,
  ReviewResults,
  RunSummary,
} from './types'

const route = useRoute()
const router = useRouter()

const role = ref<DemoRole>('RM')
const userId = computed(() => role.value === 'RM' ? 'demo-rm' : 'demo-reviewer')
const cases = ref<CaseSummary[]>([])
const serviceStatus = ref('连接检查中')
const loading = ref(false)
const detailLoading = ref(false)
const activeCase = ref<CaseDetail | null>(null)
const activeRun = ref<RunSummary | null>(null)
const facts = ref<FactReviewView | null>(null)
const results = ref<ReviewResults | null>(null)
const report = ref<ReportResponse | null>(null)
const errorMessage = ref('')
let pollTimer: number | undefined

const routeName = computed(() => String(route.name ?? 'dashboard'))
const currentRunId = computed(() => String(route.params.runId ?? ''))
const currentCaseId = computed(() => String(route.params.caseId ?? ''))
const isReviewer = computed(() => role.value === 'REVIEWER')
const isRunActive = computed(() => Boolean(activeRun.value && [
  'QUEUED',
  'RUNNING',
  'WAITING_FACT_REVIEW',
  'WAITING_REPORT_REVIEW',
].includes(activeRun.value.status)))

const statusLabels: Record<string, string> = {
  QUEUED: '排队中',
  RUNNING: '处理中',
  WAITING_FACT_REVIEW: '等待事实复核',
  WAITING_REPORT_REVIEW: '等待报告确认',
  PAUSED_RETRYABLE: '可重试暂停',
  COMPLETED: '已完成',
  RETURNED: '已退回',
  FAILED_FINAL: '最终失败',
}

const documentLabels: Record<DocumentType, string> = {
  BUSINESS_LICENSE: '营业执照',
  CREDIT_APPLICATION: '授信申请书',
  DUE_DILIGENCE: '尽调报告',
  FINANCIAL_STATEMENTS: '财务报表',
}

const createForm = reactive({
  case_no: 'CASE-DEMO-MANUAL-001',
  customer_name: '',
  customer_key: '',
  review_date: new Date().toISOString().slice(0, 10),
})
const selectedFiles = reactive<Record<DocumentType, File | undefined>>({
  BUSINESS_LICENSE: undefined,
  CREDIT_APPLICATION: undefined,
  DUE_DILIGENCE: undefined,
  FINANCIAL_STATEMENTS: undefined,
})
const factSelections = reactive<Record<string, string>>({})
const factReasons = reactive<Record<string, string>>({})
const reportReason = ref('')

function statusLabel(status: string): string {
  return statusLabels[status] ?? status
}

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'COMPLETED') return 'success'
  if (status === 'FAILED_FINAL') return 'danger'
  if (status === 'WAITING_FACT_REVIEW' || status === 'WAITING_REPORT_REVIEW' || status === 'PAUSED_RETRYABLE') {
    return 'warning'
  }
  return 'info'
}

function outcomeType(outcome: string): 'success' | 'warning' | 'danger' | 'info' {
  if (outcome === 'COMPLIANT' || outcome === 'PASS') return 'success'
  if (outcome === 'NON_COMPLIANT' || outcome === 'FAIL') return 'danger'
  if (outcome === 'NEEDS_REVIEW' || outcome === 'WARN') return 'warning'
  return 'info'
}

function safeJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

function go(path: string): void {
  void router.push(path)
}

function handleRoleChange(value: string | number | boolean | undefined): void {
  if (value !== 'RM' && value !== 'REVIEWER') return
  role.value = value
  void loadCases()
}

async function loadCases(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    cases.value = (await listCases(userId.value)).items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function loadCase(caseId: string): Promise<void> {
  if (!caseId) return
  detailLoading.value = true
  try {
    activeCase.value = await getCase(caseId, userId.value)
    activeRun.value = activeCase.value.runs[0] ?? null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    detailLoading.value = false
  }
}

async function loadRun(runId: string): Promise<void> {
  if (!runId) return
  try {
    activeRun.value = await getRun(runId, userId.value)
    if (activeCase.value && activeCase.value.id === activeRun.value.case_id) {
      const index = activeCase.value.runs.findIndex((item) => item.id === activeRun.value?.id)
      if (index >= 0) activeCase.value.runs[index] = activeRun.value
    }
    if (activeRun.value.case_id && (!activeCase.value || activeCase.value.id !== activeRun.value.case_id)) {
      await loadCase(activeRun.value.case_id)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  }
}

async function loadRouteData(): Promise<void> {
  errorMessage.value = ''
  if (routeName.value === 'dashboard') {
    await loadCases()
    return
  }
  if (routeName.value === 'case-detail') {
    await loadCase(currentCaseId.value)
    startPollingIfNeeded()
    return
  }
  if (currentRunId.value) await loadRun(currentRunId.value)
  if (routeName.value === 'run-facts' && isReviewer.value) {
    try {
      facts.value = await getFacts(currentRunId.value, userId.value)
      facts.value.conflicts.forEach((conflict) => {
        const selected = conflict.candidates.find((candidate) => (
          candidate.selected
          || (conflict.selected_value !== null && candidate.normalized_value === conflict.selected_value)
        ))
        factSelections[conflict.conflict_id] = selected?.evidence_id ?? conflict.candidates[0]?.evidence_id ?? ''
      })
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : String(error)
    }
  }
  if (routeName.value === 'run-results' && isReviewer.value) {
    try {
      results.value = await getResults(currentRunId.value, userId.value)
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 409)) {
        errorMessage.value = error instanceof Error ? error.message : String(error)
      }
    }
  }
  if (routeName.value === 'run-report') {
    try {
      report.value = await getReport(currentRunId.value, userId.value)
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : String(error)
    }
  }
  startPollingIfNeeded()
}

function startPollingIfNeeded(): void {
  if (pollTimer !== undefined) window.clearInterval(pollTimer)
  const runId = currentRunId.value || activeRun.value?.id || ''
  if (!runId || !isRunActive.value) return
  pollTimer = window.setInterval(async () => {
    await loadRun(runId)
    if (!isRunActive.value) {
      window.clearInterval(pollTimer)
      pollTimer = undefined
      await loadRouteData()
    }
  }, 2500)
}

async function seed(scenarioId: string): Promise<void> {
  loading.value = true
  try {
    const response = await seedDemo(userId.value, scenarioId)
    ElMessage.success(response.created ? '演示案件已创建' : '已复用同一演示案件')
    await loadCases()
    go('/cases/' + response.case_id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

function onFileChange(documentType: DocumentType, event: Event): void {
  const input = event.target as HTMLInputElement
  selectedFiles[documentType] = input.files?.[0]
}

async function createManualCase(): Promise<void> {
  if (!createForm.customer_name || !createForm.customer_key) {
    ElMessage.warning('请填写客户名称和客户标识')
    return
  }
  const missing = (Object.keys(documentLabels) as DocumentType[]).filter((type) => !selectedFiles[type])
  if (missing.length) {
    ElMessage.warning('请上传四类必需材料：' + missing.map((type) => documentLabels[type]).join('、'))
    return
  }
  loading.value = true
  try {
    const created = await createCase(userId.value, createForm)
    const uploadedIds: string[] = []
    for (const type of Object.keys(documentLabels) as DocumentType[]) {
      const file = selectedFiles[type]
      if (!file) continue
      const document = await uploadDocument(created.id, userId.value, type, file)
      uploadedIds.push(document.id)
    }
    const refreshed = await getCase(created.id, userId.value)
    const run = await createRun(created.id, userId.value, uploadedIds, refreshed.version)
    ElMessage.success('案件已创建并启动审查')
    go('/cases/' + created.id)
    activeRun.value = run
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

async function startCaseRun(caseData: CaseDetail): Promise<void> {
  const activeDocuments = caseData.documents.filter((document) => document.active)
  if (activeDocuments.length < 4) {
    ElMessage.warning('至少需要四类有效材料后才能启动审查')
    return
  }
  try {
    activeRun.value = await createRun(caseData.id, userId.value, activeDocuments.map((item) => item.id), caseData.version)
    await loadCase(caseData.id)
    ElMessage.success('审查任务已提交')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

async function retryCurrentRun(): Promise<void> {
  if (!activeRun.value) return
  try {
    activeRun.value = await retryRun(activeRun.value.id, userId.value)
    ElMessage.success('已重新提交任务')
    await loadRouteData()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

async function submitFacts(): Promise<void> {
  if (!facts.value) return
  const decisions = facts.value.conflicts.map((conflict) => ({
    conflict_id: conflict.conflict_id,
    action: 'SELECT_SOURCE' as const,
    selected_evidence_id: factSelections[conflict.conflict_id],
    reason: factReasons[conflict.conflict_id] ?? 'Reviewer依据材料证据裁定',
  }))
  if (decisions.some((decision) => !decision.selected_evidence_id || !decision.reason.trim())) {
    ElMessage.warning('每个矛盾项都必须选择证据并填写裁定原因')
    return
  }
  try {
    await submitFactReview(currentRunId.value, userId.value, {
      expected_snapshot_version: facts.value.snapshot_version,
      decisions,
    })
    ElMessage.success('事实裁定已提交，工作流继续运行')
    await loadRouteData()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

async function reviewReport(action: 'CONFIRM_DRAFT' | 'RETURN_FOR_RERUN'): Promise<void> {
  if (!report.value) return
  if (action === 'RETURN_FOR_RERUN' && !reportReason.value.trim()) {
    ElMessage.warning('退回报告时必须填写原因')
    return
  }
  if (action === 'CONFIRM_DRAFT') {
    await ElMessageBox.confirm('确认这是已复核的AI辅助审查草稿，不代表授信审批通过？', '报告确认', {
      type: 'warning',
      confirmButtonText: '确认报告',
      cancelButtonText: '取消',
    })
  }
  try {
    await submitReportReview(currentRunId.value, userId.value, {
      expected_snapshot_version: report.value.snapshot_version,
      action,
      reason: reportReason.value,
    })
    ElMessage.success(action === 'CONFIRM_DRAFT' ? '报告已确认' : '报告已退回重跑')
    reportReason.value = ''
    await loadRouteData()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

async function downloadReport(): Promise<void> {
  try {
    await exportReport(currentRunId.value, userId.value)
    ElMessage.success('Markdown报告已下载')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

onMounted(async () => {
  try {
    const result = await health()
    serviceStatus.value = result.service + ' · ' + result.version + ' · ' + result.status
  } catch {
    serviceStatus.value = 'API未连接'
  }
  await loadRouteData()
})

watch([() => route.fullPath, () => role.value], () => {
  void loadRouteData()
})

onUnmounted(() => {
  if (pollTimer !== undefined) window.clearInterval(pollTimer)
})
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div class="brand" role="button" tabindex="0" @click="go('/')" @keydown.enter="go('/')">
        <div class="brand-mark">CG</div>
        <div>
          <p class="eyebrow">CREDITGUARD AI · POC</p>
          <h1>授信智能合规审查工作台</h1>
        </div>
      </div>
      <div class="topbar-actions">
        <span class="service-pill"><span class="status-dot" />{{ serviceStatus }}</span>
        <el-select :model-value="role" class="role-select" size="large" @change="handleRoleChange">
          <el-option label="RM · 客户经理" value="RM" />
          <el-option label="Reviewer · 审查员" value="REVIEWER" />
        </el-select>
      </div>
    </header>

    <div class="workspace">
      <aside class="sidebar">
        <nav aria-label="主导航">
          <button :class="['nav-item', { active: routeName === 'dashboard' }]" @click="go('/')">案件总览</button>
          <button v-if="isReviewer" :class="['nav-item', { active: routeName === 'run-facts' }]" @click="(currentRunId || activeRun?.id) && go('/runs/' + (currentRunId || activeRun?.id) + '/facts')">事实复核</button>
          <button v-if="isReviewer" :class="['nav-item', { active: routeName === 'run-results' }]" @click="(currentRunId || activeRun?.id) && go('/runs/' + (currentRunId || activeRun?.id) + '/results')">规则与风险</button>
          <button :class="['nav-item', { active: routeName === 'run-report' }]" @click="(currentRunId || activeRun?.id) && go('/runs/' + (currentRunId || activeRun?.id) + '/report')">报告复核</button>
        </nav>
        <div class="sidebar-note">
          <span class="label">当前身份</span>
          <strong>{{ role === 'RM' ? 'demo-rm' : 'demo-reviewer' }}</strong>
          <p>所有案件与材料均为合成演示数据。</p>
        </div>
      </aside>

      <section class="content-area">
        <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon closable @close="errorMessage = ''" />

        <template v-if="routeName === 'dashboard'">
          <div class="page-heading">
            <div>
              <p class="eyebrow">工作台 / 案件总览</p>
              <h2>把材料、制度与审查结论放在同一条证据链上</h2>
              <p class="muted">PoC提供两条固定演示路径，也支持RM手工上传PDF、DOCX和XLSX材料。</p>
            </div>
            <el-button v-if="role === 'RM'" type="primary" size="large" @click="go('/cases/new')">新建案件</el-button>
          </div>

          <div class="demo-grid">
            <article class="demo-card normal">
              <div class="demo-card-top"><el-tag type="success">正常路径</el-tag><span>DEMO-NORMAL-001</span></div>
              <h3>星海演示科技有限公司</h3>
              <p>申请期限24个月，无实质冲突，自动进入报告复核。</p>
              <el-button type="success" plain :loading="loading" @click="seed('DEMO-NORMAL-001')">创建正常演示</el-button>
            </article>
            <article class="demo-card high">
              <div class="demo-card-top"><el-tag type="danger">高风险路径</el-tag><span>DEMO-HIGH-001</span></div>
              <h3>远山演示制造有限公司</h3>
              <p>申请书24个月、尽调报告48个月，裁定后命中R07期限规则。</p>
              <el-button type="danger" plain :loading="loading" @click="seed('DEMO-HIGH-001')">创建高风险演示</el-button>
            </article>
          </div>

          <section class="panel">
            <div class="panel-heading">
              <div><span class="label">案件池</span><h3>最近案件</h3></div>
              <div class="heading-actions"><el-tag>{{ cases.length }} 个案件</el-tag><el-button text @click="loadCases">刷新</el-button></div>
            </div>
            <el-table v-loading="loading" :data="cases" stripe empty-text="暂无案件">
              <el-table-column prop="case_no" label="案件编号" min-width="190" />
              <el-table-column prop="customer_name" label="客户名称" min-width="220" />
              <el-table-column prop="review_date" label="审查日期" width="130" />
              <el-table-column prop="version" label="版本" width="80" />
              <el-table-column prop="created_by" label="创建人" width="130" />
              <el-table-column label="操作" width="110" fixed="right">
                <template #default="scope"><el-button link type="primary" @click="go('/cases/' + scope.row.id)">查看</el-button></template>
              </el-table-column>
            </el-table>
          </section>
        </template>

        <template v-else-if="routeName === 'case-new'">
          <div class="page-heading"><div><p class="eyebrow">案件 / 新建</p><h2>创建一次可追溯的授信审查</h2><p class="muted">上传四类材料后，系统会生成新的材料版本并启动独立Run。</p></div><el-button @click="go('/')">返回总览</el-button></div>
          <section class="panel form-panel">
            <el-form label-position="top" @submit.prevent="createManualCase">
              <div class="form-grid">
                <el-form-item label="案件编号"><el-input v-model="createForm.case_no" /></el-form-item>
                <el-form-item label="审查日期"><el-date-picker v-model="createForm.review_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
                <el-form-item label="客户名称"><el-input v-model="createForm.customer_name" placeholder="例如：华东演示科技有限公司" /></el-form-item>
                <el-form-item label="客户标识"><el-input v-model="createForm.customer_key" placeholder="例如：SYNTH-MANUAL-001" /></el-form-item>
              </div>
              <div class="upload-grid">
                <label v-for="(label, type) in documentLabels" :key="type" class="upload-box">
                  <span class="label">{{ label }}</span><strong>{{ selectedFiles[type]?.name ?? '选择文件' }}</strong><small>仅支持 PDF / DOCX / XLSX，单文件20MB以内</small>
                  <input type="file" accept=".pdf,.docx,.xlsx" @change="onFileChange(type, $event)" />
                </label>
              </div>
              <div class="form-actions"><el-button @click="go('/')">取消</el-button><el-button :loading="loading" type="primary" native-type="submit">创建并启动审查</el-button></div>
            </el-form>
          </section>
        </template>

        <template v-else-if="routeName === 'case-detail'">
          <div class="page-heading"><div><p class="eyebrow">案件 / {{ activeCase?.case_no ?? currentCaseId }}</p><h2>{{ activeCase?.customer_name ?? '案件详情' }}</h2><p class="muted">客户标识：{{ activeCase?.customer_key }} · 当前版本：{{ activeCase?.version }}</p></div><el-button @click="go('/')">返回总览</el-button></div>
          <el-skeleton v-if="detailLoading" :rows="6" animated />
          <template v-else-if="activeCase">
            <section class="panel">
              <div class="panel-heading"><div><span class="label">材料版本</span><h3>案件输入</h3></div><el-button v-if="role === 'RM'" type="primary" @click="startCaseRun(activeCase)">启动新审查</el-button></div>
              <el-table :data="activeCase.documents" stripe empty-text="尚未上传材料">
                <el-table-column prop="document_type" label="类型" min-width="150"><template #default="scope">{{ documentLabels[scope.row.document_type as DocumentType] ?? scope.row.document_type }}</template></el-table-column>
                <el-table-column prop="original_filename" label="文件名" min-width="220" />
                <el-table-column prop="version" label="版本" width="80" />
                <el-table-column prop="status" label="解析状态" width="120" />
                <el-table-column label="有效" width="80"><template #default="scope"><el-tag :type="scope.row.active ? 'success' : 'info'">{{ scope.row.active ? '是' : '否' }}</el-tag></template></el-table-column>
              </el-table>
            </section>
            <section class="panel">
              <div class="panel-heading"><div><span class="label">审查Run</span><h3>工作流进度</h3></div></div>
              <el-empty v-if="!activeCase.runs.length" description="尚未启动审查" />
              <div v-for="run in activeCase.runs" :key="run.id" class="run-row">
                <div class="run-main"><strong>{{ run.id.slice(0, 12) }}</strong><span>{{ run.stage }}</span><el-tag :type="statusType(run.status)">{{ statusLabel(run.status) }}</el-tag></div>
                <el-progress :percentage="run.progress_percent" :status="run.status === 'FAILED_FINAL' ? 'exception' : undefined" />
                <div class="run-actions"><el-button link @click="go('/runs/' + run.id + '/results')">查看结果</el-button><el-button link type="primary" @click="go('/runs/' + run.id + '/report')">报告</el-button><el-button v-if="run.retryable && role === 'REVIEWER'" link type="warning" @click="activeRun = run; retryCurrentRun">重试</el-button></div>
              </div>
            </section>
          </template>
        </template>

        <template v-else-if="routeName === 'run-facts'">
          <div class="page-heading"><div><p class="eyebrow">审查Run / HITL-1</p><h2>事实冲突裁定</h2><p class="muted">只有缺件、实质冲突或事实不可用时才会进入此关口。每次裁定都会记录证据、原因和快照版本。</p></div><el-button @click="go('/runs/' + currentRunId + '/results')">查看规则结果</el-button></div>
          <el-alert v-if="!isReviewer" title="当前角色没有事实裁定权限，请切换为Reviewer。" type="warning" show-icon />
          <template v-else-if="facts">
            <section class="panel"><div class="panel-heading"><div><span class="label">待处理项</span><h3>{{ facts.conflicts.length }} 个冲突 · 快照 v{{ facts.snapshot_version }}</h3></div><el-tag :type="facts.requires_review ? 'warning' : 'success'">{{ facts.requires_review ? '需要裁定' : '无需裁定' }}</el-tag></div>
              <el-empty v-if="!facts.conflicts.length" description="当前没有实质冲突" />
              <article v-for="conflict in facts.conflicts" :key="conflict.conflict_id" class="conflict-card">
                <div class="conflict-heading"><div><span class="label">{{ conflict.field_name }} · {{ conflict.field }}</span><h3>{{ conflict.comparison }}</h3></div><el-tag :type="conflict.material ? 'danger' : 'warning'">{{ conflict.material ? '实质冲突' : '提示' }}</el-tag></div>
                <el-radio-group v-model="factSelections[conflict.conflict_id]" class="candidate-list">
                  <label v-for="candidate in conflict.candidates" :key="candidate.evidence_id" class="candidate"><el-radio :value="candidate.evidence_id"><span class="candidate-value">{{ candidate.normalized_value ?? candidate.raw_value }}</span><span class="candidate-source">{{ candidate.source }} · {{ candidate.locator?.page ? '第' + candidate.locator.page + '页' : candidate.evidence_id }}</span></el-radio></label>
                </el-radio-group>
                <el-input v-model="factReasons[conflict.conflict_id]" type="textarea" :rows="2" placeholder="填写裁定原因（必填）" />
              </article>
              <div class="form-actions"><el-button type="primary" :loading="loading" @click="submitFacts">提交事实裁定并继续</el-button></div>
            </section>
          </template>
        </template>

        <template v-else-if="routeName === 'run-results'">
          <div class="page-heading"><div><p class="eyebrow">审查Run / 规则与证据</p><h2>把每条结论拆回事实、规则和制度依据</h2><p class="muted">LLM只负责解释；确定性判断由规则和程序计算完成。</p></div><el-button type="primary" @click="go('/runs/' + currentRunId + '/report')">打开报告复核</el-button></div>
          <el-alert v-if="!isReviewer" title="规则与风险详情仅对Reviewer开放。" type="warning" show-icon />
          <template v-else-if="results">
            <div class="metric-grid"><div class="metric-card"><span class="label">综合结论</span><el-tag size="large" :type="outcomeType(results.summary_outcome)">{{ results.summary_outcome }}</el-tag></div><div class="metric-card"><span class="label">规则数</span><strong>{{ results.rules.length }}</strong></div><div class="metric-card"><span class="label">风险项</span><strong>{{ results.risks.length }}</strong></div><div class="metric-card"><span class="label">事实快照</span><strong>v{{ results.fact_snapshot_version }}</strong></div></div>
            <section class="panel"><div class="panel-heading"><div><span class="label">确定性校验</span><h3>10条授信合规规则</h3></div></div><el-table :data="results.rules" stripe><el-table-column prop="rule_id" label="规则" width="120" /><el-table-column prop="name" label="规则名称" min-width="220" /><el-table-column prop="result" label="结果" width="130"><template #default="scope"><el-tag :type="outcomeType(scope.row.result)">{{ scope.row.result }}</el-tag></template></el-table-column><el-table-column prop="reason" label="说明" min-width="320" /></el-table></section>
            <div class="two-column"><section class="panel"><div class="panel-heading"><div><span class="label">风险解释</span><h3>需关注的风险项</h3></div></div><el-empty v-if="!results.risks.length" description="暂无风险项" /><div v-for="risk in results.risks" :key="String(risk.risk_id ?? risk.title)" class="risk-row"><el-tag :type="risk.level === 'HIGH' ? 'danger' : 'warning'">{{ risk.level }}</el-tag><div><strong>{{ risk.title ?? risk.risk_id }}</strong><p>{{ risk.explanation ?? risk.reason }}</p></div></div></section><section class="panel"><div class="panel-heading"><div><span class="label">财务指标</span><h3>计算结果</h3></div></div><pre class="json-view">{{ safeJson(results.financial_metrics) }}</pre></section></div>
            <div class="two-column"><section class="panel"><div class="panel-heading"><div><span class="label">制度检索</span><h3>Top证据</h3></div></div><pre class="json-view">{{ safeJson(results.retrieval) }}</pre></section><section class="panel"><div class="panel-heading"><div><span class="label">只读工具</span><h3>工具调用状态</h3></div></div><pre class="json-view">{{ safeJson(results.tools) }}</pre></section></div>
          </template>
        </template>

        <template v-else-if="routeName === 'run-report'">
          <div class="page-heading"><div><p class="eyebrow">审查Run / HITL-2</p><h2>报告复核与导出</h2><p class="muted">确认只代表AI辅助审查草稿已被Reviewer复核，不代表授信审批通过。</p></div><el-button v-if="report?.report_status === 'CONFIRMED'" type="success" @click="downloadReport">下载Markdown</el-button></div>
          <template v-if="report">
            <div class="report-banner"><div><span class="label">报告状态</span><strong>{{ report.report_status }}</strong></div><el-tag :type="outcomeType(report.summary_outcome)" size="large">{{ report.summary_outcome }}</el-tag></div>
            <section class="panel report-panel"><div class="panel-heading"><div><span class="label">固定模板报告 · {{ report.report_hash.slice(0, 12) }}</span><h3>审查结论草稿</h3></div><span class="muted">快照 v{{ report.snapshot_version }}</span></div><pre class="report-text">{{ report.markdown }}</pre></section>
            <section v-if="role === 'REVIEWER' && report.report_status !== 'CONFIRMED'" class="panel review-actions"><el-input v-model="reportReason" type="textarea" :rows="2" placeholder="退回报告时填写原因；确认报告可留空" /><div class="form-actions"><el-button type="warning" plain @click="reviewReport('RETURN_FOR_RERUN')">退回重跑</el-button><el-button type="primary" @click="reviewReport('CONFIRM_DRAFT')">确认报告</el-button></div></section>
          </template>
        </template>

        <footer class="footer-note">CreditGuard AI PoC · Spec-first · 纯合成数据 · AI辅助审查，不替代最终授信审批</footer>
      </section>
    </div>
  </main>
</template>
