"""A writer that still appends by opening the store file directly."""


def append_row(path, line):
    with open(path, "a") as fh:
        fh.write(line)
