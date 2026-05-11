import { useState } from 'react'
import { IconButton, Tooltip } from '@mui/material'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import CheckIcon from '@mui/icons-material/Check'

interface CopyButtonProps {
  text: string
  label?: string
  size?: 'small' | 'medium'
}

export function CopyButton(props: CopyButtonProps) {
  const { text, label = 'Copy', size = 'small' } = props
  const [copied, setCopied] = useState(false)

  async function handleClick() {
    if (typeof navigator === 'undefined' || !navigator.clipboard) return
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Swallow clipboard errors silently — user can retry.
    }
  }

  return (
    <Tooltip title={label}>
      <IconButton aria-label={label} size={size} onClick={handleClick}>
        {copied ? (
          <CheckIcon fontSize={size === 'small' ? 'small' : 'medium'} />
        ) : (
          <ContentCopyIcon fontSize={size === 'small' ? 'small' : 'medium'} />
        )}
      </IconButton>
    </Tooltip>
  )
}
