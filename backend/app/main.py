from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import datasets, health, jobs, models, predict, train

APP_VERSION = "0.1.0"

app = FastAPI(title="Network Traffic MVP API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
app.include_router(train.router, prefix="/api/train", tags=["train"])
app.include_router(predict.router, prefix="/api/predict", tags=["predict"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])


# 단일 포트 운영용. dev 에선 Vite 가 :5173 에서 /api 프록시. prod 빌드(`npm run build`)
# 후엔 같은 uvicorn 이 정적 자산까지 서빙해 별도 웹서버가 필요 없어진다.
DIST_DIR = (Path(__file__).resolve().parent.parent.parent / "frontend" / "dist").resolve()
ASSETS_DIR = DIST_DIR / "assets"
INDEX_HTML = DIST_DIR / "index.html"

if INDEX_HTML.exists():
    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        """/api 미정의 경로는 404 유지, 그 외는 실제 파일 혹은 index.html.

        Why: 위에서 등록한 /api/* 라우터에 매칭되지 않은 /api 요청도 catch-all 로 떨어진다.
        SPA 응답으로 가리지 않고 404 가 나도록 명시적으로 차단해야 클라이언트가 API 오류를 인지.
        """
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        target = (DIST_DIR / full_path).resolve()
        try:
            target.relative_to(DIST_DIR)
        except ValueError as e:
            raise HTTPException(status_code=403, detail="forbidden") from e
        if target.is_file():
            return FileResponse(target)
        return FileResponse(INDEX_HTML)
