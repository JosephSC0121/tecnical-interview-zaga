import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import type { FormErrors } from '../edit'
import type { KeyDate } from '../types'

interface Props {
  value: KeyDate[]
  errors: FormErrors
  disabled: boolean
  onChange: (keyDates: KeyDate[]) => void
}

export default function KeyDatesEditor({ value, errors, disabled, onChange }: Props) {
  const update = (index: number, patch: Partial<KeyDate>) =>
    onChange(value.map((keyDate, i) => (i === index ? { ...keyDate, ...patch } : keyDate)))

  return (
    <Stack spacing={2}>
      <Typography variant="h6" component="h2">
        Key dates
      </Typography>
      {value.length === 0 && <Typography color="text.secondary">No key dates.</Typography>}
      {value.map((keyDate, index) => (
        // Rows have no id of their own; the index is stable because rows are never reordered.
        <Stack key={index} direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
          <TextField
            label="Label"
            size="small"
            value={keyDate.label}
            disabled={disabled}
            error={Boolean(errors[`key_dates.${index}.label`])}
            helperText={errors[`key_dates.${index}.label`]}
            onChange={(event) => update(index, { label: event.target.value })}
            sx={{ flex: 1 }}
          />
          <TextField
            label="Date"
            type="date"
            size="small"
            value={keyDate.date}
            disabled={disabled}
            error={Boolean(errors[`key_dates.${index}.date`])}
            helperText={errors[`key_dates.${index}.date`]}
            onChange={(event) => update(index, { date: event.target.value })}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <Button
            color="error"
            disabled={disabled}
            onClick={() => onChange(value.filter((_, i) => i !== index))}
          >
            Remove
          </Button>
        </Stack>
      ))}
      <div>
        <Button
          variant="outlined"
          disabled={disabled}
          onClick={() => onChange([...value, { label: '', date: '' }])}
        >
          Add key date
        </Button>
      </div>
    </Stack>
  )
}
