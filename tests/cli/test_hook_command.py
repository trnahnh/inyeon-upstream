import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cli.main import app
from cli.commands.hook import HOOK_MARKER


@pytest.fixture
def runner():
    return CliRunner()


class TestHookInstall:

    @patch("cli.commands.hook.is_git_repo")
    def test_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False
        result = runner.invoke(app, ["hook", "install"])
        assert result.exit_code == 1
        assert "Not a git repository" in result.stdout

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_creates_hook_file(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        hook_file = tmp_path / "prepare-commit-msg"
        mock_path.return_value = str(hook_file)

        result = runner.invoke(app, ["hook", "install"])

        assert result.exit_code == 0
        assert "Installed" in result.stdout
        assert hook_file.exists()
        content = hook_file.read_text()
        assert HOOK_MARKER in content
        assert "inyeon commit --staged --hook-mode" in content

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_overwrites_own_hook(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        hook_file = tmp_path / "prepare-commit-msg"
        hook_file.write_text(f"#!/bin/sh\n{HOOK_MARKER}\nold content\n")
        mock_path.return_value = str(hook_file)

        result = runner.invoke(app, ["hook", "install"])

        assert result.exit_code == 0
        assert "Installed" in result.stdout

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_refuses_foreign_hook(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        hook_file = tmp_path / "prepare-commit-msg"
        hook_file.write_text("#!/bin/sh\nsome other hook\n")
        mock_path.return_value = str(hook_file)

        result = runner.invoke(app, ["hook", "install"])

        assert result.exit_code == 1
        assert "not from Inyeon" in result.stdout


class TestHookRemove:

    @patch("cli.commands.hook.is_git_repo")
    def test_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False
        result = runner.invoke(app, ["hook", "remove"])
        assert result.exit_code == 1

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_no_hook_installed(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        mock_path.return_value = str(tmp_path / "nonexistent")

        result = runner.invoke(app, ["hook", "remove"])

        assert result.exit_code == 0
        assert "No hook installed" in result.stdout

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_removes_inyeon_hook(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        hook_file = tmp_path / "prepare-commit-msg"
        hook_file.write_text(f"#!/bin/sh\n{HOOK_MARKER}\n")
        mock_path.return_value = str(hook_file)

        result = runner.invoke(app, ["hook", "remove"])

        assert result.exit_code == 0
        assert "Removed" in result.stdout
        assert not hook_file.exists()

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_refuses_foreign_hook(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        hook_file = tmp_path / "prepare-commit-msg"
        hook_file.write_text("#!/bin/sh\nforeign hook\n")
        mock_path.return_value = str(hook_file)

        result = runner.invoke(app, ["hook", "remove"])

        assert result.exit_code == 1
        assert "not from Inyeon" in result.stdout


class TestHookStatus:

    @patch("cli.commands.hook.is_git_repo")
    def test_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False
        result = runner.invoke(app, ["hook", "status"])
        assert result.exit_code == 1

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_no_hook(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        mock_path.return_value = str(tmp_path / "nonexistent")

        result = runner.invoke(app, ["hook", "status"])

        assert result.exit_code == 0
        assert "No hook installed" in result.stdout

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_inyeon_hook_installed(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        hook_file = tmp_path / "prepare-commit-msg"
        hook_file.write_text(f"#!/bin/sh\n{HOOK_MARKER}\n")
        mock_path.return_value = str(hook_file)

        result = runner.invoke(app, ["hook", "status"])

        assert result.exit_code == 0
        assert "Inyeon hook is installed" in result.stdout

    @patch("cli.commands.hook._hook_path")
    @patch("cli.commands.hook.is_git_repo")
    def test_foreign_hook(self, mock_is_git, mock_path, runner, tmp_path):
        mock_is_git.return_value = True
        hook_file = tmp_path / "prepare-commit-msg"
        hook_file.write_text("#!/bin/sh\nforeign\n")
        mock_path.return_value = str(hook_file)

        result = runner.invoke(app, ["hook", "status"])

        assert result.exit_code == 0
        assert "not from Inyeon" in result.stdout
