"""Configuration loading from environment files."""

import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import cast

import dotenv

from src.constants import CLONE_URL

logger = logging.getLogger(__name__)


class SubmissionType(Enum):
    """Type of submission destination."""

    FORM = "form"
    SHEET = "sheet"
    NONE = "none"


@dataclass
class Config:
    """Configuration for scraping and submitting."""

    config_name: str
    search_url: str

    submission_type: SubmissionType
    form_url: str | None = None
    sheet_url: str | None = None
    sheet_name: str = "Sheet1"


def load_configs(env_dir: Path | None = None) -> list[Config]:
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
        config_name = cast("str", dotenv_values.get("CONFIG_NAME", env_file.stem))
        search_url = dotenv_values.get("SEARCH_URL", CLONE_URL)
        form_url = dotenv_values.get("FORM_URL")
        sheet_url = dotenv_values.get("SHEET_URL")
        sheet_name = cast("str", dotenv_values.get("SHEET_NAME", "Sheet1"))

        if not search_url:
            logger.error("Missing SEARCH_URL in %s", env_file)
            continue

        if sheet_url:
            submission_type = SubmissionType.SHEET
        elif form_url:
            submission_type = SubmissionType.FORM
        else:
            submission_type = SubmissionType.NONE
            logger.warning("No submission destination for config '%s'", config_name)

        try:
            config = Config(
                config_name=config_name,
                search_url=search_url,
                submission_type=submission_type,
                form_url=form_url,
                sheet_url=sheet_url,
                sheet_name=sheet_name,
            )
            configs.append(config)
            logger.debug("Loaded config '%s' from file: '%s'", config_name, env_file)
        except ValueError as e:
            logger.error("Invalid config in %s: %s", env_file, e)
            continue

    if not configs:
        logger.error("No valid configurations found")
        sys.exit(1)

    return configs
