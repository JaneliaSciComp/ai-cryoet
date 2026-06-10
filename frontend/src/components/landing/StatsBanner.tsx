import { Box, Grid, Paper, Typography } from '@mui/material'
import type { StatsOverviewOut } from '~/types'

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

function BannerStatCard(props: { label: string; value: string | number }) {
  const { label, value } = props
  return (
    <Paper
      elevation={0}
      sx={{
        px: 2.5,
        py: 1.75,
        minWidth: 150,
        borderRadius: 2,
        height: '100%',
      }}
    >
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {label}
      </Typography>
      <Typography variant="h4" component="div" color="primary.dark">
        {value}
      </Typography>
    </Paper>
  )
}

export function StatsBanner({ stats }: { stats: StatsOverviewOut }) {
  const { totals, by_project } = stats
  const totalBytes = by_project.reduce((sum, p) => sum + (p.size_bytes ?? 0), 0)

  const cards = [
    { label: 'Total data', value: formatBytes(totalBytes) },
    { label: 'Samples', value: totals.samples.toLocaleString() },
    { label: 'Acquisitions', value: totals.acquisitions.toLocaleString() },
    { label: 'Tomograms', value: totals.tomograms.toLocaleString() },
  ]

  return (
    <Box
      sx={{
        bgcolor: 'primary.dark',
        color: 'common.white',
        borderRadius: 2,
        px: { xs: 2, md: 4 },
        py: 3,
      }}
    >
      <Typography variant="h5" component="h2" gutterBottom>
        All data at a glance
      </Typography>
      <Grid container spacing={2}>
        {cards.map((c) => (
          <Grid item xs={6} sm={3} key={c.label}>
            <BannerStatCard label={c.label} value={c.value} />
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}
