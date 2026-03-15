#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

try:
    import browser_cookie3
except ImportError:  # pragma: no cover - checked by doctor
    browser_cookie3 = None

try:
    import websocket
except ImportError:  # pragma: no cover - checked by doctor
    websocket = None


DEFAULT_PORT = int(os.environ.get("OUTLOOK_REPLY_DEBUG_PORT", "9223"))
DEFAULT_STARTUP_WAIT = 15.0
DEFAULT_SEARCH_WARMUP = 10.0
TEMP_PROFILE_PREFIX = "codex-outlook-reply-"
OUTLOOK_ENTRY_URL = "https://outlook.office.com/mail/"
SEARCH_INPUT_SELECTOR = (
    'input[role="combobox"][placeholder="搜索"], '
    'input[role="combobox"][placeholder="Search"], '
    'input[aria-label*="搜索"], '
    'input[aria-label*="Search"]'
)
EDITOR_SELECTOR = (
    'div[role="textbox"][aria-label*="正文"], '
    'div[role="textbox"][aria-label*="body"], '
    'div[role="textbox"][aria-label*="Body"], '
    'div[role="textbox"][aria-label*="message"], '
    'div[role="textbox"][aria-label*="Message"]'
)
COOKIE_DOMAINS = (
    ".outlook.office.com",
    ".outlook.cloud.microsoft",
    ".outlook.com",
    ".office.com",
    ".office365.com",
    ".microsoftonline.com",
    ".live.com",
)
INBOX_MARKERS = ("收件箱", "inbox")
SENT_MARKERS = ("已发送邮件", "sent items", "sent mail")
DRAFT_MARKERS = ("草稿", "[草稿]", "draft")
LOGIN_MARKERS = (
    "sign in to your account",
    "pick an account",
    "stay signed in",
    "登录到你的帐户",
    "选择帐户",
    "保持登录状态",
)
HANDOFF_MARKERS = (
    "captcha",
    "verify you are human",
    "approve sign in request",
    "use microsoft authenticator",
    "验证你是人类",
    "需要更多信息",
    "microsoft authenticator",
)
SEND_LABELS = ("发送", "Send")
REPLY_LABELS = ("答复", "回复", "Reply")
DISCARD_LABELS = ("放弃", "Discard")
NEW_MAIL_LABELS = ("新邮件", "New mail")


class OutlookReplyError(RuntimeError):
    def __init__(self, message: str, *, handoff_required: bool = False) -> None:
        super().__init__(message)
        self.handoff_required = handoff_required


@dataclass
class SearchItem:
    index: int
    aria: str
    text: str

    @property
    def blob(self) -> str:
        return normalize(f"{self.aria} {self.text}")


@dataclass
class BrowserHandle:
    port: int
    browser_ws_url: str
    started_here: bool
    created_page_id: Optional[str]
    created_page_ws_url: str
    temp_profile_dir: Optional[pathlib.Path]
    keep_open_for_handoff: bool = False

    def cleanup(self) -> None:
        if self.keep_open_for_handoff:
            return
        if self.started_here:
            browser_close(self.browser_ws_url)
            if self.temp_profile_dir:
                wait_for_path_release(self.temp_profile_dir)
                shutil.rmtree(self.temp_profile_dir, ignore_errors=True)
            return
        if self.created_page_id:
            close_target_tab(self.port, self.created_page_id)


class CDPSession:
    def __init__(self, websocket_url: str) -> None:
        if websocket is None:
            raise OutlookReplyError(
                "The websocket-client package is missing. Run doctor for details."
            )
        self._ws = websocket.create_connection(websocket_url, suppress_origin=True)
        self._msg_id = 0
        for method in ("Page.enable", "Runtime.enable", "DOM.enable", "Network.enable"):
            self.call(method)

    def close(self) -> None:
        self._ws.close()

    def call(
        self, method: str, params: Optional[dict[str, Any]] = None, timeout: float = 30.0
    ) -> dict[str, Any]:
        self._msg_id += 1
        my_id = self._msg_id
        payload = {"id": my_id, "method": method, "params": params or {}}
        self._ws.send(json.dumps(payload))
        end = time.time() + timeout
        while time.time() < end:
            message = json.loads(self._ws.recv())
            if message.get("id") != my_id:
                continue
            if "error" in message:
                raise OutlookReplyError(f"{method} failed: {message['error']}")
            return message.get("result", {})
        raise OutlookReplyError(f"{method} timed out after {timeout:.1f}s")

    def evaluate(
        self, expression: str, *, by_value: bool = True, timeout: float = 20.0
    ) -> Any:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": by_value,
                "awaitPromise": True,
            },
            timeout=timeout,
        )
        remote = result.get("result", {})
        if by_value:
            return remote.get("value")
        return remote

    def evaluate_json(self, expression: str, *, timeout: float = 20.0) -> Any:
        raw = self.evaluate(expression, timeout=timeout)
        if raw in (None, ""):
            return None
        return json.loads(raw)

    def navigate(self, url: str) -> None:
        self.call("Page.navigate", {"url": url}, timeout=20.0)

    def body_text(self, limit: int = 5000) -> str:
        expr = f"document.body ? document.body.innerText.slice(0, {limit}) : ''"
        return self.evaluate(expr) or ""

    def wait_for(
        self, expression: str, *, timeout: float = 20.0, interval: float = 0.5
    ) -> Any:
        end = time.time() + timeout
        while time.time() < end:
            value = self.evaluate(expression, timeout=min(5.0, timeout))
            if value:
                return value
            time.sleep(interval)
        raise OutlookReplyError(f"Condition not met within {timeout:.1f}s")

    def query_file_inputs(self) -> list[int]:
        root = self.call("DOM.getDocument", {"depth": -1, "pierce": True})["root"][
            "nodeId"
        ]
        result = self.call(
            "DOM.querySelectorAll",
            {"nodeId": root, "selector": 'input[data-testid="local-computer-filein"]'},
        )
        return result.get("nodeIds", [])

    def set_files(self, node_id: int, files: list[str]) -> None:
        self.call(
            "DOM.setFileInputFiles",
            {"nodeId": node_id, "files": files},
            timeout=40.0,
        )


def normalize(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run(
    cmd: list[str], *, check: bool = False, capture: bool = True
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, Any] = {"text": True, "check": check}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(cmd, **kwargs)


def http_json(url: str, *, method: str = "GET", timeout: float = 5.0) -> Any:
    request = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_hint(raw: str) -> str:
    try:
        if "T" in raw:
            return dt.datetime.fromisoformat(raw).isoformat()
        return dt.date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise OutlookReplyError(
            f"Invalid date/time value: {raw!r}. Use YYYY-MM-DD or ISO datetime."
        ) from exc


def ensure_non_empty_stdin() -> str:
    body = sys.stdin.read()
    if not body.strip():
        raise OutlookReplyError("Reply body is empty. Pipe plain text into stdin.")
    return body


def ensure_attachments(paths: list[str]) -> list[str]:
    resolved: list[str] = []
    for raw in paths:
        path = pathlib.Path(raw).expanduser()
        if not path.is_absolute():
            raise OutlookReplyError(f"Attachment must use an absolute path: {raw}")
        if not path.exists():
            raise OutlookReplyError(f"Attachment does not exist: {path}")
        if not path.is_file():
            raise OutlookReplyError(f"Attachment is not a file: {path}")
        resolved.append(str(path))
    return resolved


def chrome_is_available() -> bool:
    if shutil.which("open") is None:
        return False
    return run(["open", "-Ra", "Google Chrome"], check=False).returncode == 0


def debug_endpoint_info(port: int) -> Optional[dict[str, Any]]:
    url = f"http://127.0.0.1:{port}/json/version"
    try:
        return http_json(url, timeout=1.0)
    except Exception:
        return None


def list_targets(port: int) -> list[dict[str, Any]]:
    return http_json(f"http://127.0.0.1:{port}/json/list", timeout=5.0)


def create_new_tab(port: int) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}/json/new?about:blank"
    try:
        return http_json(url, method="PUT", timeout=5.0)
    except urllib.error.HTTPError:
        return http_json(url, method="GET", timeout=5.0)


def close_target_tab(port: int, target_id: str) -> None:
    try:
        urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json/close/{target_id}", timeout=3.0
        ).read()
    except Exception:
        pass


def browser_close(browser_ws_url: str) -> None:
    if websocket is None:
        return
    try:
        ws = websocket.create_connection(browser_ws_url, suppress_origin=True)
        ws.send(json.dumps({"id": 1, "method": "Browser.close", "params": {}}))
        ws.close()
    except Exception:
        pass


def wait_for_debug_port(port: int, timeout: float = DEFAULT_STARTUP_WAIT) -> dict[str, Any]:
    end = time.time() + timeout
    while time.time() < end:
        info = debug_endpoint_info(port)
        if info:
            return info
        time.sleep(0.5)
    raise OutlookReplyError(
        f"Chrome debugging endpoint on port {port} did not become available."
    )


def launch_temp_chrome(port: int) -> tuple[pathlib.Path, dict[str, Any]]:
    if not chrome_is_available():
        raise OutlookReplyError("Google Chrome is not installed or cannot be opened.")
    profile_dir = pathlib.Path(
        tempfile.mkdtemp(prefix=TEMP_PROFILE_PREFIX, dir=tempfile.gettempdir())
    )
    cmd = [
        "open",
        "-na",
        "Google Chrome",
        "--args",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    run(cmd, check=False)
    info = wait_for_debug_port(port)
    return profile_dir, info


def wait_for_path_release(path: pathlib.Path, attempts: int = 20) -> None:
    for _ in range(attempts):
        if not path.exists():
            return
        try:
            next(path.iterdir(), None)
            return
        except OSError:
            time.sleep(0.25)


def collect_cookie_payloads() -> list[dict[str, Any]]:
    if browser_cookie3 is None:
        return []
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for domain in COOKIE_DOMAINS:
        try:
            jar = browser_cookie3.chrome(domain_name=domain)
        except Exception:
            continue
        for cookie in jar:
            domain_value = cookie.domain or domain.lstrip(".")
            key = (cookie.name, domain_value, cookie.path or "/")
            payload: dict[str, Any] = {
                "name": cookie.name,
                "value": cookie.value,
                "path": cookie.path or "/",
                "secure": bool(cookie.secure),
                "httpOnly": bool(cookie._rest.get("HttpOnly")),
                "url": f"{'https' if cookie.secure else 'http'}://{domain_value.lstrip('.')}{cookie.path or '/'}",
            }
            if cookie.name.startswith("__Host-"):
                payload["url"] = f"https://{domain_value.lstrip('.')}{cookie.path or '/'}"
            else:
                payload["domain"] = domain_value
            if cookie.expires:
                payload["expires"] = float(cookie.expires)
            same_site = str(cookie._rest.get("SameSite", "")).strip().lower()
            if same_site in {"lax", "strict"}:
                payload["sameSite"] = same_site.title()
            elif same_site in {"none", "no_restriction"}:
                payload["sameSite"] = "None"
            unique[key] = payload
    return list(unique.values())


def import_cookies(session: CDPSession, payloads: list[dict[str, Any]]) -> int:
    imported = 0
    for payload in payloads:
        try:
            result = session.call("Network.setCookie", payload, timeout=10.0)
        except OutlookReplyError:
            continue
        if result.get("success"):
            imported += 1
    return imported


def ensure_browser(port: int) -> BrowserHandle:
    info = debug_endpoint_info(port)
    started_here = False
    temp_profile_dir: Optional[pathlib.Path] = None
    if info is None:
        temp_profile_dir, info = launch_temp_chrome(port)
        started_here = True
    page = create_new_tab(port)
    return BrowserHandle(
        port=port,
        browser_ws_url=info.get("webSocketDebuggerUrl", ""),
        started_here=started_here,
        created_page_id=page.get("id"),
        created_page_ws_url=page.get("webSocketDebuggerUrl", ""),
        temp_profile_dir=temp_profile_dir,
    )


def detect_outlook_state(session: CDPSession) -> dict[str, str]:
    expr = f"""(() => {{
      const search = document.querySelector({json.dumps(SEARCH_INPUT_SELECTOR)});
      const body = document.body ? document.body.innerText : '';
      if (search) return JSON.stringify({{state: 'ready'}});
      if ({json.dumps(list(LOGIN_MARKERS))}.some(marker => body.toLowerCase().includes(marker.toLowerCase()))) {{
        return JSON.stringify({{state: 'login'}});
      }}
      if ({json.dumps(list(HANDOFF_MARKERS))}.some(marker => body.toLowerCase().includes(marker.toLowerCase()))) {{
        return JSON.stringify({{state: 'handoff'}});
      }}
      return JSON.stringify({{state: 'loading', sample: body.slice(0, 240)}});
    }})()"""
    return session.evaluate_json(expr, timeout=10.0) or {"state": "loading"}


def ensure_outlook_ready(session: CDPSession) -> None:
    session.navigate(OUTLOOK_ENTRY_URL)
    end = time.time() + 25.0
    while time.time() < end:
        state = detect_outlook_state(session)
        if state["state"] == "ready":
            return
        if state["state"] in {"login", "handoff"}:
            raise OutlookReplyError(
                "Outlook needs an interactive sign-in step.",
                handoff_required=True,
            )
        time.sleep(0.75)
    raise OutlookReplyError(
        f"Outlook did not load the mailbox view in time. Last state: {state!r}"
    )


def warm_up_mail_view(seconds: float = DEFAULT_SEARCH_WARMUP) -> None:
    # Outlook Web often renders the mailbox before its search handlers are ready.
    time.sleep(seconds)


def search_outlook(session: CDPSession, query: str) -> list[SearchItem]:
    expr = f"""(() => {{
      const input = document.querySelector({json.dumps(SEARCH_INPUT_SELECTOR)});
      if (!input) return JSON.stringify({{ok: false, reason: 'search input not found'}});
      const setValue = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setValue.call(input, {json.dumps(query)});
      input.dispatchEvent(new Event('input', {{ bubbles: true }}));
      input.dispatchEvent(new Event('change', {{ bubbles: true }}));
      input.focus();
      return JSON.stringify({{ok: true, query: input.value}});
    }})()"""
    result = session.evaluate_json(expr, timeout=10.0)
    if not result or not result.get("ok"):
        raise OutlookReplyError("Could not submit the Outlook search query.")
    press_enter(session)

    end = time.time() + 12.0
    last_body = ""
    while time.time() < end:
        items = get_search_items(session)
        if items:
            return items
        last_body = session.body_text(2500)
        if "未找到任何结果" in last_body or "No results" in last_body:
            return []
        time.sleep(0.75)
    return get_search_items(session)


def get_search_items(session: CDPSession) -> list[SearchItem]:
    expr = """(() => JSON.stringify(
      [...document.querySelectorAll('[role="option"]')].map((el, index) => ({
        index,
        aria: el.getAttribute('aria-label') || '',
        text: (el.innerText || '').trim(),
      })).slice(0, 50)
    ))()"""
    payload = session.evaluate_json(expr, timeout=10.0) or []
    return [SearchItem(**item) for item in payload]


def press_enter(session: CDPSession) -> None:
    base = {
        "key": "Enter",
        "code": "Enter",
        "windowsVirtualKeyCode": 13,
        "nativeVirtualKeyCode": 13,
    }
    session.call("Input.dispatchKeyEvent", {"type": "keyDown", **base}, timeout=5.0)
    session.call("Input.dispatchKeyEvent", {"type": "keyUp", **base}, timeout=5.0)


def choose_search_item(
    items: list[SearchItem],
    *,
    subject: str,
    counterparty: Optional[str],
    folder: str,
    attachment_names: Optional[list[str]] = None,
) -> SearchItem:
    subject_key = normalize(subject)
    counterparty_key = normalize(counterparty or "")
    wanted_folder_markers = SENT_MARKERS if folder == "sent" else INBOX_MARKERS
    excluded_markers = () if folder == "sent" else SENT_MARKERS + DRAFT_MARKERS

    scored: list[tuple[float, SearchItem]] = []
    for item in items:
        blob = item.blob
        if subject_key and subject_key not in blob:
            continue
        if excluded_markers and any(marker in blob for marker in excluded_markers):
            continue
        score = 0.0
        if any(marker in blob for marker in wanted_folder_markers):
            score += 4.0
        if counterparty_key and counterparty_key in blob:
            score += 6.0
        if attachment_names:
            for name in attachment_names:
                if normalize(name) in blob:
                    score += 1.0
        score += max(0.0, 3.0 - item.index * 0.1)
        scored.append((score, item))
    if not scored:
        raise OutlookReplyError(
            f"Could not find a {folder} search result for subject {subject!r}."
        )
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


def open_search_item(session: CDPSession, item: SearchItem, subject: str) -> None:
    expr = f"""(() => {{
      const items = [...document.querySelectorAll('[role="option"]')];
      const target = items[{item.index}];
      if (!target) return false;
      target.scrollIntoView({{ block: 'center' }});
      target.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
      target.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true }}));
      target.click();
      return true;
    }})()"""
    if not session.evaluate(expr, timeout=10.0):
        raise OutlookReplyError("Found the search result, but could not open it.")
    subject_key = normalize(subject)
    session.wait_for(
        f"""(() => {{
          const body = document.body ? document.body.innerText.toLowerCase() : '';
          return body.includes({json.dumps(subject_key)});
        }})()""",
        timeout=15.0,
    )


def reply_compose_open(session: CDPSession) -> bool:
    expr = f"""(() => {{
      const box = document.querySelector({json.dumps(EDITOR_SELECTOR)});
      const sendButton = [...document.querySelectorAll('button,[role="button"]')].find(el => {{
        const aria = el.getAttribute('aria-label') || '';
        const title = el.getAttribute('title') || '';
        return {json.dumps(list(SEND_LABELS))}.includes(aria) || {json.dumps(list(SEND_LABELS))}.some(label => title.includes(label));
      }});
      return Boolean(box && sendButton);
    }})()"""
    return bool(session.evaluate(expr, timeout=10.0))


def open_reply_compose(session: CDPSession) -> None:
    if reply_compose_open(session):
        return
    expr = f"""(() => {{
      const labels = {json.dumps(list(REPLY_LABELS))};
      const button = [...document.querySelectorAll('button,[role="button"]')].find(el => {{
        const aria = (el.getAttribute('aria-label') || '').trim();
        return labels.includes(aria);
      }});
      if (!button) return false;
      button.click();
      return true;
    }})()"""
    if not session.evaluate(expr, timeout=10.0):
        raise OutlookReplyError("Could not find Outlook's native Reply button.")
    session.wait_for(
        f"Boolean(document.querySelector({json.dumps(EDITOR_SELECTOR)}))",
        timeout=15.0,
    )
    session.wait_for(
        f"""(() => [...document.querySelectorAll('button,[role="button"]')].some(el => {{
          const aria = (el.getAttribute('aria-label') || '').trim();
          const title = el.getAttribute('title') || '';
          return {json.dumps(list(SEND_LABELS))}.includes(aria) || {json.dumps(list(SEND_LABELS))}.some(label => title.includes(label));
        }}))()""",
        timeout=15.0,
    )


def open_new_compose(session: CDPSession) -> None:
    expr = f"""(() => {{
      const labels = {json.dumps(list(NEW_MAIL_LABELS))};
      const button = [...document.querySelectorAll('button,[role="button"]')].find(el => {{
        const aria = (el.getAttribute('aria-label') || '').trim();
        return labels.includes(aria);
      }});
      if (!button) return false;
      button.click();
      return true;
    }})()"""
    if not session.evaluate(expr, timeout=10.0):
        raise OutlookReplyError("Could not find Outlook's New mail button.")
    session.wait_for(
        """(() => Boolean(
          document.querySelector('div[contenteditable="true"][aria-label="收件人"], div[contenteditable="true"][aria-label="To"]') &&
          document.querySelector('input[aria-label="主题"], input[aria-label="Subject"]') &&
          document.querySelector('div[role="textbox"][aria-label*="正文"], div[role="textbox"][aria-label*="body"], div[role="textbox"][aria-label*="Body"]')
        ))()""",
        timeout=15.0,
    )


def fill_compose_recipient(session: CDPSession, to_email: str) -> str:
    expr = f"""(() => {{
      const field = document.querySelector('div[contenteditable="true"][aria-label="收件人"], div[contenteditable="true"][aria-label="To"]');
      if (!field) return JSON.stringify({{ok: false, reason: 'recipient field not found'}});
      field.focus();
      document.execCommand('selectAll', false);
      document.execCommand('delete', false);
      document.execCommand('insertText', false, {json.dumps(to_email)});
      field.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: {json.dumps(to_email)} }}));
      return JSON.stringify({{ok: true, preview: field.innerText}});
    }})()"""
    result = session.evaluate_json(expr, timeout=10.0)
    if not result or not result.get("ok"):
        raise OutlookReplyError("Could not fill the recipient field.")
    press_enter(session)
    session.wait_for(
        f"""(() => {{
          const field = document.querySelector('div[contenteditable="true"][aria-label="收件人"], div[contenteditable="true"][aria-label="To"]');
          const body = document.body ? document.body.innerText : '';
          return body.includes({json.dumps(to_email)}) || (field && field.innerText.includes({json.dumps(to_email)}));
        }})()""",
        timeout=8.0,
    )
    return result.get("preview", "")


def fill_compose_subject(session: CDPSession, subject: str) -> str:
    expr = f"""(() => {{
      const input = document.querySelector('input[aria-label="主题"], input[aria-label="Subject"]');
      if (!input) return JSON.stringify({{ok: false, reason: 'subject input not found'}});
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, {json.dumps(subject)});
      input.dispatchEvent(new Event('input', {{ bubbles: true }}));
      input.dispatchEvent(new Event('change', {{ bubbles: true }}));
      return JSON.stringify({{ok: true, value: input.value}});
    }})()"""
    result = session.evaluate_json(expr, timeout=10.0)
    if not result or not result.get("ok"):
        raise OutlookReplyError("Could not fill the subject field.")
    return result.get("value", "")


def fill_reply_body(session: CDPSession, body: str) -> str:
    expr = f"""(() => {{
      const box = document.querySelector({json.dumps(EDITOR_SELECTOR)});
      if (!box) return JSON.stringify({{ok: false, reason: 'editor not found'}});
      box.focus();
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(box);
      selection.removeAllRanges();
      selection.addRange(range);
      document.execCommand('selectAll', false);
      document.execCommand('delete', false);
      document.execCommand('insertText', false, {json.dumps(body)});
      box.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: {json.dumps(body)} }}));
      return JSON.stringify({{ok: true, preview: box.innerText}});
    }})()"""
    result = session.evaluate_json(expr, timeout=15.0)
    if not result or not result.get("ok"):
        raise OutlookReplyError("Could not write the reply body into Outlook Web.")
    preview = result.get("preview", "")
    if normalize(body.splitlines()[0]) not in normalize(preview):
        raise OutlookReplyError("Outlook Web did not keep the reply body that was inserted.")
    return preview


def attach_files(session: CDPSession, files: list[str]) -> list[str]:
    if not files:
        return []
    names = [pathlib.Path(path).name for path in files]
    node_ids = session.query_file_inputs()
    if not node_ids:
        raise OutlookReplyError("Outlook did not expose any local file input fields.")
    for node_id in node_ids:
        session.set_files(node_id, files)
        try:
            session.wait_for(
                f"""(() => {{
                  const body = document.body ? document.body.innerText : '';
                  return {json.dumps(names)}.every(name => body.includes(name));
                }})()""",
                timeout=15.0,
            )
            body = session.body_text(5000)
            if "未插入下列文件" in body or "were not inserted" in body:
                continue
            return names
        except OutlookReplyError:
            continue
    raise OutlookReplyError("Outlook did not show the selected attachments after upload.")


def click_send(session: CDPSession) -> None:
    expr = f"""(() => {{
      const labels = {json.dumps(list(SEND_LABELS))};
      const button = [...document.querySelectorAll('button,[role="button"]')].find(el => {{
        const aria = (el.getAttribute('aria-label') || '').trim();
        const title = el.getAttribute('title') || '';
        return labels.includes(aria) || labels.some(label => title.includes(label));
      }});
      if (!button) return false;
      button.click();
      return true;
    }})()"""
    if not session.evaluate(expr, timeout=10.0):
        raise OutlookReplyError("Could not find Outlook's Send button.")
    session.wait_for(
        f"!document.querySelector({json.dumps(EDITOR_SELECTOR)})",
        timeout=20.0,
    )


def discard_draft(session: CDPSession) -> None:
    expr = f"""(() => {{
      const labels = {json.dumps(list(DISCARD_LABELS))};
      const button = [...document.querySelectorAll('button,[role="button"]')].find(el => {{
        const aria = (el.getAttribute('aria-label') || '').trim();
        const title = el.getAttribute('title') || '';
        return labels.includes(aria) || labels.some(label => title.includes(label));
      }});
      if (!button) return false;
      button.click();
      return true;
    }})()"""
    session.evaluate(expr, timeout=10.0)


def browser_verify(
    session: CDPSession,
    *,
    to_email: str,
    subject: str,
    attachment_names: list[str],
) -> dict[str, Any]:
    queries = [
        f'to:{to_email} "{subject}"',
        f'"{subject}" {to_email}',
        subject,
    ]
    last_error = "No sent result matched."
    for query in queries:
        items = search_outlook(session, query)
        if not items:
            last_error = f"No results for query {query!r}."
            continue
        try:
            candidate = choose_sent_result(items, subject, attachment_names)
        except OutlookReplyError as exc:
            last_error = str(exc)
            continue
        if attachment_names and not all(
            normalize(name) in candidate.blob for name in attachment_names
        ):
            open_search_item(session, candidate, subject)
            body = session.body_text(5000)
            if not all(name in body for name in attachment_names):
                last_error = "Found a sent item, but attachment names did not match."
                continue
        return {
            "query": query,
            "result_index": candidate.index,
            "preview": candidate.text[:240],
            "attachments": attachment_names,
        }
    raise OutlookReplyError(last_error)


def choose_sent_result(
    items: list[SearchItem], subject: str, attachment_names: list[str]
) -> SearchItem:
    subject_key = normalize(subject)
    scored: list[tuple[float, SearchItem]] = []
    for item in items:
        blob = item.blob
        if subject_key and subject_key not in blob:
            continue
        if any(marker in blob for marker in DRAFT_MARKERS):
            continue
        score = 0.0
        if any(marker in blob for marker in SENT_MARKERS):
            score += 6.0
        for name in attachment_names:
            if normalize(name) in blob:
                score += 2.0
        score += max(0.0, 3.0 - item.index * 0.1)
        scored.append((score, item))
    if not scored:
        raise OutlookReplyError(
            f"Could not find a sent search result for subject {subject!r}."
        )
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


def cmd_doctor(args: argparse.Namespace) -> int:
    debug_info = debug_endpoint_info(args.port)
    cookies = collect_cookie_payloads()
    result = {
        "ok": bool(chrome_is_available() and websocket is not None and browser_cookie3 is not None),
        "command": "doctor",
        "checks": {
            "chrome_available": chrome_is_available(),
            "debug_endpoint_active": bool(debug_info),
            "debug_browser": debug_info.get("Browser") if debug_info else None,
            "python_imports": {
                "browser_cookie3": browser_cookie3 is not None,
                "websocket_client": websocket is not None,
            },
            "cookie_candidates": len(cookies),
        },
    }
    print_json(result)
    return 0 if result["ok"] else 1


def cmd_reply(args: argparse.Namespace) -> int:
    received_after = parse_hint(args.received_after)
    attachments = ensure_attachments(args.attachment or [])
    body = ensure_non_empty_stdin()

    browser = ensure_browser(args.port)
    session = CDPSession(browser.created_page_ws_url)
    compose_open = False
    try:
        imported = import_cookies(session, collect_cookie_payloads())
        ensure_outlook_ready(session)
        warm_up_mail_view()
        items = []
        queries = [
            f'from:{args.from_email} "{args.subject}"',
            f'"{args.subject}" {args.from_email}',
            args.subject,
        ]
        for query in queries:
            items = search_outlook(session, query)
            if items:
                try:
                    candidate = choose_search_item(
                        items,
                        subject=args.subject,
                        counterparty=args.from_email,
                        folder="inbox",
                    )
                    break
                except OutlookReplyError:
                    continue
        else:
            raise OutlookReplyError(
                f"Could not find the original inbox message for subject {args.subject!r}."
            )

        open_search_item(session, candidate, args.subject)
        open_reply_compose(session)
        compose_open = True
        fill_reply_body(session, body)
        attached_names = attach_files(session, attachments)
        click_send(session)
        verification = browser_verify(
            session,
            to_email=args.from_email,
            subject=args.subject,
            attachment_names=attached_names,
        )
        print_json(
            {
                "ok": True,
                "command": "reply",
                "path": "browser",
                "to": args.from_email,
                "subject": args.subject,
                "received_after_hint": received_after,
                "attachments": attached_names,
                "cookies_imported": imported,
                "sent_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "verification": verification,
            }
        )
        return 0
    except OutlookReplyError as exc:
        if compose_open:
            try:
                discard_draft(session)
            except Exception:
                pass
        if exc.handoff_required:
            browser.keep_open_for_handoff = True
        print_json(
            {
                "ok": False,
                "command": "reply",
                "handoff_required": exc.handoff_required,
                "error": str(exc),
            }
        )
        return 1
    finally:
        session.close()
        browser.cleanup()


def cmd_verify(args: argparse.Namespace) -> int:
    after_hint = parse_hint(args.after)
    browser = ensure_browser(args.port)
    session = CDPSession(browser.created_page_ws_url)
    try:
        imported = import_cookies(session, collect_cookie_payloads())
        ensure_outlook_ready(session)
        warm_up_mail_view()
        verification = browser_verify(
            session,
            to_email=args.to,
            subject=args.subject,
            attachment_names=args.attachment_name or [],
        )
        print_json(
            {
                "ok": True,
                "command": "verify",
                "to": args.to,
                "subject": args.subject,
                "after_hint": after_hint,
                "attachment_names": args.attachment_name or [],
                "cookies_imported": imported,
                "verification": verification,
            }
        )
        return 0
    except OutlookReplyError as exc:
        if exc.handoff_required:
            browser.keep_open_for_handoff = True
        print_json(
            {
                "ok": False,
                "command": "verify",
                "handoff_required": exc.handoff_required,
                "error": str(exc),
            }
        )
        return 1
    finally:
        session.close()
        browser.cleanup()


def cmd_compose(args: argparse.Namespace) -> int:
    attachments = ensure_attachments(args.attachment or [])
    body = ensure_non_empty_stdin()

    browser = ensure_browser(args.port)
    session = CDPSession(browser.created_page_ws_url)
    compose_open = False
    try:
        imported = import_cookies(session, collect_cookie_payloads())
        ensure_outlook_ready(session)
        warm_up_mail_view()
        open_new_compose(session)
        compose_open = True
        fill_compose_recipient(session, args.to)
        fill_compose_subject(session, args.subject)
        fill_reply_body(session, body)
        attached_names = attach_files(session, attachments)
        click_send(session)
        verification = browser_verify(
            session,
            to_email=args.to,
            subject=args.subject,
            attachment_names=attached_names,
        )
        print_json(
            {
                "ok": True,
                "command": "compose",
                "path": "browser",
                "to": args.to,
                "subject": args.subject,
                "attachments": attached_names,
                "cookies_imported": imported,
                "sent_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "verification": verification,
            }
        )
        return 0
    except OutlookReplyError as exc:
        if compose_open:
            try:
                discard_draft(session)
            except Exception:
                pass
        if exc.handoff_required:
            browser.keep_open_for_handoff = True
        print_json(
            {
                "ok": False,
                "command": "compose",
                "handoff_required": exc.handoff_required,
                "error": str(exc),
            }
        )
        return 1
    finally:
        session.close()
        browser.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Browser fallback for Outlook replies with attachments."
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Chrome debugging port")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local prerequisites")
    doctor.set_defaults(func=cmd_doctor)

    reply = subparsers.add_parser("reply", help="Reply in Outlook Web with attachments")
    reply.add_argument("--from-email", required=True, help="Original sender email")
    reply.add_argument("--subject", required=True, help="Exact subject of the original email")
    reply.add_argument(
        "--received-after",
        required=True,
        help="Freshness hint in YYYY-MM-DD or ISO datetime format",
    )
    reply.add_argument(
        "--attachment",
        action="append",
        help="Absolute local file path to attach. Repeat for multiple files.",
    )
    reply.set_defaults(func=cmd_reply)

    verify = subparsers.add_parser("verify", help="Verify a sent reply in Outlook Web")
    verify.add_argument("--to", required=True, help="Reply recipient email")
    verify.add_argument("--subject", required=True, help="Exact subject to search")
    verify.add_argument(
        "--attachment-name",
        action="append",
        help="Expected attachment filename. Repeat for multiple files.",
    )
    verify.add_argument(
        "--after",
        required=True,
        help="Freshness hint in YYYY-MM-DD or ISO datetime format",
    )
    verify.set_defaults(func=cmd_verify)

    compose = subparsers.add_parser("compose", help="Compose a new Outlook Web message")
    compose.add_argument("--to", required=True, help="Recipient email")
    compose.add_argument("--subject", required=True, help="Subject line")
    compose.add_argument(
        "--attachment",
        action="append",
        help="Absolute local file path to attach. Repeat for multiple files.",
    )
    compose.set_defaults(func=cmd_compose)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except OutlookReplyError as exc:
        print_json(
            {
                "ok": False,
                "command": getattr(args, "command", None),
                "handoff_required": exc.handoff_required,
                "error": str(exc),
            }
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
