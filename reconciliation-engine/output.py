"""
Output generation and audit logging.
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List
import config
from matching import MatchResult


def ensure_client_structure(client_id: str) -> dict:
    """
    Ensure client directory structure exists.

    Args:
        client_id: Client identifier

    Returns:
        Dictionary with paths to client directories
    """
    base_path = Path(config.CLIENTS_DIR) / client_id

    paths = {
        'base': base_path,
        'input': base_path / 'input',
        'output': base_path / 'output',
        'feedback_db': base_path / 'feedback.db',
        'audit_log': base_path / 'audit.log'
    }

    # Create directories if they don't exist
    paths['input'].mkdir(parents=True, exist_ok=True)
    paths['output'].mkdir(parents=True, exist_ok=True)

    return paths


def generate_output_csv(
    results: List[MatchResult],
    our_book: pd.DataFrame,
    bank_book: pd.DataFrame,
    output_path: Path
) -> None:
    """
    Generate reconciliation output CSV.

    Output columns:
    our_ref, bank_ref, our_amount, bank_amount, delta, match_type,
    status, similarity_score, notes

    Args:
        results: List of match results
        our_book: Our book dataframe
        bank_book: Bank book dataframe
        output_path: Path to output CSV file
    """
    rows = []

    for result in results:
        row = {
            'our_ref': result.our_ref if result.our_ref is not None else '',
            'bank_ref': result.bank_ref if result.bank_ref is not None else '',
            'our_amount': result.our_amount if result.our_amount is not None else '',
            'bank_amount': result.bank_amount if result.bank_amount is not None else '',
            'delta': result.delta if result.delta is not None else '',
            'match_type': result.match_type,
            'status': result.status,
            'similarity_score': f"{result.similarity_score:.4f}",
            'notes': result.notes
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Sort by status for easier review
    status_order = {
        config.STATUS_BREAK: 0,
        config.STATUS_UNMATCHED_OURS: 1,
        config.STATUS_UNMATCHED_BANK: 2,
        config.STATUS_MATCHED: 3
    }
    df['_sort_order'] = df['status'].map(status_order)
    df = df.sort_values('_sort_order').drop(columns=['_sort_order'])

    # Write to CSV
    df.to_csv(output_path, index=False)
    print(f"\nOutput CSV written to: {output_path}")


def write_audit_log(
    audit_log_path: Path,
    client_id: str,
    our_file: str,
    bank_file: str,
    results: List[MatchResult]
) -> None:
    """
    Append audit log entry for this reconciliation run.

    Args:
        audit_log_path: Path to audit log file
        client_id: Client identifier
        our_file: Path to our book file
        bank_file: Path to bank book file
        results: List of match results
    """
    timestamp = datetime.now().isoformat()

    # Count results by status
    status_counts = {
        config.STATUS_MATCHED: 0,
        config.STATUS_BREAK: 0,
        config.STATUS_UNMATCHED_OURS: 0,
        config.STATUS_UNMATCHED_BANK: 0
    }

    for result in results:
        if result.status in status_counts:
            status_counts[result.status] += 1

    # Build log entry
    log_entry = (
        f"\n{'='*80}\n"
        f"Timestamp: {timestamp}\n"
        f"Client: {client_id}\n"
        f"Our Book: {our_file}\n"
        f"Bank Book: {bank_file}\n"
        f"Total Records: {len(results)}\n"
        f"  - MATCHED: {status_counts[config.STATUS_MATCHED]}\n"
        f"  - BREAK: {status_counts[config.STATUS_BREAK]}\n"
        f"  - UNMATCHED_OURS: {status_counts[config.STATUS_UNMATCHED_OURS]}\n"
        f"  - UNMATCHED_BANK: {status_counts[config.STATUS_UNMATCHED_BANK]}\n"
        f"{'='*80}\n"
    )

    # Append to log file
    with open(audit_log_path, 'a') as f:
        f.write(log_entry)

    print(f"Audit log updated: {audit_log_path}")


def print_summary(results: List[MatchResult]) -> None:
    """
    Print reconciliation summary to console.

    Args:
        results: List of match results
    """
    # Count results by status
    status_counts = {
        config.STATUS_MATCHED: 0,
        config.STATUS_BREAK: 0,
        config.STATUS_UNMATCHED_OURS: 0,
        config.STATUS_UNMATCHED_BANK: 0
    }

    match_type_counts = {
        config.MATCH_TYPE_ID: 0,
        config.MATCH_TYPE_SEMANTIC: 0,
        config.MATCH_TYPE_NONE: 0
    }

    for result in results:
        if result.status in status_counts:
            status_counts[result.status] += 1
        if result.match_type in match_type_counts:
            match_type_counts[result.match_type] += 1

    print("\n" + "="*80)
    print("RECONCILIATION SUMMARY")
    print("="*80)

    print("\nMatch Type Breakdown:")
    print(f"  ID Matches:       {match_type_counts[config.MATCH_TYPE_ID]:>6}")
    print(f"  Semantic Matches: {match_type_counts[config.MATCH_TYPE_SEMANTIC]:>6}")
    print(f"  No Match:         {match_type_counts[config.MATCH_TYPE_NONE]:>6}")

    print("\nStatus Breakdown:")
    print(f"  MATCHED:        {status_counts[config.STATUS_MATCHED]:>6} (amounts agree)")
    print(f"  BREAK:          {status_counts[config.STATUS_BREAK]:>6} (amounts differ)")
    print(f"  UNMATCHED_OURS: {status_counts[config.STATUS_UNMATCHED_OURS]:>6} (in our book only)")
    print(f"  UNMATCHED_BANK: {status_counts[config.STATUS_UNMATCHED_BANK]:>6} (in bank book only)")

    print(f"\nTotal Records:    {len(results):>6}")

    # Calculate reconciliation rate
    matched_count = status_counts[config.STATUS_MATCHED]
    total_count = len(results)
    if total_count > 0:
        match_rate = (matched_count / total_count) * 100
        print(f"Match Rate:       {match_rate:>6.2f}%")

    print("="*80 + "\n")
