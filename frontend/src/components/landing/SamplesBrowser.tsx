import { useState } from "react";
import {
  Box,
  Button,
  Chip,
  Drawer,
  Grid,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import FilterListIcon from "@mui/icons-material/FilterList";
import CloseIcon from "@mui/icons-material/Close";
import { useFiltersOptionsQuery, useSamplesQuery } from "~/utils/queryOptions";
import { useDebounce } from "~/hooks/useDebounce";
import type { SamplesSearchParams } from "~/utils/samplesSearch";
import {
  LandingFilters,
  type LandingFilterState,
} from "~/components/landing/LandingFilters";
import { SamplesPortalTable } from "~/components/landing/SamplesPortalTable";

// Each browse page is scoped to a single `data_source` arm of the catalog
// (Experimental/ vs MdSimulation/). The value is forced into every samples
// query here, so it is deliberately NOT part of `LandingFilterState` or the
// side-panel — a page only ever shows its own arm.
export type DataSource = "experimental" | "simulation";

// The route's `navigate`, narrowed to the only shape this component uses.
type NavigateFn = (opts: {
  search: (prev: SamplesSearchParams) => SamplesSearchParams;
  replace?: boolean;
}) => void;

// ── URL search <-> drawer state ──────────────────────────────────────────────
// The drawer models a simplified, single-valued shape (`LandingFilterState`);
// the URL holds the full `SamplesSearchParams` (e.g. `microscope` is an array).
// These two helpers translate between them.

function searchToFilters(s: SamplesSearchParams): LandingFilterState {
  return {
    project: s.project,
    dataset_type: s.dataset_type?.[0],
    microscope: s.microscope?.[0],
    pixel_size_min: s.pixel_size_min,
    pixel_size_max: s.pixel_size_max,
    n_tilts_min: s.n_tilts_min,
    n_tilts_max: s.n_tilts_max,
    has_tomograms: s.has_tomograms,
  };
}

function applyFilterPatch(
  prev: SamplesSearchParams,
  patch: Partial<LandingFilterState>,
): SamplesSearchParams {
  const next: SamplesSearchParams = { ...prev };
  const set = <K extends keyof SamplesSearchParams>(
    key: K,
    value: SamplesSearchParams[K] | undefined,
  ) => {
    // Drop empty values so they don't linger as bare keys in the URL.
    if (value === undefined) delete next[key];
    else next[key] = value;
  };

  if ("project" in patch) set("project", patch.project);
  if ("dataset_type" in patch)
    set("dataset_type", patch.dataset_type ? [patch.dataset_type] : undefined);
  if ("microscope" in patch)
    set("microscope", patch.microscope ? [patch.microscope] : undefined);
  if ("pixel_size_min" in patch) set("pixel_size_min", patch.pixel_size_min);
  if ("pixel_size_max" in patch) set("pixel_size_max", patch.pixel_size_max);
  if ("n_tilts_min" in patch) set("n_tilts_min", patch.n_tilts_min);
  if ("n_tilts_max" in patch) set("n_tilts_max", patch.n_tilts_max);
  if ("has_tomograms" in patch)
    set("has_tomograms", patch.has_tomograms ? true : undefined);
  return next;
}

function activeChips(
  f: LandingFilterState,
  showMicroscope: boolean,
  showDataType: boolean,
): Array<{ key: keyof LandingFilterState; label: string }> {
  const chips: Array<{ key: keyof LandingFilterState; label: string }> = [];
  if (f.project) chips.push({ key: "project", label: `Project: ${f.project}` });
  if (showDataType && f.dataset_type)
    chips.push({
      key: "dataset_type",
      label: `Data type: ${f.dataset_type.replace(/_/g, " ")}`,
    });
  if (showMicroscope && f.microscope)
    chips.push({ key: "microscope", label: `Microscope: ${f.microscope}` });
  if (f.pixel_size_min != null)
    chips.push({
      key: "pixel_size_min",
      label: `Pixel size ≥ ${f.pixel_size_min}`,
    });
  if (f.pixel_size_max != null)
    chips.push({
      key: "pixel_size_max",
      label: `Pixel size ≤ ${f.pixel_size_max}`,
    });
  if (f.n_tilts_min != null)
    chips.push({ key: "n_tilts_min", label: `Tilts ≥ ${f.n_tilts_min}` });
  if (f.n_tilts_max != null)
    chips.push({ key: "n_tilts_max", label: `Tilts ≤ ${f.n_tilts_max}` });
  if (f.has_tomograms)
    chips.push({ key: "has_tomograms", label: "Has tomograms" });
  return chips;
}

export function SamplesBrowser(props: {
  title: string;
  dataSource: DataSource;
  search: SamplesSearchParams;
  navigate: NavigateFn;
}) {
  const { title, dataSource, search, navigate } = props;
  const { data: filterOptions } = useFiltersOptionsQuery();

  // The URL updates immediately on every change (for shareability); debounce
  // only the value that drives the query so typing in the range fields doesn't
  // fire a request per keystroke. `data_source` is forced so the page only ever
  // shows its own arm of the catalog, regardless of the URL.
  const debouncedSearch = useDebounce(search, 300);
  const { data: samples, isFetching } = useSamplesQuery({
    ...debouncedSearch,
    data_source: dataSource,
  });
  const rows = samples ?? [];

  // Denominator for "Showing X of Y": all samples in this arm, ignoring the
  // user's filters.
  const { data: baseSamples } = useSamplesQuery({ data_source: dataSource });
  const total = baseSamples?.length ?? rows.length;

  const filters = searchToFilters(search);

  const patch = (p: Partial<LandingFilterState>) =>
    navigate({ search: (prev) => applyFilterPatch(prev, p), replace: true });
  const clearKey = (key: keyof LandingFilterState) =>
    navigate({
      search: (prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      },
      replace: true,
    });
  const reset = () => navigate({ search: () => ({}), replace: true });

  const chips = activeChips(
    filters,
    dataSource !== "simulation",
    dataSource === "simulation",
  );

  // On small screens the sidebar collapses into a button that opens this drawer.
  const [filtersOpen, setFiltersOpen] = useState(false);

  const filterPanel = (
    <LandingFilters
      options={filterOptions}
      value={filters}
      onChange={patch}
      onReset={reset}
      showMicroscope={dataSource !== "simulation"}
      showDataType={dataSource === "simulation"}
    />
  );

  return (
    <Grid container spacing={4}>
      {/* md+: filters live in a sidebar. On xs they move into the drawer below. */}
      <Grid
        item
        xs={12}
        md={3}
        lg={2}
        sx={{ display: { xs: "none", md: "block" } }}
      >
        {filterPanel}
      </Grid>

      <Grid item xs={12} md={9} lg={10}>
        {/*
          The title lives in the content column (not above the whole grid) so it
          aligns with the table, and the filters column rises to share the top
          row with it.
        */}
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
            {/* xs only: open the filters drawer. */}
            <Button
              variant="outlined"
              startIcon={<FilterListIcon />}
              onClick={() => setFiltersOpen(true)}
              sx={{ display: { xs: "inline-flex", md: "none" }, flexShrink: 0 }}
            >
              Filters{chips.length > 0 ? ` (${chips.length})` : ""}
            </Button>
          </Stack>
          <Box>
            <Typography variant="h6">
              Showing {rows.length.toLocaleString()} of {total.toLocaleString()}{" "}
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

        </Stack>
        <Box sx={{ mt: 0 }}>
          <SamplesPortalTable rows={rows} loading={isFetching} />
        </Box>
      </Grid>

      {/* xs filters drawer; live-applies as you change values (no Apply step). */}
      <Drawer
        anchor="left"
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        sx={{ display: { md: "none" } }}
      >
        <Box sx={{ width: 300, p: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
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
  );
}
