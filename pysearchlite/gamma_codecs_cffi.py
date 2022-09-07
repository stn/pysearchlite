from pysearchlite._gamma_codecs_cffi import ffi, lib


def bytes_docid(mem, pos):
    buf = ffi.from_buffer(mem)
    return lib.bytes_gamma(buf, pos)


def bytes_block_idx(mem, pos):
    buf = ffi.from_buffer(mem)
    return lib.bytes_gamma(buf, pos)


def compare_docid(mem_a, pos_a, mem_b, pos_b):
    buf_a = ffi.from_buffer(mem_a)
    buf_b = ffi.from_buffer(mem_b)
    return lib.compare_gamma(buf_a, pos_a, buf_b, pos_b)
