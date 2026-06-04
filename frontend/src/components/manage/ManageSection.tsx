import type { ReactNode, SyntheticEvent } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

// White circle with the count in the brand color — mirrors the wireframe's
// badge, themed instead of greyscale.
function CountBadge({ count }: { count: number }) {
  return (
    <Box
      sx={{
        flexShrink: 0,
        width: 40,
        height: 40,
        borderRadius: '50%',
        bgcolor: 'background.paper',
        color: 'primary.main',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
      }}
    >
      {count.toLocaleString()}
    </Box>
  )
}

export function ManageSection({
  count,
  title,
  expanded,
  onChange,
  children,
}: {
  count: number
  title: string
  expanded: boolean
  onChange: (expanded: boolean) => void
  children: ReactNode
}) {
  return (
    <Accordion
      expanded={expanded}
      onChange={(_e: SyntheticEvent, isExpanded: boolean) =>
        onChange(isExpanded)
      }
      disableGutters
      elevation={0}
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 2,
        overflow: 'hidden',
        '&:before': { display: 'none' },
      }}
    >
      <AccordionSummary
        expandIcon={
          <ExpandMoreIcon sx={{ color: 'primary.contrastText' }} />
        }
        sx={{
          bgcolor: 'primary.main',
          color: 'primary.contrastText',
          '& .MuiAccordionSummary-content': {
            alignItems: 'center',
            gap: 2,
            my: 1,
          },
        }}
      >
        <CountBadge count={count} />
        <Typography variant="h6" component="h2">
          {title}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 0 }}>{children}</AccordionDetails>
    </Accordion>
  )
}
