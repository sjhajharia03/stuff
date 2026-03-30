"""
CSV ingestion and data normalization utilities.
"""

import pandas as pd
import re
from typing import Optional, List
import config


def normalize_id(id_value: any) -> str:
    """
    Normalize a reference/trade ID for matching.

    Critical function that standardizes IDs by:
    - Converting to string
    - Lowercasing
    - Removing whitespace
    - Removing common separators (-, _, .)

    This is where most real-world breaks come from in practice.

    Args:
        id_value: The ID value to normalize (any type)

    Returns:
        Normalized ID string
    """
    if pd.isna(id_value):
        return ""

    # Convert to string
    normalized = str(id_value).strip()

    # Lowercase
    normalized = normalized.lower()

    # Remove common separators and whitespace
    normalized = re.sub(r'[-_.\s]', '', normalized)

    return normalized


def find_column(df: pd.DataFrame, possible_names: List[str], column_type: str) -> Optional[str]:
    """
    Find a column in the dataframe by trying multiple possible names.

    Args:
        df: The dataframe to search
        possible_names: List of possible column names to try
        column_type: Type of column being searched (for error messages)

    Returns:
        The actual column name found, or None if not found
    """
    # Try exact matches first (case-insensitive)
    df_columns_lower = {col.lower(): col for col in df.columns}

    for name in possible_names:
        if name.lower() in df_columns_lower:
            return df_columns_lower[name.lower()]

    return None


def load_book(file_path: str, book_type: str) -> pd.DataFrame:
    """
    Load a CSV book file and identify key columns.

    Args:
        file_path: Path to the CSV file
        book_type: Type of book ('our' or 'bank') for error messages

    Returns:
        DataFrame with standardized column names

    Raises:
        ValueError: If required columns are not found
    """
    # Load CSV
    df = pd.read_csv(file_path)

    if df.empty:
        raise ValueError(f"{book_type} book is empty: {file_path}")

    # Find ID column
    id_col = find_column(df, config.ID_FIELDS, "ID")
    if not id_col:
        raise ValueError(
            f"Could not find ID column in {book_type} book. "
            f"Tried: {', '.join(config.ID_FIELDS)}. "
            f"Available columns: {', '.join(df.columns)}"
        )

    # Find description column
    desc_col = find_column(df, config.DESCRIPTION_FIELDS, "description")
    if not desc_col:
        raise ValueError(
            f"Could not find description column in {book_type} book. "
            f"Tried: {', '.join(config.DESCRIPTION_FIELDS)}. "
            f"Available columns: {', '.join(df.columns)}"
        )

    # Find amount column
    amount_col = find_column(df, config.AMOUNT_FIELDS, "amount")
    if not amount_col:
        raise ValueError(
            f"Could not find amount column in {book_type} book. "
            f"Tried: {', '.join(config.AMOUNT_FIELDS)}. "
            f"Available columns: {', '.join(df.columns)}"
        )

    # Find date column (optional)
    date_col = find_column(df, config.DATE_FIELDS, "date")

    # Create standardized dataframe
    result = pd.DataFrame()
    result['original_index'] = df.index
    result['id_raw'] = df[id_col]
    result['id_normalized'] = df[id_col].apply(normalize_id)
    result['description'] = df[desc_col]
    result['amount'] = pd.to_numeric(df[amount_col], errors='coerce')

    if date_col:
        result['date'] = pd.to_datetime(df[date_col], errors='coerce')
    else:
        result['date'] = None

    # Keep all original columns for reference in output
    for col in df.columns:
        result[f'original_{col}'] = df[col]

    # Check for NaN amounts
    nan_count = result['amount'].isna().sum()
    if nan_count > 0:
        print(f"Warning: {nan_count} rows in {book_type} book have invalid amounts")

    return result


def prepare_books(our_file: str, bank_file: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load and prepare both books for reconciliation.

    Args:
        our_file: Path to our book CSV
        bank_file: Path to bank book CSV

    Returns:
        Tuple of (our_book_df, bank_book_df)
    """
    print(f"Loading our book: {our_file}")
    our_book = load_book(our_file, "our")
    print(f"  Loaded {len(our_book)} records")

    print(f"Loading bank book: {bank_file}")
    bank_book = load_book(bank_file, "bank")
    print(f"  Loaded {len(bank_book)} records")

    return our_book, bank_book
