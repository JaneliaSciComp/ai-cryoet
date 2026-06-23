import type { ReactNode } from 'react'
import { Box, Link, Typography } from '@mui/material'
import { ViewAllMetadataButton } from '~/components/common/ViewAllMetadataButton'

// Shared title block for the sample- and acquisition-detail pages: the page
// heading with the "View all metadata" button, an optional warnings link, and
// optional descriptive text. The two ViewAllMetadataButton instances handle
// their own responsive placement (beside the title from `md` up, below it
// otherwise).
export function DetailPageHeader(props: {
  title: string
  onViewMetadata: () => void
  // Warnings banner shown under the title when the entity has metadata
  // warnings; omitted otherwise.
  warning?: { href: string; text: string } | null
  // Optional descriptive text under the title (used on the sample view).
  description?: ReactNode
}) {
  const { title, onViewMetadata, warning, description } = props
  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 2,
        }}
      >
        <Typography variant="h5" component="h1" gutterBottom>
          {title}
        </Typography>
        <ViewAllMetadataButton placement="title" onClick={onViewMetadata} />
      </Box>

      {warning ? (
        <Link href={warning.href} variant="body2" fontWeight={700}>
          {warning.text}
        </Link>
      ) : null}

      {description ? (
        <Typography
          variant="body1"
          color="text.secondary"
          sx={{ mt: warning ? 1 : 0 }}
        >
          {description}
        </Typography>
      ) : null}

      <ViewAllMetadataButton placement="below" onClick={onViewMetadata} />
    </Box>
  )
}
