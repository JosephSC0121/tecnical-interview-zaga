import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import type { AlertColor } from '@mui/material/Alert'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import MenuItem from '@mui/material/MenuItem'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { ApiError, getProject, saveProject } from '../api'
import ConflictDialog from '../components/ConflictDialog'
import KeyDatesEditor from '../components/KeyDatesEditor'
import { applyConflictChoices, toEditable, validateForm } from '../edit'
import type { FormErrors } from '../edit'
import { SECTORS, STAGES } from '../types'
import type { Choice, EditableProject, ProjectDetail, SaveResult, Sector, Stage } from '../types'

type LoadState = 'loading' | 'ready' | 'not_found' | { error: string }
type Conflicted = Extract<SaveResult, { status: 'conflict' }>

interface Notice {
  severity: AlertColor
  text: string
  // Offered when a save's outcome is unknown: re-sending is safe and tells us what happened.
  checkAgain?: boolean
}

const NOTICES = {
  saved: { severity: 'success', text: 'Saved.' },
  merged: {
    severity: 'success',
    text: 'Saved. The record had been changed by someone else; your changes were merged with theirs.',
  },
  unchanged: { severity: 'info', text: 'Nothing to save: the form matches the record.' },
  changedDuringSave: {
    severity: 'warning',
    text: 'Your save went through, but the record was changed again while you were saving. The form now shows what is stored.',
  },
  notSaved: {
    severity: 'warning',
    text: 'Not saved: the records system timed out. Your edits are still here; save again.',
  },
  unconfirmed: {
    severity: 'warning',
    text: 'We could not confirm whether the save happened. Your edits are still here.',
    checkAgain: true,
  },
} satisfies Record<string, Notice>

export default function ProjectEditPage() {
  const { id = '' } = useParams()
  const [load, setLoad] = useState<LoadState>('loading')
  const [attempt, setAttempt] = useState(0)
  // `base` is the record as the editor last saw it stored; the backend merges against it.
  const [base, setBase] = useState<EditableProject | null>(null)
  const [form, setForm] = useState<EditableProject | null>(null)
  const [errors, setErrors] = useState<FormErrors>({})
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [conflict, setConflict] = useState<Conflicted | null>(null)

  const adopt = (project: ProjectDetail) => {
    const stored = toEditable(project)
    setBase(stored)
    setForm(stored)
    setErrors({})
  }

  useEffect(() => {
    let cancelled = false
    getProject(id).then(
      (project) => {
        if (cancelled) return
        adopt(project)
        setLoad('ready')
      },
      (error: Error) => {
        if (cancelled) return
        const notFound = error instanceof ApiError && error.status === 404
        setLoad(notFound ? 'not_found' : { error: error.message })
      },
    )
    return () => {
      cancelled = true
    }
  }, [id, attempt])

  const submit = async (sentBase: EditableProject, sentForm: EditableProject) => {
    setSaving(true)
    setNotice(null)
    try {
      const result = await saveProject(id, sentBase, sentForm)
      switch (result.status) {
        case 'saved':
          adopt(result.project)
          setNotice(result.merged_with_others ? NOTICES.merged : NOTICES.saved)
          break
        case 'unchanged':
          adopt(result.project)
          setNotice(NOTICES.unchanged)
          break
        case 'changed_during_save':
          adopt(result.project)
          setNotice(NOTICES.changedDuringSave)
          break
        case 'conflict':
          setConflict(result)
          break
        case 'not_saved':
          setNotice(NOTICES.notSaved)
          break
        case 'unconfirmed':
          setNotice(NOTICES.unconfirmed)
          break
      }
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Unexpected error'
      setNotice({ severity: 'error', text: `Not saved: ${reason}. Your edits are still here.` })
    } finally {
      setSaving(false)
    }
  }

  if (load === 'loading') return <CircularProgress aria-label="Loading project" />
  if (load === 'not_found') {
    return (
      <Alert severity="warning">
        Project {id} was not found. <Link to="/">Back to the list</Link>
      </Alert>
    )
  }
  if (typeof load === 'object') {
    const retry = () => {
      setLoad('loading')
      setAttempt((n) => n + 1)
    }
    return (
      <Alert severity="error" action={<Button onClick={retry}>Retry</Button>}>
        Could not load the project: {load.error}
      </Alert>
    )
  }
  if (!base || !form) return null

  const change = (patch: Partial<EditableProject>) => setForm({ ...form, ...patch })

  const save = () => {
    const found = validateForm(form, base)
    setErrors(found)
    setNotice(null)
    if (Object.keys(found).length === 0) void submit(base, form)
  }

  const resolve = (choices: Choice[]) => {
    if (!conflict) return
    // The stored record becomes the new base, so the backend re-checks the resolution from scratch.
    const resolved = applyConflictChoices(conflict.merged, conflict.conflicts, choices)
    setBase(conflict.current)
    setForm(resolved)
    setConflict(null)
    void submit(conflict.current, resolved)
  }

  return (
    <Stack spacing={3} component="form" noValidate onSubmit={(event) => event.preventDefault()}>
      <Typography variant="h5" component="h1">
        {id}
      </Typography>

      {notice && (
        <Alert
          severity={notice.severity}
          action={
            notice.checkAgain && (
              <Button color="inherit" disabled={saving} onClick={() => void submit(base, form)}>
                Check again
              </Button>
            )
          }
        >
          {notice.text}
        </Alert>
      )}

      <TextField
        label="Name"
        value={form.name}
        disabled={saving}
        error={Boolean(errors.name)}
        helperText={errors.name}
        onChange={(event) => change({ name: event.target.value })}
      />
      <Stack direction="row" spacing={2}>
        <TextField
          select
          label="Sector"
          value={form.sector}
          disabled={saving}
          onChange={(event) => change({ sector: event.target.value as Sector })}
          sx={{ flex: 1 }}
        >
          {SECTORS.map((sector) => (
            <MenuItem key={sector} value={sector}>
              {sector}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Stage"
          value={form.stage}
          disabled={saving}
          onChange={(event) => change({ stage: event.target.value as Stage })}
          sx={{ flex: 1 }}
        >
          {STAGES.map((stage) => (
            <MenuItem key={stage} value={stage}>
              {stage}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Country"
          value={form.country}
          disabled={saving}
          error={Boolean(errors.country)}
          helperText={errors.country}
          onChange={(event) => change({ country: event.target.value })}
          sx={{ flex: 1 }}
        />
      </Stack>

      <KeyDatesEditor
        value={form.key_dates}
        errors={errors}
        disabled={saving}
        onChange={(key_dates) => change({ key_dates })}
      />

      <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
        <Button variant="contained" disabled={saving} onClick={save}>
          {saving ? 'Saving…' : 'Save'}
        </Button>
        <Button component={Link} to="/" disabled={saving}>
          Back to the list
        </Button>
      </Stack>

      {conflict && (
        <ConflictDialog
          conflicts={conflict.conflicts}
          onConfirm={resolve}
          onCancel={() => setConflict(null)}
        />
      )}
    </Stack>
  )
}
