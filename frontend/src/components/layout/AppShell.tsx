import { Box, Drawer, useMediaQuery, useTheme } from '@mui/material'
import type { ReactNode } from 'react'

type AppShellProps = {
  drawer: ReactNode
  children: ReactNode
  open: boolean
  onOpenChange: (open: boolean) => void
  drawerWidth?: number
}

export function AppShell(props: AppShellProps) {
  const { drawer, children, open, onOpenChange, drawerWidth = 320 } = props
  const theme = useTheme()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'))
  const variant = isDesktop ? 'persistent' : 'temporary'

  return (
    // Assumes the parent route renders a 64 px AppBar above this shell.
    <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
      <Drawer
        variant={variant}
        open={open}
        onClose={() => onOpenChange(false)}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        {drawer}
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, overflow: 'auto' }}>
        {children}
      </Box>
    </Box>
  )
}
