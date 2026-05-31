import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ConfirmDialogContext } from './confirmDialogContext'
import type { ConfirmOptions } from './confirmDialogContext'

interface ConfirmRequest extends Required<Omit<ConfirmOptions, 'danger'>> {
  danger: boolean
  resolve: (confirmed: boolean) => void
}

export function ConfirmDialogProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<ConfirmRequest | null>(null)
  const cancelButtonRef = useRef<HTMLButtonElement | null>(null)

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setRequest({
        title: options.title ?? '確認',
        message: options.message,
        confirmLabel: options.confirmLabel ?? 'OK',
        cancelLabel: options.cancelLabel ?? 'キャンセル',
        danger: options.danger ?? false,
        resolve,
      })
    })
  }, [])

  const close = useCallback(
    (confirmed: boolean) => {
      setRequest((current) => {
        current?.resolve(confirmed)
        return null
      })
    },
    [setRequest],
  )

  useEffect(() => {
    if (!request) {
      return
    }

    cancelButtonRef.current?.focus()
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        close(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [close, request])

  return (
    <ConfirmDialogContext.Provider value={confirm}>
      {children}
      {request && (
        <div className="confirm-backdrop" role="presentation" onMouseDown={() => close(false)}>
          <div
            className="confirm-panel"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-message"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="confirm-icon" aria-hidden="true">
              !
            </div>
            <div className="confirm-content">
              <h2 id="confirm-dialog-title">{request.title}</h2>
              <p id="confirm-dialog-message">{request.message}</p>
              <div className="confirm-actions">
                <button
                  ref={cancelButtonRef}
                  className="secondary-button"
                  type="button"
                  onClick={() => close(false)}
                >
                  {request.cancelLabel}
                </button>
                <button
                  className={request.danger ? 'danger-button confirm-action-button' : 'primary-button'}
                  type="button"
                  onClick={() => close(true)}
                >
                  {request.confirmLabel}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </ConfirmDialogContext.Provider>
  )
}
