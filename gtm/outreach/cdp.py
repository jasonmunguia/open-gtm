"""Minimal Chrome DevTools Protocol client + browser discovery/launch.

BYOK browser: any Chromium (Chrome, Chromium, Brave, Edge, Arc) speaks CDP.
Default mode launches a DEDICATED profile under data/<icp>/ so your daily
browser is never touched and the LinkedIn session lives in a directory that
is gitignored with the rest of data/. First run: a visible window opens, you
log in once, it persists. Attach mode (`browser.cdp_url`) uses a browser you
already launched with --remote-debugging-port.

Runs offscreen by default — a window parked just past the screen corner,
never focused. Not minimized: a minimized/occluded page gets its timers
throttled and stops painting, and then nothing renders to click.
"""
import json
import os
import platform
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from . import js

DEFAULT_PORT = 9333

CANDIDATES = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ],
    "Linux": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser", "microsoft-edge"],
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
}


class NotLoggedIn(RuntimeError):
    pass


class WindowGone(RuntimeError):
    """The CDP target died. Infrastructure failure — never a candidate verdict."""


def find_browser(binary=None):
    if binary:
        if Path(binary).is_file() or shutil.which(binary):
            return binary
        raise FileNotFoundError(f"browser.binary not found: {binary}")
    for cand in CANDIDATES.get(platform.system(), []):
        if Path(cand).is_file() or shutil.which(cand):
            return cand
    raise FileNotFoundError(
        "no Chromium-family browser found. Install Google Chrome "
        "(https://www.google.com/chrome/) or set browser.binary in outreach.yaml")


def _alive(base):
    try:
        urllib.request.urlopen(base + "/json/version", timeout=3)
        return True
    except Exception:  # noqa: BLE001 — any failure here means "not up"
        return False


class Page:
    """One CDP target, one websocket, held open for the run."""

    def __init__(self, ws_url):
        from websockets.sync.client import connect
        self._ws = connect(ws_url, max_size=50_000_000)
        self._id = 0

    def rpc(self, method, params=None, timeout=25):
        self._id += 1
        self._ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = json.loads(self._ws.recv(timeout=timeout))
            if r.get("id") == self._id:
                if "error" in r:
                    raise RuntimeError(r["error"])
                return r.get("result", {})
        raise TimeoutError(method)

    def ev(self, expr, await_promise=False, timeout=25):
        r = self.rpc("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                           "userGesture": True, "awaitPromise": await_promise}, timeout)
        res = r.get("result", {})
        if res.get("subtype") == "error":
            return "JS_ERROR: " + str(res.get("description", ""))[:300]
        return res.get("value")

    def jev(self, expr, await_promise=False, timeout=25):
        """ev() and parse the JSON the scripts return. Always a dict/list."""
        v = self.ev(expr, await_promise, timeout)
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return {"raw": v}
        return v if isinstance(v, (dict, list)) else {"raw": v}

    def goto(self, url, wait=6):
        self.rpc("Page.navigate", {"url": url})
        time.sleep(wait)

    def click(self, x, y):
        for t in ("mousePressed", "mouseReleased"):
            self.rpc("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})

    def shot(self, path):
        data = self.rpc("Page.captureScreenshot", {"format": "png"}, timeout=30)["data"]
        import base64
        Path(path).write_bytes(base64.b64decode(data))

    def close(self):
        self._ws.close()


class Browser:
    def __init__(self, base_url, proc=None):
        self.base = base_url.rstrip("/")
        self.proc = proc

    @classmethod
    def attach(cls, cdp_url):
        b = cls(cdp_url)
        if not b.alive():
            raise ConnectionError(f"nothing answering at {cdp_url}/json/version — launch your browser "
                                  f"with --remote-debugging-port and log in to LinkedIn first")
        return b

    @classmethod
    def launch(cls, profile_dir, port=DEFAULT_PORT, binary=None, log=print):
        base = f"http://127.0.0.1:{port}"
        if _alive(base):
            log(f"browser already up on :{port} — reusing")
            return cls(base)
        exe = find_browser(binary)
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        args = [exe, f"--remote-debugging-port={port}", f"--user-data-dir={profile_dir}",
                "--no-first-run", "--no-default-browser-check", "--disable-session-crashed-bubble",
                "https://www.linkedin.com/feed/"]
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            if _alive(base):
                log(f"launched {Path(exe).name} on :{port} (profile {profile_dir})")
                return cls(base, proc)
            time.sleep(1)
        raise RuntimeError(f"{exe} did not open port {port} within 30s")

    def alive(self):
        return _alive(self.base)

    def targets(self):
        return json.loads(urllib.request.urlopen(self.base + "/json/list", timeout=5).read())

    def page(self, target_file, url="https://www.linkedin.com/feed/"):
        """Reuse the target recorded in target_file if it still exists, else
        create one. Returns (Page, target_id)."""
        target_file = Path(target_file)
        old = target_file.read_text().strip() if target_file.is_file() else None
        tabs = {t["id"]: t for t in self.targets() if t.get("type") == "page"}
        if old and old in tabs:
            return Page(tabs[old]["webSocketDebuggerUrl"]), old
        ver = json.loads(urllib.request.urlopen(self.base + "/json/version", timeout=5).read())
        root = Page(ver["webSocketDebuggerUrl"])
        try:
            tid = root.rpc("Target.createTarget", {"url": url, "newWindow": True, "background": True})["targetId"]
        finally:
            root.close()
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(tid)
        time.sleep(6)
        tabs = {t["id"]: t for t in self.targets()}
        if tid not in tabs:
            raise WindowGone("created a target but it is not listed — browser refused the window")
        return Page(tabs[tid]["webSocketDebuggerUrl"]), tid

    def _window(self, page, tid):
        return page.rpc("Browser.getWindowForTarget", {"targetId": tid})["windowId"]

    def place_offscreen(self, page, tid, bounds=None):
        """Park the window just past the bottom-right corner: a ~60px sliver
        stays on-screen so the OS keeps it 'visible' and painting."""
        if bounds is None:
            sz = page.jev(js.load("screen_size"))
            w, h = int(sz.get("w", 1920)), int(sz.get("h", 1080))
            bounds = {"left": w - 60, "top": h - 60, "width": 1100, "height": 850}
        page.rpc("Browser.setWindowBounds", {"windowId": self._window(page, tid), "bounds": bounds})

    def bring_onscreen(self, page, tid):
        page.rpc("Browser.setWindowBounds", {"windowId": self._window(page, tid),
                                             "bounds": {"left": 80, "top": 80, "width": 1100, "height": 850}})
        page.rpc("Page.bringToFront")


def login_status(page):
    v = page.ev(js.load("login_status"), await_promise=True, timeout=20)
    return v if isinstance(v, int) else 0


def ensure_logged_in(browser, page, tid, wait_minutes=10, log=print, sleep=time.sleep):
    """200 from /voyager/api/me or we surface the window and wait for a human
    to log in. Session cookies persist in the profile dir, so this is a
    first-run event, not a per-run one."""
    for _ in range(3):
        if login_status(page) == 200:
            return
        sleep(3)
    log("LinkedIn session not logged in — bringing the window on screen. "
        f"Log in there; I'll wait up to {wait_minutes} minutes.")
    browser.bring_onscreen(page, tid)
    page.goto("https://www.linkedin.com/login", 3)
    deadline = time.time() + wait_minutes * 60
    while time.time() < deadline:
        if login_status(page) == 200:
            log("logged in — session saved to the profile directory")
            return
        sleep(5)
    raise NotLoggedIn(f"no LinkedIn session after {wait_minutes} minutes — nothing was sent")
