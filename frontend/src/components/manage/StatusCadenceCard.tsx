import { useMemo } from 'react'
import { Box, Chip, Paper, Stack, Typography } from '@mui/material'
import ScheduleIcon from '@mui/icons-material/Schedule'
import { CronExpressionParser } from 'cron-parser'
import cronstrue from 'cronstrue'
import type { ManageLatestScan, ManageSummary } from '~/types'

// Scan timestamps are Unix seconds; render in the viewer's locale.
function formatTs(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  return new Date(seconds * 1000).toLocaleString(undefined, { timeZoneName: 'short' })
}

// Map the scan status onto a brand-themed chip colour.
function statusColor(
  status: string,
): 'success' | 'error' | 'warning' | 'default' {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'running':
      return 'warning'
    default:
      return 'default'
  }
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <Box sx={{ minWidth: 150 }}>
      <Typography
        variant="caption"
        sx={{
          textTransform: 'uppercase',
          letterSpacing: '.05em',
          color: 'text.secondary',
          display: 'block',
        }}
      >
        {label}
      </Typography>
      <Box sx={{ mt: 0.5 }}>{children}</Box>
    </Box>
  )
}

// Compute "Every hour · next ≈ HH:MM" from the cron expression. The cron fires
// in the cluster timezone (`cadence_tz`), but the next-fire instant it returns
// is absolute, so we render it in the user's LOCAL time (plan §3.4). Returns
// null when the expression can't be parsed.
function useCadence(
  cron: string,
  tz: string,
): { human: string; nextLocal: string } | null {
  return useMemo(() => {
    try {
      const human = cronstrue.toString(cron, { verbose: false })
      const interval = CronExpressionParser.parse(cron, {
        currentDate: new Date(),
        tz,
      })
      const next = interval.next().toDate()
      const nextLocal = next.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      })
      return { human, nextLocal }
    } catch {
      return null
    }
  }, [cron, tz])
}

function LastScanFields({ scan }: { scan: ManageLatestScan }) {
  return (
    <Stack direction="row" spacing={4} flexWrap="wrap" useFlexGap>
      <Field label="Last scan started">
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {formatTs(scan.started_at)}
        </Typography>
      </Field>
      <Field label="Last scan ended">
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {formatTs(scan.ended_at)}
        </Typography>
      </Field>
      <Field label="Status">
        <Chip
          label={scan.status}
          size="small"
          color={statusColor(scan.status)}
          variant="outlined"
        />
      </Field>
    </Stack>
  )
}

export function StatusCadenceCard({ summary }: { summary: ManageSummary }) {
  const cadence = useCadence(summary.cadence_cron, summary.cadence_tz)
  const { latest_scan } = summary

  return (
    <Stack spacing={2}>
      <Stack
        direction="row"
        spacing={2}
        flexWrap="wrap"
        useFlexGap
        alignItems="stretch"
      >
        <Paper variant="outlined" sx={{ px: 2.5, py: 2, borderRadius: 2 }}>
          {latest_scan ? (
            <LastScanFields scan={latest_scan} />
          ) : (
            <Typography variant="body2" color="text.secondary">
              No completed scans yet.
            </Typography>
          )}
        </Paper>

        <Paper variant="outlined" sx={{ px: 2.5, py: 2, borderRadius: 2 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <ScheduleIcon color="action" />
            <Field label="Scan cadence">
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {cadence
                  ? `${cadence.human} · next ≈ ${cadence.nextLocal}`
                  : summary.cadence_cron}
              </Typography>
            </Field>
          </Stack>
        </Paper>
      </Stack>

      <Typography variant="body2" color="text.secondary">
        Edited a{' '}
        <Box
          component="code"
          sx={{
            fontFamily: 'monospace',
            bgcolor: 'action.hover',
            px: 0.5,
            borderRadius: 0.5,
          }}
        >
          .toml
        </Box>{' '}
        after the last scan? Your change will appear after the next scan
        {cadence ? ` (~${cadence.nextLocal}).` : '.'}
      </Typography>
    </Stack>
  )
}
