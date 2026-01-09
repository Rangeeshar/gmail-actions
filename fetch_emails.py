"""
Script to fetch emails from Gmail and store them in the database
"""

import base64
from datetime import datetime
from typing import Dict

from database import EmailDatabase
from gmail_auth import GmailAuthenticator

from config import MAX_EMAILS_TO_FETCH


def decode_message_body(message_data: Dict) -> str:
    """Decode the message body from Gmail API response"""
    body = ""
    if "parts" in message_data:
        for part in message_data["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    body += base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="ignore"
                    )
            elif part["mimeType"] == "text/html" and not body:
                data = part["body"].get("data", "")
                if data:
                    body += base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="ignore"
                    )
    elif "body" in message_data and "data" in message_data["body"]:
        data = message_data["body"]["data"]
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return body


def parse_email_headers(headers: list) -> Dict[str, str]:
    """Parse email headers into a dictionary"""
    header_dict = {}
    for header in headers:
        header_dict[header["name"].lower()] = header["value"]
    return header_dict


def fetch_emails() -> None:
    """Main function to fetch emails from Gmail and store in database"""
    print("Authenticating with Gmail API...")
    authenticator = GmailAuthenticator()
    service = authenticator.authenticate()

    print("Initializing database...")
    db = EmailDatabase()

    print("Fetching emails from inbox...")
    try:
        # Get list of messages
        # pylint: disable=no-member
        results = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=MAX_EMAILS_TO_FETCH)
            .execute()
        )

        messages = results.get("messages", [])
        print(f"Found {len(messages)} messages to process")

        if not messages:
            print("No messages found in inbox.")
            return

        # Fetch details for each message
        for i, message in enumerate(messages, 1):
            try:
                # pylint: disable=no-member
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="full")
                    .execute()
                )

                # Parse headers
                headers = parse_email_headers(msg["payload"].get("headers", []))

                # Extract email data
                email_data = {
                    "id": msg["id"],
                    "thread_id": msg.get("threadId", ""),
                    "from": headers.get("from", ""),
                    "to": headers.get("to", ""),
                    "subject": headers.get("subject", ""),
                    "message_body": decode_message_body(msg["payload"]),
                    "received_date": datetime.fromtimestamp(
                        int(msg["internalDate"]) / 1000
                    ).isoformat()
                    if "internalDate" in msg
                    else datetime.now().isoformat(),
                    "is_read": "UNREAD" not in msg.get("labelIds", []),
                    "labels": msg.get("labelIds", []),
                    "raw_data": msg,
                }

                # Store in database
                db.insert_email(email_data)
                print(
                    f"Processed email {i}/{len(messages)}: {email_data['subject'][:50]}"
                )

            except (KeyError, ValueError, AttributeError) as e:
                print(f"Error processing message {message['id']}: {e}")
                continue

        print(f"\nSuccessfully stored {len(messages)} emails in database.")

    except (KeyError, ValueError, AttributeError, OSError) as e:
        print(f"Error fetching emails: {e}")
        raise


if __name__ == "__main__":
    fetch_emails()
