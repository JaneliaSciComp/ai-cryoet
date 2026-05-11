import {
  keepPreviousData,
  queryOptions,
  useQuery,
  useSuspenseQuery,
} from '@tanstack/react-query'
import { apiFetch } from '~/utils/api'
import {
  buildSamplesQueryString,
  type SamplesSearchParams,
} from '~/utils/samplesSearch'
import type {
  FiltersOptionsOut,
  SampleDetail,
  SampleSummary,
  ScanOut,
  StatsOverviewOut,
  WarningOut,
} from '~/types'

// ── /samples list ────────────────────────────────────────────────────────────

export const samplesQueryOptions = (params: SamplesSearchParams = {}) =>
  queryOptions({
    queryKey: ['samples', 'list', params],
    queryFn: () =>
      apiFetch<SampleSummary[]>(`/samples${buildSamplesQueryString(params)}`),
  })

// `useQuery` (not `useSuspenseQuery`) + `placeholderData: keepPreviousData`
// so filter edits don't suspend and unmount the table while the new fetch
// is in flight. The route loader still primes the cache via `ensureQueryData`,
// so the first render after navigation has data immediately.
export function useSamplesQuery(params: SamplesSearchParams = {}) {
  return useQuery({
    ...samplesQueryOptions(params),
    placeholderData: keepPreviousData,
  })
}

// ── /samples/{id} detail ─────────────────────────────────────────────────────

export const sampleDetailQueryOptions = (sampleId: string) =>
  queryOptions({
    queryKey: ['samples', 'detail', sampleId],
    queryFn: () =>
      apiFetch<SampleDetail>(`/samples/${encodeURIComponent(sampleId)}`),
  })

export function useSampleDetailQuery(sampleId: string) {
  return useSuspenseQuery(sampleDetailQueryOptions(sampleId))
}

// ── /samples/{id}/warnings ───────────────────────────────────────────────────

export const sampleWarningsQueryOptions = (sampleId: string) =>
  queryOptions({
    queryKey: ['samples', 'warnings', sampleId],
    queryFn: () =>
      apiFetch<WarningOut[]>(
        `/samples/${encodeURIComponent(sampleId)}/warnings`,
      ),
  })

export function useSampleWarningsQuery(sampleId: string) {
  return useSuspenseQuery(sampleWarningsQueryOptions(sampleId))
}

// ── /filters/options ─────────────────────────────────────────────────────────

export const filtersOptionsQueryOptions = queryOptions({
  queryKey: ['filters', 'options'],
  queryFn: () => apiFetch<FiltersOptionsOut>('/filters/options'),
})

export function useFiltersOptionsQuery() {
  return useSuspenseQuery(filtersOptionsQueryOptions)
}

// ── /stats/overview ──────────────────────────────────────────────────────────

export const statsOverviewQueryOptions = queryOptions({
  queryKey: ['stats', 'overview'],
  queryFn: () => apiFetch<StatsOverviewOut>('/stats/overview'),
})

export function useStatsOverviewQuery() {
  return useSuspenseQuery(statsOverviewQueryOptions)
}

// ── /scans list ──────────────────────────────────────────────────────────────

export const scansQueryOptions = queryOptions({
  queryKey: ['scans', 'list'],
  queryFn: () => apiFetch<Array<ScanOut>>('/scans'),
})

export function useScansQuery() {
  return useSuspenseQuery(scansQueryOptions)
}

// ── /scans/latest ────────────────────────────────────────────────────────────

export const latestScanQueryOptions = queryOptions({
  queryKey: ['scans', 'latest'],
  queryFn: async (): Promise<ScanOut | null> => {
    try {
      return await apiFetch<ScanOut>('/scans/latest')
    } catch (err) {
      // 404 means "no completed scan yet" — surface as null so callers can
      // render an empty branch without try/catch.
      if (err instanceof Error && err.message.includes('404')) return null
      throw err
    }
  },
})

export function useLatestScanQuery() {
  return useSuspenseQuery(latestScanQueryOptions)
}
