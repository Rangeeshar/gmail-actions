"""
Unit tests for rule processor module
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from rule_processor import RuleProcessor
from database import EmailDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = EmailDatabase(db_path=path)
    yield db
    os.unlink(path)


@pytest.fixture
def sample_email():
    """Create a sample email for testing"""
    return {
        "id": "test123",
        "thread_id": "thread123",
        "from_address": "sender@example.com",
        "to_address": "recipient@example.com",
        "subject": "Test Subject",
        "message_body": "This is a test message",
        "received_date": datetime.now().isoformat(),
        "is_read": False,
        "labels": ["INBOX"],
        "raw_data": {},
    }


@pytest.fixture
def old_email():
    """Create an old email for testing"""
    old_date = (datetime.now() - timedelta(days=60)).isoformat()
    return {
        "id": "old123",
        "thread_id": "thread456",
        "from_address": "newsletter@example.com",
        "to_address": "recipient@example.com",
        "subject": "Monthly Newsletter",
        "message_body": "Newsletter content",
        "received_date": old_date,
        "is_read": False,
        "labels": ["INBOX"],
        "raw_data": {},
    }


@pytest.fixture
def rules_file():
    """Create a temporary rules file for testing"""
    rules = {
        "rules": [
            {
                "name": "Test Rule - All",
                "predicate": "All",
                "conditions": [
                    {"field": "Subject", "predicate": "Contains", "value": "Test"},
                    {
                        "field": "From",
                        "predicate": "Equals",
                        "value": "sender@example.com",
                    },
                ],
                "actions": [{"action": "Mark as Read"}],
            },
            {
                "name": "Test Rule - Any",
                "predicate": "Any",
                "conditions": [
                    {"field": "Subject", "predicate": "Contains", "value": "Urgent"},
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


class TestRuleLoading:
    """Test rule loading functionality"""

    def test_load_rules_success(self, rules_file):
        """Test successfully loading rules from JSON file"""
        processor = RuleProcessor(rules_file)
        assert len(processor.rules) == 2
        assert processor.rules[0]["name"] == "Test Rule - All"
        assert processor.rules[1]["name"] == "Test Rule - Any"

    def test_load_rules_nonexistent_file(self):
        """Test loading rules from non-existent file"""
        processor = RuleProcessor("nonexistent.json")
        assert processor.rules == []

    def test_load_rules_invalid_json(self):
        """Test loading rules from invalid JSON file"""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("invalid json content {")

        processor = RuleProcessor(path)
        assert processor.rules == []

        os.unlink(path)

    def test_load_rules_empty_file(self):
        """Test loading rules from empty file"""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({}, f)

        processor = RuleProcessor(path)
        assert processor.rules == []

        os.unlink(path)

    def test_load_rules_no_rules_key(self):
        """Test loading rules file without 'rules' key"""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"other_key": []}, f)

        processor = RuleProcessor(path)
        assert processor.rules == []

        os.unlink(path)


class TestConditionEvaluation:
    """Test condition evaluation functionality"""

    def test_evaluate_condition_contains_matches(self, sample_email):
        """Test condition evaluation with Contains predicate that matches"""
        processor = RuleProcessor()
        condition = {"field": "Subject", "predicate": "Contains", "value": "Test"}
        assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_contains_no_match(self, sample_email):
        """Test condition evaluation with Contains predicate that doesn't match"""
        processor = RuleProcessor()
        condition = {
            "field": "Subject",
            "predicate": "Contains",
            "value": "Nonexistent",
        }
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_contains_case_insensitive(self, sample_email):
        """Test that Contains predicate is case-insensitive"""
        processor = RuleProcessor()
        condition = {"field": "Subject", "predicate": "Contains", "value": "test"}
        assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_equals_matches(self, sample_email):
        """Test condition evaluation with Equals predicate that matches"""
        processor = RuleProcessor()
        condition = {
            "field": "From",
            "predicate": "Equals",
            "value": "sender@example.com",
        }
        assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_equals_no_match(self, sample_email):
        """Test condition evaluation with Equals predicate that doesn't match"""
        processor = RuleProcessor()
        condition = {
            "field": "From",
            "predicate": "Equals",
            "value": "other@example.com",
        }
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_equals_case_insensitive(self, sample_email):
        """Test that Equals predicate is case-insensitive"""
        processor = RuleProcessor()
        condition = {
            "field": "From",
            "predicate": "Equals",
            "value": "SENDER@EXAMPLE.COM",
        }
        assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_does_not_contain_matches(self, sample_email):
        """Test condition evaluation with Does not Contain predicate"""
        processor = RuleProcessor()
        condition = {
            "field": "Subject",
            "predicate": "Does not Contain",
            "value": "Spam",
        }
        assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_does_not_contain_no_match(self, sample_email):
        """Test condition evaluation with Does not Contain that doesn't match"""
        processor = RuleProcessor()
        condition = {
            "field": "Subject",
            "predicate": "Does not Contain",
            "value": "Test",
        }
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_does_not_equal_matches(self, sample_email):
        """Test condition evaluation with Does not Equal predicate"""
        processor = RuleProcessor()
        condition = {
            "field": "From",
            "predicate": "Does not Equal",
            "value": "other@example.com",
        }
        assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_does_not_equal_no_match(self, sample_email):
        """Test condition evaluation with Does not Equal that doesn't match"""
        processor = RuleProcessor()
        condition = {
            "field": "From",
            "predicate": "Does not Equal",
            "value": "sender@example.com",
        }
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_message_field(self, sample_email):
        """Test condition evaluation on Message field"""
        processor = RuleProcessor()
        condition = {
            "field": "Message",
            "predicate": "Contains",
            "value": "test message",
        }
        assert processor._evaluate_condition(sample_email, condition) is True

        condition["value"] = "nonexistent"
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_to_field(self, sample_email):
        """Test condition evaluation on To field"""
        processor = RuleProcessor()
        condition = {"field": "To", "predicate": "Contains", "value": "recipient"}
        assert processor._evaluate_condition(sample_email, condition) is True

        condition["value"] = "nonexistent"
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_date_greater_than_matches(self, old_email):
        """Test condition evaluation with date Greater than predicate that matches"""
        processor = RuleProcessor()
        condition = {
            "field": "Received Date",
            "predicate": "Greater than",
            "value": "30 days",
        }
        assert processor._evaluate_condition(old_email, condition) is True

    def test_evaluate_condition_date_greater_than_no_match(self, old_email):
        """Test condition evaluation with date Greater than that doesn't match"""
        processor = RuleProcessor()
        condition = {
            "field": "Received Date",
            "predicate": "Greater than",
            "value": "90 days",
        }
        assert processor._evaluate_condition(old_email, condition) is False

    def test_evaluate_condition_date_less_than_matches(self, sample_email):
        """Test condition evaluation with date Less than predicate that matches"""
        processor = RuleProcessor()
        condition = {
            "field": "Received Date",
            "predicate": "Less than",
            "value": "30 days",
        }
        assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_date_less_than_no_match(self, old_email):
        """Test condition evaluation with date Less than that doesn't match"""
        processor = RuleProcessor()
        condition = {
            "field": "Received Date",
            "predicate": "Less than",
            "value": "30 days",
        }
        assert processor._evaluate_condition(old_email, condition) is False

    def test_evaluate_condition_date_with_months(self, old_email):
        """Test condition evaluation with date value in months"""
        processor = RuleProcessor()
        condition = {
            "field": "Received Date",
            "predicate": "Greater than",
            "value": "1 month",
        }
        assert processor._evaluate_condition(old_email, condition) is True

    def test_evaluate_condition_date_direct_date_string(self, old_email):
        """Test condition evaluation with direct date string"""
        processor = RuleProcessor()
        threshold_date = (datetime.now() - timedelta(days=30)).isoformat()
        condition = {
            "field": "Received Date",
            "predicate": "Greater than",
            "value": threshold_date,
        }
        assert processor._evaluate_condition(old_email, condition) is True

    def test_evaluate_condition_date_field_variations(self, sample_email):
        """Test that different date field name variations work"""
        processor = RuleProcessor()
        variations = ["Received Date", "Received Date/Time", "Date Received"]
        for field in variations:
            condition = {"field": field, "predicate": "Less than", "value": "30 days"}
            assert processor._evaluate_condition(sample_email, condition) is True

    def test_evaluate_condition_unknown_field(self, sample_email):
        """Test condition evaluation with unknown field"""
        processor = RuleProcessor()
        condition = {"field": "Unknown Field", "predicate": "Contains", "value": "test"}
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_invalid_date(self, sample_email):
        """Test condition evaluation with invalid date value"""
        processor = RuleProcessor()
        condition = {
            "field": "Received Date",
            "predicate": "Greater than",
            "value": "invalid date",
        }
        assert processor._evaluate_condition(sample_email, condition) is False

    def test_evaluate_condition_missing_field_value(self, sample_email):
        """Test condition evaluation when email is missing field value"""
        email_no_subject = sample_email.copy()
        email_no_subject["subject"] = ""
        processor = RuleProcessor()
        condition = {"field": "Subject", "predicate": "Contains", "value": "Test"}
        assert processor._evaluate_condition(email_no_subject, condition) is False


class TestRuleEvaluation:
    """Test rule evaluation functionality"""

    def test_evaluate_rule_all_predicate_all_match(self, sample_email):
        """Test rule evaluation with All predicate when all conditions match"""
        processor = RuleProcessor()
        rule = {
            "predicate": "All",
            "conditions": [
                {"field": "Subject", "predicate": "Contains", "value": "Test"},
                {"field": "From", "predicate": "Equals", "value": "sender@example.com"},
            ],
        }
        assert processor._evaluate_rule(sample_email, rule) is True

    def test_evaluate_rule_all_predicate_one_fails(self, sample_email):
        """Test rule evaluation with All predicate when one condition fails"""
        processor = RuleProcessor()
        rule = {
            "predicate": "All",
            "conditions": [
                {"field": "Subject", "predicate": "Contains", "value": "Test"},
                {"field": "From", "predicate": "Equals", "value": "other@example.com"},
            ],
        }
        assert processor._evaluate_rule(sample_email, rule) is False

    def test_evaluate_rule_any_predicate_one_matches(self, sample_email):
        """Test rule evaluation with Any predicate when one condition matches"""
        processor = RuleProcessor()
        rule = {
            "predicate": "Any",
            "conditions": [
                {"field": "Subject", "predicate": "Contains", "value": "Nonexistent"},
                {"field": "From", "predicate": "Equals", "value": "sender@example.com"},
            ],
        }
        assert processor._evaluate_rule(sample_email, rule) is True

    def test_evaluate_rule_any_predicate_none_match(self, sample_email):
        """Test rule evaluation with Any predicate when no conditions match"""
        processor = RuleProcessor()
        rule = {
            "predicate": "Any",
            "conditions": [
                {"field": "Subject", "predicate": "Contains", "value": "Nonexistent"},
                {"field": "From", "predicate": "Equals", "value": "other@example.com"},
            ],
        }
        assert processor._evaluate_rule(sample_email, rule) is False

    def test_evaluate_rule_no_conditions(self, sample_email):
        """Test rule evaluation with no conditions"""
        processor = RuleProcessor()
        rule = {"predicate": "All", "conditions": []}
        assert processor._evaluate_rule(sample_email, rule) is False

    def test_evaluate_rule_unknown_predicate(self, sample_email):
        """Test rule evaluation with unknown predicate"""
        processor = RuleProcessor()
        rule = {
            "predicate": "Unknown",
            "conditions": [
                {"field": "Subject", "predicate": "Contains", "value": "Test"},
            ],
        }
        assert processor._evaluate_rule(sample_email, rule) is False


class TestActionExecution:
    """Test action execution functionality"""

    @patch("rule_processor.GmailAuthenticator")
    def test_execute_action_mark_as_read(self, mock_auth_class, sample_email, temp_db):
        """Test executing Mark as Read action"""
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

        processor = RuleProcessor(
            "nonexistent.json"
        )  # Use nonexistent file to avoid loading real rules
        processor.db = temp_db
        temp_db.insert_email(
            {
                "id": sample_email["id"],
                "from": sample_email["from_address"],
                "to": sample_email["to_address"],
                "subject": sample_email["subject"],
                "message_body": sample_email["message_body"],
                "received_date": sample_email["received_date"],
                "is_read": False,
                "labels": [],
                "raw_data": {},
            }
        )

        action = {"action": "Mark as Read"}
        processor._execute_action(sample_email, action)

        # Verify Gmail API was called
        mock_messages.modify.assert_called_once()
        call_args = mock_messages.modify.call_args
        assert call_args[1]["userId"] == "me"
        assert call_args[1]["id"] == sample_email["id"]
        assert "UNREAD" in call_args[1]["body"]["removeLabelIds"]
        mock_execute.execute.assert_called_once()

        # Verify database was updated
        email = temp_db.get_email_by_id(sample_email["id"])
        assert email["is_read"] is True

    @patch("rule_processor.GmailAuthenticator")
    def test_execute_action_mark_as_unread(
        self, mock_auth_class, sample_email, temp_db
    ):
        """Test executing Mark as Unread action"""
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

        processor = RuleProcessor("nonexistent.json")
        processor.db = temp_db
        temp_db.insert_email(
            {
                "id": sample_email["id"],
                "from": sample_email["from_address"],
                "to": sample_email["to_address"],
                "subject": sample_email["subject"],
                "message_body": sample_email["message_body"],
                "received_date": sample_email["received_date"],
                "is_read": True,
                "labels": [],
                "raw_data": {},
            }
        )

        action = {"action": "Mark as Unread"}
        processor._execute_action(sample_email, action)

        # Verify Gmail API was called
        mock_messages.modify.assert_called_once()
        call_args = mock_messages.modify.call_args
        assert "UNREAD" in call_args[1]["body"]["addLabelIds"]
        mock_execute.execute.assert_called_once()

        # Verify database was updated
        email = temp_db.get_email_by_id(sample_email["id"])
        assert email["is_read"] is False

    @patch("rule_processor.GmailAuthenticator")
    def test_execute_action_move_message(self, mock_auth_class, sample_email):
        """Test executing Move Message action"""
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

        processor = RuleProcessor("nonexistent.json")
        action = {"action": "Move Message", "destination": "IMPORTANT"}
        processor._execute_action(sample_email, action)

        # Verify Gmail API was called
        mock_messages.modify.assert_called_once()
        call_args = mock_messages.modify.call_args
        assert call_args[1]["userId"] == "me"
        assert call_args[1]["id"] == sample_email["id"]
        assert "INBOX" in call_args[1]["body"]["removeLabelIds"]
        assert "IMPORTANT" in call_args[1]["body"]["addLabelIds"]
        mock_execute.execute.assert_called_once()

    @patch("rule_processor.GmailAuthenticator")
    def test_execute_action_move_message_no_destination(
        self, mock_auth_class, sample_email
    ):
        """Test executing Move Message action without destination"""
        mock_service = MagicMock()
        mock_auth = MagicMock()
        mock_auth.get_service.return_value = mock_service
        mock_auth_class.return_value = mock_auth

        processor = RuleProcessor("nonexistent.json")
        action = {"action": "Move Message"}
        processor._execute_action(sample_email, action)

        # Should not call Gmail API (returns early before calling service)
        mock_service.users.assert_not_called()

    @patch("rule_processor.GmailAuthenticator")
    def test_execute_action_unknown_action(self, mock_auth_class, sample_email):
        """Test executing unknown action"""
        mock_service = MagicMock()
        mock_auth = MagicMock()
        mock_auth.get_service.return_value = mock_service
        mock_auth_class.return_value = mock_auth

        processor = RuleProcessor("nonexistent.json")
        action = {"action": "Unknown Action"}
        processor._execute_action(sample_email, action)

        # Unknown action should not call get_service (returns early)
        mock_service.users.assert_not_called()

    @patch("rule_processor.GmailAuthenticator")
    def test_execute_action_api_error(self, mock_auth_class, sample_email, temp_db):
        """Test handling API error during action execution"""
        # Setup mocks with proper chaining
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()
        mock_modify = MagicMock()
        mock_execute = MagicMock()
        mock_execute.execute.side_effect = Exception("API Error")

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages
        mock_messages.modify.return_value = mock_execute

        mock_auth = MagicMock()
        mock_auth.get_service.return_value = mock_service
        mock_auth_class.return_value = mock_auth

        processor = RuleProcessor("nonexistent.json")
        processor.db = temp_db
        action = {"action": "Mark as Read"}

        # Should not raise exception, just print error
        processor._execute_action(sample_email, action)


class TestProcessEmails:
    """Test email processing functionality"""

    @patch("rule_processor.GmailAuthenticator")
    def test_process_emails_no_rules(self, mock_auth_class):
        """Test processing emails when no rules are loaded"""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({}, f)

        processor = RuleProcessor(path)
        processor.process_emails()  # Should not raise error

        os.unlink(path)

    @patch("rule_processor.GmailAuthenticator")
    def test_process_emails_with_matching_emails(self, mock_auth_class, temp_db):
        """Test processing emails that match rules"""
        # Setup rules file
        rules = {
            "rules": [
                {
                    "name": "Test Rule",
                    "predicate": "All",
                    "conditions": [
                        {"field": "Subject", "predicate": "Contains", "value": "Test"},
                    ],
                    "actions": [{"action": "Mark as Read"}],
                }
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(rules, f)

        # Insert matching email
        temp_db.insert_email(
            {
                "id": "test1",
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "message_body": "Content",
                "received_date": datetime.now().isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            }
        )

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

        # Verify action was executed
        mock_messages.modify.assert_called()
        mock_execute.execute.assert_called()

        os.unlink(path)

    @patch("rule_processor.GmailAuthenticator")
    def test_process_emails_no_matching_emails(self, mock_auth_class, temp_db):
        """Test processing emails when no emails match rules"""
        # Setup rules file
        rules = {
            "rules": [
                {
                    "name": "Test Rule",
                    "predicate": "All",
                    "conditions": [
                        {
                            "field": "Subject",
                            "predicate": "Contains",
                            "value": "Nonexistent",
                        },
                    ],
                    "actions": [{"action": "Mark as Read"}],
                }
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(rules, f)

        # Insert non-matching email
        temp_db.insert_email(
            {
                "id": "test1",
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Other Subject",
                "message_body": "Content",
                "received_date": datetime.now().isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            }
        )

        # Setup mocks
        mock_service = MagicMock()
        mock_auth = MagicMock()
        mock_auth.get_service.return_value = mock_service
        mock_auth_class.return_value = mock_auth

        processor = RuleProcessor(path)
        processor.db = temp_db
        processor.process_emails()

        # Verify action was not executed (no matching emails)
        mock_service.users.assert_not_called()

        os.unlink(path)

    @patch("rule_processor.GmailAuthenticator")
    def test_process_emails_rule_without_actions(self, mock_auth_class, temp_db):
        """Test processing emails with rule that has no actions"""
        # Setup rules file
        rules = {
            "rules": [
                {
                    "name": "Test Rule",
                    "predicate": "All",
                    "conditions": [
                        {"field": "Subject", "predicate": "Contains", "value": "Test"},
                    ],
                    "actions": [],
                }
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(rules, f)

        # Insert matching email
        temp_db.insert_email(
            {
                "id": "test1",
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "message_body": "Content",
                "received_date": datetime.now().isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            }
        )

        # Setup mocks
        mock_service = MagicMock()
        mock_auth = MagicMock()
        mock_auth.get_service.return_value = mock_service
        mock_auth_class.return_value = mock_auth

        processor = RuleProcessor(path)
        processor.db = temp_db
        processor.process_emails()

        # Verify action was not executed (rule has no actions)
        mock_service.users.assert_not_called()

        os.unlink(path)
