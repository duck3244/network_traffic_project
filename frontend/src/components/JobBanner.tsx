import type { Job, JobStatus } from '../types'

type Props = {
  job: Job | null
  finishedNotice: { kind: string; status: JobStatus; message: string } | null
  onDismiss: () => void
}

export function JobBanner({ job, finishedNotice, onDismiss }: Props) {
  if (job) {
    const pct = Math.round(job.progress * 100)
    return (
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
        <div className="flex items-baseline justify-between">
          <span className="text-sm font-semibold text-indigo-900">
            진행 중: {job.kind}
          </span>
          <span className="font-mono text-xs text-indigo-700">{pct}%</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-indigo-100">
          <div
            className="h-full bg-indigo-500 transition-[width] duration-200"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-2 truncate text-xs text-indigo-800">{job.message || '…'}</p>
      </div>
    )
  }

  if (finishedNotice) {
    const isOk = finishedNotice.status === 'succeeded'
    const cls = isOk
      ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
      : 'border-rose-200 bg-rose-50 text-rose-900'
    return (
      <div className={`flex items-start justify-between gap-3 rounded-lg border p-3 text-sm ${cls}`}>
        <div className="flex-1">
          <span className="font-semibold">
            {finishedNotice.kind} {isOk ? '완료' : '실패'}
          </span>
          {finishedNotice.message && (
            <span className="ml-2 font-mono text-xs opacity-80">
              {finishedNotice.message}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="rounded px-2 py-0.5 text-xs opacity-60 hover:opacity-100"
        >
          닫기
        </button>
      </div>
    )
  }

  return null
}
