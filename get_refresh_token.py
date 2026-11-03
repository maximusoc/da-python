"""One-time helper: log in as yourself and print a refresh token.

Register http://localhost:8080/callback as a redirect URI in your DeviantArt app first.
"""
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = "https://www.deviantart.com/oauth2/authorize"
TOKEN_URL = "https://www.deviantart.com/oauth2/token"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "browse user stash publish"


class Handler(BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        Handler.code = parse_qs(urlparse(self.path).query).get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Done. You can close this tab.")

    def log_message(self, *args):
        pass


def main():
    client_id = os.environ["DA_CLIENT_ID"]
    client_secret = os.environ["DA_CLIENT_SECRET"]

    url = AUTH_URL + "?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        }
    )
    webbrowser.open(url)
    HTTPServer(("localhost", 8080), Handler).handle_request()

    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": Handler.code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    r.raise_for_status()
    print("DA_REFRESH_TOKEN =", r.json()["refresh_token"])


if __name__ == "__main__":
    main()
