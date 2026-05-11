import { Box } from '@mui/material'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'

type SplitterProps = {
  left: ReactNode
  right: ReactNode
  initialLeftFraction?: number
  minLeftPx?: number
  minRightPx?: number
}

const DIVIDER_PX = 6

export function Splitter(props: SplitterProps) {
  const {
    left,
    right,
    initialLeftFraction = 0.33,
    minLeftPx = 240,
    minRightPx = 320,
  } = props
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [containerWidth, setContainerWidth] = useState(0)
  const [leftPx, setLeftPx] = useState<number | null>(null)
  const draggingRef = useRef(false)

  useLayoutEffect(() => {
    const el = containerRef.current
    if (!el) return
    const initialWidth = el.clientWidth
    setContainerWidth(initialWidth)
    setLeftPx((prev) =>
      prev == null ? Math.round(initialWidth * initialLeftFraction) : prev,
    )
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width)
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [initialLeftFraction])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!draggingRef.current) return
      const el = containerRef.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const next = e.clientX - rect.left
      const maxLeft = Math.max(minLeftPx, rect.width - minRightPx - DIVIDER_PX)
      setLeftPx(Math.min(maxLeft, Math.max(minLeftPx, next)))
    }
    const onUp = () => {
      draggingRef.current = false
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [minLeftPx, minRightPx])

  const resolvedLeftPx =
    leftPx ?? Math.round(containerWidth * initialLeftFraction)

  return (
    <Box
      ref={containerRef}
      sx={{
        display: 'grid',
        gridTemplateColumns: `${resolvedLeftPx}px ${DIVIDER_PX}px 1fr`,
        height: '100%',
        width: '100%',
      }}
    >
      <Box sx={{ overflow: 'auto', minWidth: 0 }}>{left}</Box>
      <Box
        role="separator"
        aria-orientation="vertical"
        onMouseDown={(e) => {
          e.preventDefault()
          draggingRef.current = true
        }}
        sx={{
          cursor: 'col-resize',
          backgroundColor: 'divider',
          userSelect: 'none',
          '&:hover': { backgroundColor: 'action.hover' },
        }}
      />
      <Box sx={{ overflow: 'auto', minWidth: 0 }}>{right}</Box>
    </Box>
  )
}
