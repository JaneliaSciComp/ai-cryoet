import { createFileRoute } from '@tanstack/react-router'
import { Typography } from '@mui/material'
import { samplesQueryOptions, useSamplesQuery } from '~/hooks/useSamples'

export const Route = createFileRoute('/samples')({
  loader: ({ context: { queryClient } }) =>
    queryClient.ensureQueryData(samplesQueryOptions),
  component: SamplesList,
})

function SamplesList() {
  const { data } = useSamplesQuery()

  return (
    <div>
      <Typography variant="h2">Samples</Typography>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Project</th>
            <th>Data source</th>
            <th>Warnings</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s) => (
            <tr key={s.sample_id}>
              <td>{s.sample_id}</td>
              <td>{s.project}</td>
              <td>{s.data_source}</td>
              <td>{s.warning_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
