const UI_STATE_STORAGE_KEY = 'teststat:ui-state:v1'

interface UiState {
  selectedTestingId?: number | null
}

function isUiState(value: unknown): value is UiState {
  if (value === null || typeof value !== 'object') {
    return false
  }

  const selectedTestingId = (value as UiState).selectedTestingId
  return (
    selectedTestingId === undefined ||
    selectedTestingId === null ||
    typeof selectedTestingId === 'number'
  )
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
