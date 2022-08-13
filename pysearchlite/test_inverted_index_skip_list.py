import io
import os.path
import tempfile

import pytest

from .inverted_index_skip_list import (
    InvertedIndexBlockSkipList,
    read_token,
    write_token,
    write_doc_ids,
)


# Big endian
B_INT16_1 = b'\x00\x01'
B_INT16_5 = b'\x00\x05'

B_INT32_0_B = b'\x00\x00\x00\x00'
B_INT32_1_B = b'\x00\x00\x00\x01'
B_INT32_2_B = b'\x00\x00\x00\x02'
B_INT32_3_B = b'\x00\x00\x00\x03'
B_INT32_4_B = b'\x00\x00\x00\x04'
B_INT32_5_B = b'\x00\x00\x00\x05'

B_INT32_0_L = b'\x00\x00\x00\x00'
B_INT32_1_L = b'\x01\x00\x00\x00'
B_INT32_2_L = b'\x02\x00\x00\x00'
B_INT32_3_L = b'\x03\x00\x00\x00'
B_INT32_4_L = b'\x04\x00\x00\x00'
B_INT32_5_L = b'\x05\x00\x00\x00'


@pytest.fixture
def idx_dir() -> str:
    tmp_dir = tempfile.TemporaryDirectory(prefix="pysearchlite_idx_dir_")
    yield tmp_dir.name

    tmp_dir.cleanup()


@pytest.fixture
def inverted_index(idx_dir) -> InvertedIndexBlockSkipList:
    yield InvertedIndexBlockSkipList(idx_dir)


def test_inverted_add(inverted_index):
    inverted_index.add(1, ['a', 'b', 'c'])
    inverted_index.add(2, ['a', 'c', 'd'])
    assert inverted_index.raw_data == {'a': [1, 2], 'b': [1], 'c': [1, 2], 'd': [2]}


def test_inverted_tmp_index_name(inverted_index):
    assert inverted_index.tmp_index_name(2).endswith('2')


def test_inverted_write_token(inverted_index):
    f = io.BytesIO()
    write_token(f, 'hello')
    assert f.getvalue() == B_INT16_5 + b'hello'


def test_inverted_read_token(inverted_index):
    f = io.BytesIO(B_INT16_5 + b'world')
    token = read_token(f)
    assert token == 'world'


def test_write_doc_ids(inverted_index):
    f = io.BytesIO()
    write_doc_ids(f, [1, 2, 5])
    assert f.getvalue() == B_INT32_3_B + B_INT32_1_B + B_INT32_2_B + B_INT32_5_B


def test_save_raw_data(inverted_index):
    inverted_index.add(1, ['c', 'b'])
    inverted_index.add(2, ['a', 'c'])
    inverted_index.save_raw_data()
    with open(inverted_index.tmp_index_name(0), 'rb') as f:
        tmp_index = f.read()
        assert tmp_index == (B_INT16_1 + b'a' + B_INT32_1_B + B_INT32_2_B +
                             B_INT16_1 + b'b' + B_INT32_1_B + B_INT32_1_B +
                             B_INT16_1 + b'c' + B_INT32_2_B + B_INT32_1_B + B_INT32_2_B)
    assert inverted_index.raw_data == {}
    assert inverted_index.raw_data_size == 0
    assert inverted_index.tmp_index_num == 1


def test_inverted_save(inverted_index):
    inverted_index.add(1, ['c', 'b'])
    inverted_index.add(2, ['a', 'c'])
    inverted_index.save()
    with open(os.path.join(inverted_index.idx_dir, 'inverted_index'), 'rb') as f:
        tmp_index = f.read()
        assert tmp_index == (B_INT16_1 + b'a' + b'\x01' + B_INT32_2_B +
                             B_INT16_1 + b'b' + b'\x01' + B_INT32_1_B +
                             B_INT16_1 + b'c' + b'\x02' + B_INT32_2_L + B_INT32_1_B + B_INT32_2_B)


def test_inverted_restore(inverted_index):
    with open(os.path.join(inverted_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + b'\x01' + B_INT32_2_B +
                B_INT16_1 + b'b' + b'\x01' + B_INT32_1_B +
                B_INT16_1 + b'c' + b'\x02' + B_INT32_2_L + B_INT32_1_B + B_INT32_2_B)
    inverted_index.restore()
    #assert inverted_index.data == {'a': [1], 'b': [0], 'c': [0, 1]}


def test_inverted_get(inverted_index):
    with open(os.path.join(inverted_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + b'\x01' + B_INT32_2_B +
                B_INT16_1 + b'b' + b'\x01' + B_INT32_1_B +
                B_INT16_1 + b'c' + b'\x02' + B_INT32_2_L + B_INT32_1_B + B_INT32_2_B)
    inverted_index.restore()
    assert inverted_index.get('a') == [B_INT32_2_B]
    assert inverted_index.get('b') == [B_INT32_1_B]
    assert inverted_index.get('c') == [B_INT32_1_B, B_INT32_2_B]
    assert inverted_index.get('d') == []


def test_inverted_search_and(inverted_index):
    with open(os.path.join(inverted_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + b'\x01' + B_INT32_2_B +
                B_INT16_1 + b'b' + b'\x01' + B_INT32_1_B +
                B_INT16_1 + b'c' + b'\x02' + B_INT32_2_L + B_INT32_1_B + B_INT32_2_B)
    inverted_index.restore()
    assert inverted_index.search_and(['a', 'b']) == []
    assert inverted_index.search_and(['a', 'c']) == [B_INT32_2_B]
    assert inverted_index.search_and(['a', 'd']) == []
    assert inverted_index.search_and(['b', 'c']) == [B_INT32_1_B]
    assert inverted_index.search_and(['b', 'd']) == []
    assert inverted_index.search_and(['a', 'b', 'c']) == []


def test_inverted_count_and(inverted_index):
    with open(os.path.join(inverted_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + b'\x01' + B_INT32_2_B +
                B_INT16_1 + b'b' + b'\x01' + B_INT32_1_B +
                B_INT16_1 + b'c' + b'\x02' + B_INT32_2_L + B_INT32_1_B + B_INT32_2_B)
    inverted_index.restore()
    assert inverted_index.count_and(['a', 'b']) == 0
    assert inverted_index.count_and(['a', 'c']) == 1
    assert inverted_index.count_and(['a', 'd']) == 0
    assert inverted_index.count_and(['b', 'c']) == 1
    assert inverted_index.count_and(['b', 'd']) == 0
    assert inverted_index.count_and(['a', 'b', 'c']) == 0


def test_inverted_clear(inverted_index):
    assert inverted_index.raw_data == {}
    assert inverted_index.data == {}
