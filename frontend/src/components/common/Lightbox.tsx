import { Box, Dialog, IconButton } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

interface LightboxProps {
  open: boolean
  onClose: () => void
  src: string
  alt: string
}

export function Lightbox(props: LightboxProps) {
  const { open, onClose, src, alt } = props
  return (
    <Dialog fullScreen open={open} onClose={onClose}>
      <IconButton
        aria-label="Close"
        onClick={onClose}
        sx={{
          position: 'absolute',
          top: 8,
          right: 8,
          zIndex: 1,
          color: 'common.white',
          backgroundColor: 'rgba(0, 0, 0, 0.4)',
          '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.6)' },
        }}
      >
        <CloseIcon />
      </IconButton>
      <Box
        sx={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'common.black',
        }}
      >
        <img
          src={src}
          alt={alt}
          style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
        />
      </Box>
    </Dialog>
  )
}
