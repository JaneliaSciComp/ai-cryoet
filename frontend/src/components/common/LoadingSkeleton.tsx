import { Card, CardContent, Skeleton, Stack } from '@mui/material'

interface LoadingSkeletonProps {
  variant: 'image' | 'row' | 'card'
  count?: number
}

export function LoadingSkeleton(props: LoadingSkeletonProps) {
  const { variant, count = 1 } = props

  function renderOne(key: number) {
    if (variant === 'image') {
      return <Skeleton key={key} variant="rectangular" height={300} />
    }
    if (variant === 'row') {
      return <Skeleton key={key} variant="text" />
    }
    return (
      <Card key={key}>
        <Skeleton variant="rectangular" height={200} />
        <CardContent>
          <Skeleton variant="text" />
          <Skeleton variant="text" />
        </CardContent>
      </Card>
    )
  }

  if (count <= 1) {
    return renderOne(0)
  }

  return (
    <Stack spacing={1}>
      {Array.from({ length: count }, (_, i) => renderOne(i))}
    </Stack>
  )
}
