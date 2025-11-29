"""Tests for configuration loading from environment files."""

import logging
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from src.config import ScraperConfig, load_configs
from src.constants import ZillowURLs

# ruff: noqa: PLR2004


class TestScraperConfig:
    """Tests for ScraperConfig dataclass."""

    def test_scraper_config(self) -> None:
        """Test creating ScraperConfig with form URL."""
        config = ScraperConfig(
            form_url="https://forms.google.com/test",
            search_url="https://zillow.com/search",
            config_name="test.env",
        )
        assert config.form_url == "https://forms.google.com/test"
        assert config.search_url == "https://zillow.com/search"
        assert config.config_name == "test.env"


class TestLoadConfigs:
    """Tests for load_configs function."""

    @pytest.fixture
    def temp_env_dir(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
        """Create temporary env directory and point config module to it."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()

        original_path = Path

        def mock_path(path_str: str) -> Path:
            if path_str == "env/":
                return env_dir
            return original_path(path_str)

        monkeypatch.setattr("config.Path", mock_path)
        return env_dir

    def test_load_single_valid_config(self, temp_env_dir: Path) -> None:
        """Test loading a single valid configuration file."""
        config_file = temp_env_dir / "config1.env"
        config_file.write_text("FORM_URL=https://forms.google.com/test\nSEARCH_URL=https://zillow.com/search\n")

        configs = load_configs(temp_env_dir)

        assert len(configs) == 1
        assert configs[0].form_url == "https://forms.google.com/test"
        assert configs[0].search_url == "https://zillow.com/search"
        assert configs[0].config_name == "config1.env"

    def test_load_multiple_valid_configs(self, temp_env_dir: Path) -> None:
        """Test loading multiple valid configuration files."""
        config_file1 = temp_env_dir / "config1.env"
        config_file1.write_text("FORM_URL=https://forms.google.com/test1\nSEARCH_URL=https://zillow.com/search1\n")

        config_file2 = temp_env_dir / "config2.env"
        config_file2.write_text("FORM_URL=https://forms.google.com/test2\nSEARCH_URL=https://zillow.com/search2\n")

        configs = load_configs(temp_env_dir)

        assert len(configs) == 2
        config_names = {c.config_name for c in configs}
        assert config_names == {"config1.env", "config2.env"}

        # Find each config and verify
        config1 = next(c for c in configs if c.config_name == "config1.env")
        config2 = next(c for c in configs if c.config_name == "config2.env")

        assert config1.form_url == "https://forms.google.com/test1"
        assert config1.search_url == "https://zillow.com/search1"
        assert config2.form_url == "https://forms.google.com/test2"
        assert config2.search_url == "https://zillow.com/search2"

    def test_load_config_without_form_url(self, temp_env_dir: Path) -> None:
        """Test loading config when FORM_URL is not provided."""
        config_file = temp_env_dir / "config.env"
        config_file.write_text("SEARCH_URL=https://zillow.com/search\n")

        configs = load_configs(temp_env_dir)

        assert len(configs) == 1
        assert configs[0].form_url is None
        assert configs[0].search_url == "https://zillow.com/search"

    def test_load_config_uses_default_search_url(self, temp_env_dir: Path) -> None:
        """Test loading config uses default CLONE_URL when SEARCH_URL not provided."""
        config_file = temp_env_dir / "config.env"
        config_file.write_text("FORM_URL=https://forms.google.com/test\n")

        configs = load_configs(temp_env_dir)

        assert len(configs) == 1
        assert configs[0].search_url == ZillowURLs.CLONE_URL

    def test_load_config_skips_empty_search_url(self, caplog: LogCaptureFixture, temp_env_dir: Path) -> None:
        """Test that configs with empty SEARCH_URL are skipped."""
        config_file = temp_env_dir / "config.env"
        config_file.write_text("FORM_URL=https://forms.google.com/test\nSEARCH_URL=\n")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                load_configs(temp_env_dir)
            assert "No valid configurations found" in caplog.text

        assert exc_info.value.code == 1

    def test_load_configs_mixed_valid_invalid(self, temp_env_dir: Path) -> None:
        """Test loading when some configs are valid and some are invalid."""
        # Valid config
        valid_file = temp_env_dir / "valid.env"
        valid_file.write_text("SEARCH_URL=https://zillow.com/search\n")

        # Invalid config (empty SEARCH_URL)
        invalid_file = temp_env_dir / "invalid.env"
        invalid_file.write_text("SEARCH_URL=\n")

        configs = load_configs(temp_env_dir)

        # Should only load the valid config
        assert len(configs) == 1
        assert configs[0].config_name == "valid.env"

    def test_load_configs_all_invalid_exits(self, caplog: LogCaptureFixture, temp_env_dir: Path) -> None:
        """Test that having only invalid configs causes system exit."""
        # Config with no SEARCH_URL and no default used
        invalid_file = temp_env_dir / "invalid.env"
        invalid_file.write_text("SEARCH_URL=\n")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                load_configs(temp_env_dir)
            assert "No valid configurations found" in caplog.text

        assert exc_info.value.code == 1

    def test_load_configs_missing_folder(self, caplog: LogCaptureFixture) -> None:
        """Test that having only invalid configs causes system exit."""
        # Config with no SEARCH_URL and no default used
        invalid_path = Path("env") / "invalid.env"

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                load_configs(invalid_path)
            assert f"{invalid_path!s} directory not found" in caplog.text

        assert exc_info.value.code == 1
