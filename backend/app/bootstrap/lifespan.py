from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = app.state.container
    container.scheduler_manager.start()
    await container.model_conversion_scheduler.start()
    try:
        yield
    finally:
        await container.model_conversion_scheduler.shutdown()
        container.scheduler_manager.shutdown()
