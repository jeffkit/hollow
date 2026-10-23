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


def test_multi_session_shared_hole(tmp_path):
    a, b = Hollow(tmp_path), Hollow(tmp_path)
    a.append("from a")
    b.append("from b")
    assert [r.text for r in Hollow(tmp_path).recent(10)] == ["from b", "from a"]
