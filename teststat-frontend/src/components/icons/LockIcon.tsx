import { LockKeyhole, LockKeyholeOpen } from 'lucide-react'

export function LockIcon({ unlocked = false }: { unlocked?: boolean }) {
  const Icon = unlocked ? LockKeyholeOpen : LockKeyhole
  return <Icon className="lock-icon" aria-hidden="true" strokeWidth={2.2} />
}
