"""A writer that goes through evidence.append, so no rule fires."""


def record(evidence, store, stream, row):
    return evidence.append(store, stream, row)
