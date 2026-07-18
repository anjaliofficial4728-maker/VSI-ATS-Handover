# app/services/google_oauth_service.py
"""
Google OAuth service.

Responsibilities:
- Build the Google authorization URL (the "Connect Google" link).
- Exchange the authorization code for OAuth credentials.
- Encrypt and store those credentials in Supabase.
- Load stored credentials back and refresh them when expired.

This is the foundation for everything that talks to Google
(Forms API, Calendar API). Nothing Google-related works until a
token has been stored via this service.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleAuthRequest

from app.database import supabase
from app.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_OAUTH_SCOPES,
    GOOGLE_ACCOUNT_EMAIL,
    TOKEN_ENCRYPTION_KEY,
)


# Allow slight scope reordering / additions from Google without erroring.
# Google sometimes returns scopes in a different order or adds 'openid'.
import os
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


class GoogleOAuthService:
    """Handles the Google OAuth flow and token persistence."""

    # ---------- internal helpers ----------

    @staticmethod
    def _fernet() -> Fernet:
        """Build the Fernet cipher from the configured key."""
        if not TOKEN_ENCRYPTION_KEY:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY is not set. Generate one with "
                "`python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\"` and put it in .env"
            )
        return Fernet(TOKEN_ENCRYPTION_KEY.encode())

    @staticmethod
    def _client_config() -> dict:
        """
        Build the client config dict that google-auth-oauthlib expects,
        using the Client ID / Secret from config instead of a JSON file.
        """
        return {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        }

    @staticmethod
    def _credentials_to_dict(creds: Credentials) -> dict:
        """Serialize Credentials to a plain dict for encryption."""
        return {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }

    @staticmethod
    def _dict_to_credentials(data: dict) -> Credentials:
        """Rebuild Credentials from the stored dict."""
        return Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes"),
        )

    # ---------- authorization URL ----------

    @staticmethod
    def build_authorization_url() -> str:
        """
        Build the Google login URL that the user visits to grant access.

        access_type=offline + prompt=consent ensures we get a
        refresh_token, so we can keep reading data without the user
        having to log in again every hour.
        """
        flow = Flow.from_client_config(
            GoogleOAuthService._client_config(),
            scopes=GOOGLE_OAUTH_SCOPES,
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        # We build a fresh Flow in authorize AND in callback (stateless
        # server), so the PKCE code_verifier generated here would be lost
        # before the callback runs -> "Missing code verifier". We're a
        # confidential client (we have a client secret), so PKCE isn't
        # needed. Disabling it keeps the two steps independent.
        flow.autogenerate_code_verifier = False

        auth_url, _state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    # ---------- callback handling ----------

    @staticmethod
    def exchange_code_and_store(code: str) -> str:
        """
        Exchange the authorization code for credentials, then encrypt
        and store them in Supabase.

        Returns the account_email the token was stored under.
        """
        flow = Flow.from_client_config(
            GoogleOAuthService._client_config(),
            scopes=GOOGLE_OAUTH_SCOPES,
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        # Match the authorize step: no PKCE (confidential client).
        flow.autogenerate_code_verifier = False

        # This performs the token exchange with Google.
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Figure out which email this token belongs to. Prefer the
        # configured account; fall back to querying userinfo.
        account_email = GOOGLE_ACCOUNT_EMAIL or GoogleOAuthService._fetch_email(creds)

        GoogleOAuthService._store_credentials(account_email, creds)
        return account_email

    @staticmethod
    def _fetch_email(creds: Credentials) -> str:
        """Look up the email of the authorizing account via userinfo."""
        try:
            from googleapiclient.discovery import build
            service = build("oauth2", "v2", credentials=creds)
            info = service.userinfo().get().execute()
            return info.get("email", "unknown")
        except Exception:
            return "unknown"

    # ---------- persistence ----------

    @staticmethod
    def _store_credentials(account_email: str, creds: Credentials) -> None:
        """Encrypt and upsert the credentials for this account."""
        payload = json.dumps(GoogleOAuthService._credentials_to_dict(creds))
        encrypted = GoogleOAuthService._fernet().encrypt(payload.encode()).decode()

        now = datetime.now(timezone.utc).isoformat()
        scopes_str = " ".join(creds.scopes or [])

        # Upsert: update if this account already has a token, else insert.
        existing = (
            supabase.table("google_oauth_tokens")
            .select("id")
            .eq("account_email", account_email)
            .execute()
        )

        if existing.data:
            supabase.table("google_oauth_tokens").update({
                "encrypted_token": encrypted,
                "scopes": scopes_str,
                "updated_at": now,
            }).eq("account_email", account_email).execute()
        else:
            supabase.table("google_oauth_tokens").insert({
                "account_email": account_email,
                "encrypted_token": encrypted,
                "scopes": scopes_str,
                "created_at": now,
                "updated_at": now,
            }).execute()

    # ---------- loading credentials for API calls ----------

    @staticmethod
    def get_credentials(account_email: Optional[str] = None) -> Optional[Credentials]:
        """
        Load and return usable Credentials for the given account
        (defaults to the configured GOOGLE_ACCOUNT_EMAIL).

        Automatically refreshes the access token if it has expired,
        and re-stores the refreshed token.

        Returns None if no token is stored yet.
        """
        target = account_email or GOOGLE_ACCOUNT_EMAIL

        query = supabase.table("google_oauth_tokens").select("*")
        if target:
            query = query.eq("account_email", target)
        result = query.limit(1).execute()

        if not result.data:
            return None

        row = result.data[0]

        try:
            decrypted = GoogleOAuthService._fernet().decrypt(
                row["encrypted_token"].encode()
            ).decode()
            creds = GoogleOAuthService._dict_to_credentials(json.loads(decrypted))
        except Exception as e:
            print(f"[OAuth] Failed to decrypt stored token: {e}")
            return None

        # Refresh if expired and we have a refresh token.
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
                GoogleOAuthService._store_credentials(row["account_email"], creds)
            except Exception as e:
                print(f"[OAuth] Token refresh failed: {e}")
                return None

        return creds

    @staticmethod
    def is_connected(account_email: Optional[str] = None) -> bool:
        """True if we have usable credentials stored."""
        return GoogleOAuthService.get_credentials(account_email) is not None