"""
Rule processor module for evaluating email rules and executing actions
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from dateutil import parser as date_parser

from database import EmailDatabase
from gmail_auth import GmailAuthenticator


class RuleProcessor:
    """Processes emails based on rules and executes actions"""

    def __init__(self, rules_file: str = "rules.json"):
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self.db = EmailDatabase()
        self.gmail_service = None

    def _load_rules(self) -> List[Dict]:
        """Load rules from JSON file"""
        rules_file_path = self.rules_file
        try:
            with open(rules_file_path, "r", encoding="utf-8") as f:
                rules_data = json.load(f)
                return rules_data.get("rules", [])
        except FileNotFoundError:
            print(f"Rules file '{rules_file_path}' not found.")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing rules file: {e}")
            return []

    def _get_gmail_service(self) -> Any:
        """Get Gmail service instance"""
        if not self.gmail_service:
            authenticator = GmailAuthenticator()
            self.gmail_service = authenticator.get_service()
        return self.gmail_service

    def _evaluate_condition(self, email: Dict, condition: Dict) -> bool:
        """Evaluate a single condition against an email"""
        field = condition.get("field", "").lower()
        predicate = condition.get("predicate", "").lower()
        value = condition.get("value", "")

        # Get field value from email
        if field == "from":
            field_value = email.get("from_address", "")
        elif field == "to":
            field_value = email.get("to_address", "")
        elif field == "subject":
            field_value = email.get("subject", "")
        elif field == "message":
            field_value = email.get("message_body", "")
        elif field in ["received date", "received date/time", "date received"]:
            field_value = email.get("received_date", "")
        else:
            return False

        # Evaluate predicate for string fields
        if field in ["from", "to", "subject", "message"]:
            field_value_lower = str(field_value).lower()
            value_lower = str(value).lower()

            if predicate == "contains":
                return value_lower in field_value_lower
            elif predicate == "does not contain":
                return value_lower not in field_value_lower
            elif predicate == "equals":
                return field_value_lower == value_lower
            elif predicate == "does not equal":
                return field_value_lower != value_lower

        # Evaluate predicate for date field
        elif field in ["received date", "received date/time", "date received"]:
            try:
                email_date = date_parser.parse(str(field_value))

                # Parse value - can be "X days" or "X months"
                value_str = str(value).lower().strip()

                if "day" in value_str:
                    days = int(value_str.split()[0])
                    threshold_date = datetime.now() - timedelta(days=days)
                elif "month" in value_str:
                    months = int(value_str.split()[0])
                    threshold_date = datetime.now() - timedelta(days=months * 30)
                else:
                    # Try to parse as direct date
                    threshold_date = date_parser.parse(value_str)

                if predicate == "less than":
                    # Less than X days means newer (received less than X days ago)
                    return email_date > threshold_date
                elif predicate == "greater than":
                    # Greater than X days means older (received more than X days ago)
                    return email_date < threshold_date
            except (ValueError, TypeError) as e:
                print(f"Error parsing date: {e}")
                return False

        return False

    def _evaluate_rule(self, email: Dict, rule: Dict) -> bool:
        """Evaluate if an email matches a rule"""
        conditions = rule.get("conditions", [])
        predicate = rule.get("predicate", "all").lower()

        if not conditions:
            return False

        if predicate == "all":
            # All conditions must match
            return all(self._evaluate_condition(email, cond) for cond in conditions)
        elif predicate == "any":
            # At least one condition must match
            return any(self._evaluate_condition(email, cond) for cond in conditions)
        else:
            print(f"Unknown predicate: {predicate}")
            return False

    def _execute_action(self, email: Dict, action: Dict) -> None:
        """Execute an action on an email"""
        action_type = action.get("action", "").lower()
        service = self._get_gmail_service()
        email_id = email["id"]

        try:
            if action_type == "mark as read":
                # Update Gmail
                # pylint: disable=no-member
                service.users().messages().modify(
                    userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                # Update database
                self.db.update_email_read_status(email_id, True)
                print(f"  ✓ Marked email '{email['subject'][:50]}' as read")

            elif action_type == "mark as unread":
                # Update Gmail
                # pylint: disable=no-member
                service.users().messages().modify(
                    userId="me", id=email_id, body={"addLabelIds": ["UNREAD"]}
                ).execute()
                # Update database
                self.db.update_email_read_status(email_id, False)
                print(f"  ✓ Marked email '{email['subject'][:50]}' as unread")

            elif action_type == "move message":
                destination = action.get("destination", "")
                if not destination:
                    print("  ✗ No destination specified for move action")
                    return

                # Remove from INBOX and add to destination
                remove_labels = ["INBOX"]
                add_labels = [destination]

                # pylint: disable=no-member
                service.users().messages().modify(
                    userId="me",
                    id=email_id,
                    body={"removeLabelIds": remove_labels, "addLabelIds": add_labels},
                ).execute()
                print(f"  ✓ Moved email '{email['subject'][:50]}' to {destination}")

            else:
                print(f"  ✗ Unknown action: {action_type}")

        except Exception as e:  # pylint: disable=broad-except
            # Catch all exceptions from Gmail API calls which can raise various
            # exception types (HttpError, AttributeError, etc.)
            print(f"  ✗ Error executing action '{action_type}': {e}")

    def process_emails(self) -> None:
        """Process all emails against all rules using efficient SQL filtering"""
        print("Loading rules...")
        if not self.rules:
            print("No rules found. Please create a rules.json file.")
            return

        print(f"Loaded {len(self.rules)} rule(s)")

        processed_count = 0

        for rule in self.rules:
            rule_name = rule.get("name", "Unnamed Rule")
            print(f"\nProcessing rule: {rule_name}")

            actions = rule.get("actions", [])
            if not actions:
                print("  No actions defined for this rule")
                continue

            # Use SQL query to filter emails directly in the database
            # This is much more efficient than fetching all emails
            print("  Querying database for matching emails...")
            matched_emails = self.db.get_emails_by_rule(rule)

            print(f"  Found {len(matched_emails)} matching email(s)")

            for email in matched_emails:
                print(f"\n  Processing email: {email['subject'][:50]}")
                for action in actions:
                    self._execute_action(email, action)
                processed_count += 1

        print(f"\nProcessing complete. Processed {processed_count} email(s).")


if __name__ == "__main__":
    import sys

    rules_file = sys.argv[1] if len(sys.argv) > 1 else "rules.json"
    processor = RuleProcessor(rules_file)
    processor.process_emails()
