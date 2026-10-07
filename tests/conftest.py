import logging

import pytest


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """set_logger() adds handlers to the root logger on every command run; without this,
    handlers (and their open file descriptors) accumulate across tests in the same process.
    """
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)
            handler.close()
