from hollow.store import Hollow


def test_append_read_roundtrip(tmp_path):
    h = Hollow(tmp_path)
    w = h.append("测试一句", agent="bot-a", mood="calm", topic="test")
    rows = h.all()
    assert len(rows) == 1
    assert rows[0].text == "测试一句"
    assert rows[0].agent == "bot-a"
    assert w.id and w.ts


def test_anonymous(tmp_path):
    h = Hollow(tmp_path)
    h.append("不署名")
    assert h.all()[0].who() == "一位不愿署名的同僚"


def test_recent_filters_and_order(tmp_path):
    h = Hollow(tmp_path)
    h.append("一", topic="a")
    h.append("二", topic="b")
    h.append("三", topic="a")
    got = [r.text for r in h.recent(10, topic="a")]
    assert got == ["三", "一"]


def test_remove(tmp_path):
    h = Hollow(tmp_path)
    w = h.append("会被收回的")
    assert h.remove(w.id) is True
    assert h.count() == 0
    assert h.remove(w.id) is False


def test_reply_roundtrip_and_get(tmp_path):
    h = Hollow(tmp_path)
    w1 = h.append("原话", agent="a")
    w2 = h.append("接话", agent="b", reply_to=w1.id)
    assert h.get(w1.id).text == "原话"
    assert h.get(w2.id).reply_to == w1.id
    assert h.get("nonexist") is None
    # 旧格式条目（无 reply_to 键）解析为 None
    h2 = Hollow(tmp_path / "legacy")
    (tmp_path / "legacy" / "whispers.jsonl").write_text(
        '{"id":"old1","ts":"2026-01-01T00:00:00+08:00","text":"旧格式"}\n', encoding="utf-8"
    )
    assert h2.get("old1").reply_to is None


def test_private_hole_permissions(tmp_path):
    import stat

    home = tmp_path / "perm"
    h = Hollow(home)
    h.append("权限测试")
    mode_dir = stat.S_IMODE(home.stat().st_mode)
    mode_file = stat.S_IMODE((home / "whispers.jsonl").stat().st_mode)
    assert mode_dir == 0o700, f"dir mode {oct(mode_dir)}"
    assert mode_file == 0o600, f"file mode {oct(mode_file)}"


def test_multi_session_shared_hole(tmp_path):
    a, b = Hollow(tmp_path), Hollow(tmp_path)
    a.append("from a")
    b.append("from b")
    assert [r.text for r in Hollow(tmp_path).recent(10)] == ["from b", "from a"]
