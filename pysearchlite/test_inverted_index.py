import io
import os.path
import tempfile

import pytest

from .inverted_index import (
    SinglePassInMemoryInvertedIndex,
)


@pytest.fixture
def idx_dir() -> str:
    tmp_dir = tempfile.TemporaryDirectory(prefix="pysearchlite_idx_dir_")
    yield tmp_dir.name

    tmp_dir.cleanup()


# Tests for SinglePassInMemoryInvertedIndex
# assume sys.byteorder == 'little'

@pytest.fixture
def spim_index(idx_dir) -> SinglePassInMemoryInvertedIndex:
    yield SinglePassInMemoryInvertedIndex(idx_dir)


def test_spim_add(spim_index):
    spim_index.add(0, {'a', 'b', 'c'})
    spim_index.add(1, {'a', 'c', 'd'})
    assert spim_index.raw_data == {'a': [0, 1], 'b': [0], 'c': [0, 1], 'd': [1]}


def test_spim_tmp_index_name(spim_index):
    assert spim_index.tmp_index_name(2).endswith('2')


def test_spim_write_token(spim_index):
    f = io.BytesIO()
    spim_index.write_token(f, 'hello')
    assert f.getvalue() == b'\x05\x00hello'


def test_spim_read_token(spim_index):
    f = io.BytesIO(b'\x05\x00world')
    token = spim_index.read_token(f)
    assert token == 'world'


def test_write_doc_ids(spim_index):
    f = io.BytesIO()
    spim_index.write_doc_ids(f, [1, 2, 5])
    assert f.getvalue() == b'\x03\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x05\x00\x00\x00'


def test_save_raw_data(spim_index):
    spim_index.add(0, {'c', 'b'})
    spim_index.add(1, {'a', 'c'})
    spim_index.save_raw_data()
    with open(spim_index.tmp_index_name(0), 'rb') as f:
        tmp_index = f.read()
        assert tmp_index == b'\x01\x00a\x01\x00\x00\x00\x01\x00\x00\x00' \
                            b'\x01\x00b\x01\x00\x00\x00\x00\x00\x00\x00' \
                            b'\x01\x00c\x02\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00'
    assert spim_index.raw_data == {}
    assert spim_index.raw_data_size == 0
    assert spim_index.tmp_index_num == 1


def test_spim_save(spim_index):
    spim_index.add(0, {'c', 'b'})
    spim_index.add(1, {'a', 'c'})
    spim_index.save()
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'rb') as f:
        tmp_index = f.read()
        assert tmp_index == b'\x01\x00a\x01\x00\x00\x00\x01\x00\x00\x00' \
                            b'\x01\x00b\x01\x00\x00\x00\x00\x00\x00\x00' \
                            b'\x01\x00c\x02\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00'


def test_spim_restore(spim_index):
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(b'\x01\x00a\x01\x00\x00\x00\x01\x00\x00\x00'
                b'\x01\x00b\x01\x00\x00\x00\x00\x00\x00\x00'
                b'\x01\x00c\x02\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00')
    spim_index.restore()
    assert spim_index.data == {'a': 2+1, 'b': (2+1+4+4)+2+1, 'c': (2+1+4+4)*2+2+1}


def test_spim_get(spim_index):
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(b'\x01\x00a\x01\x00\x00\x00\x01\x00\x00\x00'
                b'\x01\x00b\x01\x00\x00\x00\x00\x00\x00\x00'
                b'\x01\x00c\x02\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00')
    spim_index.restore()
    assert spim_index.get('a') == {1}
    assert spim_index.get('b') == {0}
    assert spim_index.get('c') == {0, 1}
    assert len(spim_index.get('d')) == 0


def test_spim_clear(spim_index):
    assert spim_index.raw_data == {}
    assert spim_index.data == {}
