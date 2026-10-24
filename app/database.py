import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://ledger:ledger@localhost:5432/ledger"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class RunModel(Base):
    __tablename__ = "runs"

    run_id = Column(String, primary_key=True)
    sandbox_name = Column(String, nullable=False)
    problem_id = Column(String, nullable=False)
    state = Column(String, nullable=False)
    execution_target = Column(String, nullable=False, default="celesto_sandbox")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create tables if they don't already exist (for local dev without Docker seed)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
