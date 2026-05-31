export function getErrorMessage(err: unknown) {
  return err instanceof Error ? err.message : '不明なエラーが発生しました'
}
