"""
Smart column detection that analyzes content patterns, not just names.
"""

import pandas as pd
import re
from typing import Optional, Dict
import config


class ColumnDetector:
    """
    Intelligently detects column types by analyzing content patterns.
    Falls back to name matching if content analysis is inconclusive.
    """

    @staticmethod
    def _is_likely_id(series: pd.Series) -> float:
        """
        Score how likely a column is an ID field (0-1).

        ID characteristics:
        - Unique or mostly unique values
        - Contains numbers, letters, or mix
        - May have prefixes/suffixes
        - Not too long (< 50 chars typically)
        """
        if len(series) == 0:
            return 0.0

        score = 0.0
        sample = series.dropna().head(100)

        if len(sample) == 0:
            return 0.0

        # Check uniqueness
        uniqueness = len(sample.unique()) / len(sample)
        score += uniqueness * 0.4

        # Check for ID-like patterns (alphanumeric with separators)
        sample_str = sample.astype(str)
        id_pattern = r'^[A-Z0-9\-_\.]+$'
        pattern_matches = sample_str.str.match(id_pattern, case=False).sum()
        score += (pattern_matches / len(sample)) * 0.3

        # Check average length (IDs are typically short)
        avg_length = sample_str.str.len().mean()
        if 3 <= avg_length <= 30:
            score += 0.3
        elif avg_length < 3:
            score += 0.1

        return min(score, 1.0)

    @staticmethod
    def _is_likely_amount(series: pd.Series) -> float:
        """
        Score how likely a column is an amount field (0-1).

        Amount characteristics:
        - Numeric values
        - Positive numbers (usually)
        - Reasonable range (not dates, not IDs)
        """
        if len(series) == 0:
            return 0.0

        score = 0.0
        sample = series.dropna().head(100)

        if len(sample) == 0:
            return 0.0

        # Check if numeric
        try:
            numeric_sample = pd.to_numeric(sample, errors='coerce')
            non_null_count = numeric_sample.notna().sum()
            numeric_ratio = non_null_count / len(sample)
            score += numeric_ratio * 0.5

            if numeric_ratio > 0.5:
                # Check if values are in reasonable amount range
                valid_values = numeric_sample.dropna()
                if len(valid_values) > 0:
                    # Amounts are typically > 0 and < 1 billion
                    positive_ratio = (valid_values > 0).sum() / len(valid_values)
                    score += positive_ratio * 0.3

                    # Check if not date-like (dates would be large numbers)
                    reasonable_range = ((valid_values < 1e10) & (valid_values > 0)).sum() / len(valid_values)
                    score += reasonable_range * 0.2
        except:
            return 0.0

        return min(score, 1.0)

    @staticmethod
    def _is_likely_description(series: pd.Series) -> float:
        """
        Score how likely a column is a description field (0-1).

        Description characteristics:
        - Text values
        - Longer strings (> 10 chars typically)
        - May contain spaces and punctuation
        - Not highly unique (descriptions can repeat)
        """
        if len(series) == 0:
            return 0.0

        score = 0.0
        sample = series.dropna().head(100)

        if len(sample) == 0:
            return 0.0

        sample_str = sample.astype(str)

        # Check average length (descriptions are longer)
        avg_length = sample_str.str.len().mean()
        if avg_length > 15:
            score += 0.4
        elif avg_length > 10:
            score += 0.2

        # Check for spaces (descriptions have spaces)
        has_spaces = sample_str.str.contains(' ').sum() / len(sample)
        score += has_spaces * 0.3

        # Check for text content (not just numbers)
        has_letters = sample_str.str.contains('[a-zA-Z]').sum() / len(sample)
        score += has_letters * 0.3

        return min(score, 1.0)

    @staticmethod
    def _is_likely_date(series: pd.Series) -> float:
        """
        Score how likely a column is a date field (0-1).
        """
        if len(series) == 0:
            return 0.0

        score = 0.0
        sample = series.dropna().head(100)

        if len(sample) == 0:
            return 0.0

        # Try to parse as datetime
        try:
            parsed = pd.to_datetime(sample, errors='coerce')
            parse_success = parsed.notna().sum() / len(sample)
            score += parse_success * 1.0
        except:
            return 0.0

        return min(score, 1.0)

    def detect_columns(self, df: pd.DataFrame, book_type: str = "unknown") -> Dict[str, Optional[str]]:
        """
        Detect column types using both content analysis and name matching.

        Args:
            df: DataFrame to analyze
            book_type: Type of book for logging

        Returns:
            Dictionary with keys: 'id', 'description', 'amount', 'date'
        """
        result = {
            'id': None,
            'description': None,
            'amount': None,
            'date': None
        }

        print(f"\nDetecting columns for {book_type} book...")
        print(f"Available columns: {', '.join(df.columns)}")

        # Score each column for each type
        scores = {col: {} for col in df.columns}

        for col in df.columns:
            col_lower = col.lower()

            # Content-based scoring
            scores[col]['id'] = self._is_likely_id(df[col])
            scores[col]['amount'] = self._is_likely_amount(df[col])
            scores[col]['description'] = self._is_likely_description(df[col])
            scores[col]['date'] = self._is_likely_date(df[col])

            # Name-based boost (if column name matches known patterns)
            if any(field.lower() in col_lower for field in config.ID_FIELDS):
                scores[col]['id'] += 0.3
            if any(field.lower() in col_lower for field in config.AMOUNT_FIELDS):
                scores[col]['amount'] += 0.3
            if any(field.lower() in col_lower for field in config.DESCRIPTION_FIELDS):
                scores[col]['description'] += 0.3
            if any(field.lower() in col_lower for field in config.DATE_FIELDS):
                scores[col]['date'] += 0.3

            # Cap at 1.0
            for key in scores[col]:
                scores[col][key] = min(scores[col][key], 1.0)

        # Select best column for each type
        for col_type in ['id', 'amount', 'description', 'date']:
            best_col = None
            best_score = 0.5  # Minimum confidence threshold

            for col in df.columns:
                if scores[col][col_type] > best_score:
                    best_score = scores[col][col_type]
                    best_col = col

            result[col_type] = best_col
            if best_col:
                print(f"  {col_type.upper()}: '{best_col}' (confidence: {best_score:.2f})")
            else:
                print(f"  {col_type.upper()}: NOT FOUND (all scores < 0.5)")

        return result
