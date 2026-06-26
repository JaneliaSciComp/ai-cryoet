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
  project?: string;
  dataset_type?: string;
  microscope?: string;
  pixel_size_min?: number;
  pixel_size_max?: number;
  n_tilts_min?: number;
  n_tilts_max?: number;
  has_tomograms?: boolean;
};

type LandingFiltersProps = {
  options: FiltersOptionsOut
  value: LandingFilterState
  onChange: (patch: Partial<LandingFilterState>) => void
  onReset: () => void
  // MD simulation samples have no microscope, so that arm hides this filter.
  showMicroscope?: boolean
  // Conversely, dataset_type (slab/bulk/single molecule) only applies to MD
  // simulation samples, so only that arm shows this filter.
  showDataType?: boolean
}

// `dataset_type` is stored as a snake_case enum value (e.g. "single_molecule");
// render it as readable words in the dropdown without altering the filter value.
export function prettyDatasetType(v: string): string {
  return v.replace(/_/g, ' ')
}

export function numOrUndef(s: string): number | undefined {
  return s === '' ? undefined : Number(s)
}

export function DropdownFilter(props: {
  label: string
  value: string
  options: string[]
  onChange: (v: string | undefined) => void
  // Optional display transform for option labels; the underlying value (used
  // for filtering) is unchanged.
  formatOption?: (v: string) => string
  disabled?: boolean
}) {
  const { label, value, options, onChange, formatOption, disabled } = props
  const display = formatOption ?? ((v: string) => v)
  return (
    <Box>
      <Typography variant="body2" gutterBottom color={disabled ? 'text.disabled' : undefined}>
        {label}
      </Typography>
      <FormControl size="small" fullWidth disabled={disabled}>
        <Select
          value={value}
          displayEmpty
          renderValue={(selected) =>
            selected ? (
              display(selected as string)
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
              {display(o)}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  )
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

export function LandingFilters(props: LandingFiltersProps) {
  const {
    options,
    value,
    onChange,
    onReset,
    showMicroscope = true,
    showDataType = false,
  } = props

  return (
    <Stack spacing={2.5}>
      <Typography variant="h6">Filters</Typography>

      <DropdownFilter
        label="Project"
        value={value.project ?? ''}
        options={options.projects}
        onChange={(v) => onChange({ project: v })}
      />

      {showDataType ? (
        <DropdownFilter
          label="Data type"
          value={value.dataset_type ?? ''}
          options={options.dataset_types}
          onChange={(v) => onChange({ dataset_type: v })}
          formatOption={prettyDatasetType}
        />
      ) : null}

      {showMicroscope ? (
        <DropdownFilter
          label="Microscope"
          value={value.microscope ?? ''}
          options={options.microscopes}
          onChange={(v) => onChange({ microscope: v })}
        />
      ) : null}

      <MinMaxRow
        label="Pixel size"
        min={value.pixel_size_min}
        max={value.pixel_size_max}
        onMin={(v) => onChange({ pixel_size_min: v })}
        onMax={(v) => onChange({ pixel_size_max: v })}
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
