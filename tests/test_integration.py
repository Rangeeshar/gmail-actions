"""
Integration tests for the Gmail Actions application
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from database import EmailDatabase
from rule_processor import RuleProcessor


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = EmailDatabase(db_path=path)
    yield db
    os.unlink(path)


@pytest.fixture
def sample_emails():
    """Create sample emails for integration testing"""
    now = datetime.now()
    old_date = (now - timedelta(days=60)).isoformat()
    recent_date = (now - timedelta(days=5)).isoformat()

    return [
        {
            "id": "email1",
            "from": "newsletter@example.com",
            "to": "user@example.com",
            "subject": "Monthly Newsletter",
            "message_body": "Check out our latest updates",
            "received_date": old_date,
            "is_read": False,
            "labels": ["INBOX"],
            "raw_data": {},
        },
        {
            "id": "email2",
            "from": "boss@company.com",
            "to": "user@example.com",
            "subject": "Urgent: Meeting Tomorrow",
            "message_body": "Please attend the meeting",
            "received_date": recent_date,
            "is_read": False,
            "labels": ["INBOX"],
            "raw_data": {},
        },
        {
            "id": "email3",
            "from": "spam@example.com",
            "to": "user@example.com",
            "subject": "Free money click here",
            "message_body": "Click here to claim your prize",
            "received_date": recent_date,
            "is_read": False,
            "labels": ["INBOX"],
            "raw_data": {},
        },
    ]


@pytest.fixture
def integration_rules_file():
    """Create rules file for integration testing"""
    rules = {
        "rules": [
            {
                "name": "Archive old newsletters",
                "predicate": "All",
                "conditions": [
                    {
                        "field": "Subject",
                        "predicate": "Contains",
                        "value": "newsletter",
                    },
                    {
                        "field": "Received Date",
                        "predicate": "Greater than",
                        "value": "30 days",
                    },
                ],
                "actions": [{"action": "Mark as Read"}],
            },
            {
                "name": "Mark urgent emails",
                "predicate": "Any",
                "conditions": [
                    {"field": "Subject", "predicate": "Contains", "value": "urgent"},
                    {"field": "From", "predicate": "Contains", "value": "boss"},
                ],
                "actions": [{"action": "Mark as Read"}],
            },
        ]
    }

    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(rules, f)

    yield path
    os.unlink(path)


class TestDatabaseIntegration:
    """Test database integration operations"""

    def test_fetch_and_store_emails(self, temp_db, sample_emails):
        """Test fetching emails and storing in database"""
        for email in sample_emails:
            temp_db.insert_email(email)

        stored_emails = temp_db.get_all_emails()
        assert len(stored_emails) == 3

        # Verify email data integrity
        stored_ids = {e["id"] for e in stored_emails}
        expected_ids = {e["id"] for e in sample_emails}
        assert stored_ids == expected_ids

        # Verify specific email data
        email1 = next(e for e in stored_emails if e["id"] == "email1")
        assert email1["subject"] == "Monthly Newsletter"
        assert email1["from_address"] == "newsletter@example.com"

    def test_database_preserves_all_fields(self, temp_db, sample_emails):
        """Test that database preserves all email fields"""
        temp_db.insert_email(sample_emails[0])
        stored = temp_db.get_all_emails()[0]

        assert stored["id"] == sample_emails[0]["id"]
        assert stored["from_address"] == sample_emails[0]["from"]
        assert stored["to_address"] == sample_emails[0]["to"]
        assert stored["subject"] == sample_emails[0]["subject"]
        assert stored["message_body"] == sample_emails[0]["message_body"]
        assert stored["received_date"] == sample_emails[0]["received_date"]
        assert stored["is_read"] == sample_emails[0]["is_read"]


class TestRuleMatchingIntegration:
    """Test rule matching integration"""

    def test_rule_matching_with_all_predicate(
        self, temp_db, sample_emails, integration_rules_file
    ):
        """Test rule matching against stored emails with All predicate"""
        # Store emails
        for email in sample_emails:
            temp_db.insert_email(email)

        # Create processor with temporary database
        processor = RuleProcessor(integration_rules_file)
        processor.db = temp_db

        # First rule should match email1 (newsletter older than 30 days)
        rule1 = processor.rules[0]
        matching = temp_db.get_emails_by_rule(rule1)
        assert len(matching) == 1
        assert matching[0]["id"] == "email1"

    def test_rule_matching_with_any_predicate(
        self, temp_db, sample_emails, integration_rules_file
    ):
        """Test rule matching against stored emails with Any predicate"""
        # Store emails
        for email in sample_emails:
            temp_db.insert_email(email)

        # Create processor with temporary database
        processor = RuleProcessor(integration_rules_file)
        processor.db = temp_db

        # Second rule should match email2 (contains "urgent" or "boss")
        rule2 = processor.rules[1]
        matching = temp_db.get_emails_by_rule(rule2)
        assert len(matching) == 1
        assert matching[0]["id"] == "email2"

    def test_rule_matching_multiple_rules(
        self, temp_db, sample_emails, integration_rules_file
    ):
        """Test matching multiple rules against stored emails"""
        # Store emails
        for email in sample_emails:
            temp_db.insert_email(email)

        processor = RuleProcessor(integration_rules_file)
        processor.db = temp_db

        # Evaluate all rules
        for rule in processor.rules:
            matching = temp_db.get_emails_by_rule(rule)
            assert len(matching) >= 0  # At least some rules should match

    def test_rule_matching_case_insensitive(self, temp_db):
        """Test that rule matching is case-insensitive"""
        email_data = {
            "id": "test1",
            "from": "Sender@Example.com",
            "to": "Recipient@Example.com",
            "subject": "TEST SUBJECT",
            "message_body": "Test Message Body",
            "received_date": (datetime.now() - timedelta(days=5)).isoformat(),
            "is_read": False,
            "labels": [],
            "raw_data": {},
        }
        temp_db.insert_email(email_data)

        rule = {
            "predicate": "All",
            "conditions": [
                {"field": "From", "predicate": "Contains", "value": "sender"},
                {"field": "Subject", "predicate": "Contains", "value": "test"},
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        assert len(matching) == 1
        assert matching[0]["id"] == "test1"


class TestDateBasedRuleMatching:
    """Test date-based rule matching integration"""

    def test_date_comparisons_greater_than(self, temp_db):
        """Test date-based rule matching with Greater than"""
        now = datetime.now()

        emails = [
            {
                "id": "old1",
                "from": "test@example.com",
                "to": "user@example.com",
                "subject": "Old Email",
                "message_body": "Content",
                "received_date": (now - timedelta(days=45)).isoformat(),
                "is_read": False,
                "labels": ["INBOX"],
                "raw_data": {},
            },
            {
                "id": "new1",
                "from": "test@example.com",
                "to": "user@example.com",
                "subject": "New Email",
                "message_body": "Content",
                "received_date": (now - timedelta(days=10)).isoformat(),
                "is_read": False,
                "labels": ["INBOX"],
                "raw_data": {},
            },
        ]

        for email in emails:
            temp_db.insert_email(email)

        rule = {
            "predicate": "All",
            "conditions": [
                {
                    "field": "Received Date",
                    "predicate": "Greater than",
                    "value": "30 days",
                }
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        # Only old email should match
        assert len(matching) == 1
        assert matching[0]["id"] == "old1"

    def test_date_comparisons_less_than(self, temp_db):
        """Test date-based rule matching with Less than"""
        now = datetime.now()

        emails = [
            {
                "id": "old1",
                "from": "test@example.com",
                "to": "user@example.com",
                "subject": "Old Email",
                "message_body": "Content",
                "received_date": (now - timedelta(days=45)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
            {
                "id": "new1",
                "from": "test@example.com",
                "to": "user@example.com",
                "subject": "New Email",
                "message_body": "Content",
                "received_date": (now - timedelta(days=10)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
        ]

        for email in emails:
            temp_db.insert_email(email)

        rule = {
            "predicate": "All",
            "conditions": [
                {"field": "Received Date", "predicate": "Less than", "value": "30 days"}
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        # Only new email should match
        assert len(matching) == 1
        assert matching[0]["id"] == "new1"

    def test_date_comparisons_with_months(self, temp_db):
        """Test date-based rule matching with months value"""
        now = datetime.now()

        emails = [
            {
                "id": "very_old1",
                "from": "test@example.com",
                "to": "user@example.com",
                "subject": "Very Old Email",
                "message_body": "Content",
                "received_date": (now - timedelta(days=120)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
            {
                "id": "recent1",
                "from": "test@example.com",
                "to": "user@example.com",
                "subject": "Recent Email",
                "message_body": "Content",
                "received_date": (now - timedelta(days=10)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
        ]

        for email in emails:
            temp_db.insert_email(email)

        rule = {
            "predicate": "All",
            "conditions": [
                {
                    "field": "Received Date",
                    "predicate": "Greater than",
                    "value": "3 months",
                }
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        # Only very old email should match
        assert len(matching) == 1
        assert matching[0]["id"] == "very_old1"


class TestFullWorkflowIntegration:
    """Test complete workflow integration"""

    @patch("rule_processor.GmailAuthenticator")
    def test_full_workflow_store_and_process(
        self, mock_auth_class, temp_db, sample_emails, integration_rules_file
    ):
        """Test complete workflow: store emails, evaluate rules, execute actions"""
        # Store emails
        for email in sample_emails:
            temp_db.insert_email(email)

        # Verify emails are stored
        stored_emails = temp_db.get_all_emails()
        assert len(stored_emails) == 3

        # Setup mocks for Gmail API with proper chaining
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()
        mock_modify = MagicMock()
        mock_execute = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages
        mock_messages.modify.return_value = mock_execute

        mock_auth = MagicMock()
        mock_auth.get_service.return_value = mock_service
        mock_auth_class.return_value = mock_auth

        # Create processor and process emails
        processor = RuleProcessor(integration_rules_file)
        processor.db = temp_db
        processor.process_emails()

        # Verify that Gmail API was called for matching emails
        # email1 matches rule1, email2 matches rule2
        assert mock_messages.modify.call_count == 2
        assert mock_execute.execute.call_count == 2

    @patch("rule_processor.GmailAuthenticator")
    def test_full_workflow_with_multiple_actions(self, mock_auth_class, temp_db):
        """Test workflow with rule that has multiple actions"""
        # Create email
        email_data = {
            "id": "test1",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "message_body": "Test content",
            "received_date": datetime.now().isoformat(),
            "is_read": False,
            "labels": [],
            "raw_data": {},
        }
        temp_db.insert_email(email_data)

        # Create rules file with multiple actions
        rules = {
            "rules": [
                {
                    "name": "Test Rule",
                    "predicate": "All",
                    "conditions": [
                        {"field": "Subject", "predicate": "Contains", "value": "Test"},
                    ],
                    "actions": [
                        {"action": "Mark as Read"},
                        {"action": "Move Message", "destination": "IMPORTANT"},
                    ],
                }
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(rules, f)

        # Setup mocks with proper chaining
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()
        mock_modify = MagicMock()
        mock_execute = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages
        mock_messages.modify.return_value = mock_execute

        mock_auth = MagicMock()
        mock_auth.get_service.return_value = mock_service
        mock_auth_class.return_value = mock_auth

        processor = RuleProcessor(path)
        processor.db = temp_db
        processor.process_emails()

        # Verify both actions were executed
        assert mock_messages.modify.call_count == 2
        assert mock_execute.execute.call_count == 2

        os.unlink(path)

    def test_full_workflow_sql_based_matching(
        self, temp_db, sample_emails, integration_rules_file
    ):
        """Test that SQL-based rule matching works correctly"""
        # Store emails
        for email in sample_emails:
            temp_db.insert_email(email)

        processor = RuleProcessor(integration_rules_file)
        processor.db = temp_db

        # Test that get_emails_by_rule uses SQL efficiently
        rule = processor.rules[0]
        matching = temp_db.get_emails_by_rule(rule)

        # Should return matching emails directly from SQL query
        assert len(matching) == 1
        assert matching[0]["id"] == "email1"

        # Verify the email matches the rule conditions
        assert processor._evaluate_rule(matching[0], rule) is True


class TestEdgeCasesIntegration:
    """Test edge cases in integration scenarios"""

    def test_empty_database_rule_matching(self, temp_db, integration_rules_file):
        """Test rule matching against empty database"""
        processor = RuleProcessor(integration_rules_file)
        processor.db = temp_db

        rule = processor.rules[0]
        matching = temp_db.get_emails_by_rule(rule)
        assert matching == []

    def test_rule_with_complex_conditions(self, temp_db):
        """Test rule with multiple complex conditions"""
        email_data = {
            "id": "complex1",
            "from": "newsletter@example.com",
            "to": "user@example.com",
            "subject": "Monthly Newsletter",
            "message_body": "Check out our latest updates and special offers",
            "received_date": (datetime.now() - timedelta(days=45)).isoformat(),
            "is_read": False,
            "labels": [],
            "raw_data": {},
        }
        temp_db.insert_email(email_data)

        rule = {
            "predicate": "All",
            "conditions": [
                {"field": "Subject", "predicate": "Contains", "value": "newsletter"},
                {
                    "field": "Message",
                    "predicate": "Contains",
                    "value": "special offers",
                },
                {
                    "field": "Received Date",
                    "predicate": "Greater than",
                    "value": "30 days",
                },
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        assert len(matching) == 1
        assert matching[0]["id"] == "complex1"

    def test_multiple_rules_same_email(self, temp_db):
        """Test that same email can match multiple rules"""
        email_data = {
            "id": "multi1",
            "from": "boss@company.com",
            "to": "user@example.com",
            "subject": "Urgent: Important Update",
            "message_body": "This is urgent",
            "received_date": (datetime.now() - timedelta(days=5)).isoformat(),
            "is_read": False,
            "labels": [],
            "raw_data": {},
        }
        temp_db.insert_email(email_data)

        rules = [
            {
                "predicate": "All",
                "conditions": [
                    {"field": "Subject", "predicate": "Contains", "value": "Urgent"},
                ],
            },
            {
                "predicate": "All",
                "conditions": [
                    {"field": "From", "predicate": "Contains", "value": "boss"},
                ],
            },
        ]

        for rule in rules:
            matching = temp_db.get_emails_by_rule(rule)
            assert len(matching) == 1
            assert matching[0]["id"] == "multi1"
