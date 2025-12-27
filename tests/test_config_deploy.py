"""Behavioral tests for config_deploy module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finanzonline_databox.config_deploy import (
    _extract_deployed_paths,  # pyright: ignore[reportPrivateUsage]
    deploy_configuration,
)
from finanzonline_databox.enums import DeployTarget

pytestmark = pytest.mark.os_agnostic


class TestExtractDeployedPaths:
    """Tests for _extract_deployed_paths helper."""

    def test_extracts_created_paths(self) -> None:
        """Extracts paths for CREATED action."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        result = DeployResult(
            destination=Path("/tmp/config.toml"),
            action=DeployAction.CREATED,
            dot_d_results=[],
        )
        paths = _extract_deployed_paths([result])
        assert len(paths) == 1
        assert paths[0] == Path("/tmp/config.toml")

    def test_extracts_overwritten_paths(self) -> None:
        """Extracts paths for OVERWRITTEN action."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        result = DeployResult(
            destination=Path("/tmp/config.toml"),
            action=DeployAction.OVERWRITTEN,
            dot_d_results=[],
        )
        paths = _extract_deployed_paths([result])
        assert len(paths) == 1
        assert paths[0] == Path("/tmp/config.toml")

    def test_skips_kept_paths(self) -> None:
        """Skips paths for KEPT action."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        result = DeployResult(
            destination=Path("/tmp/config.toml"),
            action=DeployAction.KEPT,
            dot_d_results=[],
        )
        paths = _extract_deployed_paths([result])
        assert len(paths) == 0

    def test_extracts_dot_d_results(self) -> None:
        """Extracts paths from nested dot_d_results."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        dot_d_result = DeployResult(
            destination=Path("/tmp/config.d/extra.toml"),
            action=DeployAction.CREATED,
            dot_d_results=[],
        )
        result = DeployResult(
            destination=Path("/tmp/config.toml"),
            action=DeployAction.KEPT,  # Main file not deployed
            dot_d_results=[dot_d_result],
        )
        paths = _extract_deployed_paths([result])
        assert len(paths) == 1
        assert paths[0] == Path("/tmp/config.d/extra.toml")

    def test_extracts_multiple_paths(self) -> None:
        """Extracts multiple paths from multiple results."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        results = [
            DeployResult(
                destination=Path("/tmp/config1.toml"),
                action=DeployAction.CREATED,
                dot_d_results=[],
            ),
            DeployResult(
                destination=Path("/tmp/config2.toml"),
                action=DeployAction.OVERWRITTEN,
                dot_d_results=[],
            ),
        ]
        paths = _extract_deployed_paths(results)
        assert len(paths) == 2


class TestDeployConfiguration:
    """Tests for deploy_configuration function."""

    @patch("finanzonline_databox.config_deploy.deploy_config")
    @patch("finanzonline_databox.config_deploy.get_default_config_path")
    def test_deploys_to_user_target(self, mock_get_path: MagicMock, mock_deploy: MagicMock) -> None:
        """Deploys configuration to user target."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        mock_get_path.return_value = Path("/package/defaultconfig.toml")
        mock_deploy.return_value = [
            DeployResult(
                destination=Path("/home/user/.config/test/config.toml"),
                action=DeployAction.CREATED,
                dot_d_results=[],
            )
        ]

        result = deploy_configuration(targets=[DeployTarget.USER])

        assert len(result) == 1
        mock_deploy.assert_called_once()
        call_kwargs = mock_deploy.call_args.kwargs
        assert call_kwargs["targets"] == ["user"]
        assert call_kwargs["force"] is False

    @patch("finanzonline_databox.config_deploy.deploy_config")
    @patch("finanzonline_databox.config_deploy.get_default_config_path")
    def test_deploys_with_force(self, mock_get_path: MagicMock, mock_deploy: MagicMock) -> None:
        """Force flag is passed to deploy_config."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        mock_get_path.return_value = Path("/package/defaultconfig.toml")
        mock_deploy.return_value = [
            DeployResult(
                destination=Path("/home/user/.config/test/config.toml"),
                action=DeployAction.OVERWRITTEN,
                dot_d_results=[],
            )
        ]

        result = deploy_configuration(targets=[DeployTarget.USER], force=True)

        assert len(result) == 1
        call_kwargs = mock_deploy.call_args.kwargs
        assert call_kwargs["force"] is True

    @patch("finanzonline_databox.config_deploy.deploy_config")
    @patch("finanzonline_databox.config_deploy.get_default_config_path")
    def test_deploys_with_profile(self, mock_get_path: MagicMock, mock_deploy: MagicMock) -> None:
        """Profile is passed to deploy_config."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        mock_get_path.return_value = Path("/package/defaultconfig.toml")
        mock_deploy.return_value = [
            DeployResult(
                destination=Path("/home/user/.config/test/profile/production/config.toml"),
                action=DeployAction.CREATED,
                dot_d_results=[],
            )
        ]

        result = deploy_configuration(targets=[DeployTarget.USER], profile="production")

        assert len(result) == 1
        call_kwargs = mock_deploy.call_args.kwargs
        assert call_kwargs["profile"] == "production"

    @patch("finanzonline_databox.config_deploy.deploy_config")
    @patch("finanzonline_databox.config_deploy.get_default_config_path")
    def test_deploys_to_multiple_targets(self, mock_get_path: MagicMock, mock_deploy: MagicMock) -> None:
        """Deploys to multiple targets at once."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        mock_get_path.return_value = Path("/package/defaultconfig.toml")
        mock_deploy.return_value = [
            DeployResult(
                destination=Path("/etc/xdg/test/config.toml"),
                action=DeployAction.CREATED,
                dot_d_results=[],
            ),
            DeployResult(
                destination=Path("/home/user/.config/test/config.toml"),
                action=DeployAction.CREATED,
                dot_d_results=[],
            ),
        ]

        result = deploy_configuration(targets=[DeployTarget.APP, DeployTarget.USER])

        assert len(result) == 2
        call_kwargs = mock_deploy.call_args.kwargs
        assert "app" in call_kwargs["targets"]
        assert "user" in call_kwargs["targets"]

    @patch("finanzonline_databox.config_deploy.deploy_config")
    @patch("finanzonline_databox.config_deploy.get_default_config_path")
    def test_returns_empty_when_no_files_created(self, mock_get_path: MagicMock, mock_deploy: MagicMock) -> None:
        """Returns empty list when all files are skipped."""
        from lib_layered_config.examples.deploy import DeployAction, DeployResult

        mock_get_path.return_value = Path("/package/defaultconfig.toml")
        mock_deploy.return_value = [
            DeployResult(
                destination=Path("/home/user/.config/test/config.toml"),
                action=DeployAction.KEPT,
                dot_d_results=[],
            )
        ]

        result = deploy_configuration(targets=[DeployTarget.USER])

        assert len(result) == 0
