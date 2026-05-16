import { useEffect, useState } from 'react'

import { api } from '../api'
import type {
  Dataset,
  Job,
  Model,
  PredictResponse,
  Preset,
} from '../types'

type Props = {
  dataset: Dataset | null
  models: Model[]
  selectedModel: string | null
  onSelectModel: (name: string | null) => void
  busy: boolean
  onJobStarted: (job: Job) => void
  onPrediction: (result: PredictResponse) => void
}

export function Actions(props: Props) {
  return (
    <div className="space-y-3">
      <h2 className="px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        Actions
      </h2>
      <PreprocessCard {...props} />
      <TrainCard {...props} />
      <PredictCard {...props} />
    </div>
  )
}

function Card({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string | null
  children: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-slate-700">{title}</h3>
        {hint && <span className="text-[10px] text-slate-400">{hint}</span>}
      </div>
      {children}
    </div>
  )
}

function ErrorLine({ msg }: { msg: string | null }) {
  if (!msg) return null
  return <p className="mt-1.5 break-words text-[11px] text-rose-700">{msg}</p>
}

function PrimaryButton({
  disabled,
  onClick,
  children,
}: {
  disabled?: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="w-full rounded bg-indigo-600 px-2 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
    >
      {children}
    </button>
  )
}

// ────────────────────────────────────────────────────────────────────────────
function PreprocessCard({ dataset, busy, onJobStarted }: Props) {
  const [preset, setPreset] = useState<Preset>('default')
  const [error, setError] = useState<string | null>(null)
  const [outputName, setOutputName] = useState('')

  const eligible = dataset?.kind === 'raw'
  const hint = !dataset
    ? '데이터셋 선택 필요'
    : !eligible
    ? 'raw 데이터셋만 가능'
    : null

  const run = async () => {
    if (!dataset) return
    setError(null)
    try {
      const job = await api.preprocess(dataset.name, {
        preset,
        output_name: outputName.trim() || null,
      })
      onJobStarted(job)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Card title="Preprocess" hint={hint}>
      <div className="space-y-2">
        <label className="block text-[10px] uppercase tracking-wide text-slate-400">
          preset
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value as Preset)}
            disabled={!eligible || busy}
            className="mt-0.5 block w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs disabled:bg-slate-50 disabled:text-slate-400"
          >
            <option value="default">default (1-min interval)</option>
            <option value="geant">geant (15-min, log1p)</option>
          </select>
        </label>
        <label className="block text-[10px] uppercase tracking-wide text-slate-400">
          output name (optional, .csv)
          <input
            type="text"
            value={outputName}
            onChange={(e) => setOutputName(e.target.value)}
            placeholder={
              dataset && eligible ? `processed_${dataset.name}` : ''
            }
            disabled={!eligible || busy}
            className="mt-0.5 block w-full rounded border border-slate-300 px-2 py-1 font-mono text-xs disabled:bg-slate-50"
          />
        </label>
        <PrimaryButton disabled={!eligible || busy} onClick={run}>
          전처리 시작
        </PrimaryButton>
        <ErrorLine msg={error} />
      </div>
    </Card>
  )
}

// ────────────────────────────────────────────────────────────────────────────
function TrainCard({ dataset, busy, onJobStarted }: Props) {
  const [epochs, setEpochs] = useState<number | ''>(50)
  const [batchSize, setBatchSize] = useState<number | ''>(32)
  const [seqLen, setSeqLen] = useState<number | ''>(120)
  const [error, setError] = useState<string | null>(null)

  const eligible = dataset?.kind === 'processed'
  const hint = !dataset
    ? '데이터셋 선택 필요'
    : !eligible
    ? 'processed 데이터셋만 가능'
    : null

  const run = async () => {
    if (!dataset) return
    setError(null)
    try {
      const job = await api.train({
        dataset: dataset.name,
        epochs: epochs === '' ? null : Number(epochs),
        batch_size: batchSize === '' ? null : Number(batchSize),
        sequence_length: seqLen === '' ? null : Number(seqLen),
      })
      onJobStarted(job)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Card title="Train" hint={hint}>
      <div className="space-y-2">
        <div className="grid grid-cols-3 gap-1.5">
          <NumberInput
            label="epochs"
            value={epochs}
            onChange={setEpochs}
            disabled={!eligible || busy}
          />
          <NumberInput
            label="batch"
            value={batchSize}
            onChange={setBatchSize}
            disabled={!eligible || busy}
          />
          <NumberInput
            label="seq_len"
            value={seqLen}
            onChange={setSeqLen}
            disabled={!eligible || busy}
          />
        </div>
        <PrimaryButton disabled={!eligible || busy} onClick={run}>
          학습 시작
        </PrimaryButton>
        <ErrorLine msg={error} />
      </div>
    </Card>
  )
}

// ────────────────────────────────────────────────────────────────────────────
function PredictCard({
  dataset,
  models,
  selectedModel,
  onSelectModel,
  busy,
  onPrediction,
}: Props) {
  const [steps, setSteps] = useState<number | ''>(24)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  // 모델 목록이 갱신됐는데 선택 모델이 없으면 첫 모델로 기본 선택.
  // Why: useEffect 안에서 부모 setter 호출. deps 가 안정적이어야 무한 루프 없음.
  useEffect(() => {
    if (selectedModel == null && models.length > 0) {
      onSelectModel(models[0].name)
    }
    if (selectedModel && !models.some((m) => m.name === selectedModel)) {
      onSelectModel(models[0]?.name ?? null)
    }
  }, [models, selectedModel, onSelectModel])

  const eligible =
    dataset?.kind === 'processed' && !!selectedModel && models.length > 0
  const hint = !dataset
    ? '데이터셋 선택 필요'
    : dataset.kind !== 'processed'
    ? 'processed 데이터셋만 가능'
    : models.length === 0
    ? '학습된 모델 없음'
    : null

  const run = async () => {
    if (!dataset || !selectedModel) return
    setError(null)
    setRunning(true)
    try {
      const result = await api.predict({
        model: selectedModel,
        dataset: dataset.name,
        steps: steps === '' ? 24 : Number(steps),
      })
      onPrediction(result)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card title="Predict" hint={hint}>
      <div className="space-y-2">
        <label className="block text-[10px] uppercase tracking-wide text-slate-400">
          model
          <select
            value={selectedModel ?? ''}
            onChange={(e) => onSelectModel(e.target.value || null)}
            disabled={models.length === 0 || busy || running}
            className="mt-0.5 block w-full truncate rounded border border-slate-300 bg-white px-2 py-1 font-mono text-xs disabled:bg-slate-50 disabled:text-slate-400"
          >
            {models.length === 0 && <option value="">(없음)</option>}
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        <NumberInput
          label="steps"
          value={steps}
          onChange={setSteps}
          disabled={!eligible || busy || running}
        />
        <PrimaryButton
          disabled={!eligible || busy || running}
          onClick={run}
        >
          {running ? '예측 중…' : '예측 실행'}
        </PrimaryButton>
        <ErrorLine msg={error} />
      </div>
    </Card>
  )
}

function NumberInput({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string
  value: number | ''
  onChange: (v: number | '') => void
  disabled?: boolean
}) {
  return (
    <label className="block text-[10px] uppercase tracking-wide text-slate-400">
      {label}
      <input
        type="number"
        value={value}
        onChange={(e) => {
          const v = e.target.value
          onChange(v === '' ? '' : Math.max(1, Number(v)))
        }}
        disabled={disabled}
        className="mt-0.5 block w-full rounded border border-slate-300 px-2 py-1 font-mono text-xs disabled:bg-slate-50"
      />
    </label>
  )
}
