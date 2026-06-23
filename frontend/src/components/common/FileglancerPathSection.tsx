import type { ReactNode } from 'react'
import { Stack, Typography } from '@mui/material'
import LinkIcon from '@mui/icons-material/Link'
import { CopyIconButton } from '~/components/common/CopyIconButton'
import { toFileglancerUrl } from '~/utils/fileglancer'

interface FileglancerPathSectionProps {
  // Absolute on-disk path of the entity's directory (sample or acquisition).
  path: string | null
  // Optional content rendered below the path row (e.g. the summary card on the
  // detail views).
  children?: ReactNode
}

// Shared path display used by the sample- and acquisition-detail views: a
// monospace path with copy-link / copy-path buttons and optional inset content.
export function FileglancerPathSection(props: FileglancerPathSectionProps) {
  const { path, children } = props

  const fileglancerLink = path ? toFileglancerUrl(path) : null

  return (
    <Stack spacing={2}>
      {path ? (
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Typography
            variant="body2"
            sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}
          >
            {path}
          </Typography>
          {fileglancerLink ? (
            <CopyIconButton
              text={fileglancerLink}
              tooltip="Copy Fileglancer link"
              icon={<LinkIcon fontSize="small" />}
            />
          ) : null}
          <CopyIconButton text={path} tooltip="Copy path" />
        </Stack>
      ) : null}

      {children}
    </Stack>
  )
}
