from pysearchlite._gamma_codecs_cffi import ffi, lib


def bytes_docid(mem, pos):
    buf = ffi.from_buffer(mem)
    return lib.bytes_gamma(buf, pos)


def bytes_block_idx(mem, pos):
    buf = ffi.from_buffer(mem)
    return lib.bytes_gamma(buf, pos)
