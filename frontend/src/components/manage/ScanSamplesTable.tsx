import { useMemo } from 'react'
import { Box, Stack, Typography } from '@mui/material'
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table'
import { CustomLink } from '~/components/CustomLink'
import type { ScanSampleOut, SampleWarningsGroup } from '~/types'

type Outcome = 'upserted' | 'skipped' | 'failed'

const dash = (v: unknown) => (v == null || v === '' ? '—' : String(v))

const SampleIdLink = ({ sampleId }: { sampleId: string }) => (
  <CustomLink to="/samples/$sampleId" params={{ sampleId }}>
    {sampleId}
  </CustomLink>
)

const metadataColumns: MRT_ColumnDef<ScanSampleOut>[] = [
  {
    accessorKey: 'data_source',
    header: 'Data source',
    Cell: ({ cell }) => dash(cell.getValue()),
  },
  {
    accessorKey: 'project',
    header: 'Project',
    Cell: ({ cell }) => dash(cell.getValue()),
  },
  {
    accessorKey: 'type',
    header: 'Type',
    Cell: ({ cell }) => dash(cell.getValue()),
  },
]

export function ScanSamplesTable({
  outcome,
  rows,
  warningsBySample,
}: {
  outcome: Outcome
  rows: ScanSampleOut[]
  warningsBySample: Map<string, string[]>
}) {
  const columns = useMemo<MRT_ColumnDef<ScanSampleOut>[]>(() => {
    if (outcome === 'failed') {
      return [
        {
          accessorKey: 'sample_id',
          header: 'Sample id',
          size: 220,
          // Failed samples may never have been persisted — keep as plain text.
          Cell: ({ cell }) => dash(cell.getValue()),
        },
        {
          accessorKey: 'detail',
          header: 'Error',
          Cell: ({ cell }) => dash(cell.getValue()),
        },
      ]
    }

    const base: MRT_ColumnDef<ScanSampleOut>[] = [
      {
        accessorKey: 'sample_id',
        header: 'Sample id',
        size: 220,
        Cell: ({ row }) => <SampleIdLink sampleId={row.original.sample_id} />,
      },
      ...metadataColumns,
    ]

    if (outcome === 'upserted') {
      base.push({
        accessorKey: 'warning_count',
        header: 'Warnings',
        size: 120,
        Cell: ({ cell }) => (cell.getValue<number>() ?? 0).toLocaleString(),
      })
    }
    return base
  }, [outcome])

  const table = useMaterialReactTable<ScanSampleOut>({
    columns,
    data: rows,
    getRowId: (r) => r.sample_id,
    enableTopToolbar: false,
    enableBottomToolbar: false,
    enablePagination: false,
    enableColumnActions: false,
    enableColumnFilters: false,
    enableSorting: false,
    initialState: { density: 'comfortable' },
    muiTablePaperProps: { elevation: 0, sx: { borderRadius: 0 } },
    muiDetailPanelProps: { sx: { p: 0 } },
    localization: { noRecordsToDisplay: 'No samples in this category.' },
    // Only upserted rows carry warnings worth expanding into. Returning null
    // for warning-free rows disables their expand toggle (per MRT behavior),
    // which is exactly the UX we want.
    ...(outcome === 'upserted'
      ? {
          renderDetailPanel: ({ row }) => {
            const warnings = warningsBySample.get(row.original.sample_id)
            if (!warnings || warnings.length === 0) return null
            return (
              <Box sx={{ p: 2, bgcolor: 'action.hover' }}>
                <Typography variant="overline" color="text.secondary">
                  Warnings
                </Typography>
                <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                  {warnings.map((w, i) => (
                    <Typography key={i} variant="body2">
                      {w}
                    </Typography>
                  ))}
                </Stack>
              </Box>
            )
          },
        }
      : {}),
  })

  return <MaterialReactTable table={table} />
}
