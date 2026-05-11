import { createFileRoute } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Chip,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import { DataGrid } from '@mui/x-data-grid'
import type { GridColDef } from '@mui/x-data-grid'
import { scansQueryOptions, useScansQuery } from '~/utils/queryOptions'
import type { ScanOut } from '~/types'

export const Route = createFileRoute('/scans')({
  loader: ({ context: { queryClient } }) =>
    queryClient.ensureQueryData(scansQueryOptions),
  component: ScansPage,
})

function statusColor(
  s: string,
): 'success' | 'warning' | 'error' | 'default' {
  return s === 'completed'
    ? 'success'
    : s === 'running'
      ? 'warning'
      : s === 'failed'
        ? 'error'
        : 'default'
}

function formatTimestamp(seconds: number | null | undefined): string {
  if (seconds == null) return ''
  return new Date(seconds * 1000).toLocaleString()
}

const columns: GridColDef<ScanOut>[] = [
  {
    field: 'started_at',
    headerName: 'Started',
    width: 200,
    valueFormatter: (value: number | null | undefined) =>
      formatTimestamp(value),
  },
  {
    field: 'ended_at',
    headerName: 'Ended',
    width: 200,
    valueFormatter: (value: number | null | undefined) =>
      formatTimestamp(value),
  },
  {
    field: 'root',
    headerName: 'Root',
    flex: 1,
    minWidth: 240,
    renderCell: (params) => (
      <Tooltip title={params.value ?? ''} placement="top-start">
        <Box
          sx={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            width: '100%',
          }}
        >
          {params.value}
        </Box>
      </Tooltip>
    ),
  },
  {
    field: 'status',
    headerName: 'Status',
    width: 130,
    renderCell: (params) => (
      <Chip
        size="small"
        color={statusColor(params.value as string)}
        label={params.value}
      />
    ),
  },
  {
    field: 'samples_upserted',
    headerName: 'Upserted',
    type: 'number',
    width: 110,
  },
  {
    field: 'samples_skipped',
    headerName: 'Skipped',
    type: 'number',
    width: 110,
  },
  {
    field: 'samples_failed',
    headerName: 'Failed',
    type: 'number',
    width: 110,
  },
]

function ScansPage() {
  const { data: scans } = useScansQuery()
  const queryClient = useQueryClient()

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['scans', 'list'] })
  }

  return (
    <Stack spacing={2}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
      >
        <Typography variant="h4">Scans</Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={handleRefresh} aria-label="Refresh scans">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>
      <Box sx={{ height: 'calc(100vh - 200px)', width: '100%' }}>
        <DataGrid
          rows={scans}
          columns={columns}
          getRowId={(row) => row.scan_run_id}
          density="compact"
          disableRowSelectionOnClick
          pageSizeOptions={[25, 50, 100]}
          initialState={{
            pagination: { paginationModel: { pageSize: 25 } },
            sorting: { sortModel: [{ field: 'started_at', sort: 'desc' }] },
          }}
        />
      </Box>
    </Stack>
  )
}
