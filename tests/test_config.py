from app.config import FIGMA_ACCESS_TOKEN_KEY, _read_env_value


def test_read_env_value_reads_only_requested_key(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OTHER_VALUE=keep-private\nFIGMA_ACCESS_TOKEN=figd-example-token\n",
        encoding="utf-8",
    )

    assert _read_env_value(FIGMA_ACCESS_TOKEN_KEY, env_file) == "figd-example-token"


def test_read_env_value_returns_none_when_key_is_missing(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER_VALUE=keep-private\n", encoding="utf-8")

    assert _read_env_value(FIGMA_ACCESS_TOKEN_KEY, env_file) is None
