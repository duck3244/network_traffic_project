import type { Dataset } from '../types'
import { formatBytes, formatDate } from '../format'

type Props = {
  datasets: Dataset[]
  selected: string | null
  onSelect: (name: string) => void
  loading: boolean
  error: string | null
}

export function DatasetList({ datasets, selected, onSelect, loading, error }: Props) {
  const raw = datasets.filter((d) => d.kind === 'raw')
  const processed = datasets.filter((d) => d.kind === 'processed')

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-700">Datasets</h2>
        <span className="text-xs text-slate-400">
          {loading ? '…' : `${datasets.length}건`}
        </span>
      </div>
      {error && (
        <div className="px-4 py-3 text-xs text-red-600">불러오기 실패: {error}</div>
      )}
      <Group
        title="processed"
        items={processed}
        selected={selected}
        onSelect={onSelect}
      />
      <Group title="raw" items={raw} selected={selected} onSelect={onSelect} />
      {datasets.length === 0 && !loading && !error && (
        <div className="px-4 py-6 text-center text-xs text-slate-400">
          등록된 데이터셋이 없습니다
        </div>
      )}
    </div>
  )
}

function Group({
  title,
  items,
  selected,
  onSelect,
}: {
  title: string
  items: Dataset[]
  selected: string | null
  onSelect: (name: string) => void
}) {
  if (items.length === 0) return null
  return (
    <div>
      <div className="bg-slate-50 px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {title} · {items.length}
      </div>
      <ul>
        {items.map((d) => {
          const active = d.name === selected
          return (
            <li key={`${d.kind}/${d.name}`}>
              <button
                type="button"
                onClick={() => onSelect(d.name)}
                className={
                  'flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-xs ' +
                  (active
                    ? 'bg-indigo-50 text-indigo-900'
                    : 'hover:bg-slate-50 text-slate-700')
                }
                title={`${formatDate(d.modified_at)} · ${formatBytes(d.size_bytes)}`}
              >
                <span className="truncate font-mono">{d.name}</span>
                <span className="shrink-0 text-[10px] text-slate-400">
                  {formatBytes(d.size_bytes)}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
