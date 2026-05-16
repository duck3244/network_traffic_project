import { useCallback, useEffect, useMemo, useState } from 'react'

import { api } from './api'
import { Actions } from './components/Actions'
import { Analysis } from './components/Analysis'
import { DatasetList } from './components/DatasetList'
import { JobBanner } from './components/JobBanner'
import { ModelList } from './components/ModelList'
import { Predictions } from './components/Predictions'
import { useActiveJob } from './hooks'
import type { Dataset, Health, Job, JobStatus, Model, PredictResponse } from './types'

type FinishedNotice = { kind: string; status: JobStatus; message: string }

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [datasetsError, setDatasetsError] = useState<string | null>(null)
  const [datasetsLoading, setDatasetsLoading] = useState(true)

  const [models, setModels] = useState<Model[]>([])
  const [modelsError, setModelsError] = useState<string | null>(null)
  const [modelsLoading, setModelsLoading] = useState(true)

  const [selected, setSelected] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [prediction, setPrediction] = useState<PredictResponse | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [finishedNotice, setFinishedNotice] = useState<FinishedNotice | null>(null)
  const [analysisKey, setAnalysisKey] = useState(0)

  const onFinished = useCallback((j: Job) => {
    setFinishedNotice({
      kind: j.kind,
      status: j.status,
      message: j.status === 'succeeded' ? j.message : j.error ?? j.message,
    })
    // 잡 완료 후 데이터/모델 목록 + 분석 패널 자동 갱신
    setReloadKey((k) => k + 1)
    setAnalysisKey((k) => k + 1)
    // 새 processed 산출물이 생겼으면 그쪽으로 자동 선택
    if (j.status === 'succeeded' && j.result && typeof j.result === 'object') {
      const r = j.result as { path?: string; model_name?: string }
      if (r.path) {
        const base = r.path.split(/[\\/]/).pop()
        if (base) setSelected(base)
      }
      if (r.model_name) {
        setSelectedModel(r.model_name)
      }
    }
  }, [])

  const { job: activeJob, setJob: setActiveJob } = useActiveJob({ onFinished })

  useEffect(() => {
    let cancelled = false
    api.health()
      .then((r) => !cancelled && setHealth(r))
      .catch((e: Error) => !cancelled && setHealthError(e.message))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setDatasetsLoading(true)
    setDatasetsError(null)
    api.datasets()
      .then((r) => {
        if (cancelled) return
        setDatasets(r)
        setSelected((prev) => {
          if (prev && r.some((d) => d.name === prev)) return prev
          const processed = r
            .filter((d) => d.kind === 'processed')
            .sort((a, b) => b.modified_at.localeCompare(a.modified_at))
          return processed[0]?.name ?? r[0]?.name ?? null
        })
      })
      .catch((e: Error) => !cancelled && setDatasetsError(e.message))
      .finally(() => !cancelled && setDatasetsLoading(false))
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  useEffect(() => {
    let cancelled = false
    setModelsLoading(true)
    setModelsError(null)
    api.models()
      .then((r) => !cancelled && setModels(r))
      .catch((e: Error) => !cancelled && setModelsError(e.message))
      .finally(() => !cancelled && setModelsLoading(false))
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const selectedDataset = useMemo(
    () => datasets.find((d) => d.name === selected) ?? null,
    [datasets, selected],
  )

  const busy = activeJob != null

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-base font-semibold">Network Traffic MVP</h1>
            <span className="text-xs text-slate-400">
              {health
                ? `${health.service} v${health.version}`
                : healthError
                ? '백엔드 연결 실패'
                : '—'}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setReloadKey((k) => k + 1)}
            className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
          >
            새로고침
          </button>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 px-6 py-6 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-4">
          <DatasetList
            datasets={datasets}
            selected={selected}
            onSelect={setSelected}
            loading={datasetsLoading}
            error={datasetsError}
          />
          <ModelList models={models} loading={modelsLoading} error={modelsError} />
          <Actions
            dataset={selectedDataset}
            models={models}
            selectedModel={selectedModel}
            onSelectModel={setSelectedModel}
            busy={busy}
            onJobStarted={setActiveJob}
            onPrediction={setPrediction}
          />
        </aside>
        <section className="space-y-4">
          <JobBanner
            job={activeJob}
            finishedNotice={!activeJob ? finishedNotice : null}
            onDismiss={() => setFinishedNotice(null)}
          />
          <Analysis key={analysisKey} datasetName={selected} />
          <Predictions result={prediction} />
        </section>
      </main>
    </div>
  )
}

export default App
