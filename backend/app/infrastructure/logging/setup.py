import logging

from app.infrastructure.config.settings import LoggingSettings


def configure_logging(settings: LoggingSettings) -> None:
    logging.basicConfig(level=settings.level.upper(), format=settings.format, force=True)
