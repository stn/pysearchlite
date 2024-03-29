import mmap
from random import randrange
from tempfile import TemporaryFile

import pytest as pytest

from .block_skip_list import BlockSkipList, SingleDocId, DocIdList, BlockSkipListExt
from .gamma_codecs import encode_docid, decode_docid, DOCID_BYTES

B_0 = b'\x00\x00\x00\x00'
B_1 = b'\x00\x00\x00\x01'
B_2 = b'\x00\x00\x00\x02'
B_3 = b'\x00\x00\x00\x03'
B_4 = b'\x00\x00\x00\x04'
B_5 = b'\x00\x00\x00\x05'
B_6 = b'\x00\x00\x00\x06'
B_7 = b'\x00\x00\x00\x07'
B_8 = b'\x00\x00\x00\x08'
B_9 = b'\x00\x00\x00\x09'

L_0 = b'\x00\x00\x00\x00'
L_1 = b'\x01\x00\x00\x00'
L_2 = b'\x02\x00\x00\x00'
L_3 = b'\x03\x00\x00\x00'
L_4 = b'\x04\x00\x00\x00'
L_5 = b'\x05\x00\x00\x00'

V_0 = b'\x00'
V_1 = b'\x01'
V_2 = b'\x02'
V_3 = b'\x03'
V_4 = b'\x04'
V_5 = b'\x05'
V_6 = b'\x06'
V_7 = b'\x07'
V_8 = b'\x08'
V_9 = b'\x09'


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
    block_size = 10
    max_level = 2
    sl = BlockSkipList.from_list([1], block_size=block_size, max_level=max_level)
    assert type(sl) == SingleDocId
    assert sl.doc_id == V_1
    sl = BlockSkipList.from_list([1, 2], block_size=block_size, max_level=max_level)
    assert type(sl) == DocIdList
    assert sl.ids == [V_1, V_2]
    sl = BlockSkipList.from_list([1, 2, 3], block_size=block_size, max_level=max_level)
    assert type(sl) == DocIdList
    assert sl.ids == [V_1, V_2, V_3]
    sl = BlockSkipList.from_list([1, 2, 3, 4, 5, 6, 7, 8, 9], block_size=9, max_level=max_level)
    assert sl.block_size == 9
    assert sl.max_level == 2
    assert sl.blocks == [bytearray(b'\x01\x02\x03\x04'), bytearray(b'\x05\x06\x07\x08'), bytearray(b'\x01\x00\x05\x01'),
                         bytearray(b'\x09'), bytearray(b'\x09\x03'),
                         bytearray(b'\x01\x02\x09\x04')]
    assert sl.next_block_idx == [1, 3, 4, 0, 0, 0]
    assert sl.level_block_idx == [0, 2, 5]
    assert sl.freq == 9
    sl = BlockSkipList.from_list([1, 2, 3, 4, 5, 6, 7, 8, 9], block_size=9, max_level=1)
    assert sl.max_level == 1
    assert sl.blocks == [bytearray(b'\x01\x02\x03\x04'), bytearray(b'\x05\x06\x07\x08'), bytearray(b'\x01\x00\x05\x01'),
                         bytearray(b'\x09'), bytearray(b'\x09\x03')]
    assert sl.next_block_idx == [1, 3, 4, 0, 0]
    assert sl.level_block_idx == [0, 2]
    assert sl.freq == 9


@pytest.mark.parametrize('arr, target', search_test_cases(100, 50))
def test_block_skip_list_ext_search(arr, target):
    # prepare skip_list_ext
    skip_list = BlockSkipList.from_list(arr, block_size=20)
    with TemporaryFile(prefix="pysearchlite_") as file:
        skip_list.write(file)
        file.seek(0)
        mem = file.read()
        skip_list_ext = BlockSkipListExt.read(mem)
        # prepare target
        mem_target = bytearray(encode_docid(target))
        skip_list_ext_iter = skip_list_ext.get_iter()
        ret, cmp = skip_list_ext_iter.search(mem_target, 0)
        i = linear_search(arr, target)
        if i == len(arr):
            assert decode_docid(skip_list_ext.mem, ret) == arr[-1]
        else:
            assert decode_docid(skip_list_ext.mem, ret) == arr[i]


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
