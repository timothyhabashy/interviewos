from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interviewos.http.db import create_schema, make_engine, make_session_factory
from interviewos.http.routes import router
from interviewos.http.settings import cors_origins, database_url


def create_app(database: str | None = None) -> FastAPI:
    app = FastAPI(title="InterviewOS API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    engine = make_engine(database or database_url())
    create_schema(engine)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.include_router(router)
    return app


app = create_app()
