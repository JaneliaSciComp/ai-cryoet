import type { ReactNode } from 'react'
import { Box, Button, Stack, Typography } from '@mui/material'
import LinkIcon from '@mui/icons-material/Link'
import { CopyIconButton } from '~/components/common/CopyIconButton'
import { toFileglancerUrl } from '~/utils/fileglancer'

interface FileglancerPathSectionProps {
  // Absolute on-disk path of the entity's directory (sample or acquisition).
  path: string | null
  // Metadata file that lives in that directory — `sample.toml` for samples,
  // `acquisition.toml` for acquisitions. Linked by the "View metadata" button.
  metadataFilename: string
  // Optional content rendered between the path row and the metadata button
  // (e.g. the sample-contents card on the sample-detail view).
  children?: ReactNode
}

// Shared path display used by the sample- and acquisition-detail views: a
// monospace path with copy-link / copy-path buttons, optional inset content,
// and a button-styled link that opens the entity's metadata in Fileglancer.
export function FileglancerPathSection(props: FileglancerPathSectionProps) {
  const { path, metadataFilename, children } = props

  const fileglancerLink = path ? toFileglancerUrl(path) : null
  const metadataLink = path
    ? toFileglancerUrl(`${path}/${metadataFilename}`)
    : null

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

      {metadataLink ? (
        <Box>
          <Button
            variant="outlined"
            href={metadataLink}
            target="_blank"
            rel="noopener noreferrer"
          >
            View metadata file in Fileglancer
          </Button>
        </Box>
      ) : null}
    </Stack>
  )
}
