from . import search_engine as se


def test_search(tmpdir):
    se.init(tmpdir)
    se.index("id1", "hello world")
    se.index("id2", "this is a test")
    se.index("id3", "this is another test")
    se.save_index()
    se.clear_index()
    se.restore_index()
    assert se.search("hello") == ["id1"]
    assert se.search("this test") == ["id2", "id3"]
    assert se.search("that") == []


def test_count(tmpdir):
    se.init(tmpdir)
    se.index("id1", "hello world")
    se.index("id2", "this is a test")
    se.index("id3", "this is another test")
    se.save_index()
    se.clear_index()
    se.restore_index()
    assert se.count("hello") == 1
    assert se.count("this test") == 2
    assert se.count("that") == 0
