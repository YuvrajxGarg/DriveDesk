import io
import json
import threading
import unittest
import urllib.parse
import urllib.request
from threading import Event
from unittest.mock import patch

import google_auth


class FakeSettings:
    values = {}

    def __init__(self, *_args):
        pass

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class GoogleAuthTests(unittest.TestCase):
    def setUp(self):
        FakeSettings.values = {}

    def test_desktop_sign_in_validates_state_and_stores_refresh_in_keyring(self):
        stored = {}
        original_open = urllib.request.urlopen

        def fake_open(request, timeout=30):
            url = request.full_url if hasattr(request, "full_url") else request
            if url.startswith("http://127.0.0.1:"):
                return original_open(request, timeout=timeout)
            if url.endswith("/token"):
                return Response(json.dumps({"access_token": "access", "refresh_token": "refresh",
                                            "expires_in": 3600}).encode())
            if "drive/v3/about" in url:
                return Response(json.dumps({"user": {"permissionId": "123", "displayName": "Alex",
                                                     "emailAddress": "alex@example.com"}}).encode())
            raise AssertionError(url)

        callback_threads = []
        def fake_browser(url):
            params = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            self.assertEqual(params["code_challenge_method"], ["S256"])
            self.assertEqual(params["scope"], [google_auth.SCOPE])
            redirect = params["redirect_uri"][0]
            callback = redirect + "?" + urllib.parse.urlencode({"state": params["state"][0], "code": "auth-code"})
            thread = threading.Thread(target=lambda: fake_open(callback).close())
            thread.start()
            callback_threads.append(thread)
            return True

        with patch.object(google_auth, "QSettings", FakeSettings), \
             patch.object(google_auth.webbrowser, "open", side_effect=fake_browser), \
             patch.object(google_auth.urllib.request, "urlopen", side_effect=fake_open), \
             patch.object(google_auth.keyring, "set_password", side_effect=lambda service, user, secret: stored.update({user: secret})), \
             patch.object(google_auth.keyring, "get_password", side_effect=lambda service, user: stored.get(user)):
            auth = google_auth.NativeGoogleAuth()
            remote = auth.connect(Event())
            self.assertEqual(remote, "native:123")
            self.assertEqual(stored[remote], "refresh")
            self.assertEqual(auth.accounts()[0]["email"], "alex@example.com")
            self.assertEqual(auth.access_token(remote), "access")
        for thread in callback_threads:
            thread.join(timeout=2)

    def test_client_id_validation(self):
        with patch.object(google_auth, "QSettings", FakeSettings):
            auth = google_auth.NativeGoogleAuth()
            with self.assertRaises(google_auth.GoogleAuthError):
                auth.set_client_id("not-a-client-id")
