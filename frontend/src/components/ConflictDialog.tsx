import { useState } from 'react'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import FormControlLabel from '@mui/material/FormControlLabel'
import Radio from '@mui/material/Radio'
import RadioGroup from '@mui/material/RadioGroup'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import type { Choice, Conflict, ConflictValue } from '../types'

interface Props {
  conflicts: Conflict[]
  onConfirm: (choices: Choice[]) => void
  onCancel: () => void
}

const FIELD_NAMES: Record<Conflict['field'], string> = {
  name: 'Name',
  sector: 'Sector',
  country: 'Country',
  stage: 'Stage',
  key_dates: 'Key dates',
}

function title(conflict: Conflict): string {
  return conflict.label === null
    ? FIELD_NAMES[conflict.field]
    : `Key date “${conflict.label}”`
}

function show(value: ConflictValue): string {
  if (value === null) return 'removed'
  if (typeof value === 'string') return value
  if (value.length === 0) return 'no key dates'
  return value.map((keyDate) => `${keyDate.label}: ${keyDate.date}`).join(', ')
}

// Mounted only while there is a conflict, so the choices start empty for every new conflict.
export default function ConflictDialog({ conflicts, onConfirm, onCancel }: Props) {
  const [choices, setChoices] = useState<(Choice | null)[]>(() => conflicts.map(() => null))
  const complete = choices.every((choice) => choice !== null)

  const choose = (index: number, choice: Choice) =>
    setChoices((current) => current.map((c, i) => (i === index ? choice : c)))

  return (
    <Dialog open onClose={onCancel} fullWidth maxWidth="sm">
      <DialogTitle>Someone else changed the same {conflicts.length > 1 ? 'fields' : 'field'}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Nothing has been saved yet. Choose which value to keep for each one. Your other changes
          and theirs are kept either way.
        </DialogContentText>
        <Stack spacing={2}>
          {conflicts.map((conflict, index) => (
            <div key={`${conflict.field}:${conflict.label ?? ''}`}>
              <Typography variant="subtitle1">{title(conflict)}</Typography>
              <Typography variant="body2" color="text.secondary">
                When you opened it: {show(conflict.base)}
              </Typography>
              <RadioGroup
                value={choices[index] ?? ''}
                onChange={(event) => choose(index, event.target.value as Choice)}
              >
                <FormControlLabel
                  value="mine"
                  control={<Radio />}
                  label={`Your value: ${show(conflict.mine)}`}
                />
                <FormControlLabel
                  value="theirs"
                  control={<Radio />}
                  label={`Stored value: ${show(conflict.theirs)}`}
                />
              </RadioGroup>
            </div>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          variant="contained"
          disabled={!complete}
          onClick={() => onConfirm(choices as Choice[])}
        >
          Save with these choices
        </Button>
      </DialogActions>
    </Dialog>
  )
}
