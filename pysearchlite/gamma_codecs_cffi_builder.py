from cffi import FFI
ffibuilder = FFI()


ffibuilder.cdef("""
int bytes_gamma(const unsigned char *mem, size_t pos);
int compare_gamma(const unsigned char *mem_a, size_t pos_a, const unsigned char *mem_b, size_t pos_b);
""")


ffibuilder.set_source("pysearchlite._gamma_codecs_cffi", """
unsigned int VAR_ENCODE_BYTES[] = {
1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
5, 5, 5, 5, 5, 5, 5, 5
};

int bytes_gamma(const unsigned char * mem, size_t pos) {
  return VAR_ENCODE_BYTES[(unsigned int)(mem[pos])];
}

int compare_gamma(const unsigned char *mem_a, size_t pos_a, const unsigned char *mem_b, size_t pos_b) {
  const unsigned char *pa = mem_a + pos_a;
  const unsigned char *pb = mem_a + pos_a;
  const unsigned char a0 = *pa;
  const unsigned char b0 = *pb;
  if (a0 < b0) {
    return -1;
  } else if (a0 > b0) {
    return 1;
  } else if (a0 < 128) {
    return 0;
  }
  
  const unsigned char a1 = *(++pa);
  const unsigned char b1 = *(++pb);
  if (a1 < b1) {
    return -1;
  } else if (a1 > b1) {
    return 1;
  } else if (a0 < 192) {
    return 0;
  }
  
  const unsigned char a2 = *(++pa);
  const unsigned char b2 = *(++pb);
  if (a2 < b2) {
    return -1;
  } else if (a2 > b2) {
    return 1;
  } else if (a0 < 224) {
    return 0;
  }
  
  const unsigned char a3 = *(++pa);
  const unsigned char b3 = *(++pb);
  if (a3 < b3) {
    return -1;
  } else if (a3 > b3) {
    return 1;
  } else if (a0 < 240) {
    return 0;
  }
  
  const unsigned char a4 = *(++pa);
  const unsigned char b4 = *(++pb);
  if (a4 < b4) {
    return -1;
  } else if (a4 > b4) {
    return 1;
  }
  
  return 0;
}
""")


if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
