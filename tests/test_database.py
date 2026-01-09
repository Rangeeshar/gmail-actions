"""
Unit tests for database module
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
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
def sample_email_data():
    """Sample email data for testing"""
    return {
        "id": "test123",
        "thread_id": "thread123",
        "from": "sender@example.com",
        "to": "recipient@example.com",
        "subject": "Test Subject",
        "message_body": "This is a test message body",
        "received_date": "2024-01-01T12:00:00",
        "is_read": False,
        "labels": ["INBOX", "UNREAD"],
        "raw_data": {"test": "data"},
    }


class TestDatabaseInitialization:
    """Test database initialization and setup"""

    def test_database_initialization(self, temp_db):
        """Test that database is initialized correctly with empty tables"""
        emails = temp_db.get_all_emails()
        assert emails == []

    def test_database_creates_tables(self, temp_db):
        """Test that database creates required tables"""
        # Try to query the table - should not raise an error
        emails = temp_db.get_all_emails()
        assert isinstance(emails, list)


class TestEmailInsertion:
    """Test email insertion operations"""

    def test_insert_email_success(self, temp_db, sample_email_data):
        """Test successfully inserting an email"""
        result = temp_db.insert_email(sample_email_data)
        assert result is True

        emails = temp_db.get_all_emails()
        assert len(emails) == 1
        assert emails[0]["id"] == "test123"
        assert emails[0]["from_address"] == "sender@example.com"
        assert emails[0]["to_address"] == "recipient@example.com"
        assert emails[0]["subject"] == "Test Subject"
        assert emails[0]["message_body"] == "This is a test message body"
        assert emails[0]["is_read"] is False

    def test_insert_email_with_minimal_data(self, temp_db):
        """Test inserting email with minimal required fields"""
        email_data = {
            "id": "minimal123",
            "from": "sender@example.com",
            "subject": "Minimal",
            "message_body": "Content",
            "received_date": "2024-01-01T12:00:00",
        }
        result = temp_db.insert_email(email_data)
        assert result is True

        email = temp_db.get_email_by_id("minimal123")
        assert email is not None
        assert email["thread_id"] == ""
        assert email["to_address"] == ""
        assert email["labels"] == []
        assert email["raw_data"] == {}

    def test_insert_email_with_labels(self, temp_db, sample_email_data):
        """Test inserting email with labels"""
        sample_email_data["labels"] = ["INBOX", "IMPORTANT", "STARRED"]
        temp_db.insert_email(sample_email_data)

        email = temp_db.get_email_by_id("test123")
        assert email["labels"] == ["INBOX", "IMPORTANT", "STARRED"]

    def test_insert_email_with_raw_data(self, temp_db, sample_email_data):
        """Test inserting email with raw data"""
        raw_data = {"key1": "value1", "key2": ["list", "data"]}
        sample_email_data["raw_data"] = raw_data
        temp_db.insert_email(sample_email_data)

        email = temp_db.get_email_by_id("test123")
        assert email["raw_data"] == raw_data

    def test_insert_email_updates_existing(self, temp_db, sample_email_data):
        """Test that inserting same email ID updates existing record"""
        temp_db.insert_email(sample_email_data)

        # Update the email
        sample_email_data["subject"] = "Updated Subject"
        sample_email_data["is_read"] = True
        temp_db.insert_email(sample_email_data)

        emails = temp_db.get_all_emails()
        assert len(emails) == 1  # Still only one email
        assert emails[0]["subject"] == "Updated Subject"
        assert emails[0]["is_read"] is True

    def test_insert_multiple_emails(self, temp_db):
        """Test inserting multiple emails"""
        for i in range(5):
            email_data = {
                "id": f"test{i}",
                "from": f"sender{i}@example.com",
                "to": f"recipient{i}@example.com",
                "subject": f"Test Email {i}",
                "message_body": f"Message content {i}",
                "received_date": f"2024-01-{i + 1:02d}T12:00:00",
                "is_read": i % 2 == 0,
                "labels": [],
                "raw_data": {},
            }
            temp_db.insert_email(email_data)

        emails = temp_db.get_all_emails()
        assert len(emails) == 5
        assert all(e["id"] in [f"test{i}" for i in range(5)] for e in emails)


class TestEmailRetrieval:
    """Test email retrieval operations"""

    def test_get_all_emails_empty(self, temp_db):
        """Test getting all emails from empty database"""
        emails = temp_db.get_all_emails()
        assert emails == []

    def test_get_all_emails_ordered_by_date(self, temp_db):
        """Test that emails are ordered by received_date DESC"""
        base_date = datetime(2024, 1, 1)
        for i in range(3):
            email_data = {
                "id": f"test{i}",
                "from": f"sender{i}@example.com",
                "subject": f"Test {i}",
                "message_body": "Content",
                "received_date": (base_date + timedelta(days=i)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            }
            temp_db.insert_email(email_data)

        emails = temp_db.get_all_emails()
        assert len(emails) == 3
        # Should be ordered DESC (newest first)
        assert emails[0]["id"] == "test2"
        assert emails[1]["id"] == "test1"
        assert emails[2]["id"] == "test0"

    def test_get_email_by_id_exists(self, temp_db, sample_email_data):
        """Test retrieving email by ID when it exists"""
        temp_db.insert_email(sample_email_data)

        email = temp_db.get_email_by_id("test123")
        assert email is not None
        assert email["id"] == "test123"
        assert email["from_address"] == "sender@example.com"
        assert email["subject"] == "Test Subject"

    def test_get_email_by_id_not_exists(self, temp_db):
        """Test retrieving email by ID when it doesn't exist"""
        email = temp_db.get_email_by_id("nonexistent")
        assert email is None

    def test_get_email_by_id_preserves_data_types(self, temp_db, sample_email_data):
        """Test that retrieved email preserves data types"""
        temp_db.insert_email(sample_email_data)

        email = temp_db.get_email_by_id("test123")
        assert isinstance(email["is_read"], bool)
        assert isinstance(email["labels"], list)
        assert isinstance(email["raw_data"], dict)


class TestEmailUpdate:
    """Test email update operations"""

    def test_update_email_read_status_to_read(self, temp_db, sample_email_data):
        """Test updating email read status to read"""
        sample_email_data["is_read"] = False
        temp_db.insert_email(sample_email_data)

        result = temp_db.update_email_read_status("test123", True)
        assert result is True

        email = temp_db.get_email_by_id("test123")
        assert email["is_read"] is True

    def test_update_email_read_status_to_unread(self, temp_db, sample_email_data):
        """Test updating email read status to unread"""
        sample_email_data["is_read"] = True
        temp_db.insert_email(sample_email_data)

        result = temp_db.update_email_read_status("test123", False)
        assert result is True

        email = temp_db.get_email_by_id("test123")
        assert email["is_read"] is False

    def test_update_email_read_status_nonexistent(self, temp_db):
        """Test updating read status for non-existent email"""
        result = temp_db.update_email_read_status("nonexistent", True)
        assert result is False

    def test_update_email_read_status_updates_timestamp(
        self, temp_db, sample_email_data
    ):
        """Test that updating read status updates the updated_at timestamp"""
        temp_db.insert_email(sample_email_data)
        original_email = temp_db.get_email_by_id("test123")
        original_timestamp = original_email["updated_at"]

        # Wait a tiny bit to ensure timestamp difference
        import time

        time.sleep(0.01)

        temp_db.update_email_read_status("test123", True)
        updated_email = temp_db.get_email_by_id("test123")
        assert updated_email["updated_at"] != original_timestamp


class TestDatabaseCleanup:
    """Test database cleanup operations"""

    def test_clear_all_emails(self, temp_db):
        """Test clearing all emails from database"""
        # Insert multiple emails
        for i in range(3):
            email_data = {
                "id": f"test{i}",
                "from": f"sender{i}@example.com",
                "subject": f"Test {i}",
                "message_body": "Content",
                "received_date": "2024-01-01T12:00:00",
                "is_read": False,
                "labels": [],
                "raw_data": {},
            }
            temp_db.insert_email(email_data)

        assert len(temp_db.get_all_emails()) == 3

        temp_db.clear_all_emails()
        assert len(temp_db.get_all_emails()) == 0

    def test_clear_all_emails_empty_database(self, temp_db):
        """Test clearing emails from empty database"""
        temp_db.clear_all_emails()
        assert len(temp_db.get_all_emails()) == 0


class TestSQLConditionBuilding:
    """Test SQL condition building for rule matching"""

    def test_build_sql_condition_from_contains(self, temp_db):
        """Test building SQL condition for From field with Contains predicate"""
        condition = {"field": "From", "predicate": "Contains", "value": "example"}
        sql, params = temp_db._build_sql_condition(condition)

        assert "LOWER(from_address) LIKE ?" in sql
        assert "%example%" in params[0]

    def test_build_sql_condition_subject_equals(self, temp_db):
        """Test building SQL condition for Subject field with Equals predicate"""
        condition = {"field": "Subject", "predicate": "Equals", "value": "Test"}
        sql, params = temp_db._build_sql_condition(condition)

        assert "LOWER(subject) = ?" in sql
        assert params[0] == "test"

    def test_build_sql_condition_message_does_not_contain(self, temp_db):
        """Test building SQL condition for Message field with Does not Contain"""
        condition = {
            "field": "Message",
            "predicate": "Does not Contain",
            "value": "spam",
        }
        sql, params = temp_db._build_sql_condition(condition)

        assert "LOWER(message_body) NOT LIKE ?" in sql
        assert "%spam%" in params[0]

    def test_build_sql_condition_to_does_not_equal(self, temp_db):
        """Test building SQL condition for To field with Does not Equal"""
        condition = {
            "field": "To",
            "predicate": "Does not Equal",
            "value": "test@example.com",
        }
        sql, params = temp_db._build_sql_condition(condition)

        assert "LOWER(to_address) != ?" in sql
        assert params[0] == "test@example.com"

    def test_build_sql_condition_date_greater_than_days(self, temp_db):
        """Test building SQL condition for date with Greater than (days)"""
        condition = {
            "field": "Received Date",
            "predicate": "Greater than",
            "value": "30 days",
        }
        sql, params = temp_db._build_sql_condition(condition)

        # Greater than 30 days means older (received_date < threshold)
        assert "received_date < ?" in sql
        assert len(params) == 1
        # Should be a date in ISO format
        assert "T" in params[0] or "-" in params[0]

    def test_build_sql_condition_date_less_than_months(self, temp_db):
        """Test building SQL condition for date with Less than (months)"""
        condition = {
            "field": "Received Date",
            "predicate": "Less than",
            "value": "3 months",
        }
        sql, params = temp_db._build_sql_condition(condition)

        # Less than 3 months means newer (received_date > threshold)
        assert "received_date > ?" in sql
        assert len(params) == 1

    def test_build_sql_condition_date_direct_date(self, temp_db):
        """Test building SQL condition with direct date string"""
        condition = {
            "field": "Received Date",
            "predicate": "Less than",
            "value": "2024-01-01",
        }
        sql, params = temp_db._build_sql_condition(condition)

        # Less than means newer (received_date > threshold)
        assert "received_date > ?" in sql
        assert len(params) == 1

    def test_build_sql_condition_date_field_variations(self, temp_db):
        """Test that different date field names map to same column"""
        variations = ["Received Date", "Received Date/Time", "Date Received"]
        for field in variations:
            condition = {
                "field": field,
                "predicate": "Greater than",
                "value": "30 days",
            }
            sql, params = temp_db._build_sql_condition(condition)
            assert "received_date" in sql

    def test_build_sql_condition_unknown_field(self, temp_db):
        """Test building SQL condition for unknown field returns false condition"""
        condition = {"field": "Unknown Field", "predicate": "Contains", "value": "test"}
        sql, params = temp_db._build_sql_condition(condition)

        assert sql == "1 = 0"
        assert params == []

    def test_build_sql_condition_unknown_predicate(self, temp_db):
        """Test building SQL condition with unknown predicate"""
        condition = {
            "field": "Subject",
            "predicate": "Unknown Predicate",
            "value": "test",
        }
        sql, params = temp_db._build_sql_condition(condition)

        assert sql == "1 = 0"
        assert params == []

    def test_build_sql_condition_invalid_date(self, temp_db):
        """Test building SQL condition with invalid date value"""
        condition = {
            "field": "Received Date",
            "predicate": "Greater than",
            "value": "invalid date",
        }
        sql, params = temp_db._build_sql_condition(condition)

        # Should return false condition on error
        assert sql == "1 = 0"
        assert params == []


class TestRuleBasedQuerying:
    """Test querying emails by rule conditions"""

    def test_get_emails_by_rule_all_predicate(self, temp_db):
        """Test getting emails matching rule with All predicate"""
        # Insert test emails
        emails = [
            {
                "id": "match1",
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "message_body": "Test content",
                "received_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
            {
                "id": "nomatch1",
                "from": "other@example.com",
                "to": "recipient@example.com",
                "subject": "Other Subject",
                "message_body": "Other content",
                "received_date": (datetime.now() - timedelta(days=5)).isoformat(),
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
                {"field": "From", "predicate": "Contains", "value": "sender"},
                {"field": "Subject", "predicate": "Contains", "value": "Test"},
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        assert len(matching) == 1
        assert matching[0]["id"] == "match1"

    def test_get_emails_by_rule_any_predicate(self, temp_db):
        """Test getting emails matching rule with Any predicate"""
        emails = [
            {
                "id": "match1",
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Other Subject",
                "message_body": "Content",
                "received_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
            {
                "id": "match2",
                "from": "other@example.com",
                "to": "recipient@example.com",
                "subject": "Test Subject",
                "message_body": "Content",
                "received_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
            {
                "id": "nomatch1",
                "from": "other@example.com",
                "to": "recipient@example.com",
                "subject": "Other Subject",
                "message_body": "Content",
                "received_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
        ]
        for email in emails:
            temp_db.insert_email(email)

        rule = {
            "predicate": "Any",
            "conditions": [
                {"field": "From", "predicate": "Contains", "value": "sender"},
                {"field": "Subject", "predicate": "Contains", "value": "Test"},
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        assert len(matching) == 2
        assert all(e["id"] in ["match1", "match2"] for e in matching)

    def test_get_emails_by_rule_date_condition(self, temp_db):
        """Test getting emails matching date-based rule"""
        now = datetime.now()
        emails = [
            {
                "id": "old1",
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Old Email",
                "message_body": "Content",
                "received_date": (now - timedelta(days=45)).isoformat(),
                "is_read": False,
                "labels": [],
                "raw_data": {},
            },
            {
                "id": "new1",
                "from": "sender@example.com",
                "to": "recipient@example.com",
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
                {
                    "field": "Received Date",
                    "predicate": "Greater than",
                    "value": "30 days",
                },
            ],
        }

        matching = temp_db.get_emails_by_rule(rule)
        assert len(matching) == 1
        assert matching[0]["id"] == "old1"

    def test_get_emails_by_rule_no_conditions(self, temp_db):
        """Test getting emails with rule that has no conditions"""
        rule = {"predicate": "All", "conditions": []}
        matching = temp_db.get_emails_by_rule(rule)
        assert matching == []

    def test_get_emails_by_rule_unknown_predicate(self, temp_db):
        """Test getting emails with unknown predicate"""
        rule = {
            "predicate": "Unknown",
            "conditions": [
                {"field": "Subject", "predicate": "Contains", "value": "test"},
            ],
        }
        matching = temp_db.get_emails_by_rule(rule)
        assert matching == []

    def test_get_emails_by_rule_case_insensitive(self, temp_db):
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
