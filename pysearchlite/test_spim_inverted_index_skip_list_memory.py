import io
import os.path
import tempfile
from random import randrange

import pytest

from .spim_inveted_index_skip_list_memory import (
    SinglePassInMemoryInvertedIndexSkipListMemory,
    read_token,
    write_token,
    write_doc_ids,
    make_skip_list,
    skip_list_search,
    skip_list_and,
)


# Big endian
B_INT16_1 = b'\x00\x01'
B_INT16_5 = b'\x00\x05'

B_INT32_0 = b'\x00\x00\x00\x00'
B_INT32_1 = b'\x00\x00\x00\x01'
B_INT32_2 = b'\x00\x00\x00\x02'
B_INT32_3 = b'\x00\x00\x00\x03'
B_INT32_4 = b'\x00\x00\x00\x04'
B_INT32_5 = b'\x00\x00\x00\x05'


@pytest.fixture
def idx_dir() -> str:
    tmp_dir = tempfile.TemporaryDirectory(prefix="pysearchlite_idx_dir_")
    yield tmp_dir.name

    tmp_dir.cleanup()


# Tests for SinglePassInMemoryInvertedIndex
# assume sys.byteorder == 'little'

@pytest.fixture
def spim_index(idx_dir) -> SinglePassInMemoryInvertedIndexSkipListMemory:
    yield SinglePassInMemoryInvertedIndexSkipListMemory(idx_dir)


def test_spim_add(spim_index):
    spim_index.add(0, ['a', 'b', 'c'])
    spim_index.add(1, ['a', 'c', 'd'])
    assert spim_index.raw_data == {'a': [0, 1], 'b': [0], 'c': [0, 1], 'd': [1]}


def test_spim_tmp_index_name(spim_index):
    assert spim_index.tmp_index_name(2).endswith('2')


def test_spim_write_token(spim_index):
    f = io.BytesIO()
    write_token(f, 'hello')
    assert f.getvalue() == B_INT16_5 + b'hello'


def test_spim_read_token(spim_index):
    f = io.BytesIO(B_INT16_5 + b'world')
    token = read_token(f)
    assert token == 'world'


def test_write_doc_ids(spim_index):
    f = io.BytesIO()
    write_doc_ids(f, [1, 2, 5])
    assert f.getvalue() == B_INT32_3 + B_INT32_1 + B_INT32_2 + B_INT32_5


def test_save_raw_data(spim_index):
    spim_index.add(0, ['c', 'b'])
    spim_index.add(1, ['a', 'c'])
    spim_index.save_raw_data()
    with open(spim_index.tmp_index_name(0), 'rb') as f:
        tmp_index = f.read()
        assert tmp_index == (B_INT16_1 + b'a' + B_INT32_1 + B_INT32_1 +
                             B_INT16_1 + b'b' + B_INT32_1 + B_INT32_0 +
                             B_INT16_1 + b'c' + B_INT32_2 + B_INT32_0 + B_INT32_1)
    assert spim_index.raw_data == {}
    assert spim_index.raw_data_size == 0
    assert spim_index.tmp_index_num == 1


def test_spim_save(spim_index):
    spim_index.add(0, ['c', 'b'])
    spim_index.add(1, ['a', 'c'])
    spim_index.save()
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'rb') as f:
        tmp_index = f.read()
        assert tmp_index == (B_INT16_1 + b'a' + B_INT32_1 + B_INT32_1 +
                             B_INT16_1 + b'b' + B_INT32_1 + B_INT32_0 +
                             B_INT16_1 + b'c' + B_INT32_2 + B_INT32_0 + B_INT32_1)


def test_spim_restore(spim_index):
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + B_INT32_1 + B_INT32_1 +
                B_INT16_1 + b'b' + B_INT32_1 + B_INT32_0 +
                B_INT16_1 + b'c' + B_INT32_2 + B_INT32_0 + B_INT32_1)
    spim_index.restore()
    #assert spim_index.data == {'a': [1], 'b': [0], 'c': [0, 1]}


def test_spim_get(spim_index):
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + B_INT32_1 + B_INT32_1 +
                B_INT16_1 + b'b' + B_INT32_1 + B_INT32_0 +
                B_INT16_1 + b'c' + B_INT32_2 + B_INT32_0 + B_INT32_1)
    spim_index.restore()
    assert spim_index.get('a') == [1]
    assert spim_index.get('b') == [0]
    assert spim_index.get('c') == [0, 1]
    assert spim_index.get('d') == []


def test_spim_search_and(spim_index):
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + B_INT32_1 + B_INT32_1 +
                B_INT16_1 + b'b' + B_INT32_1 + B_INT32_0 +
                B_INT16_1 + b'c' + B_INT32_2 + B_INT32_0 + B_INT32_1)
    spim_index.restore()
    assert spim_index.search_and(['a', 'b']) == []
    assert spim_index.search_and(['a', 'c']) == [1]
    assert spim_index.search_and(['a', 'd']) == []
    assert spim_index.search_and(['b', 'c']) == [0]
    assert spim_index.search_and(['b', 'd']) == []
    assert spim_index.search_and(['a', 'b', 'c']) == []


def test_spim_count_and(spim_index):
    with open(os.path.join(spim_index.idx_dir, 'inverted_index'), 'wb') as f:
        f.write(B_INT16_1 + b'a' + B_INT32_1 + B_INT32_1 +
                B_INT16_1 + b'b' + B_INT32_1 + B_INT32_0 +
                B_INT16_1 + b'c' + B_INT32_2 + B_INT32_0 + B_INT32_1)
    spim_index.restore()
    assert spim_index.count_and(['a', 'b']) == 0
    assert spim_index.count_and(['a', 'c']) == 1
    assert spim_index.count_and(['a', 'd']) == 0
    assert spim_index.count_and(['b', 'c']) == 1
    assert spim_index.count_and(['b', 'd']) == 0
    assert spim_index.count_and(['a', 'b', 'c']) == 0


def test_spim_clear(spim_index):
    assert spim_index.raw_data == {}
    assert spim_index.data == {}


def linear_search(arr, target, left=0, right=None):
    if right is None:
        right = len(arr)
    for i in range(left, right):
        if arr[i] >= target:
            return i
    return right


def skip_list_search_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        arr_len = randrange(1, max_len)
        arr = sorted(set(randrange(arr_len * 4) for _ in range(arr_len)))
        target = randrange(arr_len * 4)
        tests.append((arr, target))
    return tests


@pytest.mark.parametrize('arr, target', skip_list_search_test_cases(100, 10))
def test_skip_list_search(arr, target):
    s = make_skip_list(arr)
    ret, skip_list_pos = skip_list_search(s,target, 0)
    i = linear_search(arr, target)
    if i == len(arr):
        assert ret == arr[-1]
    else:
        assert ret == arr[i]


def skip_list_and_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        a_len = randrange(1, max_len)
        b_len = randrange(1, max_len)
        if a_len > b_len:
            a_len, b_len = b_len, a_len
        a = sorted(set(randrange(a_len * 4) for _ in range(a_len)))
        b = sorted(set(randrange(b_len * 4) for _ in range(b_len)))
        tests.append((a, b))
    return tests


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 10))
def test_skip_list_and(a, b):
    s = make_skip_list(a)
    t = make_skip_list(b)
    result = skip_list_and(s, t)
    assert set(result) == set(a) & set(b)
