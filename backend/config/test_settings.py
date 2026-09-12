"""
Settings overrides used only by the automated test suite. Not used in
development or production.
"""
from .settings import *  # noqa: F401,F403

# Surface real tracebacks in the test runner instead of rendering Django's
# HTML debug page (which has a known incompatibility with newer Python
# versions), so failing tests show the actual error.
DEBUG_PROPAGATE_EXCEPTIONS = True
