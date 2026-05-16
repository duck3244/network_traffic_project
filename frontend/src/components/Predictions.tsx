import { useMemo } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatNumber } from '../format'
import type { PredictResponse } from '../types'

type Props = {
  result: PredictResponse | null
}

export function Predictions({ result }: Props) {
  const series = useMemo(
    () => result?.points.map((p) => ({ step: p.t + 1, value: p.value })) ?? [],
    [result],
  )
  const stats = useMemo(() => {
    if (!result || result.points.length === 0) return null
    const vals = result.points.map((p) => p.value)
    return {
      min: Math.min(...vals),
      max: Math.max(...vals),
      mean: vals.reduce((s, v) => s + v, 0) / vals.length,
    }
  }, [result])

  if (!result) return null

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-700">Predictions</h3>
          <p className="mt-0.5 text-[11px] text-slate-500">
            <span className="font-mono">{result.model}</span> ·{' '}
            <span className="font-mono">{result.dataset}</span> · {result.steps}{' '}
            steps
          </p>
        </div>
        {stats && (
          <div className="flex gap-3 text-[11px]">
            <Stat label="min" value={stats.min} />
            <Stat label="mean" value={stats.mean} />
            <Stat label="max" value={stats.max} />
          </div>
        )}
      </div>
      {series.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-xs text-slate-400">
          예측 결과 없음
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={series}
              margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="step"
                tick={{ fontSize: 10, fill: '#64748b' }}
                label={{
                  value: 'step',
                  position: 'insideBottomRight',
                  offset: -2,
                  fontSize: 10,
                  fill: '#94a3b8',
                }}
              />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={48} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                formatter={(v: number) => formatNumber(v, 3)}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#10b981"
                strokeWidth={1.75}
                dot={{ r: 2 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] uppercase tracking-wide text-slate-400">
        {label}
      </span>
      <span className="font-mono text-xs text-slate-900">
        {formatNumber(value, 3)}
      </span>
    </div>
  )
}
