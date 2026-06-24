import type { ReactNode } from 'react'
import { IconButton, Stack, Tooltip, Typography } from '@mui/material'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { CopyIconButton } from '~/components/common/CopyIconButton'
import { toFileglancerUrl } from '~/utils/fileglancer'

interface FileglancerPathSectionProps {
  // Absolute on-disk path of the entity's directory (sample or acquisition).
  path: string | null
  // Optional content rendered below the path row (e.g. the summary card on the
  // detail views).
  children?: ReactNode
}

// Shared path display used by the sample- and acquisition-detail views: the
// on-disk path with a copy-path button, a link out to Fileglancer, and
// optional inset content.
export function FileglancerPathSection(props: FileglancerPathSectionProps) {
  const { path, children } = props

  const fileglancerLink = path ? toFileglancerUrl(path) : null

  return (
    <Stack spacing={2}>
      {path ? (
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Typography
            variant="body2"
            sx={{
              fontFamily: 'monospace',
              fontSize: '0.8125rem',
              wordBreak: 'break-all',
            }}
          >
            {path}
          </Typography>
          <CopyIconButton text={path} tooltip="Copy path" />
          {fileglancerLink ? (
            <Tooltip title="View data in Fileglancer">
              <IconButton
                aria-label="View data in Fileglancer"
                size="small"
                component="a"
                href={fileglancerLink}
                target="_blank"
                rel="noopener noreferrer"
              >
                <OpenInNewIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          ) : null}
        </Stack>
      ) : null}

      {children}
    </Stack>
  )
}
