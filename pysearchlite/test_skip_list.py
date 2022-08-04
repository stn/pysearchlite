from array import array
from random import randrange

import pytest as pytest

from .skip_list import SkipList


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


def test_skip_list_fromlist():
    p = 2
    offset = 0
    sl = SkipList.from_list([1], p=p, offset=offset)
    assert sl.data == [array('i', [1])]
    sl = SkipList.from_list([1, 2], p=p, offset=offset)
    assert sl.data == [array('i', [1]), array('i', [2])]
    sl = SkipList.from_list([1, 2, 3], p=p, offset=offset)
    assert sl.data == [array('i', [1, 2]), array('i', [2]), array('i', [3, -1])]
    sl = SkipList.from_list([1, 2, 3, 4], p=p, offset=offset)
    assert sl.data == [array('i', [1, 2]), array('i', [2]), array('i', [3, -1]), array('i', [4])]
    sl = SkipList.from_list([1, 2, 3, 4, 5], p=p, offset=offset)
    assert sl.data == [array('i', [1, 2, 4]), array('i', [2]), array('i', [3, 4]), array('i', [4]), array('i', [5, -1, -1])]
    sl = SkipList.from_list([1, 2, 3, 4, 5], p=p, offset=1)
    assert sl.data == [array('i', [1, 2]), array('i', [2]), array('i', [3, 4]), array('i', [4]), array('i', [5, -1])]


@pytest.mark.parametrize('arr, target', skip_list_search_test_cases(100, 10))
def test_skip_list_search(arr, target):
    skip_list = SkipList.from_list(arr)
    ret, skip_list_pos = skip_list.search(target, 0)
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
def test_skip_list_intersection(a, b):
    s = SkipList.from_list(a)
    t = SkipList.from_list(b)
    result = s.intersection(t)
    assert set(result) == set(a) & set(b)


@pytest.mark.parametrize('a, b', skip_list_and_test_cases(100, 10))
def test_skip_list_intersection_with_doc_ids(a, b):
    t = SkipList.from_list(b)
    result = t.intersection_with_doc_ids(a)
    assert set(result) == set(a) & set(b)
