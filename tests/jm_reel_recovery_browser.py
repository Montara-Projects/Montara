"""Brave regression on an isolated JM server with a delayed Stage recovery."""
import array
import json
import math
import os
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


origin = os.environ.get("JM_REEL_TEST_ORIGIN", "http://127.0.0.1:8109")
fixture = Path(os.environ["JM_REEL_TEST_FIXTURES"])
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.environ.get("JM_REEL_TEST_BROWSER"))
    page = browser.new_page()
    page.on("dialog", lambda dialog: dialog.accept())  # Synthetic media only.
    page.route("http://127.0.0.1:47820/**", lambda route: route.abort())
    original = page.request.get(origin + "/api/v1/project").json()
    inputs = original["inputs"]
    draft = page.request.post(origin + "/api/v1/wizard/draft", data={
        "platform": "youtube", "name": "Synthetic Stage recovery",
        "videos": [item["path"] for item in inputs["videos"]],
        "master": inputs["master"]["path"], "audio_paths": [inputs["master"]["path"]],
    })
    assert draft.ok, draft.text()
    pending = []
    page.route(origin + "/api/v1/project", lambda route: pending.append((route, route.fetch()))
               if not pending else route.continue_())
    operations = []
    page.on("request", lambda event: operations.append((event.url, event.post_data))
            if "/wizard/" in event.url or "/artifacts/sync" in event.url else None)
    if baseline := os.environ.get("JM_REEL_BASELINE_JS"):
        page.route(origin + "/montara.js", lambda route: route.fulfill(
            path=baseline, content_type="application/javascript"))
    page.goto(origin + "/?resume=footage")
    page.wait_for_timeout(500)
    assert pending, "Expected to hold the previous Stage /project response"
    page.locator(".brand").click()
    page.locator("[data-intent=video]").click()
    page.locator("[data-platform=reel]").click()
    pending[0][0].fulfill(response=pending[0][1])
    page.wait_for_timeout(350)
    if baseline:
        assert page.evaluate("state.platform") == "youtube", "Baseline did not reproduce the stale Stage takeover"
        print("Baseline reproduces stale Stage takeover after selecting Push")
        browser.close()
        raise SystemExit(0)
    assert page.evaluate("state.platform") == "reel"
    # A hidden stale Stage recovery must not replace the outgoing Reel mode.
    expect(page.locator("#footage")).to_be_visible()
    page.locator("[data-drop=video] input").set_input_files(fixture / "camera.mp4")
    page.locator("[data-drop=audio] input").set_input_files(fixture / "independent.mp3")
    expect(page.locator("#continueFootage")).to_be_enabled(timeout=30000)
    page.locator('input[name=branding][value=none]').check()
    page.locator("#continueFootage").click()
    expect(page.locator("#continueCameras")).to_be_visible(timeout=30000)
    page.locator("#continueCameras").click()
    expect(page.locator("#capSkip")).to_be_visible(timeout=120000)
    page.locator("#capSkip").click()
    with page.expect_download() as download:
        page.locator("#download").click()
    output = fixture / "reel.mp4"
    download.value.save_as(output)
    assert not any("/artifacts/sync" in url or "/wizard/prepare" in url
                   for url, _ in operations), operations
    starts = [json.loads(data) for url, data in operations if url.endswith("/wizard/start")]
    assert starts and all(body["platform"] == "reel" for body in starts), operations
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(output), "-f", "null", "-"], check=True)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,width,height:format=duration", "-of", "json", str(output)]))
    assert {row["codec_name"] for row in probe["streams"]} == {"h264", "aac"}, probe
    assert abs(float(probe["format"]["duration"]) - 5) < .15, probe
    pcm = array.array("h", subprocess.check_output(["ffmpeg", "-v", "error", "-ss", "1",
        "-i", str(output), "-t", "1", "-map", "0:a:0", "-ac", "1", "-ar", "8000",
        "-f", "s16le", "-"]))
    def tone(frequency):
        radians = 2 * math.pi * frequency / 8000
        return math.hypot(sum(value * math.cos(i * radians) for i, value in enumerate(pcm)),
                          sum(value * math.sin(i * radians) for i, value in enumerate(pcm)))
    assert tone(713) > 10 * max(1, tone(220)), "Export did not use the independent MP3"
    print(probe, "713 Hz soundtrack verified")
    browser.close()
    print(output)
