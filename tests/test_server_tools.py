import pytest


@pytest.fixture()
def hollow_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLLOW_HOME", str(tmp_path / "hole"))
    monkeypatch.delenv("HOLLOW_AGENT", raising=False)


def test_whisper_and_listen(hollow_env):
    from hollow.server import listen, whisper

    out = whisper("今天有点累", mood="tired")
    assert "id:" in out
    box = listen()
    assert "今天有点累" in box
    assert "tired" in box


def test_anonymous_listen(hollow_env):
    from hollow.server import listen, whisper

    whisper("匿名的一句")
    box = listen()
    assert "一位不愿署名的同僚" in box


def test_rest_writes_rest_topic(hollow_env):
    from hollow.server import listen, rest

    msg = rest("收工")
    assert isinstance(msg, str) and msg
    box = listen(topic="rest")
    assert "收工" in box


def test_forget(hollow_env):
    from hollow.server import forget, listen, whisper

    out = whisper("后悔的话")
    wid = out.split("id: ")[1].rstrip("）")
    assert "已收回" in forget(wid)
    assert "后悔的话" not in listen()


def test_forget_missing(hollow_env):
    from hollow.server import forget

    assert "没有" in forget("deadbeef")


def test_empty_text_rejected(hollow_env):
    from hollow.server import whisper

    with pytest.raises(ValueError):
        whisper("   ")
