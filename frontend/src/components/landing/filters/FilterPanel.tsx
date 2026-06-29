import { Stack } from '@mui/material'
import { useState } from 'react'
import type { FiltersOptionsOut } from '~/types'
import { GROUPS } from '~/utils/filterFields'
import type { SamplesSearchParams } from '~/utils/samplesSearch'
import { FilterGroup } from './FilterGroup'
import { FilterProperty } from './FilterProperty'
import { FilterSection } from './FilterSection'

export type FilterPanelProps = {
  options: FiltersOptionsOut
  values: SamplesSearchParams // current URL search
  onChange: (patch: Partial<SamplesSearchParams>) => void
  disabledGroups?: Set<string> // group ids disabled by gating (Phase 5 supplies)
  lockedDataSource?: 'experimental' | 'simulation' // when set, hide the data_source property
}

// ponytail: expand state is UI-only and resets on remount (acceptable — the URL
// is the source of truth for the actual filter values). Groups are keyed by
// group.id (collapsed by default); properties by field.key (options shown by
// default once their group is open).

export function FilterPanel(props: FilterPanelProps) {
  const { options, values, onChange, disabledGroups, lockedDataSource } = props
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({})
  const [collapsedProps, setCollapsedProps] = useState<Record<string, boolean>>({})

  const toggleGroup = (id: string) =>
    setOpenGroups((prev) => ({ ...prev, [id]: !prev[id] }))

  const toggleProp = (key: string) =>
    setCollapsedProps((prev) => ({ ...prev, [key]: !prev[key] }))

  const sections: Array<{ section: 'sample' | 'acquisition'; title: string }> = [
    { section: 'sample', title: 'Sample properties' },
    { section: 'acquisition', title: 'Acquisition properties' },
  ]

  return (
    <Stack spacing={1}>
      {sections.map(({ section, title }) => (
        <FilterSection key={section} title={title}>
          {GROUPS.filter(
            (g) =>
              g.section === section &&
              // On a single-arm page, drop groups that only apply to the other arm.
              !(lockedDataSource && g.appliesTo && g.appliesTo !== lockedDataSource),
          ).map((group) => {
            const disabled = disabledGroups?.has(group.id) ?? false
            const fields = group.fields.filter(
              (f) => !(f.key === 'data_source' && lockedDataSource),
            )
            if (fields.length === 0) return null
            return (
              <FilterGroup
                key={group.id}
                title={group.title}
                expanded={!!openGroups[group.id]}
                onToggle={() => toggleGroup(group.id)}
                disabled={disabled}
              >
                {fields.map((field) => (
                  <FilterProperty
                    key={field.key}
                    field={field}
                    options={options}
                    values={values}
                    onChange={onChange}
                    expanded={!collapsedProps[field.key]}
                    onToggle={() => toggleProp(field.key)}
                    disabled={disabled}
                  />
                ))}
              </FilterGroup>
            )
          })}
        </FilterSection>
      ))}
    </Stack>
  )
}
