import model_tools  # noqa: F401 - triggers provider plugin discovery

from agent.chat_completion_helpers import _get_request_provider_profile


def test_named_custom_provider_uses_custom_request_profile(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text(
        "providers:\n"
        "  command:\n"
        "    api: http://127.0.0.1:20128/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    profile = _get_request_provider_profile("command")

    assert profile is not None
    assert profile.name == "custom"
