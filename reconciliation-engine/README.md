# Inter-Party Book Reconciliation Engine - MVP

A Python-based CLI tool for reconciling trade/transaction books between professional services firms and their bank clients. Uses intelligent ID-first matching with semantic similarity fallback.

## Overview

This engine reconciles two CSV files (firm's book vs. bank's book) using a two-phase matching strategy:

1. **Phase 1: ID Matching** - Attempts exact match on normalized reference/trade IDs
2. **Phase 2: Semantic Matching** - Falls back to semantic similarity on descriptions for unmatched records
3. **Amount Validation** - Treats amounts as a hard constraint (exact match required, not a scoring weight)

## Features

- **Intelligent ID Normalization**: Strips whitespace, lowercases, removes separators (`-`, `_`, `.`)
- **Semantic Similarity**: Uses sentence-transformers (`all-MiniLM-L6-v2`) for description matching
- **Break Classification**:
  - `MATCHED` - Match found, amounts agree
  - `BREAK` - Match found, amounts differ
  - `UNMATCHED_OURS` - In firm's book only
  - `UNMATCHED_BANK` - In bank's book only
- **Per-Client Organization**: Automatic folder structure with input/output/feedback/audit
- **Audit Logging**: Every run logged with timestamp and match statistics
- **Feedback System**: SQLite database for analyst overrides and confirmations
- **Fully Offline**: No API calls, works entirely locally

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
python reconcile.py --client bank_a --our-book sample_our_book.csv --bank-book sample_bank_book.csv
```

## Usage

### Basic Reconciliation

```bash
python reconcile.py --client <client_id> --our-book <our_file.csv> --bank-book <bank_file.csv>
```

### Custom Output Filename

```bash
python reconcile.py --client bank_a --our-book our.csv --bank-book bank.csv --output report_jan_2024.csv
```

### Adjust Semantic Threshold

```bash
python reconcile.py --client bank_a --our-book our.csv --bank-book bank.csv --threshold 0.75
```

## Input File Format

CSV files should contain columns for:
- **Reference/Trade ID**: Any of `trade_id`, `ref_id`, `reference`, `transaction_id`, etc.
- **Description**: Any of `description`, `narrative`, `details`, etc.
- **Amount**: Any of `amount`, `value`, `total`, etc.
- **Date** (optional): Any of `date`, `trade_date`, `transaction_date`, etc.

The engine automatically detects column names from the configured list.

## Output Format

CSV with columns:
```
our_ref, bank_ref, our_amount, bank_amount, delta, match_type, status, similarity_score, notes
```

Sorted by status (breaks first, then unmatched, then matched).

## Project Structure

```
reconcile.py          # CLI entrypoint
config.py            # Configuration and constants
ingestion.py         # CSV loading and ID normalization
embedding.py         # Sentence transformer embeddings
matching.py          # Core reconciliation logic
output.py            # CSV output and audit logging
feedback.py          # SQLite feedback storage
requirements.txt     # Python dependencies

clients/
  {client_id}/
    input/           # Place input files here
    output/          # Reconciliation reports
    feedback.db      # Analyst feedback database
    audit.log        # Audit trail
```

## Configuration

Edit `config.py` to adjust:

- `SEMANTIC_THRESHOLD` (default: 0.80) - Minimum similarity for semantic matches
- `AMOUNT_TOLERANCE` (default: 0.01) - Tolerance for amount comparison
- `ID_FIELDS` - List of possible ID column names
- `DESCRIPTION_FIELDS` - List of possible description column names
- `AMOUNT_FIELDS` - List of possible amount column names
- `DATE_FIELDS` - List of possible date column names

## ID Normalization

The `normalize_id()` function is critical for matching:

1. Converts to string
2. Lowercases
3. Removes whitespace
4. Removes common separators (`-`, `_`, `.`)

Example: `"TRD-001"` → `"trd001"` matches `"TRD_001"` → `"trd001"`

## Matching Logic

### Phase 1: ID Matching
- Normalize IDs on both sides
- Exact string match on normalized IDs
- If match found: check amounts
  - Amounts agree → `MATCHED` (ID)
  - Amounts differ → `BREAK` (ID)

### Phase 2: Semantic Matching (for unmatched records)
- Generate embeddings for descriptions
- Compute cosine similarity matrix
- Find best match above threshold
- If match found: check amounts
  - Amounts agree → `MATCHED` (SEMANTIC)
  - Amounts differ → `BREAK` (SEMANTIC)
- If no match above threshold → `UNMATCHED_OURS`

### Phase 3: Unmatched Bank Records
- Any bank records not matched → `UNMATCHED_BANK`

## Example Scenarios

### Scenario 1: Perfect ID Match
```
Our book:   TRD-001, "Equity purchase", $15000.00
Bank book:  TRD001,  "Equity purchase", $15000.00
Result:     MATCHED (ID match, amounts agree)
```

### Scenario 2: ID Match with Break
```
Our book:   TRD-002, "Bond sale", $25000.50
Bank book:  TRD002,  "Bond sale", $25100.50
Result:     BREAK (ID match, amounts differ by $100.00)
```

### Scenario 3: Semantic Match
```
Our book:   TRD-005, "Stock dividend reinvestment plan execution", $3500.75
Bank book:  XYZ-999, "Stock dividend reinvest program execution",  $3500.75
Result:     MATCHED (SEMANTIC match @ 0.91, amounts agree)
```

### Scenario 4: Semantic Match with Break
```
Our book:   TRD-006, "Derivative contract settlement futures", $18000.00
Bank book:  ABC-888, "Derivative futures contract settlement",  $18500.00
Result:     BREAK (SEMANTIC match @ 0.89, amounts differ by $500.00)
```

### Scenario 5: Unmatched
```
Our book:   TRD-010, "Mutual fund redemption", $22000.00
Bank book:  (no match)
Result:     UNMATCHED_OURS
```

## Feedback System

Analysts can record feedback in the SQLite database:

```python
from feedback import FeedbackStore
from pathlib import Path

store = FeedbackStore(Path("clients/bank_a/feedback.db"))

# Confirm a match is correct
store.record_confirmation("TRD-001", "TRD001", analyst="jane.doe", notes="Verified correct")

# Reject an incorrect match
store.record_rejection("TRD-005", "XYZ-999", analyst="john.smith", notes="Different transactions")

# Override with correct match
store.record_override("TRD-005", "ABC-123", analyst="jane.doe", notes="Manual verification")
```

## Testing

Sample data files are provided:
- `sample_our_book.csv` - Sample firm book with 10 records
- `sample_bank_book.csv` - Sample bank book with 10 records

Test with:
```bash
python reconcile.py --client test_bank --our-book sample_our_book.csv --bank-book sample_bank_book.csv
```

## Technical Stack

- **Python 3.9+**
- **sentence-transformers** - Semantic embeddings
- **scikit-learn** - Cosine similarity computation
- **pandas** - Data manipulation
- **SQLite** - Feedback storage

## Design Principles

1. **ID-first**: Always attempt normalized ID matching before semantic
2. **Amount is binary**: Amounts either match or they don't - no partial credit
3. **Semantic finds candidates**: Similarity score finds the candidate, amount check determines status
4. **Offline-first**: No API calls, fully local operation
5. **Audit everything**: Complete trail of all reconciliation runs
6. **Client isolation**: Each client has separate folders and feedback

## Future Enhancements

- Multi-currency support with exchange rates
- Fuzzy date matching windows
- Machine learning from analyst feedback
- Batch processing multiple client files
- Interactive review mode
- Export to Excel with conditional formatting
- Integration with accounting systems

## License

Proprietary - Internal use only

## Support

For issues or questions, contact the reconciliation team.
