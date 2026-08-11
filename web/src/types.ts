export type DemoRole = 'RM' | 'REVIEWER'

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

export interface RunSummary {
  id: string
  case_id: string
  status: string
  stage: string
  progress_percent: number
  waiting_gate: string | null
  retryable: boolean
  allowed_actions: string[]
  updated_at: string
}

export interface CaseListResponse {
  items: CaseSummary[]
  next_cursor: string | null
}
