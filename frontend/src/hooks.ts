import { useEffect, useRef, useState } from 'react'

import { api } from './api'
import type { Job } from './types'

type Options = {
  onFinished?: (job: Job) => void
  /** active 잡이 있을 때 폴링 간격(ms). 짧을수록 진행률 반응이 빠름. */
  activeMs?: number
  /** active 잡이 없을 때 폴링 간격(ms). */
  idleMs?: number
}

/** /api/jobs/active 적응형 폴링.
 *
 * 외부에서 잡을 트리거한 직후 `setJob(...)` 으로 즉시 갱신하면 다음 폴링이 active 간격으로 빨리 돌아온다.
 * `onFinished` 는 running → null 전이가 감지될 때 한 번 호출 (잡의 마지막 스냅샷을 인자로).
 */
export function useActiveJob({ onFinished, activeMs = 800, idleMs = 2500 }: Options = {}) {
  const [job, setJobState] = useState<Job | null>(null)
  const prev = useRef<Job | null>(null)
  const finishedCb = useRef(onFinished)
  finishedCb.current = onFinished

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    const tick = async () => {
      if (cancelled) return
      let next: Job | null = null
      try {
        next = await api.activeJob()
      } catch (e) {
        // 폴링 실패는 무시 — 다음 사이클에서 복구
        console.warn('[useActiveJob] poll failed', e)
      }
      if (cancelled) return
      if (prev.current && !next) {
        // running → null: 마지막 잡 ID 로 한번 더 가져와서 결과/에러를 onFinished 에 전달
        try {
          const final = await api.job(prev.current.id)
          if (!cancelled) finishedCb.current?.(final)
        } catch {
          if (!cancelled && prev.current) finishedCb.current?.(prev.current)
        }
      }
      prev.current = next
      if (!cancelled) {
        setJobState(next)
        timer = setTimeout(tick, next ? activeMs : idleMs)
      }
    }
    tick()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [activeMs, idleMs])

  const setJob = (j: Job | null) => {
    prev.current = j
    setJobState(j)
  }
  return { job, setJob }
}
