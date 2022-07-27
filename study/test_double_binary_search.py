from random import randrange

import pytest as pytest

from .double_binary_search import *


def linear_search(arr, target, left, right):
    ans = left - 1
    for i in range(left, right):
        if arr[i] > target:
            return ans
        ans = i
    return ans


def binary_search_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        arr_len = randrange(1, max_len)
        arr = sorted([randrange(arr_len * 4) for _ in range(arr_len)])
        left = randrange(arr_len)
        right = randrange(arr_len)
        target = randrange(arr_len * 4)
        tests.append((arr, target, left, right))
    return tests


@pytest.mark.parametrize('arr, target, left, right', binary_search_test_cases(100, 100))
def test_binary_search(arr, target, left, right):
    assert binary_search_rightmost(arr, target, left, right) == linear_search(arr, target, left, right)


def double_binary_search_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        a_len = randrange(1, max_len)
        a = sorted(list(set([randrange(a_len * 4) for _ in range(a_len)])))
        b_len = randrange(a_len, max_len)
        b = sorted(list(set([randrange(b_len * 4) for _ in range(b_len)])))
        tests.append((a, b))
    return tests


@pytest.mark.parametrize('a, b', double_binary_search_test_cases(100, 20))
def test_double_binary_search(a, b):
    result = []
    intersect_by_double_binary_search(a, 0, len(a), b, 0, len(b), result)
    assert result == sorted(list(set(a) & set(b)))
