import { Box, Stack, Typography } from '@mui/material'
import { ButtonLink } from '~/components/CustomLink'
import { HeroBackdrop } from './HeroBackdrop'

// The portal's front door: a dark banner that mirrors the app's existing
// `primary.dark` styling (StatsBanner, Footer) and routes visitors to the two
// data collections. The wireframe's "Browse all data" button and the
// filter/search controls are intentionally omitted — the two data sets are
// kept separate.
export function LandingHero() {
  return (
    <Box
      sx={{
        position: 'relative',
        overflow: 'hidden',
        // Rendered as a sibling of <Header> (see __root.tsx), so it's already
        // full viewport width and flush under the nav — no full-bleed hacks.
        bgcolor: 'primary.dark',
        color: 'common.white',
        px: { xs: 3, md: 6 },
        py: { xs: 5, md: 7 },
        textAlign: 'center',
      }}
    >
      <HeroBackdrop />
      <Box
        sx={(theme) => ({
          // Keep the text/buttons readable and aligned with the page content
          // below, while the background spans edge to edge.
          position: 'relative',
          zIndex: 1,
          maxWidth: theme.breakpoints.values.lg,
          mx: 'auto',
        })}
      >
      <Typography variant="h3" component="h1" color="secondary.main" gutterBottom>
        AI+CryoET Data Portal
      </Typography>
      <Typography
        variant="h6"
        component="p"
        color="inherit"
        sx={{ opacity: 0.85, mb: 4 }}
      >
        Track, explore, and visualize data collected for the AI+CryoET project
      </Typography>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        justifyContent="center"
      >
        <ButtonLink
          to="/data"
          variant="contained"
          size="large"
          sx={{
            bgcolor: 'common.white',
            color: 'primary.dark',
            '&:hover': { bgcolor: 'grey.200' },
          }}
        >
          All Data
        </ButtonLink>
        <ButtonLink
          to="/experimental"
          variant="contained"
          size="large"
          sx={{
            bgcolor: 'common.white',
            color: 'primary.dark',
            '&:hover': { bgcolor: 'grey.200' },
          }}
        >
          Experimental Data
        </ButtonLink>
        <ButtonLink
          to="/md-simulation"
          variant="contained"
          size="large"
          sx={{
            bgcolor: 'common.white',
            color: 'primary.dark',
            '&:hover': { bgcolor: 'grey.200' },
          }}
        >
          MD Simulations
        </ButtonLink>
      </Stack>
      </Box>
    </Box>
  )
}
