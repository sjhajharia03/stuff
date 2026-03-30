#!/usr/bin/env python3
"""
Inter-Party Book Reconciliation Engine - CLI Entrypoint

Usage:
    python reconcile.py --client <client_id> --our-book <file_a.csv> --bank-book <file_b.csv>
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from ingestion import prepare_books
from matching import ReconciliationEngine
from output import ensure_client_structure, generate_output_csv, write_audit_log, print_summary
from feedback import FeedbackStore
import config


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Inter-Party Book Reconciliation Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reconcile.py --client bank_a --our-book data/our_book.csv --bank-book data/bank_book.csv
  python reconcile.py --client bank_b --our-book our.csv --bank-book bank.csv --output report.csv
        """
    )

    parser.add_argument(
        '--client',
        required=True,
        help='Client identifier (e.g., bank_a, bank_b)'
    )

    parser.add_argument(
        '--our-book',
        required=True,
        help='Path to our book CSV file'
    )

    parser.add_argument(
        '--bank-book',
        required=True,
        help='Path to bank book CSV file'
    )

    parser.add_argument(
        '--output',
        help='Custom output CSV filename (default: reconciliation_YYYYMMDD_HHMMSS.csv)'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        help=f'Semantic similarity threshold (default: {config.SEMANTIC_THRESHOLD})'
    )

    args = parser.parse_args()

    # Override threshold if provided
    if args.threshold is not None:
        config.SEMANTIC_THRESHOLD = args.threshold

    print("="*80)
    print("INTER-PARTY BOOK RECONCILIATION ENGINE")
    print("="*80)
    print(f"Client: {args.client}")
    print(f"Semantic threshold: {config.SEMANTIC_THRESHOLD}")
    print(f"Amount tolerance: ${config.AMOUNT_TOLERANCE}")
    print("="*80)

    try:
        # Ensure client directory structure exists
        print("\nSetting up client directory structure...")
        client_paths = ensure_client_structure(args.client)
        print(f"Client directory: {client_paths['base']}")

        # Initialize feedback store
        feedback_store = FeedbackStore(client_paths['feedback_db'])

        # Load and prepare books
        print("\n" + "="*80)
        print("LOADING BOOKS")
        print("="*80)
        our_book, bank_book = prepare_books(args.our_book, args.bank_book)

        # Perform reconciliation
        print("\n" + "="*80)
        print("PERFORMING RECONCILIATION")
        print("="*80)

        engine = ReconciliationEngine()
        results = engine.reconcile(our_book, bank_book)

        # Generate output
        print("\n" + "="*80)
        print("GENERATING OUTPUT")
        print("="*80)

        # Determine output filename
        if args.output:
            output_filename = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"reconciliation_{timestamp}.csv"

        output_path = client_paths['output'] / output_filename

        # Write CSV output
        generate_output_csv(results, our_book, bank_book, output_path)

        # Write audit log
        write_audit_log(
            client_paths['audit_log'],
            args.client,
            args.our_book,
            args.bank_book,
            results
        )

        # Print summary
        print_summary(results)

        # Print feedback statistics if any exist
        feedback_stats = feedback_store.get_statistics()
        if feedback_stats:
            print("Feedback Statistics:")
            for action, count in feedback_stats.items():
                print(f"  {action}: {count}")
            print()

        print(f"Reconciliation complete. Results written to: {output_path}")
        print(f"Audit log: {client_paths['audit_log']}")
        print(f"Feedback database: {client_paths['feedback_db']}")

        return 0

    except FileNotFoundError as e:
        print(f"\nError: File not found - {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
