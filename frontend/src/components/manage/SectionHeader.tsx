import { Box, Typography } from '@mui/material'

// Manage-page section heading: an optional count in the brand colour followed
// by a brief title (replaces the old count-badge accordion header).
export function SectionHeader({
  count,
  title,
}: {
  count?: number
  title: string
}) {
  return (
    <Typography variant="h6" component="h2" sx={{ mb: 1 }}>
      {count != null ? (
        <>
          <Box component="span" sx={{ color: 'primary.main', fontWeight: 700 }}>
            {count.toLocaleString()}
          </Box>{' '}
        </>
      ) : null}
      {title}
    </Typography>
  )
}
