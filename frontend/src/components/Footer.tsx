import { Box, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { metaQueryOptions } from '~/utils/queryOptions'

export function Footer() {
  // Non-blocking: if /meta fails (e.g. API down) the footer still renders,
  // just without the version line.
  const { data: meta } = useQuery(metaQueryOptions())

  return (
    <Box
      component="footer"
      sx={{
        bgcolor: 'primary.main',
        color: 'primary.contrastText',
        px: { xs: 2, md: 4 },
        py: 2,
        textAlign: 'right',
      }}
    >
      <Typography variant="body2">HHMI Janelia</Typography>
      {meta && (
        <Typography variant="caption" sx={{ opacity: 0.8 }}>
          Portal {meta.portal_version} · Data format v{meta.data_format_version}
        </Typography>
      )}
    </Box>
  )
}
