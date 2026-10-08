import type { Choice, Conflict, EditableProject, KeyDate, ProjectDetail } from './types'

// Keyed by field: "name", "country", "key_dates.<index>.label", "key_dates.<index>.date".
export type FormErrors = Record<string, string>

// Same identity rule as the backend's merge: a key date is its label, ignoring case and spaces.
export function labelKey(label: string): string {
  return label.trim().toLowerCase()
}

export function toEditable(project: ProjectDetail): EditableProject {
  return {
    name: project.name,
    sector: project.sector,
    country: project.country,
    stage: project.stage,
    key_dates: project.key_dates,
  }
}

export function validateForm(form: EditableProject, base: EditableProject): FormErrors {
  const errors: FormErrors = {}
  if (!form.name.trim()) errors.name = 'Required'
  if (!form.country.trim()) errors.country = 'Required'

  // A record that already has repeated labels must stay editable, so only a changed list is checked.
  const keyDatesChanged = JSON.stringify(form.key_dates) !== JSON.stringify(base.key_dates)
  const seen = new Set<string>()
  form.key_dates.forEach((keyDate, index) => {
    const key = labelKey(keyDate.label)
    if (!key) errors[`key_dates.${index}.label`] = 'Required'
    else if (keyDatesChanged && seen.has(key)) {
      errors[`key_dates.${index}.label`] = 'Label is already used'
    }
    seen.add(key)
    if (!keyDate.date) errors[`key_dates.${index}.date`] = 'Required'
  })
  return errors
}

// Starts from the backend's merge (conflicting fields at the stored value) and puts the editor's
// value back wherever they chose "mine". The result is sent with `base` = the stored record.
export function applyConflictChoices(
  merged: EditableProject,
  conflicts: Conflict[],
  choices: Choice[],
): EditableProject {
  return conflicts.reduce(
    (project, conflict, index) =>
      choices[index] === 'mine' ? withMyValue(project, conflict) : project,
    merged,
  )
}

function withMyValue(project: EditableProject, conflict: Conflict): EditableProject {
  const { field, label, mine } = conflict
  if (field !== 'key_dates') return { ...project, [field]: mine }
  if (label === null) return { ...project, key_dates: mine as KeyDate[] }

  const key = labelKey(label)
  const others = project.key_dates.filter((keyDate) => labelKey(keyDate.label) !== key)
  if (mine === null) return { ...project, key_dates: others }

  const date = mine as string
  const exists = others.length !== project.key_dates.length
  const key_dates = exists
    ? project.key_dates.map((kd) => (labelKey(kd.label) === key ? { ...kd, date } : kd))
    : [...project.key_dates, { label, date }]
  return { ...project, key_dates }
}
