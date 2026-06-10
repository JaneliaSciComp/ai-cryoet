// Fileglancer browses by share name: the data mount `/groups/cryoet/cryoet`
// is exposed as the share `groups_cryoet_cryoet`, followed by the path relative
// to that mount. e.g. `/groups/cryoet/cryoet/data/x` ->
// `.../browse/groups_cryoet_cryoet/data/x`.
const FILEGLANCER_BASE = 'https://fileglancer.int.janelia.org/browse'
const FILEGLANCER_MOUNT = '/groups/cryoet/cryoet'
const FILEGLANCER_SHARE = 'groups_cryoet_cryoet'

// Maps an absolute on-disk path under the data mount to its Fileglancer browse
// URL. Returns null for paths outside the mount (nothing to link to).
export function toFileglancerUrl(absPath: string): string | null {
  if (
    absPath !== FILEGLANCER_MOUNT &&
    !absPath.startsWith(`${FILEGLANCER_MOUNT}/`)
  )
    return null
  const rel = absPath.slice(FILEGLANCER_MOUNT.length) // leading '/' or empty
  return `${FILEGLANCER_BASE}/${FILEGLANCER_SHARE}${rel}`
}
