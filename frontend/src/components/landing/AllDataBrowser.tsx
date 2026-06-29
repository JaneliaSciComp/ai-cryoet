import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  Drawer,
  Grid,
  IconButton,
  Stack,
  Typography,
} from '@mui/material'
import FilterListIcon from '@mui/icons-material/FilterList'
import CloseIcon from '@mui/icons-material/Close'
import { useFiltersOptionsQuery, useSamplesQuery } from '~/utils/queryOptions'
import { useDebounce } from '~/hooks/useDebounce'
import type { SamplesSearchParams } from '~/utils/samplesSearch'
import {
  AllDataFilters,
  type AllDataFilterState,
} from '~/components/landing/AllDataFilters'
import { SamplesPortalTable } from '~/components/landing/SamplesPortalTable'

// The /data page spans both arms of the catalog. Unlike SamplesBrowser (which
// forces a single `data_source`), here `data_source` is a user-settable filter
// and arm-specific filters (microscope / dataset_type) are always available.

type NavigateFn = (opts: {
  search: (prev: SamplesSearchParams) => SamplesSearchParams
  replace?: boolean
}) => void

// ── URL search <-> drawer state ──────────────────────────────────────────────

function searchToFilters(s: SamplesSearchParams): AllDataFilterState {
  return {
    data_source:
      s.data_source === 'experimental' || s.data_source === 'simulation'
        ? s.data_source
        : undefined,
    project: s.project,
    dataset_type: s.dataset_type?.[0],
    microscope: s.microscope?.[0],
    pixel_size_min: s.pixel_size_min,
    pixel_size_max: s.pixel_size_max,
    has_tomograms: s.has_tomograms,
  }
}

function applyFilterPatch(
  prev: SamplesSearchParams,
  patch: Partial<AllDataFilterState>,
): SamplesSearchParams {
  const next: SamplesSearchParams = { ...prev }
  const set = <K extends keyof SamplesSearchParams>(
    key: K,
    value: SamplesSearchParams[K] | undefined,
  ) => {
    if (value === undefined) delete next[key]
    else next[key] = value
  }

  if ('data_source' in patch) {
    set('data_source', patch.data_source)
    // Selecting one arm clears the opposite arm's filter so a stale value
    // doesn't silently exclude every sample in the newly-selected arm.
    if (patch.data_source === 'experimental') delete next.dataset_type
    if (patch.data_source === 'simulation') delete next.microscope
  }
  if ('project' in patch) set('project', patch.project)
  if ('dataset_type' in patch)
    set('dataset_type', patch.dataset_type ? [patch.dataset_type] : undefined)
  if ('microscope' in patch)
    set('microscope', patch.microscope ? [patch.microscope] : undefined)
  if ('pixel_size_min' in patch) set('pixel_size_min', patch.pixel_size_min)
  if ('pixel_size_max' in patch) set('pixel_size_max', patch.pixel_size_max)
  if ('has_tomograms' in patch)
    set('has_tomograms', patch.has_tomograms ? true : undefined)
  return next
}

function prettyDataSource(v: string): string {
  return v.charAt(0).toUpperCase() + v.slice(1)
}

function activeChips(
  f: AllDataFilterState,
): Array<{ key: keyof AllDataFilterState; label: string }> {
  const chips: Array<{ key: keyof AllDataFilterState; label: string }> = []
  if (f.data_source)
    chips.push({
      key: 'data_source',
      label: `Data source: ${prettyDataSource(f.data_source)}`,
    })
  if (f.project) chips.push({ key: 'project', label: `Project: ${f.project}` })
  if (f.microscope)
    chips.push({ key: 'microscope', label: `Microscope: ${f.microscope}` })
  if (f.dataset_type)
    chips.push({
      key: 'dataset_type',
      label: `Data type: ${f.dataset_type.replace(/_/g, ' ')}`,
    })
  if (f.pixel_size_min != null)
    chips.push({
      key: 'pixel_size_min',
      label: `Pixel size ≥ ${f.pixel_size_min}`,
    })
  if (f.pixel_size_max != null)
    chips.push({
      key: 'pixel_size_max',
      label: `Pixel size ≤ ${f.pixel_size_max}`,
    })
  if (f.has_tomograms)
    chips.push({ key: 'has_tomograms', label: 'Has tomograms' })
  return chips
}

// Arm-specific filters and the arm they belong to. When one of these is set but
// no `data_source` is selected, the filter implicitly restricts results to its
// arm, so we warn the user (the filter has no effect on the other arm).
const ARM_SPECIFIC: Array<{
  key: 'microscope' | 'dataset_type'
  name: string
  arm: 'experimental' | 'simulation'
}> = [
  { key: 'microscope', name: 'Microscope', arm: 'experimental' },
  { key: 'dataset_type', name: 'Data type', arm: 'simulation' },
]

function armWarnings(f: AllDataFilterState): string[] {
  if (f.data_source) return []
  return ARM_SPECIFIC.filter((a) => f[a.key] != null).map(
    (a) =>
      `${a.name} only applies to ${a.arm} data — only ${a.arm} samples and acquisitions matching this filter are shown.`,
  )
}

export function AllDataBrowser(props: {
  title: string
  search: SamplesSearchParams
  navigate: NavigateFn
}) {
  const { title, search, navigate } = props
  const { data: filterOptions } = useFiltersOptionsQuery()

  // The URL updates immediately for shareability; debounce only the value that
  // drives the query so typing in the range fields doesn't fire a request per
  // keystroke. `data_source` flows through from the URL — it is a filter here.
  const debouncedSearch = useDebounce(search, 300)
  const { data: samples, isFetching } = useSamplesQuery(debouncedSearch)
  const rows = samples ?? []

  // Denominator for "Showing X of Y": every sample across both arms, ignoring
  // the user's filters.
  const { data: baseSamples } = useSamplesQuery({})
  const total = baseSamples?.length ?? rows.length

  const filters = searchToFilters(search)
  const warnings = armWarnings(filters)

  const patch = (p: Partial<AllDataFilterState>) =>
    navigate({ search: (prev) => applyFilterPatch(prev, p), replace: true })
  const clearKey = (key: keyof AllDataFilterState) =>
    navigate({
      search: (prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      },
      replace: true,
    })
  const reset = () => navigate({ search: () => ({}), replace: true })

  const chips = activeChips(filters)

  // On small screens the sidebar collapses into a button that opens this drawer.
  const [filtersOpen, setFiltersOpen] = useState(false)

  const filterPanel = (
    <AllDataFilters
      options={filterOptions}
      value={filters}
      onChange={patch}
      onReset={reset}
    />
  )

  return (
    <Grid container spacing={4}>
      <Grid
        item
        xs={12}
        md={3}
        lg={2}
        sx={{ display: { xs: 'none', md: 'block' } }}
      >
        {filterPanel}
      </Grid>

      <Grid item xs={12} md={9} lg={10}>
        <Stack spacing={2}>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            spacing={2}
          >
            <Typography variant="h4" component="h1">
              {title}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<FilterListIcon />}
              onClick={() => setFiltersOpen(true)}
              sx={{ display: { xs: 'inline-flex', md: 'none' }, flexShrink: 0 }}
            >
              Filters{chips.length > 0 ? ` (${chips.length})` : ''}
            </Button>
          </Stack>
          <Box>
            <Typography variant="h6">
              Showing {rows.length.toLocaleString()} of {total.toLocaleString()}{' '}
              samples
            </Typography>
            {/* Reserve a row's height whether or not chips are present so the
                table doesn't jump as filters are added/removed. */}
            <Box sx={{ mt: 1, minHeight: 40 }}>
              {chips.length > 0 ? (
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  flexWrap="wrap"
                  useFlexGap
                >
                  <Typography variant="body2" color="text.secondary">
                    Filtered by:
                  </Typography>
                  {chips.map((c) => (
                    <Chip
                      key={c.key}
                      size="small"
                      label={c.label}
                      onDelete={() => clearKey(c.key)}
                    />
                  ))}
                  <Chip
                    size="small"
                    color="primary"
                    label="Clear all"
                    onClick={reset}
                  />
                </Stack>
              ) : null}
            </Box>
          </Box>

          {warnings.length > 0 ? (
            <Stack spacing={1}>
              {warnings.map((w) => (
                <Alert key={w} severity="warning">
                  {w}
                </Alert>
              ))}
            </Stack>
          ) : null}

        </Stack>
        {/* Table sits outside the spaced Stack so its top gap is controlled
            here rather than inheriting the Stack's 24px spacing. */}
        <Box sx={{ mt: 1 }}>
          <SamplesPortalTable rows={rows} loading={isFetching} />
        </Box>
      </Grid>

      <Drawer
        anchor="left"
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        sx={{ display: { md: 'none' } }}
      >
        <Box sx={{ width: 300, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
            <IconButton
              aria-label="Close filters"
              onClick={() => setFiltersOpen(false)}
            >
              <CloseIcon />
            </IconButton>
          </Box>
          {filterPanel}
        </Box>
      </Drawer>
    </Grid>
  )
}
