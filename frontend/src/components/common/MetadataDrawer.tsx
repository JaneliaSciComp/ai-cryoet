import { useState } from 'react'
import type { ReactNode } from 'react'
import {
  Box,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Tab,
  Tabs,
  Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

export type MetadataTab = { label: string; content: ReactNode }

// Right-anchored drawer that surfaces the full metadata tree for an entity.
// Header mirrors the data-portal reference: a small eyebrow label, the entity
// name as the heading, and a close button.
//
// Pass `children` for a single-pane drawer (sample page), or `tabs` for a
// tabbed drawer (acquisition page) — the first tab is focused on open.
export function MetadataDrawer({
  open,
  onClose,
  eyebrow,
  title,
  tabs,
  children,
}: {
  open: boolean
  onClose: () => void
  eyebrow: string
  title: string
  tabs?: MetadataTab[]
  children?: ReactNode
}) {
  const [tab, setTab] = useState(0)
  const active = tabs ? Math.min(tab, tabs.length - 1) : 0

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      slotProps={{ paper: { sx: { width: { xs: '100%', sm: 460 } } } }}
    >
      <Box sx={{ px: 3, pt: 2.5, pb: tabs ? 0 : 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ letterSpacing: 1, fontWeight: 700 }}
          >
            {eyebrow}
          </Typography>
          <IconButton
            aria-label="Close metadata"
            onClick={onClose}
            edge="end"
            sx={{ mt: -1 }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="h6" component="h2" sx={{ mt: 0.5 }}>
          {title}
        </Typography>
        {tabs ? (
          <Tabs
            value={active}
            onChange={(_e, value) => setTab(value)}
            sx={{ mt: 1 }}
          >
            {tabs.map((t) => (
              <Tab key={t.label} label={t.label} />
            ))}
          </Tabs>
        ) : null}
      </Box>
      <Divider />
      <Box sx={{ overflowY: 'auto', px: 3, py: 2 }}>
        <Stack spacing={1.5}>{tabs ? tabs[active].content : children}</Stack>
      </Box>
    </Drawer>
  )
}
