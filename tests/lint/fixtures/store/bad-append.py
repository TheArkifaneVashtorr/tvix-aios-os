"""A writer that still appends via the raw append flag, bypassing evidence.

This is the shape the old `pkgs/helm/collect.py` `_append_status_row` used: an
os.open with the append flag under flock. It must trip the store-writers
append rule so a tree-run that stops sweeping `pkgs/helm` cannot hide a
regression.
"""

import os


def append_row(path, line):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    os.write(fd, line.encode())
    os.close(fd)
