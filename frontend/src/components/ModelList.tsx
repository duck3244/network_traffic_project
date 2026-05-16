import type { Model } from '../types'
import { formatBytes, formatDate, formatNumber } from '../format'

const METRIC_KEYS = ['mse', 'rmse', 'mae', 'r2'] as const

type Props = {
  models: Model[]
  loading: boolean
  error: string | null
}

export function ModelList({ models, loading, error }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-700">Models</h2>
        <span className="text-xs text-slate-400">
          {loading ? '…' : `${models.length}건`}
        </span>
      </div>
      {error && (
        <div className="px-4 py-3 text-xs text-red-600">불러오기 실패: {error}</div>
      )}
      {models.length === 0 && !loading && !error ? (
        <div className="px-4 py-6 text-center text-xs text-slate-400">
          학습된 모델이 없습니다
        </div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {models.map((m) => (
            <li key={m.name} className="px-4 py-3">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate font-mono text-xs text-slate-800">
                  {m.name}
                </span>
                <span className="shrink-0 text-[10px] text-slate-400">
                  {formatBytes(m.size_bytes)}
                </span>
              </div>
              <div className="mt-0.5 text-[10px] text-slate-400">
                {formatDate(m.modified_at)}
              </div>
              {m.metrics ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {METRIC_KEYS.map((k) =>
                    m.metrics && k in m.metrics ? (
                      <MetricChip
                        key={k}
                        label={k.toUpperCase()}
                        value={m.metrics[k]}
                      />
                    ) : null,
                  )}
                </div>
              ) : (
                <div className="mt-2 text-[10px] text-slate-400">
                  metrics 정보 없음
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function MetricChip({ label, value }: { label: string; value: number }) {
  const tone =
    label === 'R2'
      ? value >= 0.5
        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
        : value >= 0
        ? 'bg-amber-50 text-amber-700 border-amber-200'
        : 'bg-rose-50 text-rose-700 border-rose-200'
      : 'bg-slate-50 text-slate-700 border-slate-200'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-mono ${tone}`}
    >
      <span className="font-semibold">{label}</span>
      <span>{formatNumber(value, label === 'R2' ? 3 : 2)}</span>
    </span>
  )
}
