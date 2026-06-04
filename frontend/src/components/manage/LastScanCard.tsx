import { Box, Paper, Stack, Typography } from '@mui/material'
import type { ScanOut } from '~/types'

// Scan timestamps are Unix seconds; render in the viewer's locale.
function formatTs(seconds: number | null): string {
  if (seconds == null) return '—'
  return new Date(seconds * 1000).toLocaleString()
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ minWidth: 160 }}>
      <Typography variant="subtitle2" gutterBottom>
        {label}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {value}
      </Typography>
    </Box>
  )
}

export function LastScanCard({ scan }: { scan: ScanOut | null }) {
  if (scan == null) {
    return (
      <Typography variant="body2" color="text.secondary">
        No completed scans yet.
      </Typography>
    )
  }

  return (
    <Paper
      variant="outlined"
      sx={{ px: 2.5, py: 2, borderRadius: 2, display: 'inline-block' }}
    >
      <Stack direction="row" spacing={4}>
        <Field label="Started" value={formatTs(scan.started_at)} />
        <Field label="Ended" value={formatTs(scan.ended_at)} />
        <Field label="Status" value={scan.status} />
      </Stack>
    </Paper>
  )
}
