import { Box, Stack, TextField, Typography } from '@mui/material'

// Shared filter subcomponents. The full per-field filter UI now lives in
// `filters/` (FilterPanel + Section/Group/Property, registry-driven); this file
// keeps only the small primitives those components reuse.

// `dataset_type` is stored as a snake_case enum value (e.g. "single_molecule");
// render it as readable words without altering the underlying filter value.
export function prettyDatasetType(v: string): string {
  return v.replace(/_/g, ' ')
}

export function numOrUndef(s: string): number | undefined {
  return s === '' ? undefined : Number(s)
}

export function MinMaxRow(props: {
  label: string
  min: number | undefined
  max: number | undefined
  onMin: (v: number | undefined) => void
  onMax: (v: number | undefined) => void
  disabled?: boolean
}) {
  const { label, min, max, onMin, onMax, disabled } = props
  return (
    <Box>
      <Typography variant="body2" gutterBottom color={disabled ? 'text.disabled' : undefined}>
        {label}
      </Typography>
      <Stack direction="row" spacing={1}>
        <TextField
          size="small"
          type="number"
          placeholder="min"
          value={min ?? ''}
          disabled={disabled}
          onChange={(e) => onMin(numOrUndef(e.target.value))}
        />
        <TextField
          size="small"
          type="number"
          placeholder="max"
          value={max ?? ''}
          disabled={disabled}
          onChange={(e) => onMax(numOrUndef(e.target.value))}
        />
      </Stack>
    </Box>
  )
}
