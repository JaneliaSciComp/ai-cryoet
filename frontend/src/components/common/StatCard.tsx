import { Card, CardContent, Typography } from '@mui/material'

interface StatCardProps {
  label: string
  value: string | number
  subtext?: string
}

export function StatCard(props: StatCardProps) {
  const { label, value, subtext } = props
  return (
    <Card>
      <CardContent>
        <Typography variant="overline" component="div">
          {label}
        </Typography>
        <Typography variant="h4" component="div">
          {value}
        </Typography>
        {subtext ? (
          <Typography variant="body2" color="text.secondary">
            {subtext}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  )
}
