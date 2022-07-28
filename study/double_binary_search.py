

def binary_search(arr: list[int], target: int, left: int, right: int) -> int:
    original_right = right
    while left != right:
        lr = left + right
        m = (lr // 2)
        if arr[m] < target:
            left = m + 1
        else:
            right = m
    if right < original_right and arr[right] < target:
        return right + 1
    return right


def double_binary_search(a: list[int], left_a: int, right_a: int,
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

        mb = binary_search(b, ma_val, left_b, right_b)
        if mb >= right_b:
            return
        if b[mb] == ma_val:
            result.append(ma_val)
        return

    ma = (left_a + right_a) // 2
    ma_val = a[ma]
    mb = binary_search(b, ma_val, left_b, right_b)
    if mb >= right_b:
        double_binary_search(a, left_a, ma, b, left_b, right_b, result)
        return

    if b[mb] > ma_val:
        if ma - left_a <= mb - left_b:
            double_binary_search(a, left_a, ma, b, left_b, mb, result)
        else:
            double_binary_search(b, left_b, mb, a, left_a, ma, result)
        if right_a - ma <= right_b - mb:
            double_binary_search(a, ma + 1, right_a, b, mb, right_b, result)
        else:
            double_binary_search(b, mb, right_b, a, ma + 1, right_a, result)
    elif b[mb] < ma_val:
        assert False  # never happens
    else:  # mb_val == ma_val
        assert b[mb] == ma_val
        if ma - left_a <= mb - left_b:
            double_binary_search(a, left_a, ma, b, left_b, mb, result)
        else:
            double_binary_search(b, left_b, mb, a, left_a, ma, result)
        result.append(ma_val)
        if right_a - ma <= right_b - mb:
            double_binary_search(a, ma + 1, right_a, b, mb + 1, right_b, result)
        else:
            double_binary_search(b, mb + 1, right_b, a, ma + 1, right_a, result)
