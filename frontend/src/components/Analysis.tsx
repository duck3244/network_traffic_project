import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api } from '../api'
import { dayLabel, formatDate, formatDateTimeShort, formatNumber } from '../format'
import type { Analysis as AnalysisData } from '../types'

type Props = {
  datasetName: string | null
}

export function Analysis({ datasetName }: Props) {
  const [data, setData] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bins, setBins] = useState(40)

  useEffect(() => {
    if (!datasetName) {
      setData(null)
      setError(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .analyze(datasetName, { bins, timelineMaxPoints: 600 })
      .then((r) => {
        if (!cancelled) setData(r)
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [datasetName, bins])

  if (!datasetName) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white py-24 text-sm text-slate-400">
        왼쪽에서 데이터셋을 선택하세요
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border border-slate-200 bg-white px-5 py-4">
        <div>
          <h2 className="font-mono text-base text-slate-900">{datasetName}</h2>
          {data && (
            <p className="mt-0.5 text-xs text-slate-500">
              {data.rows.toLocaleString()} rows · {data.columns.length} columns
              {data.period && (
                <>
                  {' · '}
                  {formatDate(data.period.start)} → {formatDate(data.period.end)}
                </>
              )}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs">
          <label className="text-slate-500" htmlFor="bins">
            bins
          </label>
          <input
            id="bins"
            type="number"
            min={5}
            max={200}
            value={bins}
            onChange={(e) => setBins(Math.max(5, Number(e.target.value) || 40))}
            className="w-20 rounded border border-slate-300 px-2 py-1 font-mono"
          />
          {loading && <span className="text-slate-400">로딩 중…</span>}
        </div>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          분석 실패: {error}
        </div>
      )}

      {data && (
        <>
          <StatsGrid stats={data.stats} />
          <div className="grid gap-4 lg:grid-cols-2">
            <TimelineCard data={data} />
            <DistributionCard data={data} />
            <HourlyCard data={data} />
            <DailyCard data={data} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <PeaksCard data={data} />
            <AnomalyCard data={data} />
          </div>
        </>
      )}
    </div>
  )
}

function StatsGrid({ stats }: { stats: AnalysisData['stats'] }) {
  if (!stats) return null
  const items: Array<[string, number]> = [
    ['min', stats.min],
    ['max', stats.max],
    ['mean', stats.mean],
    ['median', stats.median],
    ['std', stats.std],
    ['p95', stats.p95],
    ['p99', stats.p99],
  ]
  return (
    <div className="grid grid-cols-2 gap-2 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-4 lg:grid-cols-7">
      {items.map(([label, value]) => (
        <div key={label} className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wide text-slate-400">
            {label}
          </span>
          <span className="font-mono text-sm text-slate-900">
            {formatNumber(value, 3)}
          </span>
        </div>
      ))}
    </div>
  )
}

function Card({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        {subtitle && <span className="text-[10px] text-slate-400">{subtitle}</span>}
      </div>
      {children}
    </div>
  )
}

function TimelineCard({ data }: { data: AnalysisData }) {
  const series = useMemo(
    () =>
      (data.timeline ?? []).map((p) => ({
        ts: p.timestamp,
        label: formatDateTimeShort(p.timestamp),
        value: p.value,
      })),
    [data.timeline],
  )
  return (
    <Card title="Timeline" subtitle={`${series.length} pts`}>
      {series.length === 0 ? (
        <Empty />
      ) : (
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: '#64748b' }}
                minTickGap={40}
              />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={48} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                labelFormatter={(_, payload) =>
                  payload?.[0]?.payload?.ts ?? ''
                }
                formatter={(v: number) => formatNumber(v, 3)}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#4f46e5"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}

function DistributionCard({ data }: { data: AnalysisData }) {
  const series = useMemo(() => {
    if (!data.distribution) return []
    const { bin_edges, counts } = data.distribution
    return counts.map((c, i) => ({
      label: formatNumber((bin_edges[i] + bin_edges[i + 1]) / 2, 2),
      count: c,
    }))
  }, [data.distribution])

  return (
    <Card title="Distribution" subtitle={`${series.length} bins`}>
      {series.length === 0 ? (
        <Empty />
      ) : (
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={series} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: '#64748b' }}
                minTickGap={20}
              />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={48} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar
                dataKey="count"
                fill="#6366f1"
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}

function HourlyCard({ data }: { data: AnalysisData }) {
  const series = useMemo(
    () =>
      (data.hourly ?? []).map((h) => ({
        hour: `${h.hour}시`,
        mean: h.mean,
        max: h.max,
      })),
    [data.hourly],
  )
  return (
    <Card title="Hourly avg / max" subtitle={`${series.length}시간`}>
      {series.length === 0 ? (
        <Empty hint="hour 컬럼이 없습니다 (전처리 필요)" />
      ) : (
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={series} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={48} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                formatter={(v: number) => formatNumber(v, 3)}
              />
              <Bar dataKey="mean" fill="#0ea5e9" isAnimationActive={false} />
              <Bar dataKey="max" fill="#f97316" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}

function DailyCard({ data }: { data: AnalysisData }) {
  const series = useMemo(
    () =>
      (data.daily ?? []).map((d) => ({
        day: dayLabel(d.day_of_week),
        mean: d.mean,
        max: d.max,
      })),
    [data.daily],
  )
  return (
    <Card title="Daily avg / max">
      {series.length === 0 ? (
        <Empty hint="day_of_week 컬럼이 없습니다 (전처리 필요)" />
      ) : (
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={series} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={48} />
              <Tooltip
                contentStyle={{ fontSize: 12 }}
                formatter={(v: number) => formatNumber(v, 3)}
              />
              <Bar dataKey="mean" fill="#0ea5e9" isAnimationActive={false} />
              <Bar dataKey="max" fill="#f97316" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}

function PeaksCard({ data }: { data: AnalysisData }) {
  const peaks = data.peaks ?? []
  return (
    <Card title="Top peaks" subtitle={`${peaks.length}건`}>
      {peaks.length === 0 ? (
        <Empty />
      ) : (
        <ol className="divide-y divide-slate-100 text-xs">
          {peaks.map((p, i) => (
            <li
              key={`${p.timestamp ?? i}-${p.value}`}
              className="flex items-center justify-between py-1.5"
            >
              <span className="font-mono text-slate-500">
                #{String(i + 1).padStart(2, '0')}
              </span>
              <span className="text-slate-600">
                {p.timestamp ? formatDate(p.timestamp) : '—'}
              </span>
              <span className="font-mono text-slate-900">
                {formatNumber(p.value, 3)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </Card>
  )
}

function AnomalyCard({ data }: { data: AnalysisData }) {
  const a = data.anomalies
  if (!a) {
    return (
      <Card title="Anomalies">
        <Empty hint="is_anomaly 컬럼이 없습니다 (전처리 필요)" />
      </Card>
    )
  }
  const ratioPct = (a.ratio * 100).toFixed(2)
  return (
    <Card
      title="Anomalies"
      subtitle={`${a.count.toLocaleString()}건 · ${ratioPct}%`}
    >
      {a.samples.length === 0 ? (
        <div className="py-4 text-xs text-slate-400">감지된 이상치 없음</div>
      ) : (
        <ul className="divide-y divide-slate-100 text-xs">
          {a.samples.map((s, i) => (
            <li
              key={`${s.timestamp ?? i}-${s.value}`}
              className="flex items-center justify-between gap-2 py-1.5"
            >
              <span className="text-slate-600">
                {s.timestamp ? formatDate(s.timestamp) : '—'}
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-slate-900">
                  {formatNumber(s.value, 3)}
                </span>
                {s.z_score != null && (
                  <span className="rounded bg-rose-50 px-1.5 py-0.5 font-mono text-[10px] text-rose-700">
                    z={formatNumber(s.z_score, 2)}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function Empty({ hint }: { hint?: string } = {}) {
  return (
    <div className="flex h-40 items-center justify-center text-center text-xs text-slate-400">
      {hint ?? '데이터 없음'}
    </div>
  )
}
