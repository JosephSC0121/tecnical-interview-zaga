// Allowed values mirror the backend's (backend/app/models.py), which are checked against the upstream.
export const SECTORS = ['energy', 'mining', 'water', 'transport', 'oil_and_gas', 'ict'] as const
export const STAGES = [
  'idea',
  'feasibility',
  'tender',
  'financing',
  'construction',
  'operation',
  'cancelled',
] as const

export type Sector = (typeof SECTORS)[number]
export type Stage = (typeof STAGES)[number]

export interface KeyDate {
  label: string
  date: string
}

export interface ProjectSummary {
  id: string
  name: string
  sector: Sector
  country: string
  stage: Stage
}

export interface EditableProject {
  name: string
  sector: Sector
  country: string
  stage: Stage
  key_dates: KeyDate[]
}

export interface ProjectDetail extends EditableProject {
  id: string
}

export type ConflictValue = string | KeyDate[] | null

// For one key date, `label` is set and the values are ISO dates (null: absent on that side).
// For a whole-list conflict, `label` is null and the values are lists.
export interface Conflict {
  field: keyof EditableProject
  label: string | null
  base: ConflictValue
  mine: ConflictValue
  theirs: ConflictValue
}

export type Choice = 'mine' | 'theirs'

export type SaveResult =
  | { status: 'saved'; project: ProjectDetail; merged_with_others: boolean }
  | { status: 'unchanged'; project: ProjectDetail }
  | { status: 'changed_during_save'; project: ProjectDetail }
  | { status: 'conflict'; conflicts: Conflict[]; current: EditableProject; merged: EditableProject }
  | { status: 'not_saved' }
  | { status: 'unconfirmed' }
