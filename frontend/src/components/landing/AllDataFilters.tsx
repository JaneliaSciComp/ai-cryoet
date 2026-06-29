import {
  Box,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  Stack,
  Typography,
} from '@mui/material'
import type { FiltersOptionsOut } from '~/types'
import {
  DropdownFilter,
  MinMaxRow,
  prettyDatasetType,
  type LandingFilterState,
} from '~/components/landing/LandingFilters'

// The /data ("All data") page differs from the single-arm browse pages: it
// spans both arms, so `data_source` is a real, user-settable filter rather than
// a value forced by the route. Arm-specific filters (microscope for
// experimental, dataset_type for simulation) move into labelled sections and
// disable when the opposite arm is selected.
export type AllDataFilterState = LandingFilterState & {
  data_source?: 'experimental' | 'simulation'
}

type AllDataFiltersProps = {
  options: FiltersOptionsOut
  value: AllDataFilterState
  onChange: (patch: Partial<AllDataFilterState>) => void
  onReset: () => void
}

export function AllDataFilters(props: AllDataFiltersProps) {
  const { options, value, onChange, onReset } = props

  // Each arm-specific section is disabled when the *other* arm is selected;
  // when no data_source is chosen both stay enabled (and a warning is shown
  // near the table once an arm-specific filter is set — see AllDataBrowser).
  const experimentalDisabled = value.data_source === 'simulation'
  const simulationDisabled = value.data_source === 'experimental'

  return (
    <Stack spacing={2.5}>
      <Typography variant="h6">Filters</Typography>

      <DropdownFilter
        label="Data source"
        value={value.data_source ?? ''}
        options={options.data_sources}
        onChange={(v) =>
          onChange({
            data_source: v as AllDataFilterState['data_source'],
          })
        }
        formatOption={(v) => v.charAt(0).toUpperCase() + v.slice(1)}
      />

      <DropdownFilter
        label="Project"
        value={value.project ?? ''}
        options={options.projects}
        onChange={(v) => onChange({ project: v })}
      />

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

      <Divider />

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Experimental only
        </Typography>
        <DropdownFilter
          label="Microscope"
          value={value.microscope ?? ''}
          options={options.microscopes}
          onChange={(v) => onChange({ microscope: v })}
          disabled={experimentalDisabled}
        />
      </Box>

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Simulation only
        </Typography>
        <DropdownFilter
          label="Data type"
          value={value.dataset_type ?? ''}
          options={options.dataset_types}
          onChange={(v) => onChange({ dataset_type: v })}
          formatOption={prettyDatasetType}
          disabled={simulationDisabled}
        />
      </Box>

      <Box>
        <Button variant="outlined" onClick={onReset}>
          Reset
        </Button>
      </Box>
    </Stack>
  )
}
