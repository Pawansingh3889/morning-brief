"""Gmail API OAuth flow, read-only scope only."""
from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def gmail_service(credentials_file: Path, token_file: Path):
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_file), SCOPES
            )
            creds = _run_flow(flow)
        token_file.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def _run_flow(flow: InstalledAppFlow):
    # On WSL the browser on Windows cannot reliably reach a server bound
    # inside WSL, so skip straight to the paste-the-URL manual flow.
    if not _is_wsl():
        try:
            return flow.run_local_server(port=0, timeout_seconds=60)
        except Exception:
            pass
    return _manual_flow(flow)


def _manual_flow(flow: InstalledAppFlow):
    flow.redirect_uri = "http://localhost:1/"
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    print("\nManual OAuth flow:")
    print("  1. Open this URL in your browser and approve the scope:\n")
    print(f"     {auth_url}\n")
    print("  2. Browser will land on a 'site can't be reached' page at localhost:1.")
    print("  3. Copy the full URL from the address bar (contains ?code=...&state=...).")
    response_url = input("\nPaste the full redirect URL here: ").strip()
    # oauthlib blocks http:// redirects by default. We intentionally use
    # http://localhost:1/ as a throwaway desktop redirect that the browser
    # fails to reach. Opt in to relax the check for this fetch only.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    try:
        flow.fetch_token(authorization_response=response_url)
    finally:
        os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)
    return flow.credentials
