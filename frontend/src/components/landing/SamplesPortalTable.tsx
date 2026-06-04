import { useMemo } from 'react'
import { Box } from '@mui/material'
import ImageOutlinedIcon from '@mui/icons-material/ImageOutlined'
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table'
import type { SampleSummary } from '~/types'
import { AcquisitionsSubTable } from './AcquisitionsSubTable'

const dash = (v: unknown) => (v == null || v === '' ? '—' : String(v))

function Thumbnail() {
  return (
    <Box
      sx={{
        width: 56,
        height: 40,
        borderRadius: 1,
        bgcolor: 'action.hover',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'text.disabled',
      }}
    >
      <ImageOutlinedIcon fontSize="small" />
    </Box>
  )
}

export function SamplesPortalTable(props: {
  rows: SampleSummary[]
  loading?: boolean
}) {
  const { rows, loading } = props

  const columns = useMemo<MRT_ColumnDef<SampleSummary>[]>(
    () => [
      {
        id: 'thumbnail',
        header: '',
        columnDefType: 'display',
        size: 80,
        Cell: () => <Thumbnail />,
      },
      { accessorKey: 'sample_id', header: 'Sample id', minSize: 160 },
      { accessorKey: 'data_source', header: 'Data source' },
      { accessorKey: 'project', header: 'Project' },
      {
        accessorKey: 'type',
        header: 'Type',
        Cell: ({ cell }) => dash(cell.getValue()),
      },
      { accessorKey: 'n_acquisitions', header: 'Acq', size: 80 },
      { accessorKey: 'n_tilt_series', header: 'Tilt', size: 80 },
      { accessorKey: 'n_tomograms', header: 'Tomo', size: 80 },
    ],
    [],
  )

  const table = useMaterialReactTable({
    columns,
    data: rows,
    getRowId: (r) => r.sample_id,
    positionExpandColumn: 'first',
    // MRT wraps the panel in <Collapse mountOnEnter unmountOnExit>, so this
    // component only mounts (and fetches its sample detail) when the row is
    // expanded — acquisitions load lazily on demand, not N fetches up front.
    // Returning a truthy element here (rather than null when collapsed) is
    // what keeps each row's expand button enabled.
    renderDetailPanel: ({ row }) => (
      <AcquisitionsSubTable sampleId={row.original.sample_id} />
    ),
    enableColumnActions: false,
    enableColumnFilters: false,
    enableTopToolbar: false,
    enableDensityToggle: false,
    state: { isLoading: loading },
    initialState: {
      density: 'comfortable',
      pagination: { pageSize: 10, pageIndex: 0 },
    },
    muiTablePaperProps: {
      elevation: 0,
      sx: { border: 1, borderColor: 'divider', borderRadius: 2 },
    },
    muiDetailPanelProps: { sx: { p: 0 } },
  })

  return <MaterialReactTable table={table} />
}
