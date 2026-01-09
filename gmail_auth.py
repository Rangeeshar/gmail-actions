"""
Gmail API authentication module using OAuth2
"""

import os
import pickle
from typing import Any

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import CREDENTIALS_FILE, SCOPES, TOKEN_FILE


class GmailAuthenticator:
    """Handles Gmail API authentication"""

    def __init__(self):
        self.service = None
        self.creds = None

    def authenticate(self) -> Any:
        """Authenticate and create Gmail service"""
        # Load existing token if available
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                self.creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Credentials file '{CREDENTIALS_FILE}' not found. "
                        "Please download it from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(self.creds, token)

        self.service = build("gmail", "v1", credentials=self.creds)
        return self.service

    def get_service(self) -> Any:
        """Get the Gmail service instance"""
        if not self.service:
            self.authenticate()
        return self.service
