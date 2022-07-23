from .search_engine import *


def test_search(tmpdir):
    init(tmpdir)
    index("id1", "hello world")
    index("id2", "this is a test")
    index("id3", "this is another test")
    save_index()
    clear_index()
    restore_index()
    assert search("hello") == ["id1"]
    assert search("this test") == ["id2", "id3"]
    assert search("that") == []
