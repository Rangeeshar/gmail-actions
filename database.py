"""
Database module for storing and retrieving emails using SQLite3
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from dateutil import parser as date_parser

from config import DATABASE_PATH


class EmailDatabase:
    """Handles all database operations for emails"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database and create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                from_address TEXT,
                to_address TEXT,
                subject TEXT,
                message_body TEXT,
                received_date TIMESTAMP,
                is_read INTEGER DEFAULT 0,
                labels TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_from ON emails(from_address)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_to ON emails(to_address)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subject ON emails(subject)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_body ON emails(message_body)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_received_date ON emails(received_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_is_read ON emails(is_read)
        """)

        conn.commit()
        conn.close()

    def insert_email(self, email_data: Dict) -> bool:
        """Insert or update an email in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO emails 
                (id, thread_id, from_address, to_address, subject, message_body, 
                 received_date, is_read, labels, raw_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email_data["id"],
                    email_data.get("thread_id", ""),
                    email_data.get("from", ""),
                    email_data.get("to", ""),
                    email_data.get("subject", ""),
                    email_data.get("message_body", ""),
                    email_data.get("received_date"),
                    1 if email_data.get("is_read", False) else 0,
                    json.dumps(email_data.get("labels", [])),
                    json.dumps(email_data.get("raw_data", {})),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return True
        except (sqlite3.Error, KeyError, ValueError) as e:
            print(f"Error inserting email: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_all_emails(self) -> List[Dict]:
        """Retrieve all emails from the database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM emails ORDER BY received_date DESC")
        rows = cursor.fetchall()

        emails = []
        for row in rows:
            email = dict(row)
            email["labels"] = json.loads(email["labels"]) if email["labels"] else []
            email["raw_data"] = (
                json.loads(email["raw_data"]) if email["raw_data"] else {}
            )
            email["is_read"] = bool(email["is_read"])
            emails.append(email)

        conn.close()
        return emails

    def get_email_by_id(self, email_id: str) -> Optional[Dict]:
        """Retrieve a specific email by its ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
        row = cursor.fetchone()

        if row:
            email = dict(row)
            email["labels"] = json.loads(email["labels"]) if email["labels"] else []
            email["raw_data"] = (
                json.loads(email["raw_data"]) if email["raw_data"] else {}
            )
            email["is_read"] = bool(email["is_read"])
            conn.close()
            return email

        conn.close()
        return None

    def update_email_read_status(self, email_id: str, is_read: bool) -> bool:
        """Update the read status of an email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE emails 
                SET is_read = ?, updated_at = ?
                WHERE id = ?
            """,
                (1 if is_read else 0, datetime.now().isoformat(), email_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except (sqlite3.Error, ValueError) as e:
            print(f"Error updating email read status: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_unprocessed_emails(self) -> List[Dict]:
        """Get emails that haven't been processed yet (for rule processing)"""
        return self.get_all_emails()

    def clear_all_emails(self) -> None:
        """Clear all emails from the database (useful for testing)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emails")
        conn.commit()
        conn.close()

    def _build_sql_condition(self, condition: Dict) -> Tuple[str, List]:
        """
        Build a SQL WHERE condition from a rule condition.
        Returns (sql_fragment, parameter_values)
        """
        field = condition.get("field", "").lower()
        predicate = condition.get("predicate", "").lower()
        value = condition.get("value", "")

        # Map rule fields to database columns
        field_mapping = {
            "from": "from_address",
            "to": "to_address",
            "subject": "subject",
            "message": "message_body",
            "received date": "received_date",
            "received date/time": "received_date",
            "date received": "received_date",
        }

        db_column = field_mapping.get(field)
        if not db_column:
            # Return a condition that always evaluates to false
            return "1 = 0", []

        # Handle string field predicates
        if field in ["from", "to", "subject", "message"]:
            value_lower = str(value).lower()
            if predicate == "contains":
                return f"LOWER({db_column}) LIKE ?", [f"%{value_lower}%"]
            elif predicate == "does not contain":
                return f"LOWER({db_column}) NOT LIKE ?", [f"%{value_lower}%"]
            elif predicate == "equals":
                return f"LOWER({db_column}) = ?", [value_lower]
            elif predicate == "does not equal":
                return f"LOWER({db_column}) != ?", [value_lower]

        # Handle date field predicates
        elif field in ["received date", "received date/time", "date received"]:
            try:
                value_str = str(value).lower().strip()

                # Parse value - can be "X days" or "X months"
                if "day" in value_str:
                    days = int(value_str.split()[0])
                    threshold_date = datetime.now() - timedelta(days=days)
                elif "month" in value_str:
                    months = int(value_str.split()[0])
                    threshold_date = datetime.now() - timedelta(days=months * 30)
                else:
                    # Try to parse as direct date
                    threshold_date = date_parser.parse(value_str)

                threshold_iso = threshold_date.isoformat()

                if predicate == "less than":
                    # Less than X days means newer (received less than X days ago)
                    return f"{db_column} > ?", [threshold_iso]
                elif predicate == "greater than":
                    # Greater than X days means older (received more than X days ago)
                    return f"{db_column} < ?", [threshold_iso]
            except (ValueError, TypeError) as e:
                print(f"Error parsing date condition: {e}")
                return "1 = 0", []

        # Unknown predicate
        return "1 = 0", []

    def get_emails_by_rule(self, rule: Dict) -> List[Dict]:
        """
        Retrieve emails that match a rule's conditions using SQL filtering.
        This is much more efficient than fetching all emails and filtering in Python.
        """
        conditions = rule.get("conditions", [])
        predicate = rule.get("predicate", "all").lower()

        if not conditions:
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Build WHERE clause from conditions
            where_parts = []
            all_params = []

            for condition in conditions:
                sql_fragment, params = self._build_sql_condition(condition)
                where_parts.append(f"({sql_fragment})")
                all_params.extend(params)

            if not where_parts:
                return []

            # Combine conditions based on predicate (all = AND, any = OR)
            if predicate == "all":
                where_clause = " AND ".join(where_parts)
            elif predicate == "any":
                where_clause = " OR ".join(where_parts)
            else:
                print(f"Unknown predicate: {predicate}")
                return []

            # Execute query
            query = (
                f"SELECT * FROM emails WHERE {where_clause} ORDER BY received_date DESC"
            )
            cursor.execute(query, all_params)
            rows = cursor.fetchall()

            # Convert rows to dictionaries
            emails = []
            for row in rows:
                email = dict(row)
                email["labels"] = json.loads(email["labels"]) if email["labels"] else []
                email["raw_data"] = (
                    json.loads(email["raw_data"]) if email["raw_data"] else {}
                )
                email["is_read"] = bool(email["is_read"])
                emails.append(email)

            return emails
        except (sqlite3.Error, ValueError, KeyError) as e:
            print(f"Error querying emails by rule: {e}")
            return []
        finally:
            conn.close()
