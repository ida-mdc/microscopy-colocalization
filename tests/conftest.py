import logging

import matplotlib
import pytest

# Headless-safe backend for tests: plotting.py otherwise picks an interactive backend (e.g.
# Tk), which has no display to attach to on CI runners and crashes outright on some of them
# (observed on Windows). Must be set before any other module imports matplotlib.pyplot.
matplotlib.use('Agg')


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
