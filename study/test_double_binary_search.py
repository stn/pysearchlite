from random import randrange

import pytest as pytest

from .double_binary_search import *


def linear_search(arr, target, left, right):
    for i in range(left, right):
        if arr[i] >= target:
            return i
    return right


def binary_search_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        arr_len = randrange(1, max_len)
        arr = sorted(set(randrange(arr_len * 4) for _ in range(arr_len)))
        target = randrange(arr_len * 4)
        tests.append((arr, target))
    return tests


@pytest.mark.parametrize('arr, target', binary_search_test_cases(100, 10))
def test_binary_search(arr, target):
    assert binary_search(arr, target, 0, len(arr)) == linear_search(arr, target, 0, len(arr))


def double_binary_search_test_cases(num, max_len):
    tests = []
    for _ in range(num):
        a_len = randrange(1, max_len)
        a = sorted(list(set([randrange(a_len * 4) for _ in range(a_len)])))
        b_len = randrange(a_len, max_len)
        b = sorted(list(set([randrange(b_len * 4) for _ in range(b_len)])))
        tests.append((a, b))
    return tests


@pytest.mark.parametrize('a, b', double_binary_search_test_cases(100, 10))
def test_double_binary_search(a, b):
    result = []
    double_binary_search(a, 0, len(a), b, 0, len(b), result)
    assert result == sorted(list(set(a) & set(b)))
