import { useMemo, useState } from 'react'
import {
  Box,
  MenuItem,
  Stack,
  TextField,
  alpha,
} from '@mui/material'
import {
  MaterialReactTable,
  MRT_TablePagination,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table'
import type { IssueGroup } from '~/types'
import {
  type IssueFilters,
  useOutstandingIssuesQuery,
} from '~/utils/queryOptions'
import {
  EntityCell,
  FileCell,
  IssuesCell,
  SeverityPill,
  StillPresentCell,
  formatDate,
  issueRowId,
} from './issueCells'

// File-kind options come from the contract's enum; we also fold in any kinds
// present in the current rows so the select never hides a value in the data.
const FILE_KIND_OPTIONS = [
  'sample_toml',
  'acquisition_toml',
  'md_run_toml',
  'mdoc',
  'mrc_header',
  'zarr_attrs',
  'frames',
  'filesystem',
  'other',
]

function useColumns(): MRT_ColumnDef<IssueGroup>[] {
  return useMemo(
    () => [
      {
        id: 'entity',
        header: 'Sample / Acquisition',
        size: 220,
        Cell: ({ row }) => <EntityCell group={row.original} />,
      },
      {
        id: 'file',
        header: 'File',
        size: 260,
        Cell: ({ row }) => <FileCell group={row.original} />,
      },
      {
        accessorKey: 'severity',
        header: 'Severity',
        size: 110,
        Cell: ({ row }) => <SeverityPill severity={row.original.severity} />,
      },
      {
        id: 'issues',
        header: 'Issues',
        Cell: ({ row }) => <IssuesCell group={row.original} />,
      },
      {
        accessorKey: 'first_seen_at',
        header: 'First seen',
        size: 130,
        Cell: ({ cell }) => formatDate(cell.getValue<number>()),
      },
      {
        id: 'still_present',
        header: 'Still present as of',
        size: 170,
        Cell: ({ row }) => <StillPresentCell group={row.original} />,
      },
    ],
    [],
  )
}

export function OutstandingIssuesTable({
  initialFilters = {},
}: {
  // Seeded from the manage route's URL search params so a "view metadata
  // errors" link lands here pre-filtered to one sample/acquisition.
  initialFilters?: IssueFilters
}) {
  const [filters, setFilters] = useState<IssueFilters>(initialFilters)
  const { data = [], isFetching, isError } = useOutstandingIssuesQuery(filters)
  const columns = useColumns()

  const setFilter = <K extends keyof IssueFilters>(
    key: K,
    value: IssueFilters[K] | '',
  ) =>
    setFilters((prev) => {
      const next = { ...prev }
      if (value === '' || value == null) delete next[key]
      else next[key] = value as IssueFilters[K]
      return next
    })

  const fileKinds = useMemo(() => {
    const present = new Set(data.map((g) => g.file_kind))
    return Array.from(new Set([...FILE_KIND_OPTIONS, ...present]))
  }, [data])

  const table = useMaterialReactTable<IssueGroup>({
    columns,
    data,
    getRowId: issueRowId,
    state: { showProgressBars: isFetching, showAlertBanner: isError },
    muiToolbarAlertBannerProps: isError
      ? { color: 'error', children: 'Failed to load outstanding issues.' }
      : undefined,
    enableColumnActions: false,
    enableColumnFilters: false,
    enableDensityToggle: false,
    enableSorting: true,
    // The toolbar is our own filter controls; MRT's built-ins are off.
    enableGlobalFilter: false,
    // Paginated, 10 rows by default; the page-size selector (5/10/15/20/25)
    // lives in the top toolbar beside the filters. Bottom toolbar off.
    enablePagination: true,
    enableBottomToolbar: false,
    initialState: {
      density: 'comfortable',
      sorting: [{ id: 'severity', desc: false }],
      pagination: { pageSize: 10, pageIndex: 0 },
    },
    // Match the portal tables (/data, /experimental, /md-simulation).
    muiTablePaperProps: {
      elevation: 0,
      sx: { border: 1, borderColor: 'divider', borderRadius: 2 },
    },
    localization: { noRecordsToDisplay: 'No outstanding warnings or errors.' },
    renderTopToolbar: ({ table }) => (
      <Box
        sx={{
          p: 1.5,
          bgcolor: (t) => alpha(t.palette.primary.main, 0.12),
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1.5,
          flexWrap: 'wrap',
        }}
      >
        <Stack
          direction="row"
          spacing={1.5}
          alignItems="center"
          flexWrap="wrap"
          useFlexGap
          sx={{ flex: 1 }}
        >
          <TextField
            size="small"
            placeholder="Filter by sample, project, or path…"
            value={filters.q ?? ''}
            onChange={(e) => setFilter('q', e.target.value)}
            sx={{ flex: 1, minWidth: 220, maxWidth: 320, bgcolor: 'common.white' }}
          />
          <TextField
            select
            size="small"
            label="Severity"
            value={filters.severity ?? ''}
            onChange={(e) =>
              setFilter('severity', e.target.value as IssueFilters['severity'])
            }
            sx={{ minWidth: 150, bgcolor: 'common.white' }}
          >
            <MenuItem value="">All severities</MenuItem>
            <MenuItem value="error">Errors only</MenuItem>
            <MenuItem value="warning">Warnings only</MenuItem>
          </TextField>
          <TextField
            select
            size="small"
            label="File"
            value={filters.file_kind ?? ''}
            onChange={(e) => setFilter('file_kind', e.target.value)}
            sx={{ minWidth: 170, bgcolor: 'common.white' }}
          >
            <MenuItem value="">All files</MenuItem>
            {fileKinds.map((kind) => (
              <MenuItem key={kind} value={kind}>
                {kind}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
        <MRT_TablePagination table={table} />
      </Box>
    ),
  })

  return <MaterialReactTable table={table} />
}
