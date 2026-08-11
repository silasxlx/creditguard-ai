export type DemoRole = 'RM' | 'REVIEWER'

export type DocumentType =
  | 'BUSINESS_LICENSE'
  | 'CREDIT_APPLICATION'
  | 'DUE_DILIGENCE'
  | 'FINANCIAL_STATEMENTS'

export type RunStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'WAITING_FACT_REVIEW'
  | 'WAITING_REPORT_REVIEW'
  | 'PAUSED_RETRYABLE'
  | 'COMPLETED'
  | 'RETURNED'
  | 'FAILED_FINAL'

export interface CaseSummary {
  id: string
  case_no: string
  customer_name: string
  customer_key: string
  review_date: string
  version: number
  created_by: string
  created_at: string
  updated_at: string
}

export interface DocumentSummary {
  id: string
  case_id: string
  document_type: DocumentType
  version: number
  active: boolean
  original_filename: string
  content_hash: string
  mime: string
  size_bytes: number
  storage_key: string
  status: string
  created_at: string
  updated_at: string
}

export interface RunSummary {
  id: string
  case_id: string
  status: RunStatus
  stage: string
  progress_percent: number
  waiting_gate: string | null
  retryable: boolean
  pause_reason: string | null
  error_code: string | null
  input_document_version_ids: string[]
  workflow_version: string
  rule_pack_version: string
  policy_pack_version: string
  policy_index_version: string
  prompt_versions: Record<string, string>
  model_profile: Record<string, string>
  allowed_actions: string[]
  created_at: string
  updated_at: string
}

export interface CaseDetail extends CaseSummary {
  documents: DocumentSummary[]
  runs: RunSummary[]
}

export interface CaseListResponse {
  items: CaseSummary[]
  next_cursor: string | null
}

export interface DemoScenarioResponse {
  scenario_id: string
  case_id: string
  run_id: string
  case_version: number
  input_document_version_ids: string[]
  run_status: RunStatus
  created: boolean
}

export interface FactCandidate {
  field: string
  field_name: string
  value_type: string
  raw_value: string
  normalized_value: string | number | null
  document_version_id: string
  evidence_id: string
  locator: Record<string, unknown>
  source: string
  selected: boolean
  validation_reasons: string[] | null
}

export interface FactConflict {
  conflict_id: string
  field: string
  field_name: string
  comparison: string
  candidates: FactCandidate[]
  difference: Record<string, string> | null
  material: boolean
  selected_value: string | number | null
}

export interface FactField {
  field: string
  field_name: string
  value_type: string
  candidates: FactCandidate[]
  selected_value: string | number | null
  requires_review: boolean
}

export interface FactReviewView {
  run_id: string
  snapshot_version: number
  fields: Record<string, FactField>
  missing_fields: string[]
  conflicts: FactConflict[]
  requires_review: boolean
  allowed_actions: string[]
}

export interface ReviewResults {
  run_id: string
  summary_outcome: string
  fact_snapshot_version: number
  facts: Record<string, unknown>
  rules: Array<Record<string, unknown>>
  financial_metrics: Record<string, unknown>
  retrieval: Record<string, unknown>
  tools: Record<string, unknown>
  unsupported_claims: Array<Record<string, unknown>>
  risks: Array<Record<string, unknown>>
  report_status: string
  report_snapshot_version: number | null
}

export interface ReportResponse {
  run_id: string
  snapshot_version: number
  report_status: string
  report_hash: string
  summary_outcome: string
  markdown: string
  risks: Array<Record<string, unknown>>
  unsupported_claims: Array<Record<string, unknown>>
  evidence_refs: string[]
  allowed_actions: string[]
}
