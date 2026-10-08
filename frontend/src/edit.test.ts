import { describe, expect, it } from 'vitest'
import { applyConflictChoices, validateForm } from './edit'
import type { Conflict, EditableProject } from './types'

const BASE: EditableProject = {
  name: 'Solar Park',
  sector: 'energy',
  country: 'Chile',
  stage: 'tender',
  key_dates: [
    { label: 'Tender launch', date: '2026-03-01' },
    { label: 'Financial close', date: '2026-09-01' },
  ],
}

describe('validateForm', () => {
  it('accepts a valid form', () => {
    expect(validateForm({ ...BASE, name: 'Renamed' }, BASE)).toEqual({})
  })

  it('reports an empty name and an empty country', () => {
    expect(validateForm({ ...BASE, name: '  ', country: '' }, BASE)).toEqual({
      name: 'Required',
      country: 'Required',
    })
  })

  it('reports a key date with no label and one with no date', () => {
    const form = {
      ...BASE,
      key_dates: [
        { label: ' ', date: '2026-03-01' },
        { label: 'Financial close', date: '' },
      ],
    }

    expect(validateForm(form, BASE)).toEqual({
      'key_dates.0.label': 'Required',
      'key_dates.1.date': 'Required',
    })
  })

  it('reports a repeated label, ignoring case and surrounding spaces', () => {
    const form = {
      ...BASE,
      key_dates: [...BASE.key_dates, { label: '  tender LAUNCH ', date: '2027-01-01' }],
    }

    expect(validateForm(form, BASE)).toEqual({ 'key_dates.2.label': 'Label is already used' })
  })

  it('accepts repeated labels the record already had when the key dates are untouched', () => {
    const repeated = { ...BASE, key_dates: [BASE.key_dates[0], BASE.key_dates[0]] }

    expect(validateForm({ ...repeated, name: 'Renamed' }, repeated)).toEqual({})
  })
})

describe('applyConflictChoices', () => {
  const merged: EditableProject = { ...BASE, stage: 'construction', country: 'Peru' }

  const stage: Conflict = {
    field: 'stage',
    label: null,
    base: 'tender',
    mine: 'financing',
    theirs: 'construction',
  }
  const keyDate = (mine: string | null, theirs: string | null, label = 'Financial close') =>
    ({ field: 'key_dates', label, base: '2026-09-01', mine, theirs }) satisfies Conflict

  it('leaves the merged record untouched when their value is chosen', () => {
    expect(applyConflictChoices(merged, [stage], ['theirs'])).toEqual(merged)
  })

  it('sets a core field to my value', () => {
    const resolved = applyConflictChoices(merged, [stage], ['mine'])

    expect(resolved).toEqual({ ...merged, stage: 'financing' })
  })

  it('sets the date of an existing key date', () => {
    const resolved = applyConflictChoices(merged, [keyDate('2026-10-10', '2026-11-11')], ['mine'])

    expect(resolved.key_dates).toEqual([
      { label: 'Tender launch', date: '2026-03-01' },
      { label: 'Financial close', date: '2026-10-10' },
    ])
  })

  it('removes a key date I had removed', () => {
    const resolved = applyConflictChoices(merged, [keyDate(null, '2026-11-11')], ['mine'])

    expect(resolved.key_dates).toEqual([{ label: 'Tender launch', date: '2026-03-01' }])
  })

  it('adds back a key date they had removed', () => {
    const withoutClose = { ...merged, key_dates: [merged.key_dates[0]] }

    const resolved = applyConflictChoices(withoutClose, [keyDate('2026-10-10', null)], ['mine'])

    expect(resolved.key_dates).toEqual([
      { label: 'Tender launch', date: '2026-03-01' },
      { label: 'Financial close', date: '2026-10-10' },
    ])
  })

  it('replaces the whole list for a whole-list conflict', () => {
    const mine = [{ label: 'Only', date: '2030-01-01' }]
    const wholeList: Conflict = {
      field: 'key_dates',
      label: null,
      base: BASE.key_dates,
      mine,
      theirs: merged.key_dates,
    }

    expect(applyConflictChoices(merged, [wholeList], ['mine']).key_dates).toEqual(mine)
  })

  it('applies each choice independently and does not mutate its input', () => {
    const snapshot = structuredClone(merged)

    const resolved = applyConflictChoices(
      merged,
      [stage, keyDate('2026-10-10', '2026-11-11')],
      ['theirs', 'mine'],
    )

    expect(resolved.stage).toBe('construction')
    expect(resolved.key_dates[1].date).toBe('2026-10-10')
    expect(merged).toEqual(snapshot)
  })
})
