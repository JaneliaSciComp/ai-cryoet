import type { ReactNode } from 'react'
import { Stack, Typography } from '@mui/material'

interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}

export function EmptyState(props: EmptyStateProps) {
  const { title, description, action, icon } = props
  return (
    <Stack alignItems="center" spacing={2} sx={{ py: 4, px: 2 }}>
      {icon}
      <Typography variant="h6" component="div">
        {title}
      </Typography>
      {description ? (
        <Typography variant="body2" color="text.secondary" textAlign="center">
          {description}
        </Typography>
      ) : null}
      {action}
    </Stack>
  )
}
