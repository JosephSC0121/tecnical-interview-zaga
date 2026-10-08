import type { EditableProject, ProjectDetail, ProjectSummary, SaveResult } from './types'

export class ApiError extends Error {
  // null when the request never got an answer.
  readonly status: number | null

  constructor(status: number | null, message: string) {
    super(message)
    this.status = status
  }
}

export function listProjects(): Promise<ProjectSummary[]> {
  return getJson('/api/projects')
}

export function getProject(id: string): Promise<ProjectDetail> {
  return getJson(`/api/projects/${encodeURIComponent(id)}`)
}

// `changes` may be the whole form: the backend treats a field equal to `base` as unchanged.
export async function saveProject(
  id: string,
  base: EditableProject,
  changes: EditableProject,
): Promise<SaveResult> {
  const response = await request(`/api/projects/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base, changes }),
  })
  const body: unknown = await response.json().catch(() => null)
  // Conflicts, "not saved" and "unconfirmed" are outcomes of a save, not errors, whatever the code.
  if (isRecord(body) && typeof body.status === 'string') return body as SaveResult
  throw new ApiError(response.status, describe(body, response.status))
}

async function getJson<T>(path: string): Promise<T> {
  const response = await request(path)
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, describe(body, response.status))
  return body as T
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init)
  } catch {
    throw new ApiError(null, 'Cannot reach the server')
  }
}

function describe(body: unknown, status: number): string {
  const detail = isRecord(body) ? body.detail : undefined
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(detailMessage).filter(Boolean)
    if (messages.length) return messages.join('; ')
  }
  return `Request failed (${status})`
}

// Covers our own {field, message} entries and FastAPI's {loc, msg} entries.
function detailMessage(entry: unknown): string {
  if (!isRecord(entry)) return ''
  const where = entry.field ?? (Array.isArray(entry.loc) ? entry.loc.slice(1).join('.') : '')
  const what = entry.message ?? entry.msg ?? ''
  return [where, what].filter(Boolean).join(': ')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
