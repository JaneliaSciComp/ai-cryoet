import { Box, Chip, Paper, Stack, Typography } from '@mui/material'
import type { AcquisitionScanStatus, EntityScanStatus } from '~/types'

// Scan timestamps are Unix seconds; render in the viewer's locale.
function formatTs(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  return new Date(seconds * 1000).toLocaleString()
}

function outcomeColor(
  outcome: EntityScanStatus['last_outcome'],
): 'success' | 'error' | 'default' {
  switch (outcome) {
    case 'upserted':
      return 'success'
    case 'failed':
      return 'error'
    default:
      return 'default'
  }
}

function outcomeLabel(outcome: EntityScanStatus['last_outcome']): string {
  return outcome === 'upserted' ? 'updated' : outcome
}

function Row({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <Box
      sx={{ display: 'flex', justifyContent: 'space-between', gap: 3, minWidth: 0 }}
    >
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Box sx={{ minWidth: 0, textAlign: 'right' }}>{children}</Box>
    </Box>
  )
}

// Thumbnail provenance block — acquisition-only. `missing_source` /
// `render_failed` / a never-generated thumbnail drive the "no preview source"
// and "never" states (plan §4.5, wireframe).
function ThumbnailProvenance({ status }: { status: AcquisitionScanStatus }) {
  const noSource =
    status.thumbnail_status === 'missing_source' ||
    status.thumbnail_source_kind === 'none' ||
    status.thumbnail_source_kind == null
  const failed = status.thumbnail_status === 'render_failed'

  return (
    <>
      <Row label="Thumbnail source file">
        {noSource ? (
          <Typography variant="body2" sx={{ color: 'warning.main' }}>
            — no preview source found —
          </Typography>
        ) : failed ? (
          <Typography variant="body2" sx={{ color: 'error.main' }}>
            render failed
          </Typography>
        ) : status.thumbnail_source_path ? (
          <Typography
            variant="body2"
            sx={{
              fontFamily: 'monospace',
              fontSize: 12.5,
              wordBreak: 'break-all',
            }}
          >
            {status.thumbnail_source_path}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.disabled">
            —
          </Typography>
        )}
      </Row>
      <Row label="Thumbnail generated">
        {status.thumbnail_generated_at == null ? (
          <Typography variant="body2" sx={{ color: 'warning.main' }}>
            never
          </Typography>
        ) : (
          <Typography variant="body2">
            {formatTs(status.thumbnail_generated_at)}
          </Typography>
        )}
      </Row>
    </>
  )
}

// Priority 2 readout on the sample / acquisition detail pages (plan §1.6, §5.2).
// A not-yet-rescanned entity has `status === null`.
export function EntityFreshnessCard({
  status,
  kind,
}: {
  status: EntityScanStatus | AcquisitionScanStatus | null
  kind: 'sample' | 'acquisition'
}) {
  return (
    <Paper
      elevation={0}
      sx={{ px: 2.5, py: 2, borderRadius: 2, bgcolor: 'grey.100' }}
    >
      <Typography variant="subtitle2" gutterBottom>
        Data freshness &amp; preview
      </Typography>
      {status == null ? (
        <Typography variant="body2" color="text.secondary">
          This {kind} has not been scanned yet.
        </Typography>
      ) : (
        <Stack spacing={0.5}>
          <Row label="Last scan outcome">
            <Chip
              label={outcomeLabel(status.last_outcome)}
              size="small"
              color={outcomeColor(status.last_outcome)}
              variant="outlined"
            />
          </Row>
          <Row label="Last updated">
            <Typography variant="body2">
              {formatTs(status.last_changed_at)}
            </Typography>
          </Row>
          <Row label="Last scanned">
            <Typography variant="body2">
              {formatTs(status.last_scanned_at)}
            </Typography>
          </Row>
          {kind === 'acquisition' ? (
            <ThumbnailProvenance status={status as AcquisitionScanStatus} />
          ) : null}
        </Stack>
      )}
    </Paper>
  )
}
