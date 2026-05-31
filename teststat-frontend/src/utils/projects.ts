import type { ProjectItem } from '../api/types'

export function sortProjects(projects: ProjectItem[]) {
  return [...projects].sort((a, b) => {
    if (a.archived !== b.archived) {
      return Number(a.archived) - Number(b.archived)
    }
    return b.updated_at.localeCompare(a.updated_at)
  })
}
