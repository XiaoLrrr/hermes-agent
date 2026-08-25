from unittest.mock import patch

from hermes_cli.oneshot import run_oneshot


def test_oneshot_forwards_reasoning_override():
    captured = {}

    def fake_run_agent(*args, **kwargs):
        captured.update(kwargs)
        return "ok", {"final_response": "ok"}

    with patch("hermes_cli.oneshot._run_agent", fake_run_agent):
        assert run_oneshot("hello", reasoning="low") == 0

    assert captured["reasoning"] == "low"
