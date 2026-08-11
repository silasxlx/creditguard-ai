import type {
  CaseDetail,
  CaseListResponse,
  CaseSummary,
  DemoScenarioResponse,
  DocumentSummary,
  FactReviewView,
  ReportResponse,
  ReviewResults,
  RunSummary,
} from './types'
import type { paths } from './generated/openapi'

type HealthResponse = paths['/health']['get']['responses'][200]['content']['application/json']
type CasesResponse = paths['/api/v1/cases']['get']['responses'][200]['content']['application/json']

export class ApiError extends Error {
  status: number
  code?: string
  detail?: string

  constructor(status: number, message: string, code?: string, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

type RequestOptions = {
  userId: string
  method?: string
  body?: BodyInit | null
  json?: unknown
  idempotencyKey?: string
}

function newKey(prefix: string): string {
  const suffix = typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2)
  return prefix + '-' + suffix
}

async function request<T>(path: string, options: RequestOptions): Promise<T> {
  const headers: Record<string, string> = { 'X-Demo-User-Id': options.userId }
  let body = options.body
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.json)
  }
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey

  const response = await fetch(path, {
    method: options.method ?? 'GET',
    headers,
    body,
  })
  if (!response.ok) {
    let payload: { detail?: string; title?: string; code?: string } = {}
    try {
      payload = await response.json()
    } catch {
      // Keep a useful status message when the server does not return JSON.
    }
    throw new ApiError(
      response.status,
      payload.detail ?? payload.title ?? '请求失败（HTTP ' + response.status + '）',
      payload.code,
      payload.detail,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function health(): Promise<HealthResponse> {
  return request('/health', { userId: 'demo-rm' })
}

export function listCases(userId: string): Promise<CaseListResponse> {
  return request<CasesResponse>('/api/v1/cases', { userId }) as Promise<CaseListResponse>
}

export function getCase(caseId: string, userId: string): Promise<CaseDetail> {
  return request('/api/v1/cases/' + encodeURIComponent(caseId), { userId })
}

export function createCase(
  userId: string,
  payload: { case_no: string; customer_name: string; customer_key: string; review_date: string },
): Promise<CaseSummary> {
  return request('/api/v1/cases', {
    userId,
    method: 'POST',
    json: payload,
    idempotencyKey: newKey('case'),
  })
}

export function uploadDocument(
  caseId: string,
  userId: string,
  documentType: string,
  file: File,
  replacesDocumentId?: string,
): Promise<DocumentSummary> {
  const body = new FormData()
  body.append('document_type', documentType)
  body.append('file', file, file.name)
  if (replacesDocumentId) body.append('replaces_document_id', replacesDocumentId)
  return request('/api/v1/cases/' + encodeURIComponent(caseId) + '/documents', {
    userId,
    method: 'POST',
    body,
    idempotencyKey: newKey('document'),
  })
}

export function createRun(
  caseId: string,
  userId: string,
  documentVersionIds: string[],
  expectedCaseVersion: number,
): Promise<RunSummary> {
  return request('/api/v1/cases/' + encodeURIComponent(caseId) + '/runs', {
    userId,
    method: 'POST',
    json: {
      document_version_ids: documentVersionIds,
      expected_case_version: expectedCaseVersion,
    },
    idempotencyKey: newKey('run'),
  })
}

export function seedDemo(userId: string, scenarioId: string): Promise<DemoScenarioResponse> {
  return request('/api/v1/demo/scenarios/' + encodeURIComponent(scenarioId), {
    userId,
    method: 'POST',
    idempotencyKey: 'demo-' + scenarioId,
  })
}

export function getRun(runId: string, userId: string): Promise<RunSummary> {
  return request('/api/v1/runs/' + encodeURIComponent(runId), { userId })
}

export function retryRun(runId: string, userId: string, expectedStatus = 'PAUSED_RETRYABLE'):
  Promise<RunSummary> {
  return request('/api/v1/runs/' + encodeURIComponent(runId) + '/retry', {
    userId,
    method: 'POST',
    json: { expected_status: expectedStatus },
    idempotencyKey: newKey('retry'),
  })
}

export function getFacts(runId: string, userId: string): Promise<FactReviewView> {
  return request('/api/v1/runs/' + encodeURIComponent(runId) + '/facts', { userId })
}

export function submitFactReview(
  runId: string,
  userId: string,
  payload: {
    expected_snapshot_version: number
    decisions: Array<{
      conflict_id: string
      action: 'SELECT_SOURCE' | 'CORRECT_VALUE' | 'REQUEST_RESUBMISSION'
      selected_evidence_id?: string
      corrected_value?: unknown
      reason: string
    }>
  },
): Promise<RunSummary> {
  return request('/api/v1/runs/' + encodeURIComponent(runId) + '/fact-review', {
    userId,
    method: 'POST',
    json: payload,
    idempotencyKey: newKey('fact-review'),
  })
}

export function getResults(runId: string, userId: string): Promise<ReviewResults> {
  return request('/api/v1/runs/' + encodeURIComponent(runId) + '/review-results', { userId })
}

export function getReport(runId: string, userId: string): Promise<ReportResponse> {
  return request('/api/v1/runs/' + encodeURIComponent(runId) + '/report', { userId })
}

export function submitReportReview(
  runId: string,
  userId: string,
  payload: { expected_snapshot_version: number; action: 'CONFIRM_DRAFT' | 'RETURN_FOR_RERUN'; reason: string },
): Promise<RunSummary> {
  return request('/api/v1/runs/' + encodeURIComponent(runId) + '/report-review', {
    userId,
    method: 'POST',
    json: payload,
    idempotencyKey: newKey('report-review'),
  })
}

export async function exportReport(runId: string, userId: string): Promise<void> {
  const response = await fetch('/api/v1/runs/' + encodeURIComponent(runId) + '/report/export?format=markdown', {
    headers: { 'X-Demo-User-Id': userId },
  })
  if (!response.ok) throw new ApiError(response.status, '报告导出失败（HTTP ' + response.status + '）')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'credit-review-' + runId + '.md'
  link.click()
  URL.revokeObjectURL(url)
}
