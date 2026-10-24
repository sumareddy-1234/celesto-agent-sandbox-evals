from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .database import get_db, RunModel, init_db
from .models import RunCreate, RunOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: create tables (idempotent; in Docker the seed SQL runs first)
    await init_db()
    yield


app = FastAPI(title="Celesto Run Ledger API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Assessment requires invalid requests (bad target, bad state, bad name) to return 400."""
    return JSONResponse(
        status_code=400,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/runs", response_model=List[RunOut])
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunModel).order_by(RunModel.created_at))
    return result.scalars().all()


@app.post("/api/runs", status_code=201, response_model=RunOut)
async def create_run(run: RunCreate, db: AsyncSession = Depends(get_db)):
    obj = RunModel(**run.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj
