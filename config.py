"""
Configuration file for Gmail Actions application
"""

import os

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "gmail_actions.db")

# Gmail API configuration
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
]
CREDENTIALS_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

# Email fetch configuration
MAX_EMAILS_TO_FETCH = 100  # Set to None to fetch all emails
