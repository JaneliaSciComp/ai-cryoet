import { Alert, Button, Stack } from '@mui/material'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { useMutation } from '@tanstack/react-query'
import { apiFetch } from '~/utils/api'
import type { ViewerLaunchOut } from '~/types'

interface NeuroglancerButtonProps {
  launchPath: string
  label?: string
}

export function NeuroglancerButton(props: NeuroglancerButtonProps) {
  const { launchPath, label = 'View in Neuroglancer' } = props

  const mutation = useMutation<ViewerLaunchOut>({
    mutationFn: () => apiFetch<ViewerLaunchOut>(launchPath, { method: 'POST' }),
    onSuccess: (data) => {
      if (typeof window === 'undefined') return
      try {
        const rewritten = new URL(data.url)
        rewritten.hostname = window.location.hostname
        window.open(rewritten.toString(), '_blank', 'noopener,noreferrer')
      } catch {
        // If URL parsing fails, fall back to opening the raw URL.
        window.open(data.url, '_blank', 'noopener,noreferrer')
      }
    },
  })

  return (
    <Stack>
      <Button
        variant="contained"
        startIcon={<OpenInNewIcon />}
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
      >
        {label}
      </Button>
      {mutation.isError ? (
        <Alert severity="error" sx={{ mt: 1 }}>
          {String(mutation.error)}
        </Alert>
      ) : null}
    </Stack>
  )
}
