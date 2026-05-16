# Architecture — Network Traffic MVP

네트워크 트래픽 수집·전처리·학습·예측을 한 프로세스에서 서빙하는 단일 사용자 MVP. FastAPI 백엔드와 React/Vite 프론트엔드가 같은 `uvicorn` 포트로 운영된다.

---

## 1. 시스템 개요

```
┌─────────────────────────┐         ┌──────────────────────────────────────────┐
│  Browser (React + Vite) │  HTTP   │  FastAPI (uvicorn, single process)       │
│  - DatasetList          │ ──────► │  /api/health                             │
│  - ModelList            │         │  /api/datasets   /api/datasets/{n}/...   │
│  - Actions              │         │  /api/train      /api/predict            │
│  - Analysis / Predict   │ ◄────── │  /api/models     /api/jobs/active        │
│  - JobBanner (poll)     │  JSON   │  / (SPA fallback, prod build only)       │
└─────────────────────────┘         └──────────────────────────────────────────┘
                                            │
                                            │ in-process calls
                                            ▼
                                    ┌────────────────────────────────────────┐
                                    │  Service layer (app/services/*)        │
                                    │   datasets / preprocessing / training  │
                                    │   prediction / analysis                │
                                    └────────────────────────────────────────┘
                                            │
                                            │ uses domain modules
                                            ▼
                                    ┌────────────────────────────────────────┐
                                    │  Domain (backend/)                     │
                                    │   utils.data_processor                 │
                                    │   utils.data_collector                 │
                                    │   utils.visualizer                     │
                                    │   train_model.TrafficPredictor         │
                                    │   predict.TrafficForecaster            │
                                    └────────────────────────────────────────┘
                                            │
                                            ▼
                                    ┌────────────────────────────────────────┐
                                    │  Filesystem                             │
                                    │   backend/data/raw/*.csv                │
                                    │   backend/data/processed/*.csv          │
                                    │   backend/data/predictions/*.csv        │
                                    │   backend/models/*.h5 + *_scaler.pkl    │
                                    └────────────────────────────────────────┘
```

핵심 결정 사항:

- 단일 포트 운영. Vite는 dev에서 `:5173` 프록시. 프로덕션 빌드 후엔 `uvicorn`이 `frontend/dist`까지 정적 서빙해 별도 웹서버가 필요 없다 (`backend/app/main.py:32-56`).
- 단일 사용자 MVP. 동시에 실행 가능한 잡은 **한 개**로 제한 (`backend/app/core/state.py:JobRegistry`).
- 영속성은 파일시스템에만 둔다. DB 없음. 잡 상태는 인메모리 dict.
- TensorFlow는 모든 진입점에서 **lazy import** — uvicorn 부팅 지연 방지 (`backend/app/services/training.py:34`, `backend/app/services/prediction.py:36`).

---

## 2. 디렉토리 구조

```
network_traffic_project/
├── backend/
│   ├── app/                          # FastAPI 애플리케이션
│   │   ├── main.py                   # FastAPI 인스턴스 + 라우터 등록 + SPA fallback
│   │   ├── api/                      # HTTP 라우터 (얇은 어댑터)
│   │   │   ├── health.py
│   │   │   ├── datasets.py           # 업로드/목록/전처리 트리거/분석
│   │   │   ├── train.py              # 학습 잡 트리거
│   │   │   ├── predict.py            # 예측 동기 실행
│   │   │   ├── models.py             # 학습 산출물 목록
│   │   │   └── jobs.py               # 잡 폴링
│   │   ├── core/
│   │   │   └── state.py              # JobRegistry (단일 슬롯)
│   │   ├── schemas/
│   │   │   └── common.py             # Pydantic out 모델
│   │   └── services/                 # 도메인 로직 어댑터
│   │       ├── datasets.py           # raw → processed 파일 경로 해석
│   │       ├── preprocessing.py      # default / geant 프리셋
│   │       ├── training.py           # TrafficPredictor 래퍼
│   │       ├── prediction.py         # TrafficForecaster 캐싱
│   │       └── analysis.py           # 분석 결과 JSON 직렬화
│   ├── utils/                        # 도메인 모듈 (CLI에서도 단독 사용 가능)
│   │   ├── data_collector.py         # psutil 기반 실시간 수집
│   │   ├── data_processor.py         # 전처리/특성공학/이상치
│   │   └── visualizer.py             # matplotlib/seaborn 시각화
│   ├── train_model.py                # TrafficPredictor (LSTM)
│   ├── predict.py                    # TrafficForecaster
│   ├── analyze_traffic.py            # CLI 분석 진입점
│   ├── generate_sample_data.py       # 더미 데이터 생성
│   ├── parse_geant.py / process_geant.py  # GEANT 데이터 처리
│   ├── config.py                     # 경로/하이퍼파라미터
│   ├── requirements.txt
│   ├── data/
│   │   ├── raw/         # 업로드된 원본
│   │   ├── processed/   # 전처리 결과
│   │   └── predictions/ # 예측 결과 CSV
│   └── models/          # *.h5, *_scaler.pkl, *_metrics.json
└── frontend/
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx                   # 페이지 조합 + 잡 흐름 오케스트레이션
    │   ├── api.ts                    # /api/* 호출
    │   ├── hooks.ts                  # useActiveJob 폴링 훅
    │   ├── types.ts                  # 백엔드 스키마 mirror
    │   ├── format.ts
    │   └── components/
    │       ├── DatasetList.tsx
    │       ├── ModelList.tsx
    │       ├── Actions.tsx           # Preprocess / Train / Predict 카드
    │       ├── Analysis.tsx
    │       ├── Predictions.tsx
    │       └── JobBanner.tsx
    ├── vite.config.ts
    ├── tailwind.config.js
    └── package.json
```

---

## 3. 레이어 구성

| 계층 | 위치 | 책임 | 의존 |
|------|------|------|------|
| UI Components | `frontend/src/components/` | 입력/표시. 비즈니스 로직 없음 | `api`, `types`, `hooks` |
| App Shell | `frontend/src/App.tsx` | 상태 통합·잡 라이프사이클 처리 | Components, Hooks |
| API Client | `frontend/src/api.ts` | `fetch` 래핑, 에러 표준화 | (브라우저) |
| HTTP API | `backend/app/api/*` | 검증 → 서비스 호출 → DTO 직렬화 | services, schemas |
| Service | `backend/app/services/*` | 잡 진행률 보고·캐싱·예외 변환 | utils, train_model, predict, JobRegistry |
| Domain | `backend/utils/*`, `train_model.py`, `predict.py` | TF·scikit·pandas 사용. CLI도 지원 | numpy/pandas/TF/sklearn |
| State | `backend/app/core/state.py` | 잡 등록·진행률·결과 (단일 슬롯) | threading |

원칙:

1. **API는 얇다.** Pydantic 검증과 HTTP 코드 매핑만. 도메인 로직 금지.
2. **Service가 잡과 도메인의 다리.** `JobRegistry.update()`로 진행률을 보고하고 예외를 잡 상태에 흡수.
3. **Domain은 모듈 단독 실행 가능.** 모든 핵심 모듈이 `__main__` 진입점을 가져 CLI에서 그대로 쓸 수 있다.
4. **TF lazy import.** uvicorn 워커가 부팅될 때 TF가 로딩되면 첫 응답이 수 초 늦어지므로 라우터/서비스 모듈 최상단에 TF를 두지 않는다.

---

## 4. 데이터 흐름 — 학습 파이프라인

```
사용자                  Frontend                  Backend                       Filesystem
──────                  ────────                  ───────                       ──────────
업로드 ────────────────► POST /api/datasets/upload ► datasets.py
                                                  └─► RAW_DATA_DIR/<name>.csv  ───► raw/

[preprocess]                                       POST /datasets/{name}/process
                                                   ├─ JobRegistry.create("preprocess")
                                                   └─ BackgroundTasks
                                                         └─► services.preprocessing
                                                               ├─ default → TrafficDataProcessor.process_and_save
                                                               └─ geant   → clip→log1p→features→lags→anomaly
                                                                       │
                                                                       └────────► processed/
                          poll /api/jobs/active ◄── JobRegistry.update(progress, msg)
                          (idle 2.5s, busy 0.8s)

[train]                                            POST /api/train
                                                   ├─ JobRegistry.create("train")
                                                   ├─ prediction cache invalidate
                                                   └─ BackgroundTasks
                                                         └─► services.training
                                                               └─ TrafficPredictor
                                                                    ├─ prepare_data
                                                                    ├─ build_lstm_model
                                                                    ├─ train (with _ProgressCallback)
                                                                    └─ save_model
                                                                              │
                                                                              └─► models/
                                                                                   ├─ traffic_lstm_<ts>.h5
                                                                                   ├─ ..._scaler.pkl
                                                                                   ├─ ..._target_scaler.pkl
                                                                                   └─ ..._metrics.json

[predict]                                          POST /api/predict
                                                   └─► services.prediction
                                                         ├─ _get_forecaster (캐시 hit/miss)
                                                         │   └─ TrafficForecaster.__init__
                                                         │        (model+scaler 로딩)
                                                         └─ predict_next_steps
                                                              ◄── points: [{t, value}]

[analyze]                                          GET /api/datasets/{n}/analysis
                                                   └─► services.analysis.run_analysis
                                                        ◄── stats/peaks/hourly/daily/anomalies/...
```

---

## 5. Job 모델 — 단일 슬롯 동시성

`backend/app/core/state.py`에 정의된 `JobRegistry`는 프로세스 내에서 한 번에 하나의 잡만 허용한다.

- 상태: `pending → running → succeeded | failed` (`JobStatus` 리터럴).
- `create(kind)`가 `_active_id`를 점유하고 새 잡 생성. 이미 점유 중이면 `RuntimeError` → 라우터에서 HTTP 409로 변환.
- `update()`에서 `status in ("succeeded", "failed")`가 되는 순간 `_active_id`를 해제 — 다음 잡이 들어올 수 있다.
- 프론트는 `useActiveJob` 훅이 `/api/jobs/active`를 폴링: 활성 잡 있으면 800ms, 없으면 2500ms 간격. running→null 전이가 감지되면 마지막 잡 ID로 `/api/jobs/{id}` 한 번 더 호출해 결과를 받아온다 (`frontend/src/hooks.ts:39-48`).

확장 시: SQLite/JSON 파일 백킹으로 `JobRegistry`만 교체하면 영속성 확보. API 계약 변경 없음.

---

## 6. 보안 / 안전 가드

| 가드 | 위치 | 목적 |
|------|------|------|
| 업로드 화이트리스트 | `datasets.upload` `_safe_filename`, `^[A-Za-z0-9._-]+$`, `.csv` only | 경로 traversal·임의 확장자 차단 |
| 업로드 크기 제한 | `datasets.upload` MAX 100MB | 디스크 보호 |
| 데이터셋 경로 해석 | `services.datasets.resolve_dataset` | basename만 허용. `RAW → PROCESSED` 순으로 탐색 |
| SPA fallback 경로 검증 | `main.spa_fallback` `target.relative_to(DIST_DIR)` | 정적 자산 디렉터리 밖 접근 차단 (403) |
| `/api` 미정의 경로 404 강제 | `main.spa_fallback` 첫 분기 | SPA 응답이 API 오류를 가리지 않도록 |
| 잡 동시성 차단 | `JobRegistry.create` | TF 세션·디스크 IO 충돌 방지 |
| 학습 누설 차단 | `TrafficPredictor.prepare_data` exclude_cols | target 구성요소(sent/recv) 및 파생값 제외 + scaler를 train에서만 fit |
| 모델 입력 feature 사전 검증 | `services.prediction._required_features` | scaler `feature_names_in_`로 누락 컬럼을 명시적 에러로 변환 |

---

## 7. 외부 의존 / 기술 스택

**백엔드** (`backend/requirements.txt`)
- FastAPI + uvicorn — HTTP 서버
- Pydantic — 입출력 검증
- TensorFlow/Keras — LSTM 학습·예측
- scikit-learn — MinMaxScaler/StandardScaler, 평가 지표
- pandas/numpy — 데이터 처리
- joblib — scaler 직렬화
- psutil — 네트워크 통계 수집 (`utils/data_collector.py`)
- matplotlib/seaborn — `utils/visualizer.py` (백엔드 응답엔 사용 안 함)

**프론트엔드** (`frontend/package.json`)
- React 18 + TypeScript
- Vite — dev server + 프로덕션 빌드
- Tailwind CSS — 스타일
- Recharts — 차트 (Analysis/Predictions)
- ESLint — 정적 검사

**런타임 구성**
- 개발: `cd frontend && npm run dev` (`:5173`) ↔ `cd backend && uvicorn app.main:app --reload` (`:8000`) — Vite proxy로 `/api` 전달.
- 배포: `npm run build` 후 `uvicorn app.main:app --port 8000` 단일 프로세스. `frontend/dist`가 존재하면 같은 포트에서 SPA를 서빙.

---

## 8. 설정 (`backend/config.py`)

| 키 | 기본값 | 영향 |
|----|--------|------|
| `RAW_DATA_DIR`, `PROCESSED_DATA_DIR`, `PREDICTIONS_DIR`, `MODELS_DIR` | `backend/{data,models}/*` | 모든 IO 루트 |
| `SEQUENCE_LENGTH` | 120 | LSTM 입력 윈도우 (1초 간격 기준 2분) |
| `LSTM_UNITS` | `[32, 16]` | 2층 LSTM 유닛 수 |
| `DROPOUT_RATE` | 0.2 | LSTM/Dense 드롭아웃 |
| `LEARNING_RATE` | 0.001 | Adam |
| `EPOCHS` | 50 | EarlyStopping(patience=10)로 자동 중단 |
| `BATCH_SIZE` | 32 | — |
| `PREDICTION_STEPS` | 24 | 기본 예측 미래 시점 수 |
| `COLLECTION_INTERVAL`, `COLLECTION_DURATION` | 1초 / 300초 | `NetworkTrafficCollector` |

---

## 9. 확장 포인트

| 요구 | 손볼 곳 | 영향 범위 |
|------|---------|-----------|
| 다중 사용자 / 잡 큐 | `app/core/state.py` JobRegistry → SQLite/Redis queue | 라우터 변경 없음 |
| 새 전처리 프리셋 | `app/services/preprocessing.py`에 `_run_<name>` 추가, `Preset` Literal 확장 | datasets 라우터의 `ProcessRequest.preset` 정규식, 프론트 select 옵션 |
| 새 모델 타입 | `train_model.TrafficPredictor.build_<x>_model` 추가, `model_type` Literal 확장 | services.training 분기 없음 (이미 위임됨) |
| 인증 | FastAPI 의존성 (`Depends(get_current_user)`) | 각 라우터에 부착 |
| 실시간 진행률 (WebSocket) | `app/api/jobs.py`에 `/ws` 추가, `JobRegistry.update` 후 pub/sub | 프론트 `useActiveJob` 폴링 대체 |
