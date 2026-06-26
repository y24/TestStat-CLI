const UI_STATE_STORAGE_KEY = 'teststat:ui-state:v1'

interface UiState {
  selectedTestingId?: number | null
  // testing_id ごとの「表示対象」絞り込み（選択中の label 一覧）を保持する。
  selectedLabelsByTestingId?: Record<string, string[]>
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

function isSelectedLabelsMap(value: unknown): value is Record<string, string[]> {
  if (value === null || typeof value !== 'object') {
    return false
  }
  return Object.values(value as Record<string, unknown>).every(isStringArray)
}

function isUiState(value: unknown): value is UiState {
  if (value === null || typeof value !== 'object') {
    return false
  }

  const selectedTestingId = (value as UiState).selectedTestingId
  const selectedTestingIdValid =
    selectedTestingId === undefined ||
    selectedTestingId === null ||
    typeof selectedTestingId === 'number'

  const selectedLabelsByTestingId = (value as UiState).selectedLabelsByTestingId
  const selectedLabelsValid =
    selectedLabelsByTestingId === undefined || isSelectedLabelsMap(selectedLabelsByTestingId)

  return selectedTestingIdValid && selectedLabelsValid
}

function readUiState(): UiState {
  try {
    const rawValue = window.localStorage.getItem(UI_STATE_STORAGE_KEY)
    if (rawValue === null) {
      return {}
    }

    const parsedValue: unknown = JSON.parse(rawValue)
    return isUiState(parsedValue) ? parsedValue : {}
  } catch {
    return {}
  }
}

function writeUiState(state: UiState) {
  try {
    window.localStorage.setItem(UI_STATE_STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Ignore storage errors so the app remains usable in restricted environments.
  }
}

export function getStoredSelectedTestingId() {
  return readUiState().selectedTestingId ?? null
}

export function setStoredSelectedTestingId(selectedTestingId: number | null) {
  writeUiState({
    ...readUiState(),
    selectedTestingId,
  })
}

export function getStoredSelectedLabels(testingId: number): string[] {
  return readUiState().selectedLabelsByTestingId?.[String(testingId)] ?? []
}

export function setStoredSelectedLabels(testingId: number, labels: string[]) {
  const state = readUiState()
  const map = { ...(state.selectedLabelsByTestingId ?? {}) }
  if (labels.length === 0) {
    delete map[String(testingId)]
  } else {
    map[String(testingId)] = labels
  }
  writeUiState({
    ...state,
    selectedLabelsByTestingId: map,
  })
}
