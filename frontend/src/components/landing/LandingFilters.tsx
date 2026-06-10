import {
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import type { FiltersOptionsOut } from '~/types'

export type LandingFilterState = {
  project?: string
  data_source?: string
  microscope?: string
  pixel_size_min?: number
  pixel_size_max?: number
  n_tilts_min?: number
  n_tilts_max?: number
  has_tomograms?: boolean
}

type LandingFiltersProps = {
  options: FiltersOptionsOut
  value: LandingFilterState
  onChange: (patch: Partial<LandingFilterState>) => void
  onReset: () => void
}

function numOrUndef(s: string): number | undefined {
  return s === '' ? undefined : Number(s)
}

function DropdownFilter(props: {
  label: string
  value: string
  options: string[]
  onChange: (v: string | undefined) => void
}) {
  const { label, value, options, onChange } = props
  return (
    <Box>
      <Typography variant="body2" gutterBottom>
        {label}
      </Typography>
      <FormControl size="small" fullWidth>
        <Select
          value={value}
          displayEmpty
          renderValue={(selected) =>
            selected ? (
              (selected as string)
            ) : (
              <Typography component="span" color="text.disabled">
                Select from dropdown
              </Typography>
            )
          }
          onChange={(e) =>
            onChange(e.target.value === '' ? undefined : e.target.value)
          }
        >
          <MenuItem value="">
            <em>Any</em>
          </MenuItem>
          {options.map((o) => (
            <MenuItem key={o} value={o}>
              {o}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  )
}

function MinMaxRow(props: {
  label: string
  min: number | undefined
  max: number | undefined
  onMin: (v: number | undefined) => void
  onMax: (v: number | undefined) => void
}) {
  const { label, min, max, onMin, onMax } = props
  return (
    <Box>
      <Typography variant="body2" gutterBottom>
        {label}
      </Typography>
      <Stack direction="row" spacing={1}>
        <TextField
          size="small"
          type="number"
          placeholder="min"
          value={min ?? ''}
          onChange={(e) => onMin(numOrUndef(e.target.value))}
        />
        <TextField
          size="small"
          type="number"
          placeholder="max"
          value={max ?? ''}
          onChange={(e) => onMax(numOrUndef(e.target.value))}
        />
      </Stack>
    </Box>
  )
}

export function LandingFilters(props: LandingFiltersProps) {
  const { options, value, onChange, onReset } = props

  return (
    <Stack spacing={2.5}>
      <Typography variant="h6">Filters</Typography>

      <DropdownFilter
        label="Project"
        value={value.project ?? ''}
        options={options.projects}
        onChange={(v) => onChange({ project: v })}
      />

      <DropdownFilter
        label="Data source"
        value={value.data_source ?? ''}
        options={options.data_sources}
        onChange={(v) => onChange({ data_source: v })}
      />

      <DropdownFilter
        label="Microscope"
        value={value.microscope ?? ''}
        options={options.microscopes}
        onChange={(v) => onChange({ microscope: v })}
      />

      <MinMaxRow
        label="Pixel size"
        min={value.pixel_size_min}
        max={value.pixel_size_max}
        onMin={(v) => onChange({ pixel_size_min: v })}
        onMax={(v) => onChange({ pixel_size_max: v })}
      />

      <MinMaxRow
        label="Number of tilts"
        min={value.n_tilts_min}
        max={value.n_tilts_max}
        onMin={(v) => onChange({ n_tilts_min: v })}
        onMax={(v) => onChange({ n_tilts_max: v })}
      />

      <FormControlLabel
        control={
          <Checkbox
            checked={value.has_tomograms === true}
            onChange={(e) =>
              onChange({ has_tomograms: e.target.checked ? true : undefined })
            }
          />
        }
        label="Has tomograms"
      />

      <Box>
        <Button variant="outlined" onClick={onReset}>
          Reset
        </Button>
      </Box>
    </Stack>
  )
}
