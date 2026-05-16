"""학습 잡 실행 — TrafficPredictor를 라우터에서 호출 가능하게 감싼다.

- TF/Keras는 함수 진입 시점에 lazy import (uvicorn 부팅 지연 방지).
- 진행률은 _ProgressCallback이 epoch마다 JobRegistry 갱신.
- 학습 종료 후 tf.keras.backend.clear_session()로 세션 누적 방지.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from app.core.state import registry
from app.services.datasets import resolve_dataset


def run_training(
    job_id: str,
    dataset: str,
    *,
    model_type: str = "lstm",
    epochs: int | None = None,
    batch_size: int | None = None,
    sequence_length: int | None = None,
) -> None:
    """JobRegistry에 미리 등록된 학습 잡을 실행하고 완료/실패를 보고한다.

    Why: BackgroundTasks에서 직접 호출되는 진입점. 예외도 여기서 잡아 잡 상태에 기록한다.
    """
    try:
        import pandas as pd
        import tensorflow as tf
        from tensorflow.keras.callbacks import Callback

        from config import BATCH_SIZE, EPOCHS, MODELS_DIR, SEQUENCE_LENGTH
        from train_model import TrafficPredictor

        ep = epochs or EPOCHS
        bs = batch_size or BATCH_SIZE
        seq = sequence_length or SEQUENCE_LENGTH

        data_path = resolve_dataset(dataset)
        registry.update(job_id, progress=0.05, message=f"loading {data_path.name}")
        df = pd.read_csv(data_path)

        predictor = TrafficPredictor(sequence_length=seq, model_type=model_type)

        registry.update(job_id, progress=0.10, message="preparing sequences")
        X_train, X_test, y_train, y_test, feature_cols = predictor.prepare_data(df)

        split_idx = int(len(X_train) * 0.9)
        X_val, y_val = X_train[split_idx:], y_train[split_idx:]
        X_train, y_train = X_train[:split_idx], y_train[:split_idx]

        class _ProgressCallback(Callback):
            """epoch 종료 시점마다 잡 진행률을 0.10 → 0.90 구간에 매핑."""

            def __init__(self, total_epochs: int) -> None:
                super().__init__()
                self.total = max(1, total_epochs)

            def on_epoch_end(self, epoch, logs=None):  # type: ignore[override]
                fraction = (epoch + 1) / self.total
                progress = 0.10 + 0.80 * fraction
                logs = logs or {}
                msg = (
                    f"epoch {epoch + 1}/{self.total} "
                    f"loss={logs.get('loss', 0):.4f} "
                    f"val_loss={logs.get('val_loss', 0):.4f}"
                )
                registry.update(job_id, progress=progress, message=msg)

        predictor.train(
            X_train,
            y_train,
            X_val,
            y_val,
            epochs=ep,
            batch_size=bs,
            extra_callbacks=[_ProgressCallback(ep)],
        )

        registry.update(job_id, progress=0.92, message="evaluating")
        metrics, _ = predictor.evaluate(X_test, y_test)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"traffic_{model_type}_{timestamp}.h5"
        model_path = os.path.join(MODELS_DIR, model_name)
        predictor.save_model(model_path)

        metrics_path = model_path.replace(".h5", "_metrics.json")
        Path(metrics_path).write_text(json.dumps(metrics, indent=2))

        registry.update(
            job_id,
            status="succeeded",
            progress=1.0,
            message="done",
            result={
                "model_name": model_name,
                "metrics": metrics,
                "feature_cols": feature_cols,
            },
        )
    except Exception as e:  # noqa: BLE001 — 라우터로 예외를 흘려보내지 않고 잡 상태에 기록
        registry.update(job_id, status="failed", error=str(e))
    finally:
        try:
            import tensorflow as tf  # 재import 안전

            tf.keras.backend.clear_session()
        except Exception:  # noqa: BLE001
            pass
