"""Desktop Google OAuth and OS-backed refresh-token storage for DriveDesk."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Lock

import keyring
from PyQt6.QtCore import QSettings


SERVICE = "DriveDesk Google Drive"
SCOPE = "https://www.googleapis.com/auth/drive"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_CLIENT_ID = "912215158408-b0d65vcera70u4jh91jv1um8s1p3deoo.apps.googleusercontent.com"


class GoogleAuthError(RuntimeError):
    pass


def _token_request(values: dict[str, str]) -> dict:
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(values).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            code = json.load(exc).get("error", "authorization_failed")
        except (ValueError, OSError):
            code = "authorization_failed"
        raise GoogleAuthError(f"Google authorization failed: {code}") from exc
    except OSError as exc:
        raise GoogleAuthError(f"Google authorization connection failed: {exc}") from exc


class NativeGoogleAuth:
    """Account metadata stays in settings; refresh tokens stay in the OS vault."""

    def __init__(self):
        self.settings = QSettings("DriveDesk", "DriveDesk")
        self._cache: dict[str, tuple[str, float]] = {}
        self._lock = Lock()

    def accounts(self) -> list[dict[str, str]]:
        raw = self.settings.value("native_google/accounts", "[]")
        try:
            values = json.loads(raw)
            return [value for value in values if isinstance(value, dict) and
                    all(key in value for key in ("id", "name", "email", "client_id"))]
        except (TypeError, ValueError):
            return []

    def _save(self, accounts: list[dict[str, str]]):
        self.settings.setValue("native_google/accounts", json.dumps(accounts))

    def client_id(self) -> str:
        return str(self.settings.value("native_google/client_id", DEFAULT_CLIENT_ID) or DEFAULT_CLIENT_ID)

    def set_client_id(self, client_id: str):
        client_id = client_id.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.apps\.googleusercontent\.com", client_id):
            raise GoogleAuthError("Enter a Google Desktop OAuth client ID ending in .apps.googleusercontent.com.")
        self.settings.setValue("native_google/client_id", client_id)

    def connect(self, cancelled: Event, *, expected_remote: str = "") -> str:
        client_id = self.client_id()
        if not client_id:
            raise GoogleAuthError("Set a Google Desktop OAuth client ID first.")
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
        result: dict[str, str] = {}

        class Callback(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlsplit(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                if parsed.path != "/oauth2/callback" or query.get("state", [""])[0] != state:
                    self.send_error(400, "Invalid authorization response")
                    return
                result["code"] = query.get("code", [""])[0]
                result["error"] = query.get("error", [""])[0]
                body = b"<html><body><h2>DriveDesk sign-in received</h2><p>You can close this tab and return to DriveDesk.</p></body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                pass

        with HTTPServer(("127.0.0.1", 0), Callback) as server:
            server.timeout = 0.5
            redirect = f"http://127.0.0.1:{server.server_port}/oauth2/callback"
            params = {
                "client_id": client_id, "redirect_uri": redirect, "response_type": "code",
                "scope": SCOPE, "access_type": "offline", "prompt": "consent",
                "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
            }
            url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
            if not webbrowser.open(url):
                raise GoogleAuthError("Could not open the browser for Google sign-in.")
            deadline = time.monotonic() + 300
            while not result and not cancelled.is_set() and time.monotonic() < deadline:
                server.handle_request()
        if cancelled.is_set():
            raise GoogleAuthError("Sign-in was cancelled.")
        if result.get("error"):
            raise GoogleAuthError(f"Google sign-in was declined: {result['error']}")
        if not result.get("code"):
            raise GoogleAuthError("Google sign-in timed out. Try again.")
        token = _token_request({
            "client_id": client_id, "redirect_uri": redirect,
            "grant_type": "authorization_code", "code": result["code"],
            "code_verifier": verifier,
        })
        access = token.get("access_token", "")
        refresh = token.get("refresh_token", "")
        if not access or not refresh:
            raise GoogleAuthError("Google did not return offline access. Reconnect and grant Drive access.")
        about = urllib.request.Request(
            "https://www.googleapis.com/drive/v3/about?fields=user(permissionId,displayName,emailAddress)",
            headers={"Authorization": f"Bearer {access}"},
        )
        try:
            with urllib.request.urlopen(about, timeout=30) as response:
                user = (json.load(response).get("user") or {})
        except (OSError, ValueError) as exc:
            raise GoogleAuthError("Could not verify the connected Google account.") from exc
        permission_id = user.get("permissionId", "")
        if not permission_id:
            raise GoogleAuthError("Google did not identify the connected Drive account.")
        remote = "native:" + permission_id
        if expected_remote and remote != expected_remote:
            raise GoogleAuthError("Choose the same Google account to reconnect this connection.")
        try:
            keyring.set_password(SERVICE, remote, refresh)
        except keyring.errors.KeyringError as exc:
            raise GoogleAuthError("Could not save Google access in the system credential store.") from exc
        accounts = [account for account in self.accounts() if account["id"] != remote]
        accounts.append({"id": remote, "name": user.get("displayName") or "Google Drive",
                         "email": user.get("emailAddress") or "", "client_id": client_id})
        self._save(accounts)
        with self._lock:
            self._cache[remote] = (access, time.monotonic() + max(0, int(token.get("expires_in", 3600)) - 60))
        return remote

    def access_token(self, remote: str, *, force: bool = False) -> str:
        with self._lock:
            cached = self._cache.get(remote)
            if cached and cached[1] > time.monotonic() and not force:
                return cached[0]
            account = next((item for item in self.accounts() if item["id"] == remote), None)
            if not account:
                raise GoogleAuthError("This Google account is no longer connected.")
            try:
                refresh = keyring.get_password(SERVICE, remote)
            except keyring.errors.KeyringError as exc:
                raise GoogleAuthError("Could not read Google access from the system credential store.") from exc
            if not refresh:
                raise GoogleAuthError("Google access is missing. Reconnect this account.")
            token = _token_request({"client_id": account["client_id"],
                                    "grant_type": "refresh_token", "refresh_token": refresh})
            access = token.get("access_token", "")
            if not access:
                raise GoogleAuthError("Google did not return an access token. Reconnect this account.")
            self._cache[remote] = (access, time.monotonic() + max(0, int(token.get("expires_in", 3600)) - 60))
            return access

    def remove(self, remote: str):
        try:
            keyring.delete_password(SERVICE, remote)
        except keyring.errors.PasswordDeleteError:
            pass
        except keyring.errors.KeyringError as exc:
            raise GoogleAuthError("Could not remove Google access from the system credential store.") from exc
        self._save([account for account in self.accounts() if account["id"] != remote])
        with self._lock:
            self._cache.pop(remote, None)
