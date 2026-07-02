"""Tests for the ``mawaqit-py`` console script."""

from __future__ import annotations

import pytest

from mawaqit.cli import main


def test_login_uses_env_credentials_without_prompting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MAWAQIT_USERNAME", "envuser")
    monkeypatch.setenv("MAWAQIT_PASSWORD", "envpass")
    seen: dict[str, tuple[str, str]] = {}

    def fake_login(username: str, password: str) -> str:
        seen["creds"] = (username, password)
        return "envtoken"

    monkeypatch.setattr("mawaqit.cli.login", fake_login)
    main(["login"])

    out = capsys.readouterr()
    assert out.out == "envtoken\n"  # stdout is just the token
    assert seen["creds"] == ("envuser", "envpass")


def test_login_prompts_for_missing_credentials(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MAWAQIT_USERNAME", raising=False)
    monkeypatch.delenv("MAWAQIT_PASSWORD", raising=False)
    monkeypatch.setattr("builtins.input", lambda: "typeduser")
    monkeypatch.setattr("mawaqit.cli.getpass.getpass", lambda *a, **k: "typedpass")
    monkeypatch.setattr("mawaqit.cli.login", lambda u, p: f"tok:{u}:{p}")

    main(["login"])

    out = capsys.readouterr()
    assert out.out == "tok:typeduser:typedpass\n"
    assert "MAWAQIT username: " in out.err  # prompt went to stderr, not stdout
