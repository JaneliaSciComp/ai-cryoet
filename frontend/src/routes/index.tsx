import { createFileRoute, Link } from '@tanstack/react-router'
import {
  Box,
  Button,
  Chip,
  Grid,
  Stack,
  Typography,
} from '@mui/material'
import {
  latestScanQueryOptions,
  statsOverviewQueryOptions,
  useLatestScanQuery,
  useStatsOverviewQuery,
} from '~/utils/queryOptions'
import { ProjectSummaryCard } from '~/components/common/ProjectSummaryCard'
import { StatCard } from '~/components/common/StatCard'
import type { ScanOut } from '~/types'

export const Route = createFileRoute('/')({
  loader: ({ context: { queryClient } }) =>
    Promise.all([
      queryClient.ensureQueryData(statsOverviewQueryOptions),
      queryClient.ensureQueryData(latestScanQueryOptions),
    ]),
  component: Home,
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

function LastScanLine({ scan }: { scan: ScanOut | null }) {
  if (!scan) {
    return (
      <Typography variant="body2" color="text.secondary">
        No scans yet.
      </Typography>
    )
  }
  const when = formatTimestamp(scan.ended_at ?? scan.started_at)
  const upserted = scan.samples_upserted ?? 0
  return (
    <Stack
      direction="row"
      spacing={1}
      alignItems="center"
      flexWrap="wrap"
      useFlexGap
    >
      <Typography variant="body2" color="text.secondary">
        Last scan: {when} —
      </Typography>
      <Chip
        size="small"
        color={statusColor(scan.status)}
        label={scan.status}
      />
      <Typography variant="body2" color="text.secondary">
        ({upserted} upserted)
      </Typography>
      <Typography variant="body2" color="text.secondary">
        ·
      </Typography>
      <Link to="/scans" style={{ textDecoration: 'none' }}>
        <Typography variant="body2" color="primary">
          View all scans
        </Typography>
      </Link>
    </Stack>
  )
}

function Home() {
  const { data: stats } = useStatsOverviewQuery()
  const { data: latestScan } = useLatestScanQuery()
  const { totals, by_project } = stats

  return (
    <Stack spacing={4}>
      <Typography variant="h3" gutterBottom>
        CryoET Catalog
      </Typography>

      {by_project.length > 0 ? (
        <Box>
          <Typography variant="h5" gutterBottom>
            Projects
          </Typography>
          <Grid container spacing={2}>
            {by_project.map((row) => (
              <Grid item xs={12} sm={6} md={4} key={row.project}>
                <ProjectSummaryCard row={row} />
              </Grid>
            ))}
          </Grid>
        </Box>
      ) : null}

      <Box>
        <Typography variant="h5" gutterBottom>
          Totals
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={6} sm={4} md={2.4}>
            <StatCard label="Samples" value={totals.samples} />
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <StatCard label="Acquisitions" value={totals.acquisitions} />
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <StatCard label="Tilt series" value={totals.tilt_series} />
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <StatCard label="Tomograms" value={totals.tomograms} />
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <StatCard label="Annotations" value={totals.annotations} />
          </Grid>
        </Grid>
      </Box>

      <Box>
        <Typography variant="h5" gutterBottom>
          Browse
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" component={Link} to="/samples">
            Browse samples
          </Button>
          <Button variant="outlined" component={Link} to="/scans">
            Scan history
          </Button>
        </Stack>
      </Box>

      <Box>
        <LastScanLine scan={latestScan} />
      </Box>
    </Stack>
  )
}
