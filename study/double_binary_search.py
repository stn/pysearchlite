def binary_search(arr: list[int], target: int, left: int, right: int) -> int:
    while left < right:
        m = (left + right) // 2
        if arr[m] < target:
            left = m + 1
        else:
            right = m
    return left


def binary_search_rightmost(arr: list[int], target: int, left: int, right: int) -> int:
    return binary_search(arr, target + 1, left, right) - 1


def intersect_by_double_binary_search(a: list[int], left_a: int, right_a: int,
                                      b: list[int], left_b: int, right_b: int,
                                      result: list[int]):
    if left_a >= right_a or left_b >= right_b:
        return

    len_a = right_a - left_a
    len_b = right_b - left_b

    if len_a == 1:
        ma_val = a[left_a]
        if len_b == 1:
            if b[left_b] == ma_val:
                result.append(ma_val)
            return

        mb = binary_search(b, ma_val + 1, left_b, right_b) - 1
        if mb < left_b:
            return
        if b[mb] == ma_val:
            result.append(ma_val)
        return

    ma = (left_a + right_a) // 2
    ma_val = a[ma]

    mb = binary_search(b, ma_val + 1, left_b, right_b) - 1
    if mb < left_b:
        intersect_by_double_binary_search(a, ma + 1, right_a, b, left_b, right_b, result)
        return

    if b[mb] < ma_val:
        intersect_by_double_binary_search(a, left_a, ma, b, left_b, mb + 1, result)
        intersect_by_double_binary_search(a, ma + 1, right_a, b, mb + 1, right_b, result)
    elif b[mb] > ma_val:
        assert False  # never happens
    else:  # mb_val == ma_val
        assert b[mb] == ma_val
        intersect_by_double_binary_search(a, left_a, ma, b, left_b, mb, result)
        result.append(ma_val)
        intersect_by_double_binary_search(a, ma + 1, right_a, b, mb + 1, right_b, result)
