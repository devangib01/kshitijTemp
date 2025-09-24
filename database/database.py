from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from config.config import Config
URL_DATABASE = Config.DATABASE_URL

engine = create_async_engine(URL_DATABASE, future=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

