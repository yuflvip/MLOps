from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI

from app.api.deps.request_context import install_request_context_middleware
from app.api.errors.http import install_http_error_handlers
from app.api.routers import install_routers
from app.bootstrap.container import build_container
from app.bootstrap.lifespan import application_lifespan
from app.infrastructure.logging import configure_logging


def create_app(config_path: Optional[Union[Path, str]] = None) -> FastAPI:
    container = build_container(config_path=config_path)
    settings = container.settings

    configure_logging(settings.logging)

    app = FastAPI(
        title=settings.app.name,
        debug=settings.app.debug,
        root_path=settings.app.root_path,
        docs_url=settings.app.docs_url,
        openapi_url=settings.app.openapi_url,
        lifespan=application_lifespan,
    )
    app.state.container = container

    install_request_context_middleware(app)
    install_http_error_handlers(app)
    install_routers(app, container)
    return app


app = create_app()
