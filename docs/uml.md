# UML — Network Traffic MVP

Mermaid 기반 UML 다이어그램 모음. GitHub/VSCode/PyCharm Markdown 프리뷰에서 그대로 렌더된다.

> 모든 도메인/서비스 이름은 `backend/`와 `frontend/src/` 의 실제 모듈에서 가져왔다.

---

## 1. 컴포넌트 다이어그램

시스템 전체 구성과 의존 방향을 한 장에 표현.

```mermaid
flowchart LR
    subgraph Browser["Browser (React + Vite)"]
        UI_App["App.tsx"]
        UI_DS["DatasetList"]
        UI_ML["ModelList"]
        UI_Act["Actions<br/>(Preprocess / Train / Predict)"]
        UI_An["Analysis"]
        UI_Pr["Predictions"]
        UI_JB["JobBanner"]
        UI_Api["api.ts"]
        UI_Hk["useActiveJob (hooks.ts)"]
        UI_App --> UI_DS
        UI_App --> UI_ML
        UI_App --> UI_Act
        UI_App --> UI_An
        UI_App --> UI_Pr
        UI_App --> UI_JB
        UI_App --> UI_Hk
        UI_Act --> UI_Api
        UI_An --> UI_Api
        UI_Pr --> UI_Api
        UI_Hk --> UI_Api
    end

    subgraph Server["FastAPI (uvicorn, single process)"]
        direction TB
        R_Health["api/health"]
        R_DS["api/datasets"]
        R_Tr["api/train"]
        R_Pr["api/predict"]
        R_Md["api/models"]
        R_Jb["api/jobs"]

        subgraph Svc["app/services"]
            S_DS["datasets.resolve_dataset"]
            S_Pre["preprocessing"]
            S_Tr["training"]
            S_Pred["prediction (+ cache)"]
            S_An["analysis"]
        end

        State["core/state<br/>JobRegistry (single slot)"]

        R_DS --> S_DS
        R_DS --> S_Pre
        R_DS --> S_An
        R_Tr --> S_Tr
        R_Tr --> S_Pred
        R_Pr --> S_Pred
        R_Md --> FS
        R_Jb --> State
        S_Pre --> State
        S_Tr --> State
    end

    subgraph Domain["backend (domain)"]
        D_Coll["utils.data_collector<br/>NetworkTrafficCollector"]
        D_Proc["utils.data_processor<br/>TrafficDataProcessor"]
        D_Viz["utils.visualizer<br/>TrafficVisualizer"]
        D_Tr["train_model<br/>TrafficPredictor"]
        D_Pr["predict<br/>TrafficForecaster"]
    end

    FS[("Filesystem<br/>data/{raw,processed,predictions}<br/>models/*.h5 *.pkl")]

    UI_Api -- "/api/*" --> R_Health
    UI_Api --> R_DS
    UI_Api --> R_Tr
    UI_Api --> R_Pr
    UI_Api --> R_Md
    UI_Api --> R_Jb

    S_Pre --> D_Proc
    S_Tr --> D_Tr
    D_Tr --> D_Proc
    S_Pred --> D_Pr
    D_Pr --> D_Proc
    D_Coll --> FS
    D_Proc --> FS
    D_Tr --> FS
    D_Pr --> FS
    S_An --> FS
```

---

## 2. 클래스 다이어그램 — 백엔드 핵심

도메인·서비스·상태의 주요 클래스. Pydantic out 모델은 데이터 전송 형태 표현용.

```mermaid
classDiagram
    direction LR

    class JobRegistry {
        -Lock _lock
        -dict~str,Job~ _jobs
        -str? _active_id
        +create(kind: str) Job
        +update(job_id, progress?, message?, status?, result?, error?)
        +get(job_id: str) Job?
        +active() Job?
    }

    class Job {
        +str id
        +str kind
        +JobStatus status
        +float progress
        +str message
        +dict? result
        +str? error
        +datetime created_at
        +datetime updated_at
    }

    class JobOut {
        <<Pydantic>>
        +str id
        +str kind
        +JobStatus status
        +float progress
        +str message
        +dict? result
        +str? error
        +datetime created_at
        +datetime updated_at
    }

    class DatasetOut {
        <<Pydantic>>
        +str name
        +Literal kind  "raw|processed"
        +int size_bytes
        +datetime modified_at
    }

    class ModelOut {
        <<Pydantic>>
        +str name
        +int size_bytes
        +datetime modified_at
        +dict? metrics
    }

    class TrafficDataProcessor {
        +str scaler_type
        +Scaler scaler
        +load_data(filepath) DataFrame
        +add_time_features(df) DataFrame
        +add_statistical_features(df, window=10) DataFrame
        +add_lag_features(df, lags) DataFrame
        +detect_anomalies(df, column, threshold) DataFrame
        +create_sequences(data, seq_len, target) tuple
        +process_and_save(in, out, add_features, detect_anomaly) tuple
    }

    class NetworkTrafficCollector {
        +str? interface
        +int interval
        +list data
        +get_network_stats() dict
        +collect(duration: int)
        +save_data(filename) str
        +get_dataframe() DataFrame
    }

    class TrafficVisualizer {
        +tuple figsize
        +int dpi
        +plot_traffic_timeline(df, save_path)
        +plot_anomalies(df, save_path)
        +plot_distribution(df, save_path)
        +plot_predictions(actual, predicted, save_path)
        +plot_correlation_matrix(df, save_path)
    }

    class TrafficPredictor {
        +int sequence_length
        +str model_type
        +Model? model
        +Scaler? scaler
        +Scaler? target_scaler
        +TrafficDataProcessor processor
        +list~str~ feature_cols
        +build_lstm_model(input_shape) Model
        +prepare_data(df, target_col, test_size) tuple
        +train(X_tr, y_tr, X_val, y_val, epochs, batch_size, extra_callbacks) History
        +evaluate(X_test, y_test) tuple
        +save_model(filepath)
        +load_model(filepath)
    }

    class TrafficForecaster {
        +str model_path
        +Model model
        +Scaler? scaler
        +Scaler? target_scaler
        +TrafficDataProcessor processor
        +predict_next_steps(data, steps) ndarray
        +predict_with_confidence(data, steps, n_sim) dict
        +save_predictions(predictions, timestamps, output_path) str
    }

    class PreprocessingService {
        <<module>>
        +run_preprocessing(name, preset, add_features, detect_anomaly, output_name, job_id) dict
        +run_preprocessing_job(job_id, name, ...)
    }

    class TrainingService {
        <<module>>
        +run_training(job_id, dataset, model_type, epochs, batch_size, sequence_length)
    }

    class PredictionService {
        <<module>>
        -dict _cache
        -Lock _cache_lock
        +run_prediction(model_name, dataset, steps) list~dict~
        +invalidate(model_name?)
        -_get_forecaster(model_name) TrafficForecaster
    }

    class AnalysisService {
        <<module>>
        +run_analysis(name, bins, timeline_max_points, top_n_peaks, anomaly_samples) dict
    }

    class DatasetsService {
        <<module>>
        +resolve_dataset(name) Path
    }

    JobRegistry "1" o-- "*" Job
    Job ..> JobOut : serialized as
    TrafficPredictor o-- TrafficDataProcessor
    TrafficForecaster o-- TrafficDataProcessor
    TrainingService ..> TrafficPredictor : uses
    PredictionService ..> TrafficForecaster : caches
    PreprocessingService ..> TrafficDataProcessor : uses
    PreprocessingService ..> JobRegistry : reports
    TrainingService ..> JobRegistry : reports
    AnalysisService ..> DatasetsService : resolves
    PredictionService ..> DatasetsService : resolves
    PreprocessingService ..> DatasetsService : resolves
    TrainingService ..> DatasetsService : resolves
```

---

## 3. 클래스 다이어그램 — 프론트엔드 타입

`frontend/src/types.ts` 의 도메인 객체와 컴포넌트 의존을 정리한 도식.

```mermaid
classDiagram
    direction LR

    class Health {
        +string status
        +string service
        +string version
    }

    class Dataset {
        +string name
        +DatasetKind kind  "raw|processed"
        +number size_bytes
        +string modified_at
    }

    class Model {
        +string name
        +number size_bytes
        +string modified_at
        +Record~string,number~? metrics
    }

    class Job {
        +string id
        +string kind
        +JobStatus status
        +number progress
        +string message
        +Record? result
        +string? error
        +string created_at
        +string updated_at
    }

    class Analysis {
        +string name
        +number rows
        +string[] columns
        +AnalysisStats? stats
        +Period? period
        +Peak[]? peaks
        +HourlyPoint[]? hourly
        +DailyPoint[]? daily
        +AnomalyInfo? anomalies
        +Distribution? distribution
        +TimelinePoint[]? timeline
    }

    class PredictRequest {
        +string model
        +string dataset
        +number? steps
    }

    class PredictResponse {
        +string model
        +string dataset
        +number steps
        +PredictPoint[] points
    }

    class TrainRequest {
        +string dataset
        +string? model_type
        +number? epochs
        +number? batch_size
        +number? sequence_length
    }

    class PreprocessRequest {
        +Preset? preset  "default|geant"
        +boolean? add_features
        +boolean? detect_anomaly
        +string? output_name
    }

    class api {
        <<module>>
        +health() Promise~Health~
        +datasets() Promise~Dataset[]~
        +models() Promise~Model[]~
        +analyze(name, opts) Promise~Analysis~
        +activeJob() Promise~Job?~
        +job(id) Promise~Job~
        +preprocess(name, req) Promise~Job~
        +train(req) Promise~Job~
        +predict(req) Promise~PredictResponse~
    }

    class useActiveJob {
        <<hook>>
        +job: Job?
        +setJob(j)
    }

    class App {
        <<component>>
        -health: Health?
        -datasets: Dataset[]
        -models: Model[]
        -selected: string?
        -selectedModel: string?
        -prediction: PredictResponse?
        -activeJob: Job?
    }

    class Actions {
        <<component>>
        +PreprocessCard
        +TrainCard
        +PredictCard
    }

    App ..> useActiveJob
    App ..> Actions
    App ..> Analysis
    App ..> Dataset
    App ..> Model
    Actions ..> api
    Actions ..> PreprocessRequest
    Actions ..> TrainRequest
    Actions ..> PredictRequest
    api ..> Health
    api ..> Dataset
    api ..> Model
    api ..> Job
    api ..> Analysis
    api ..> PredictResponse
```

---

## 4. 시퀀스 다이어그램 — 학습 잡

`POST /api/train` 호출부터 진행률 폴링·완료 처리까지.

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as App.tsx
    participant Act as Actions(TrainCard)
    participant API as api.ts
    participant TR as api/train
    participant Reg as JobRegistry
    participant SVC as services.training
    participant TP as TrafficPredictor (TF)
    participant FS as Filesystem
    participant Hk as useActiveJob

    U->>Act: 학습 시작 클릭
    Act->>API: api.train({dataset, epochs, ...})
    API->>TR: POST /api/train
    TR->>Reg: create("train")
    Reg-->>TR: Job(running, id)
    TR->>SVC: BackgroundTasks.add_task(run_training)
    TR-->>API: 202 JobOut
    API-->>Act: Job
    Act->>FE: onJobStarted(job)
    FE->>Hk: setJob(job)

    par 백그라운드 실행
        SVC->>TP: prepare_data(df)
        SVC->>Reg: update(progress=0.10, "preparing sequences")
        loop epochs
            TP->>TP: model.fit (1 epoch)
            TP-->>SVC: on_epoch_end (callback)
            SVC->>Reg: update(progress, "epoch i/N loss=...")
        end
        SVC->>TP: evaluate(X_test, y_test)
        SVC->>FS: save_model(.h5, _scaler.pkl, _target_scaler.pkl, _metrics.json)
        SVC->>Reg: update(status="succeeded", result={model_name, metrics, feature_cols})
    and 폴링
        loop activeMs=800ms
            Hk->>API: api.activeJob()
            API->>TR: GET /api/jobs/active
            TR->>Reg: active()
            Reg-->>TR: Job(running, progress)
            TR-->>API: JobOut
            API-->>Hk: Job
            Hk-->>FE: setJob(job) → JobBanner 진행률
        end
    end

    Note over Hk,Reg: running → null 전이 감지
    Hk->>API: api.job(id) (최종 결과 한 번 더)
    API->>TR: GET /api/jobs/{id}
    TR-->>API: JobOut(succeeded, result)
    API-->>Hk: Job
    Hk->>FE: onFinished(job)
    FE->>FE: reloadKey++ → datasets/models refetch
    FE->>FE: setSelectedModel(result.model_name)
```

---

## 5. 시퀀스 다이어그램 — 예측 (동기)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant Act as Actions(PredictCard)
    participant API as api.ts
    participant PR as api/predict
    participant SVC as services.prediction
    participant Cache as _cache (dict)
    participant TFC as TrafficForecaster
    participant FS as Filesystem

    U->>Act: 예측 실행
    Act->>API: api.predict({model, dataset, steps})
    API->>PR: POST /api/predict
    PR->>SVC: run_prediction(model, dataset, steps)
    SVC->>SVC: resolve_dataset(dataset), read_csv

    alt cache hit
        SVC->>Cache: get(model_name)
        Cache-->>SVC: TrafficForecaster
    else cache miss
        SVC->>FS: exists(models/<model>.h5)?
        SVC->>TFC: TrafficForecaster(model_path)  ← TF lazy import
        TFC->>FS: load_model(.h5) + load(scaler.pkl, target_scaler.pkl)
        TFC-->>SVC: forecaster
        SVC->>Cache: put(model_name, forecaster)
    end

    SVC->>SVC: _required_features(forecaster) ← scaler.feature_names_in_
    alt 누락 feature 있음
        SVC-->>PR: raise ValueError("missing features ...")
        PR-->>API: 400 detail
        API-->>Act: Error
    else 정상
        SVC->>TFC: predict_next_steps(df, steps)
        TFC-->>SVC: ndarray (steps,)
        SVC-->>PR: [{t, value}, ...]
        PR-->>API: PredictResponse
        API-->>Act: PredictResponse
        Act->>Act: onPrediction(result)
    end
```

---

## 6. 시퀀스 다이어그램 — 전처리 잡

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant Act as Actions(PreprocessCard)
    participant API as api.ts
    participant DS as api/datasets
    participant Svc as services.preprocessing
    participant DP as TrafficDataProcessor
    participant Reg as JobRegistry
    participant FS as Filesystem

    U->>Act: 전처리 시작 (preset=default|geant)
    Act->>API: api.preprocess(name, {preset, output_name})
    API->>DS: POST /datasets/{name}/process

    DS->>DS: _safe_filename, resolve_dataset, _output_path (사전검증)
    DS->>Reg: create("preprocess")
    Reg-->>DS: Job(running)
    DS->>Svc: BackgroundTasks.add_task(run_preprocessing_job)
    DS-->>API: 202 JobOut

    par background
        alt preset=default
            Svc->>DP: process_and_save(in, out, ...)
            DP->>DP: add_time_features + add_statistical_features + add_lag_features + detect_anomalies
            DP->>FS: write processed/<output>.csv
        else preset=geant
            Svc->>DP: load_data + add_time_features + ...
            Svc->>Svc: clip(p99) + log1p + trend_index
            Svc->>DP: add_statistical_features + add_lag_features(1,4,96) + detect_anomalies
            Svc->>FS: write processed/<output>.csv
        end
        Svc->>Reg: update(progress 0.05→0.95, message)
        Svc->>Reg: update(status="succeeded", result={path,rows,columns,...})
    end

    Note right of Reg: useActiveJob 폴링이 완료를 감지<br/>App.tsx 가 datasets refetch + 새 파일 자동 선택
```

---

## 7. 상태 다이어그램 — Job 라이프사이클

```mermaid
stateDiagram-v2
    [*] --> pending : JobRegistry.create()
    pending --> running : 즉시 (생성 시 status="running")
    running --> succeeded : update(status="succeeded", result=...)
    running --> failed : update(status="failed", error=...)
    succeeded --> [*]
    failed --> [*]

    note right of running
      _active_id 점유
      progress 0.0 → 1.0
      message 업데이트
      프론트가 800ms 폴링
    end note

    note right of succeeded
      _active_id 해제
      다음 잡 등록 가능
      프론트가 onFinished 콜백
    end note
```

`JobRegistry.create`는 점유 중이면 `RuntimeError`를 던지고, 라우터가 이를 HTTP 409로 변환한다.

---

## 8. 배포 다이어그램

```mermaid
flowchart TB
    subgraph Dev["개발 환경"]
        direction LR
        ViteDev["Vite dev<br/>:5173"]
        UvDev["uvicorn --reload<br/>:8000"]
        ViteDev -- "proxy /api → :8000" --> UvDev
    end

    subgraph Prod["프로덕션 (단일 프로세스)"]
        direction LR
        UvProd["uvicorn app.main:app<br/>:8000"]
        Dist["frontend/dist/<br/>(npm run build)"]
        UvProd -- "/" --> Dist
        UvProd -- "/api/*" --> ApiR["FastAPI routers"]
    end

    subgraph Disk["디스크"]
        D1["backend/data/raw/"]
        D2["backend/data/processed/"]
        D3["backend/data/predictions/"]
        D4["backend/models/<br/>*.h5 / *_scaler.pkl / *_metrics.json"]
    end

    UvDev --- Disk
    UvProd --- Disk
```

dev에서는 두 프로세스(Vite + uvicorn), prod에서는 uvicorn 하나로 정적 자산과 API를 모두 처리한다 (`backend/app/main.py:36-56`).
