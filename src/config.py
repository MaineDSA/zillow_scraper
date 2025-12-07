"""Configuration loading from environment files."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import dotenv

from src.constants import CLONE_URL

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for a single scraping run."""

    form_url: str | None
    search_url: str
    config_name: str


def load_configs(env_dir: Path | None = None) -> list[ScraperConfig]:
    """Load all configurations from env directory."""
    configs = []
    if not env_dir:
        env_dir = Path("env/")

    if not env_dir.exists():
        logger.error("%s directory not found", str(env_dir))
        sys.exit(1)

    for env_file in env_dir.iterdir():
        if not env_file.is_file():
            continue

        dotenv_values = dotenv.dotenv_values(env_file)
        form_url = dotenv_values.get("FORM_URL", None)
        search_url = dotenv_values.get("SEARCH_URL", CLONE_URL)
        config_name = cast("str", dotenv_values.get("CONFIG_NAME", env_file.name))  # mypy doesn't know env_file.name is returned as default

        if not search_url:
            logger.error("Missing search url in %s", env_file)
            continue

        configs.append(ScraperConfig(form_url=form_url, search_url=search_url, config_name=config_name))
        logger.debug("Loaded config: '%s'", env_file)

    if not configs:
        logger.error("No valid configurations found")
        sys.exit(1)

    return configs
