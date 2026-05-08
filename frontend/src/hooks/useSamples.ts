import { queryOptions, useSuspenseQuery } from '@tanstack/react-query'
import { apiFetch } from '~/utils/api'

export type SampleSummary = {
  sample_id: string
  project: string
  data_source: string
  description: string | null
  warning_count: number
}

export const samplesQueryOptions = queryOptions({
  queryKey: ['samples'],
  queryFn: () => apiFetch<Array<SampleSummary>>('/samples'),
})

export function useSamplesQuery() {
  return useSuspenseQuery(samplesQueryOptions)
}
