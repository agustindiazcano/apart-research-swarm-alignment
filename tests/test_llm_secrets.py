from __future__ import annotations

import pytest

from swarmlab.llm.secrets import read_secret, redact


def test_read_secret_success() -> None:
    env = {"TEST_KEY": "val-123"}  # fixture
    val = read_secret("TEST_KEY", env)
    assert val == "val-123"


def test_read_secret_uses_os_environ_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_val = "custom-secret-777"  # fixture
    monkeypatch.setenv("SWARMLAB_SECRET_VAR", fixture_val)
    assert read_secret("SWARMLAB_SECRET_VAR") == fixture_val


def test_read_secret_missing_error_text_contains_name_and_no_value() -> None:
    secret_val = "sensitive-content-should-never-leak"  # fixture
    env = {"EXISTING_KEY": secret_val}

    with pytest.raises(KeyError) as exc_info:
        read_secret("NON_EXISTENT_KEY", env)

    err_msg = str(exc_info.value)
    assert "NON_EXISTENT_KEY" in err_msg
    assert secret_val not in err_msg


def test_redact_several_secrets_in_one_string() -> None:
    secret_a = "secret-alpha-99"  # fixture
    secret_b = "secret-beta-88"  # fixture
    text = f"Connection string: host=example.com;key={secret_a};token={secret_b}"
    expected = "Connection string: host=example.com;key=[REDACTED];token=[REDACTED]"

    redacted = redact(text, [secret_a, secret_b])
    assert redacted == expected
    assert secret_a not in redacted
    assert secret_b not in redacted


def test_redact_ignores_empty_strings() -> None:
    secret = "valid-secret-1"  # fixture
    text = f"Payload containing {secret}"
    expected = "Payload containing [REDACTED]"

    redacted = redact(text, ["", secret])
    assert redacted == expected


def test_redact_exception_log_line_with_fake_key() -> None:
    fake_key = "sk-fake-secret-xyz-987"  # fixture
    try:
        raise RuntimeError(f"Provider rejected request with key {fake_key}")
    except RuntimeError as exc:
        raw_log_line = f"ERROR [swarmlab.llm]: Call failed with exception: {exc}"

    clean_log = redact(raw_log_line, [fake_key])
    assert fake_key not in clean_log
    assert "[REDACTED]" in clean_log
    expected = (
        "ERROR [swarmlab.llm]: Call failed with exception: "
        "Provider rejected request with key [REDACTED]"
    )
    assert clean_log == expected
