import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Typography,
} from '@mui/material'
import type { ReactNode } from 'react'

type Props = {
  title: string
  // Whether the group is open, revealing its member properties.
  expanded: boolean
  onToggle: () => void
  disabled?: boolean
  children: ReactNode
}

// A collapsible group ("General", "Chromatin", …). Collapsed by default: the
// title's expand button reveals the member FilterProperty rows. Open state is
// owned by FilterPanel.
export function FilterGroup(props: Props) {
  const { title, expanded, onToggle, disabled, children } = props
  return (
    <Accordion
      expanded={expanded}
      onChange={onToggle}
      disabled={disabled}
      disableGutters
      elevation={0}
      square
      sx={{ '&:before': { display: 'none' }, mb: 1 }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon fontSize="small" />}
        aria-label={`${expanded ? 'Collapse' : 'Expand'} all ${title} filters`}
        sx={{ px: 1, bgcolor: 'action.hover', borderRadius: 1 }}
      >
        <Typography variant="subtitle2" fontWeight="bold">
          {title}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 0, pt: 0 }}>{children}</AccordionDetails>
    </Accordion>
  )
}
