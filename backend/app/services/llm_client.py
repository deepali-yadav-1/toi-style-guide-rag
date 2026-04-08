from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


def build_ssl_verify_config() -> bool | str:
    settings = get_settings()
    if settings.openai_ca_bundle:
        ca_bundle_path = Path(settings.openai_ca_bundle).expanduser()
        if ca_bundle_path.exists():
            return str(ca_bundle_path)
        logger.warning(
            "OPENAI_CA_BUNDLE was set to %s but the file does not exist. Falling back to OPENAI_VERIFY_SSL=%s",
            settings.openai_ca_bundle,
            settings.openai_verify_ssl,
        )
    return settings.openai_verify_ssl


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    settings = get_settings()
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            settings.openai_timeout_seconds,
            connect=settings.openai_connect_timeout_seconds,
        ),
        trust_env=settings.openai_trust_env,
        verify=build_ssl_verify_config(),
    )
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        http_client=http_client,
        max_retries=settings.openai_max_retries,
    )
