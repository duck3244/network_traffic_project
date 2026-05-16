import type {
  Analysis,
  Dataset,
  Health,
  Job,
  Model,
  PredictRequest,
  PredictResponse,
  PreprocessRequest,
  TrainRequest,
} from './types'

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const r = await fetch(path, init)
  if (!r.ok) {
    const body = await r.text().catch(() => '')
    let detail = body
    try {
      const parsed = JSON.parse(body) as { detail?: string }
      if (parsed?.detail) detail = parsed.detail
    } catch {
      /* keep raw body */
    }
    throw new Error(`HTTP ${r.status}${detail ? `: ${detail}` : ''}`)
  }
  // 204/empty 응답 안전 처리
  const text = await r.text()
  return (text ? JSON.parse(text) : null) as T
}

function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export type AnalyzeOptions = {
  bins?: number
  timelineMaxPoints?: number
}

export const api = {
  health: () => get<Health>('/api/health'),
  datasets: () => get<Dataset[]>('/api/datasets'),
  models: () => get<Model[]>('/api/models'),
  analyze: (name: string, opts: AnalyzeOptions = {}) => {
    const params = new URLSearchParams()
    if (opts.bins != null) params.set('bins', String(opts.bins))
    if (opts.timelineMaxPoints != null)
      params.set('timeline_max_points', String(opts.timelineMaxPoints))
    const qs = params.toString()
    const suffix = qs ? `?${qs}` : ''
    return get<Analysis>(
      `/api/datasets/${encodeURIComponent(name)}/analysis${suffix}`,
    )
  },
  activeJob: () => get<Job | null>('/api/jobs/active'),
  job: (id: string) => get<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  preprocess: (name: string, req: PreprocessRequest = {}) =>
    post<Job>(`/api/datasets/${encodeURIComponent(name)}/process`, req),
  train: (req: TrainRequest) => post<Job>('/api/train', req),
  predict: (req: PredictRequest) => post<PredictResponse>('/api/predict', req),
}
