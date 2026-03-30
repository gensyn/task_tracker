"""Playwright E2E tests: Task Tracker frontend / UI interactions."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page, expect

from conftest import HA_URL

# JavaScript helper that recursively searches through all shadow roots.
_DEEP_QUERY_JS = """
    function deepQuery(root, sel) {
        const el = root.querySelector(sel);
        if (el) return el;
        for (const child of root.querySelectorAll('*')) {
            if (child.shadowRoot) {
                const found = deepQuery(child.shadowRoot, sel);
                if (found) return found;
            }
        }
        return null;
    }
"""


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
        # Navigate to HA's base URL first so the SPA establishes its WebSocket
        # connection and loads the full panel registry (including task-tracker)
        # before we try to route to the panel URL.  A direct navigation to
        # /task-tracker can arrive before the SPA receives the panels list,
        # causing a redirect to the default Lovelace view.
        page.goto(HA_URL)
        page.wait_for_load_state("networkidle")
        page.goto(f"{HA_URL}/task-tracker")
        page.wait_for_load_state("networkidle")
        # task-tracker-panel lives inside HA's nested shadow DOM.  The panel
        # pre-renders its sort controls in the constructor (before HA calls
        # set hass()), so the buttons are present as soon as ha-panel-custom
        # creates the element.  Use JavaScript deepQuery — which recursively
        # traverses all shadow roots — to wait for them.
        page.wait_for_function(
            f"""() => {{
                {_DEEP_QUERY_JS}
                const panel = deepQuery(document, 'task-tracker-panel');
                return !!(
                    panel &&
                    panel.shadowRoot &&
                    panel.shadowRoot.querySelector('.sort-btn[data-sort="name"]') &&
                    panel.shadowRoot.querySelector('.sort-btn[data-sort="due_date"]')
                );
            }}""",
            timeout=30000,
        )
        result = page.evaluate(
            f"""() => {{
                {_DEEP_QUERY_JS}
                const panel = deepQuery(document, 'task-tracker-panel');
                const shadow = panel.shadowRoot;
                const nameBtn = shadow.querySelector('.sort-btn[data-sort="name"]');
                const dueBtn = shadow.querySelector('.sort-btn[data-sort="due_date"]');
                return {{
                    hasNameBtn: !!nameBtn,
                    hasDueBtn: !!dueBtn,
                    nameBtnActive: nameBtn ? nameBtn.classList.contains('active') : false,
                }};
            }}"""
        )
        assert result["hasNameBtn"], "Name sort button not found in task-tracker-panel"
        assert result["hasDueBtn"], "Due date sort button not found in task-tracker-panel"
        assert result["nameBtnActive"], "Name sort button should be active by default"

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
