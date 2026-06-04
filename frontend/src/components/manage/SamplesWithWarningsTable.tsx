import { useMemo } from 'react'
import { Stack, Typography } from '@mui/material'
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table'
import { CustomLink } from '~/components/CustomLink'
import type { SampleWarningsGroup } from '~/types'

export function SamplesWithWarningsTable({
  groups,
}: {
  groups: SampleWarningsGroup[]
}) {
  const columns = useMemo<MRT_ColumnDef<SampleWarningsGroup>[]>(
    () => [
      {
        accessorKey: 'sample_id',
        header: 'Sample id',
        size: 200,
        Cell: ({ row }) => (
          <CustomLink
            to="/samples/$sampleId"
            params={{ sampleId: row.original.sample_id }}
          >
            {row.original.sample_id}
          </CustomLink>
        ),
      },
      {
        id: 'warnings',
        header: 'Warnings',
        accessorFn: (g) => g.warnings.join('\n'),
        Cell: ({ row }) => (
          <Stack spacing={0.5}>
            {row.original.warnings.map((w, i) => (
              <Typography key={i} variant="body2">
                {w}
              </Typography>
            ))}
          </Stack>
        ),
      },
    ],
    [],
  )

  const table = useMaterialReactTable({
    columns,
    data: groups,
    getRowId: (g) => g.sample_id,
    enableTopToolbar: false,
    enableBottomToolbar: false,
    enablePagination: false,
    enableColumnActions: false,
    enableColumnFilters: false,
    enableSorting: false,
    initialState: { density: 'comfortable' },
    muiTablePaperProps: { elevation: 0, sx: { borderRadius: 0 } },
    localization: { noRecordsToDisplay: 'No samples with warnings.' },
  })

  return <MaterialReactTable table={table} />
}
