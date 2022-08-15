import mmap
from random import randrange
from tempfile import TemporaryFile

import pytest as pytest

from .block_skip_list import BlockSkipList, SingleDocId, DocIdList, BlockSkipListExt
from .codecs import encode_docid, decode_docid

B_0 = b'\x00\x00\x00\x00'
B_1 = b'\x00\x00\x00\x01'
B_2 = b'\x00\x00\x00\x02'
B_3 = b'\x00\x00\x00\x03'
B_4 = b'\x00\x00\x00\x04'
B_5 = b'\x00\x00\x00\x05'

L_0 = b'\x00\x00\x00\x00'
L_1 = b'\x01\x00\x00\x00'
L_2 = b'\x02\x00\x00\x00'
L_3 = b'\x03\x00\x00\x00'
L_4 = b'\x04\x00\x00\x00'
L_5 = b'\x05\x00\x00\x00'


def linear_search(arr, target, left=0, right=None):
    if right is None:
        right = len(arr)
    for i in range(left, right):
        if arr[i] >= target:
            return i
    return right


def search_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        arr_len = randrange(1, max_len)
        arr = sorted(set(randrange(1, arr_len * 4) for _ in range(arr_len)))
        target = randrange(1, arr_len * 4 + 1)
        tests.append((arr, target))
    return tests


def test_block_skip_list_fromlist():
    p = 2
    max_level = 2
    sl = BlockSkipList.from_list([1], p=p, max_level=max_level)
    assert type(sl) == SingleDocId
    assert sl.doc_id == B_1
    sl = BlockSkipList.from_list([1, 2], p=p, max_level=max_level)
    assert type(sl) == DocIdList
    assert sl.ids == [B_1, B_2]
    sl = BlockSkipList.from_list([1, 2, 3], p=p, max_level=max_level)
    assert sl.max_level == 1
    assert sl.blocks == [[B_1, B_2], [B_1, L_0, B_3, L_2], [B_3]]
    assert sl.next_block_idx == [2, 0, 0]
    sl = BlockSkipList.from_list([1, 2, 3, 4], p=p, max_level=max_level)
    assert sl.max_level == 1
    assert sl.blocks == [[B_1, B_2], [B_1, L_0, B_3, L_2], [B_3, B_4]]
    assert sl.next_block_idx == [2, 0, 0]
    sl = BlockSkipList.from_list([1, 2, 3, 4, 5], p=p, max_level=max_level)
    assert sl.max_level == 2
    assert sl.blocks == [[B_1, B_2], [B_1, L_0, B_3, L_3], [B_1, L_1, B_5, L_5],
                         [B_3, B_4], [B_5], [B_5, L_4]]
    assert sl.next_block_idx == [3, 5, 0, 4, 0, 0]
    sl = BlockSkipList.from_list([1, 2, 3, 4, 5], p=p, max_level=1)
    assert sl.max_level == 1
    assert sl.blocks == [[B_1, B_2], [B_1, L_0, B_3, L_2],
                         [B_3, B_4], [B_5],
                         [B_5, L_3]]
    assert sl.next_block_idx == [2, 4, 3, 0, 0]


@pytest.mark.parametrize('arr, target', search_test_cases(100, 30))
def test_block_skip_list_search(arr, target):
    skip_list = BlockSkipList.from_list(arr, p=2)
    skip_list.reset()
    ret = skip_list.search(encode_docid(target))
    i = linear_search(arr, target)
    if i == len(arr):
        assert decode_docid(ret) == arr[-1]
    else:
        assert decode_docid(ret) == arr[i]


@pytest.mark.parametrize('arr, target', search_test_cases(100, 30))
def test_block_skip_list_ext_search(arr, target):
    skip_list = BlockSkipList.from_list(arr, p=2)
    with TemporaryFile(prefix="pysearchlite_") as file:
        skip_list.write(file)
        file.seek(0)
        mem = mmap.mmap(file.fileno(), length=0, access=mmap.ACCESS_READ)
        skip_list_ext = BlockSkipListExt.read(mem)
        skip_list_ext.reset()
        ret = skip_list_ext.search(encode_docid(target))
        i = linear_search(arr, target)
        if i == len(arr):
            assert decode_docid(ret) == arr[-1]
        else:
            assert decode_docid(ret) == arr[i]


def skip_list_and_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        a_len = randrange(1, max_len)
        b_len = randrange(1, max_len)
        if a_len > b_len:
            a_len, b_len = b_len, a_len
        a = sorted(set(randrange(1, a_len * 4 + 1) for _ in range(a_len)))
        b = sorted(set(randrange(1, b_len * 4 + 1) for _ in range(b_len)))
        tests.append((a, b))
    return tests


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 30))
def test_skip_list_intersection(a, b):
    s = BlockSkipList.from_list(a, p=2)
    t = BlockSkipList.from_list(b, p=2)
    result = s.intersection(t)
    assert set([decode_docid(x) for x in result]) == set(a) & set(b)


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 30))
def test_skip_list_ext_intersection(a, b):
    s = BlockSkipList.from_list(a, p=2)
    t = BlockSkipList.from_list(b, p=2)
    with TemporaryFile(prefix="pysearchlite_") as file_s:
        with TemporaryFile(prefix="pysearchlite_") as file_t:
            s.write(file_s)
            file_s.seek(0)
            mem_s = mmap.mmap(file_s.fileno(), length=0, access=mmap.ACCESS_READ)
            s_ext = BlockSkipListExt.read(mem_s)
            t.write(file_t)
            file_t.seek(0)
            mem_t = mmap.mmap(file_t.fileno(), length=0, access=mmap.ACCESS_READ)
            t_ext = BlockSkipListExt.read(mem_t)
            result = s_ext.intersection(t_ext)
            assert set([decode_docid(x) for x in result]) == set(a) & set(b)


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 30))
def test_skip_list_intersection_with_doc_ids(a, b):
    t = BlockSkipList.from_list(b, p=2)
    result = t.intersection_with_doc_ids([encode_docid(doc_id) for doc_id in a])
    assert set([decode_docid(x) for x in result]) == set(a) & set(b)


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 30))
def test_skip_list_ext_intersection_with_doc_ids(a, b):
    a_bin = [encode_docid(x) for x in a]
    t = BlockSkipList.from_list(b, p=2)
    with TemporaryFile(prefix="pysearchlite_") as file_t:
        t.write(file_t)
        file_t.seek(0)
        mem_t = mmap.mmap(file_t.fileno(), length=0, access=mmap.ACCESS_READ)
        t_ext = BlockSkipListExt.read(mem_t)
        result = t_ext.intersection_with_doc_ids(a_bin)
    assert set([decode_docid(x) for x in result]) == set(a) & set(b)
