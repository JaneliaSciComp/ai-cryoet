import AddIcon from '@mui/icons-material/Add'
import RemoveIcon from '@mui/icons-material/Remove'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  RadioGroup,
  Stack,
  Typography,
} from '@mui/material'
import type { Field } from '~/utils/filterFields'
import type { SamplesSearchParams } from '~/utils/samplesSearch'
import type { FiltersOptionsOut } from '~/types'
import { MinMaxRow, prettyDatasetType } from '../LandingFilters'

type Props = {
  field: Field
  options: FiltersOptionsOut
  values: SamplesSearchParams
  onChange: (patch: Partial<SamplesSearchParams>) => void
  expanded: boolean
  onToggle: () => void
  disabled?: boolean
}

// Per-field display transform. Only the display string changes; the stored
// value is always the raw option string.
function optionLabel(fieldKey: string, v: string): string {
  if (fieldKey === 'dataset_type') return prettyDatasetType(v)
  if (fieldKey === 'data_source') return v.charAt(0).toUpperCase() + v.slice(1)
  return v
}

// A single filter property: a collapsed-by-default Accordion whose body renders
// by field.kind. Selection lives entirely in `values` (URL); emits patches up.
export function FilterProperty(props: Props) {
  const { field, options, values, onChange, expanded, onToggle, disabled } = props
  const v = values as Record<string, unknown>

  return (
    <Accordion
      expanded={expanded}
      onChange={onToggle}
      disableGutters
      elevation={0}
      square
      disabled={disabled}
      sx={{
        '&:before': { display: 'none' },
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <AccordionSummary
        expandIcon={expanded ? <RemoveIcon fontSize="small" /> : <AddIcon fontSize="small" />}
        aria-label={field.label}
        sx={{ px: 0, minHeight: 40, '& .MuiAccordionSummary-content': { my: 0.5 } }}
      >
        <Typography variant="body2" fontWeight={600}>{field.label}</Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 0, pt: 0 }}>
        {renderBody(field, options, v, onChange)}
      </AccordionDetails>
    </Accordion>
  )
}

const noValues = (
  <Typography variant="body2" fontStyle="italic" color="text.secondary">
    No values for this property have been provided or derived
  </Typography>
)

function renderBody(
  field: Field,
  options: FiltersOptionsOut,
  v: Record<string, unknown>,
  onChange: (patch: Partial<SamplesSearchParams>) => void,
) {
  switch (field.kind) {
    case 'text': {
      const opts = options.categorical[field.key] ?? []
      if (opts.length === 0) return noValues
      const selected = (v[field.key] as string[] | undefined) ?? []
      const toggle = (opt: string) => {
        const next = selected.includes(opt)
          ? selected.filter((s) => s !== opt)
          : [...selected, opt]
        onChange({ [field.key]: next.length ? next : undefined })
      }
      return (
        <FormControl component="fieldset" variant="standard" sx={{ width: '100%' }}>
          <FormLabel component="legend" sx={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>
            {field.label}
          </FormLabel>
          <Stack>
            {opts.map((opt) => (
              <FormControlLabel
                key={opt}
                sx={{ ml: 0 }}
                control={
                  <Checkbox
                    size="small"
                    checked={selected.includes(opt)}
                    onChange={() => toggle(opt)}
                  />
                }
                label={<Typography variant="body2">{optionLabel(field.key, opt)}</Typography>}
              />
            ))}
          </Stack>
        </FormControl>
      )
    }
    case 'range': {
      const bounds = options.ranges[field.key]
      if (!bounds || (bounds.min == null && bounds.max == null)) return noValues
      return (
        <MinMaxRow
          label={
            bounds && (bounds.min != null || bounds.max != null)
              ? `${bounds.min ?? ''}–${bounds.max ?? ''}`
              : ''
          }
          min={v[`${field.key}_min`] as number | undefined}
          max={v[`${field.key}_max`] as number | undefined}
          onMin={(val) => onChange({ [`${field.key}_min`]: val })}
          onMax={(val) => onChange({ [`${field.key}_max`]: val })}
        />
      )
    }
    case 'boolean': {
      const cur = v[field.key] as boolean | undefined
      const strVal = cur === true ? 'yes' : cur === false ? 'no' : 'any'
      return (
        <FormControl component="fieldset" variant="standard">
          <FormLabel component="legend" sx={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>
            {field.label}
          </FormLabel>
          <RadioGroup
            row
            value={strVal}
            onChange={(e) => {
              const val =
                e.target.value === 'yes' ? true : e.target.value === 'no' ? false : undefined
              onChange({ [field.key]: val })
            }}
          >
            <FormControlLabel value="yes" control={<Radio size="small" />} label="Yes" />
            <FormControlLabel value="no" control={<Radio size="small" />} label="No" />
            <FormControlLabel value="any" control={<Radio size="small" />} label="Any" />
          </RadioGroup>
        </FormControl>
      )
    }
    case 'existence': {
      const checked = v[field.key] === true
      return (
        <FormControlLabel
          sx={{ ml: 0 }}
          control={
            <Checkbox
              size="small"
              checked={checked}
              onChange={(e) => onChange({ [field.key]: e.target.checked ? true : undefined })}
            />
          }
          label={<Typography variant="body2">{field.label}</Typography>}
        />
      )
    }
  }
}
