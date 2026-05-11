import { Card, CardContent, Stack, Typography } from '@mui/material'
import type { ProjectStatRow } from '~/types'

interface ProjectSummaryCardProps {
  row: ProjectStatRow
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(1)} ${units[unit]}`
}

export function ProjectSummaryCard(props: ProjectSummaryCardProps) {
  const { row } = props
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" component="div" gutterBottom>
          {row.project}
        </Typography>
        <Stack direction="row" spacing={3} flexWrap="wrap">
          <Stat label="Samples" value={row.samples} />
          <Stat label="Acquisitions" value={row.acquisitions} />
          <Stat label="Tomograms" value={row.tomograms} />
          <Stat label="Size" value={formatBytes(row.size_bytes)} />
        </Stack>
      </CardContent>
    </Card>
  )
}

function Stat(props: { label: string; value: string | number }) {
  const { label, value } = props
  return (
    <Stack>
      <Typography variant="overline" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h6">{value}</Typography>
    </Stack>
  )
}
