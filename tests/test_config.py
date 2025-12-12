"""Tests for configuration loading from environment files."""

import logging
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from src.config import SubmissionType, load_configs
from src.constants import CLONE_URL


@pytest.fixture
def temp_env_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    """Create temporary env directory and point config module to it."""
    env_dir = tmp_path / "env"
    env_dir.mkdir()

    original_path = Path

    def mock_path(path_str: str) -> Path:
        if path_str == "env/":
            return env_dir
        return original_path(path_str)

    monkeypatch.setattr("src.config.Path", mock_path)
    return env_dir


class TestLoadConfigs:
    """Tests for load_configs function."""

    @pytest.mark.parametrize(
        ("env_content", "expected_type", "expected_attrs"),
        [
            (
                "CONFIG_NAME=TestConfig\nFORM_URL=https://forms.google.com/test\nSEARCH_URL=https://zillow.com/search\n",
                SubmissionType.FORM,
                {"config_name": "TestConfig", "form_url": "https://forms.google.com/test", "search_url": "https://zillow.com/search"},
            ),
            (
                "SHEET_URL=https://docs.google.com/spreadsheets/test\nSEARCH_URL=https://zillow.com/search\nSHEET_NAME=MySheet\n",
                SubmissionType.SHEET,
                {"sheet_url": "https://docs.google.com/spreadsheets/test", "search_url": "https://zillow.com/search", "sheet_name": "MySheet"},
            ),
            ("SEARCH_URL=https://zillow.com/search\n", SubmissionType.NONE, {"form_url": None, "sheet_url": None, "search_url": "https://zillow.com/search"}),
        ],
    )
    def test_load_single_config(self, temp_env_dir: Path, env_content: str, expected_type: SubmissionType, expected_attrs: dict) -> None:
        """Test loading various single configuration files."""
        config_file = temp_env_dir / "config.env"
        config_file.write_text(env_content)

        configs = load_configs(temp_env_dir)

        assert len(configs) == 1
        assert configs[0].submission_type == expected_type

        for attr, expected_value in expected_attrs.items():
            assert getattr(configs[0], attr) == expected_value

    def test_config_name_defaults_to_filename(self, temp_env_dir: Path) -> None:
        """Test that CONFIG_NAME defaults to filename stem."""
        config_file = temp_env_dir / "myconfig.env"
        config_file.write_text("SEARCH_URL=https://zillow.com/search\n")

        configs = load_configs(temp_env_dir)
        assert configs[0].config_name == "myconfig"

    def test_load_multiple_configs(self, temp_env_dir: Path) -> None:
        """Test loading multiple valid configuration files."""
        (temp_env_dir / "config1.env").write_text("FORM_URL=https://forms.google.com/test1\nSEARCH_URL=https://zillow.com/search1\n")
        (temp_env_dir / "config2.env").write_text("SHEET_URL=https://docs.google.com/spreadsheets/test2\nSEARCH_URL=https://zillow.com/search2\n")

        configs = load_configs(temp_env_dir)

        assert len(configs) == 2
        assert {c.config_name for c in configs} == {"config1", "config2"}
        assert {c.submission_type for c in configs} == {SubmissionType.FORM, SubmissionType.SHEET}

    def test_sheet_prioritized_over_form(self, temp_env_dir: Path) -> None:
        """Test that SHEET_URL takes priority over FORM_URL when both are present."""
        config_file = temp_env_dir / "config.env"
        config_file.write_text(
            "FORM_URL=https://forms.google.com/test\nSHEET_URL=https://docs.google.com/spreadsheets/test\nSEARCH_URL=https://zillow.com/search\n"
        )

        configs = load_configs(temp_env_dir)

        assert configs[0].submission_type == SubmissionType.SHEET
        assert configs[0].sheet_url == "https://docs.google.com/spreadsheets/test"

    def test_default_search_url(self, temp_env_dir: Path) -> None:
        """Test that SEARCH_URL defaults to CLONE_URL when not provided."""
        config_file = temp_env_dir / "config.env"
        config_file.write_text("FORM_URL=https://forms.google.com/test\n")

        configs = load_configs(temp_env_dir)
        assert configs[0].search_url == CLONE_URL

    def test_default_sheet_name(self, temp_env_dir: Path) -> None:
        """Test that SHEET_NAME defaults to 'Sheet1' when not provided."""
        config_file = temp_env_dir / "config.env"
        config_file.write_text("SHEET_URL=https://docs.google.com/spreadsheets/test\nSEARCH_URL=https://zillow.com/search\n")

        configs = load_configs(temp_env_dir)
        assert configs[0].sheet_name == "Sheet1"

    def test_missing_search_url_skips_config(self, caplog: LogCaptureFixture, temp_env_dir: Path) -> None:
        """Test that configs with empty SEARCH_URL are skipped."""
        (temp_env_dir / "valid.env").write_text("SEARCH_URL=https://zillow.com/search\n")
        (temp_env_dir / "invalid.env").write_text("SEARCH_URL=\n")

        with caplog.at_level(logging.ERROR):
            configs = load_configs(temp_env_dir)
            assert "Missing SEARCH_URL" in caplog.text

        assert len(configs) == 1
        assert configs[0].config_name == "valid"

    def test_no_valid_configs_exits(self, caplog: LogCaptureFixture, temp_env_dir: Path) -> None:
        """Test that having no valid configs causes system exit."""
        (temp_env_dir / "invalid.env").write_text("SEARCH_URL=\n")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                load_configs(temp_env_dir)
            assert "No valid configurations found" in caplog.text

        assert exc_info.value.code == 1

    def test_missing_env_directory_exits(self, caplog: LogCaptureFixture) -> None:
        """Test that missing env directory causes system exit."""
        invalid_path = Path("nonexistent_env_directory")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                load_configs(invalid_path)
            assert f"{invalid_path!s} directory not found" in caplog.text

        assert exc_info.value.code == 1

    def test_ignores_subdirectories(self, temp_env_dir: Path) -> None:
        """Test that subdirectories are ignored during config loading."""
        (temp_env_dir / "config.env").write_text("SEARCH_URL=https://zillow.com/search\n")

        subdir = temp_env_dir / "subdir"
        subdir.mkdir()
        (subdir / "config_subdir.env").write_text("SEARCH_URL=https://zillow.com/search\n")

        configs = load_configs(temp_env_dir)
        assert len(configs) == 1
