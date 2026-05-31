import { createContext, useContext } from 'react'

export interface ConfirmOptions {
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
}

export const ConfirmDialogContext = createContext<((options: ConfirmOptions) => Promise<boolean>) | null>(null)

export function useConfirmDialog() {
  const confirm = useContext(ConfirmDialogContext)
  if (!confirm) {
    throw new Error('useConfirmDialog must be used inside ConfirmDialogProvider')
  }
  return confirm
}
