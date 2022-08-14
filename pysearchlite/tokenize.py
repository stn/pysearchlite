import re

ASCII = re.compile("[A-Za-z0-9]+")


def normalized_tokens(s):
    return list(map(lambda x: x.lower(), ASCII.findall(s)))


def tokenize(s):
    return s.split()
