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

  // The persistent Drawer paper is `position: fixed; top: 0` by default and
  // sits above the AppBar (drawer z-index 1200 > app-bar 1100), which would
  // hide the nav links on the left of the AppBar. Offset the paper top by the
  // AppBar height so the drawer slides in below it. Only apply to the
  // persistent variant — the temporary (mobile) variant covers the screen on
  // purpose so the backdrop can dismiss it.
  const APP_BAR_HEIGHT = 64
  const persistentPaperSx =
    variant === 'persistent'
      ? { top: APP_BAR_HEIGHT, height: `calc(100% - ${APP_BAR_HEIGHT}px)` }
      : {}

  return (
    <Box sx={{ display: 'flex', height: `calc(100vh - ${APP_BAR_HEIGHT}px)` }}>
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
            ...persistentPaperSx,
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
