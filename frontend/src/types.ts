export type Health = {
  status: string
  service: string
  version: string
}

export type DatasetKind = 'raw' | 'processed'

export type Dataset = {
  name: string
  kind: DatasetKind
  size_bytes: number
  modified_at: string
}

export type Model = {
  name: string
  size_bytes: number
  modified_at: string
  metrics: Record<string, number> | null
}

export type AnalysisStats = {
  min: number
  max: number
  mean: number
  median: number
  std: number
  p95: number
  p99: number
}

export type Period = { start: string; end: string }

export type TimelinePoint = { timestamp: string; value: number }
export type Distribution = { bin_edges: number[]; counts: number[] }
export type HourlyPoint = { hour: number; mean: number; std: number; max: number }
export type DailyPoint = { day_of_week: number; mean: number; std: number; max: number }
export type Peak = { timestamp: string | null; value: number }
export type AnomalySample = {
  timestamp: string | null
  value: number
  z_score: number | null
}
export type AnomalyInfo = {
  count: number
  ratio: number
  samples: AnomalySample[]
}

export type Analysis = {
  name: string
  rows: number
  columns: string[]
  stats: AnalysisStats | null
  period: Period | null
  peaks: Peak[] | null
  hourly: HourlyPoint[] | null
  daily: DailyPoint[] | null
  anomalies: AnomalyInfo | null
  distribution: Distribution | null
  timeline: TimelinePoint[] | null
}

export type JobStatus = 'pending' | 'running' | 'succeeded' | 'failed'

export type Job = {
  id: string
  kind: string
  status: JobStatus
  progress: number
  message: string
  result: Record<string, unknown> | null
  error: string | null
  created_at: string
  updated_at: string
}

export type Preset = 'default' | 'geant'

export type PreprocessRequest = {
  preset?: Preset
  add_features?: boolean
  detect_anomaly?: boolean
  output_name?: string | null
}

export type TrainRequest = {
  dataset: string
  model_type?: string
  epochs?: number | null
  batch_size?: number | null
  sequence_length?: number | null
}

export type PredictRequest = {
  model: string
  dataset: string
  steps?: number
}

export type PredictPoint = { t: number; value: number }

export type PredictResponse = {
  model: string
  dataset: string
  steps: number
  points: PredictPoint[]
}
