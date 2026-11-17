"""Browser fixture for Work Home and Your Projects, without a live OAuth session."""
import json
import os
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class WorkLanguageBrowserTests(unittest.TestCase):
    def test_home_and_project_dialog_in_four_locales(self):
        strings = json.loads((ROOT / "urano/work_strings.json").read_text())
        html = (ROOT / "web/index.html").read_text()
        header = html[html.index('<header class="top">'):html.index('<!-- Step 1: mode -->')]
        modes = html[html.index('<section class="screen" id="mode"'):
                     html.index('<nav id="showNavigation"')]
        runtime = (ROOT / "urano/work_i18n.js").read_text()
        bridge = (ROOT / "urano/native_owner_browser_bridge.js").read_text()
        translations = "window.MontaraWorkStrings = " + json.dumps(strings) + ";"
        fixture = (f"<html><head><style>{(ROOT / 'web/montara.css').read_text()}"
                   f"{(ROOT / 'urano/owner_account.css').read_text()}</style></head><body>"
                   f"{header}{modes}<script>{translations}{runtime}</script>"
                   f"<script>{bridge}</script></body></html>")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.environ.get("MONTARA_TEST_BROWSER"))
            page = browser.new_page()
            preferences = {"language": "en"}

            def respond(route):
                path = route.request.url.removeprefix("https://work.test")
                if path == "/":
                    return route.fulfill(content_type="text/html", body=fixture)
                if path == "/urano/v1/session/account":
                    return route.fulfill(json={**preferences, "name": "Work Tester"})
                if path == "/urano/v1/session/refresh":
                    return route.fulfill(json={"csrf": "a" * 64})
                if path == "/urano/v1/session/language":
                    preferences.update(route.request.post_data_json)
                    return route.fulfill(json=preferences)
                if path == "/urano/v1/native/ensure":
                    return route.fulfill(json={"state": "ready", "generation": 1})
                if path == "/urano/v1/native/rpc/api/v1/wizard/projects":
                    return route.fulfill(json={"projects": [{"title": "Mix a song"}]})
                return route.fulfill(status=404)

            page.route("https://work.test/**", respond)
            page.goto("https://work.test/")
            page.locator("#home").evaluate("(node) => node.hidden = true")
            page.locator("#mode").evaluate("(node) => node.hidden = false")
            avatar = page.locator(".montara-work-avatar")
            for locale in ("en", "es", "de", "fr"):
                with self.subTest(locale=locale):
                    def label(key):
                        return key if locale == "en" else strings[key][("es", "de", "fr").index(locale)]

                    avatar.click()
                    page.locator("#montaraWorkAccountPanel select").select_option(locale)
                    expect(page.locator("html")).to_have_attribute("lang", locale)
                    expect(page.locator("#modeQuestion")).to_have_text(label("What would you like to make?"))
                    expect(page.locator('[data-intent="music"] small')).to_have_text(
                        label("Mix tracks or master a finished song."))
                    page.get_by_role("button", name=label("Your Projects")).click()
                    dialog = page.get_by_role("dialog", name=label("Your Projects"))
                    expect(dialog).to_be_visible()
                    expect(dialog.get_by_text("Mix a song", exact=True)).to_be_visible()
                    if destination := os.environ.get("MONTARA_I18N_SCREENSHOTS"):
                        page.screenshot(path=str(Path(destination) / f"projects-{locale}.png"))
                    dialog.get_by_role("button", name=label("Close")).click()
                    if destination:
                        page.screenshot(path=str(Path(destination) / f"home-{locale}.png"))
            browser.close()
