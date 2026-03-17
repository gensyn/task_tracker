"""pytest-homeassistant-custom-component conftest for Task Tracker integration tests.

This file wires the component (which lives at the repo root, not inside a
conventional ``custom_components/`` sub-directory) into Home Assistant's custom
component loader, and provides shared fixtures used by all integration tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

# The repo root IS the component package (content_in_root: true).
REPO_ROOT = Path(__file__).parent.parent.parent  # …/task_tracker/task_tracker/

# Make the repo root importable so Python can see it as a top-level package.
_REPO_PARENT = str(REPO_ROOT.parent)
if _REPO_PARENT not in sys.path:
    sys.path.insert(0, _REPO_PARENT)

# ---------------------------------------------------------------------------
# custom_components symlink
# ---------------------------------------------------------------------------
# Home Assistant's component loader imports the ``custom_components`` package
# and iterates its subdirectories.  We create a symlink
#   <repo_root>/custom_components/task_tracker -> <repo_root>
# so that HA can discover and load the component as ``custom_components.task_tracker``.

_CUSTOM_COMPONENTS = REPO_ROOT / "custom_components"
_CUSTOM_COMPONENTS.mkdir(exist_ok=True)
(_CUSTOM_COMPONENTS / "__init__.py").touch()

_SYMLINK = _CUSTOM_COMPONENTS / "task_tracker"
if not _SYMLINK.exists():
    _SYMLINK.symlink_to(REPO_ROOT)

# Make custom_components importable from within the repo root.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def expected_lingering_timers() -> bool:
    """The midnight-update timer registered by ``async_setup`` is intentionally
    kept running until HA shuts down.  Allow it to linger during test teardown
    so PHCC logs a warning rather than failing the test.
    """
    return True


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for every test in this package."""


@pytest.fixture(autouse=True)
def mock_frontend_setup():
    """Skip lovelace / panel registration — irrelevant for integration tests.

    ``async_setup`` calls ``TaskTrackerCardRegistration.async_register`` which
    interacts with the lovelace subsystem.  We patch it to a no-op so the
    integration tests can focus on the component's business logic.
    """
    with patch(
        "custom_components.task_tracker.TaskTrackerCardRegistration"
    ) as mock_cls:
        mock_cls.return_value.async_register = AsyncMock()
        yield
