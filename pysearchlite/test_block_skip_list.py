from array import array
from random import randrange

import pytest as pytest

from .block_skip_list import BlockSkipList, SingleDocId, DocIdList


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
        arr = sorted(set(randrange(arr_len * 4) for _ in range(arr_len)))
        target = randrange(arr_len * 4)
        tests.append((arr, target))
    return tests


def test_block_skip_list_fromlist():
    p = 2
    max_level = 2
    sl = BlockSkipList.from_list([1], p=p, max_level=max_level)
    assert type(sl) == SingleDocId
    assert sl.doc_id == 1
    sl = BlockSkipList.from_list([1, 2], p=p, max_level=max_level)
    assert type(sl) == DocIdList
    assert sl.ids == array('i', [1, 2])
    sl = BlockSkipList.from_list([1, 2, 3], p=p, max_level=max_level)
    assert sl.max_level == 1
    assert sl.blocks == [array('i', [1, 2, 2]), array('i', [1, 0, 3, 2]), array('i', [3])]
    sl = BlockSkipList.from_list([1, 2, 3, 4], p=p, max_level=max_level)
    assert sl.max_level == 1
    assert sl.blocks == [array('i', [1, 2, 2]), array('i', [1, 0, 3, 2]), array('i', [3, 4])]
    sl = BlockSkipList.from_list([1, 2, 3, 4, 5], p=p, max_level=max_level)
    assert sl.max_level == 2
    assert sl.blocks == [array('i', [1, 2, 3]), array('i', [1, 0, 3, 3, 5]), array('i', [1, 1, 5, 5]),
                         array('i', [3, 4, 4]), array('i', [5]), array('i', [5, 4])]
    sl = BlockSkipList.from_list([1, 2, 3, 4, 5], p=p, max_level=1)
    assert sl.max_level == 1
    assert sl.blocks == [array('i', [1, 2, 2]), array('i', [1, 0, 3, 2, 4]),
                         array('i', [3, 4, 3]), array('i', [5]),
                         array('i', [5, 3])]


@pytest.mark.parametrize('arr, target', search_test_cases(100, 30))
def test_block_skip_list_search(arr, target):
    skip_list = BlockSkipList.from_list(arr, p=2)
    skip_list.reset()
    ret = skip_list.search(target)
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


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 30))
def test_skip_list_intersection(a, b):
    s = BlockSkipList.from_list(a, p=2)
    t = BlockSkipList.from_list(b, p=2)
    result = s.intersection(t)
    assert set(result) == set(a) & set(b)


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 30))
def test_skip_list_intersection_with_doc_ids(a, b):
    t = BlockSkipList.from_list(b, p=2)
    result = t.intersection_with_doc_ids(a)
    assert set(result) == set(a) & set(b)
