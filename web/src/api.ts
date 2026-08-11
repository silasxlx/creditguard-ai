import type { CaseListResponse } from './types'

async function request<T>(path: string, userId: string): Promise<T> {
  const response = await fetch(path, { headers: { 'X-Demo-User-Id': userId } })
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json() as Promise<T>
}

export function listCases(userId: string): Promise<CaseListResponse> {
  return request<CaseListResponse>('/api/v1/cases', userId)
}

export function health(): Promise<{ status: string; service: string; version: string }> {
  return request('/health', 'demo-rm')
}
