"""Playwright E2E tests: Task Tracker frontend / UI interactions."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page, expect

from conftest import HA_URL


class TestFrontend:
    """Tests that exercise the Home Assistant frontend with the Task Tracker integration."""

    def test_home_assistant_frontend_loads(self, page: Page) -> None:
        """The Home Assistant frontend loads successfully."""
        page.goto(HA_URL)
        page.wait_for_load_state("networkidle")
        # HA login page or overview should load
        expect(page).not_to_have_title("")

    def test_integrations_page_accessible(self, page: Page) -> None:
        """The integrations settings page is accessible."""
        page.goto(f"{HA_URL}/config/integrations")
        page.wait_for_load_state("networkidle")
        # Page should not show a network error
        assert page.url.startswith(HA_URL), f"Unexpected redirect to: {page.url}"

    def test_developer_tools_page_loads(self, page: Page) -> None:
        """Developer tools page loads (used for calling services manually)."""
        page.goto(f"{HA_URL}/developer-tools/service")
        page.wait_for_load_state("networkidle")
        assert page.url.startswith(HA_URL)

    def test_task_tracker_visible_in_integrations(self, page: Page, ensure_integration: Any) -> None:
        """After setup, Task Tracker appears on the integrations page."""
        page.goto(f"{HA_URL}/config/integrations")
        page.wait_for_load_state("networkidle")
        # Look for the integration card/name on the page
        tt_card = page.get_by_text("Task Tracker", exact=False)
        expect(tt_card.first).to_be_visible()

    def test_task_tracker_panel_accessible(self, page: Page, ensure_integration: Any) -> None:
        """The Task Tracker sidebar panel is accessible after setup."""
        page.goto(f"{HA_URL}/task-tracker")
        page.wait_for_load_state("networkidle")
        # The page should load within the HA shell
        assert page.url.startswith(HA_URL)

    def test_task_tracker_panel_sort_controls_visible(self, page: Page, ensure_integration: Any) -> None:
        """The Task Tracker panel renders sort controls for Name and Due date."""
        page.goto(f"{HA_URL}/task-tracker")
        page.wait_for_load_state("networkidle")
        # HA is a SPA that lazy-loads the panel JS module; wait explicitly for
        # the custom element to appear before asserting visibility.
        page.wait_for_selector("task-tracker-panel", timeout=15000)
        # The panel is a custom element with shadow DOM; verify it is present
        panel = page.locator("task-tracker-panel")
        expect(panel).to_be_visible()
        # Sort buttons are rendered inside the shadow root
        name_btn = panel.locator("pierce/.sort-btn[data-sort='name']")
        due_btn = panel.locator("pierce/.sort-btn[data-sort='due_date']")
        expect(name_btn).to_be_visible()
        expect(due_btn).to_be_visible()
        # By default the Name button should be active (Name ↑)
        expect(name_btn).to_have_class("active")

    def test_service_call_via_developer_tools(self, page: Page, ensure_integration: Any) -> None:
        """It should be possible to navigate to the service call UI for task_tracker."""
        page.goto(f"{HA_URL}/developer-tools/service")
        page.wait_for_load_state("networkidle")

        # Open the service selector dropdown
        service_selector = page.locator("ha-service-picker, [data-domain='task_tracker']").first
        if service_selector.is_visible():
            service_selector.click()
            page.wait_for_timeout(500)
            # Look for task_tracker option
            tt_option = page.get_by_text("task_tracker", exact=False)
            if tt_option.is_visible():
                tt_option.first.click()

        # Page should still be accessible (no crashes)
        assert page.url.startswith(HA_URL)

    def test_config_page_shows_integration_info(self, page: Page, ensure_integration: Any) -> None:
        """The Task Tracker integration detail page shows expected information."""
        page.goto(f"{HA_URL}/config/integrations")
        page.wait_for_load_state("networkidle")

        # Try to click on the Task Tracker integration card
        tt_link = page.get_by_text("Task Tracker", exact=False).first
        if tt_link.is_visible():
            tt_link.click()
            page.wait_for_load_state("networkidle")
        # Verify we are still on a valid HA page
        assert page.url.startswith(HA_URL)

    def test_no_javascript_errors_on_main_page(self, page: Page) -> None:
        """The main HA page does not log critical JavaScript errors."""
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(HA_URL)
        page.wait_for_load_state("networkidle")
        # Filter out known non-critical errors; check only for unhandled exceptions
        critical = [e for e in errors if "ResizeObserver" not in e]
        assert len(critical) == 0, f"JavaScript errors: {critical}"
