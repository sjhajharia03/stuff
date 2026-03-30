"""
Feedback storage for analyst overrides.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class FeedbackStore:
    """
    Manages analyst feedback and overrides in SQLite.

    Analysts can:
    - Confirm a match is correct
    - Reject a match as incorrect
    - Override suggested matches
    """

    def __init__(self, db_path: Path):
        """
        Initialize feedback store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                our_ref TEXT NOT NULL,
                bank_ref TEXT,
                action TEXT NOT NULL,
                notes TEXT,
                analyst TEXT
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_our_ref ON feedback(our_ref)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bank_ref ON feedback(bank_ref)
        """)

        conn.commit()
        conn.close()

    def record_confirmation(
        self,
        our_ref: str,
        bank_ref: str,
        analyst: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Record that an analyst confirmed a match is correct.

        Args:
            our_ref: Our reference ID
            bank_ref: Bank reference ID
            analyst: Analyst name/ID
            notes: Optional notes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO feedback (timestamp, our_ref, bank_ref, action, notes, analyst)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            our_ref,
            bank_ref,
            'CONFIRM',
            notes,
            analyst
        ))

        conn.commit()
        conn.close()

    def record_rejection(
        self,
        our_ref: str,
        bank_ref: str,
        analyst: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Record that an analyst rejected a match as incorrect.

        Args:
            our_ref: Our reference ID
            bank_ref: Bank reference ID
            analyst: Analyst name/ID
            notes: Optional notes (reason for rejection)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO feedback (timestamp, our_ref, bank_ref, action, notes, analyst)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            our_ref,
            bank_ref,
            'REJECT',
            notes,
            analyst
        ))

        conn.commit()
        conn.close()

    def record_override(
        self,
        our_ref: str,
        correct_bank_ref: str,
        analyst: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Record an analyst override for the correct match.

        Args:
            our_ref: Our reference ID
            correct_bank_ref: The correct bank reference ID
            analyst: Analyst name/ID
            notes: Optional notes (reason for override)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO feedback (timestamp, our_ref, bank_ref, action, notes, analyst)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            our_ref,
            correct_bank_ref,
            'OVERRIDE',
            notes,
            analyst
        ))

        conn.commit()
        conn.close()

    def get_feedback_for_ref(self, our_ref: str) -> list[dict]:
        """
        Get all feedback for a given reference.

        Args:
            our_ref: Our reference ID

        Returns:
            List of feedback records (most recent first)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, our_ref, bank_ref, action, notes, analyst
            FROM feedback
            WHERE our_ref = ?
            ORDER BY timestamp DESC
        """, (our_ref,))

        rows = cursor.fetchall()
        conn.close()

        feedback = []
        for row in rows:
            feedback.append({
                'id': row[0],
                'timestamp': row[1],
                'our_ref': row[2],
                'bank_ref': row[3],
                'action': row[4],
                'notes': row[5],
                'analyst': row[6]
            })

        return feedback

    def get_all_overrides(self) -> dict[str, str]:
        """
        Get all override mappings.

        Returns:
            Dictionary mapping our_ref -> bank_ref for all overrides
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get most recent override for each our_ref
        cursor.execute("""
            SELECT our_ref, bank_ref
            FROM feedback
            WHERE action = 'OVERRIDE'
            AND (our_ref, timestamp) IN (
                SELECT our_ref, MAX(timestamp)
                FROM feedback
                WHERE action = 'OVERRIDE'
                GROUP BY our_ref
            )
        """)

        rows = cursor.fetchall()
        conn.close()

        overrides = {row[0]: row[1] for row in rows}
        return overrides

    def get_all_rejections(self) -> set[tuple[str, str]]:
        """
        Get all rejected match pairs.

        Returns:
            Set of (our_ref, bank_ref) tuples that have been rejected
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT our_ref, bank_ref
            FROM feedback
            WHERE action = 'REJECT'
        """)

        rows = cursor.fetchall()
        conn.close()

        rejections = {(row[0], row[1]) for row in rows}
        return rejections

    def get_statistics(self) -> dict:
        """
        Get feedback statistics.

        Returns:
            Dictionary with counts by action type
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM feedback
            GROUP BY action
        """)

        rows = cursor.fetchall()
        conn.close()

        stats = {row[0]: row[1] for row in rows}
        return stats
