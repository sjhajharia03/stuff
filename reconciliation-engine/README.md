# Inter-Party Book Reconciliation Engine - MVP

A Python-based CLI tool for reconciling trade/transaction books between professional services firms and their bank clients. Uses intelligent multi-strategy matching with smart column detection.

## Overview

This engine reconciles two CSV files (firm's book vs. bank's book) using a **5-phase matching pipeline** that handles real-world scenarios like mismatched IDs, generic descriptions, and varying column names.

### Matching Pipeline

1. **Phase 1: ID Matching** - Exact match on normalized reference/trade IDs
2. **Phase 2: Amount + Date Matching** - Match by exact amount with date proximity (NEW!)
3. **Phase 3: Semantic Matching** - Match using AI-powered description similarity
4. **Phase 4: Amount-Only Matching** - Single amount matches within date window (with warnings)
5. **Phase 5: Mark Unmatched** - Identify records with no counterpart

### Why Multiple Strategies?

Real-world reconciliation data often has:
- ✅ **Different ID schemes** (e.g., "V001" vs "B001") - Amount+Date catches these
- ✅ **Generic descriptions** (e.g., "Auto generated transaction 1") - Amount+Date works when semantic fails
- ✅ **Varying column names** - Smart detection handles "amount", "amount_inr", "value", etc.
- ✅ **Off-by-one dates** - Date proximity scoring handles processing delays

## Key Features

### Smart Column Detection
- **Content-based analysis**: Analyzes data patterns, not just column names
- **Zero manual configuration**: Automatically detects ID, amount, description, and date columns
- **Confidence scoring**: Reports detection confidence for each column
- **Fallback to name matching**: Uses configured column name lists if content analysis is inconclusive

### Multi-Strategy Matching
- **ID Normalization**: Strips whitespace, lowercases, removes separators (`-`, `_`, `.`)
- **Amount+Date Matching**: Catches records with identical amounts and nearby dates
- **Semantic Similarity**: Uses sentence-transformers (`all-MiniLM-L6-v2`) for AI-powered description matching
- **Amount-Only Matching**: Safe fallback for unique amount values (with manual verification warnings)

### Break Classification
- `MATCHED` - Match found, amounts agree exactly
- `BREAK` - Match found, but amounts differ (flags the delta)
- `UNMATCHED_OURS` - In firm's book only (potential missing bank record)
- `UNMATCHED_BANK` - In bank's book only (potential missing firm record)

### Production Features
- **Per-Client Organization**: Automatic folder structure with input/output/feedback/audit
- **Audit Logging**: Every run logged with timestamp and match statistics
- **Feedback System**: SQLite database for analyst overrides and confirmations
- **Fully Offline**: No API calls, works entirely locally
- **Configurable Pipeline**: Enable/disable matching strategies via config

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

## How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     reconcile.py (CLI Entry)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  column_detector.py: Smart Column Detection                     │
│  • Analyzes content patterns (uniqueness, data types, length)   │
│  • Scores each column for ID/amount/description/date likelihood │
│  • Falls back to name matching if needed                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  ingestion.py: Load & Normalize Data                            │
│  • Load CSVs with pandas                                        │
│  • Normalize IDs (strip, lowercase, remove separators)          │
│  • Standardize column names                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  matching.py: 5-Phase Matching Pipeline                         │
│                                                                  │
│  Phase 1: ID Matching                                           │
│    ├─ Build normalized ID lookup table                          │
│    ├─ Exact match on normalized IDs                             │
│    └─ Check amounts: match → MATCHED, differ → BREAK            │
│                                                                  │
│  Phase 2: Amount + Date Matching                                │
│    ├─ Find exact amount matches                                 │
│    ├─ Score date proximity (0-1, linear decay over 7 days)      │
│    └─ Take best date proximity match                            │
│                                                                  │
│  Phase 3: Semantic Matching (embedding.py)                      │
│    ├─ Generate embeddings with sentence-transformers            │
│    ├─ Compute cosine similarity matrix                          │
│    ├─ Match if similarity > threshold (default 0.80)            │
│    └─ Adjust score with date proximity if available             │
│                                                                  │
│  Phase 4: Amount-Only Matching                                  │
│    ├─ Find exact amount matches                                 │
│    ├─ Only if dates within 14-day window                        │
│    ├─ Only if exactly ONE match (avoid ambiguity)               │
│    └─ Flag with WARNING for manual verification                 │
│                                                                  │
│  Phase 5: Mark Unmatched                                        │
│    └─ Flag all remaining records as UNMATCHED                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  output.py: Generate Reports                                    │
│  • Write CSV with match results sorted by status                │
│  • Append to audit log with statistics                          │
│  • Print summary to console                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Algorithms

**1. ID Normalization** (`ingestion.py:12-30`)
```python
"TRD-001"  → "trd001"
"TRD_001"  → "trd001"
"TRD.001"  → "trd001"
"trd 001"  → "trd001"
```

**2. Date Proximity Scoring** (`matching.py:80-99`)
```python
score = 1.0 - (days_diff / DATE_PROXIMITY_WINDOW)

0 days apart   → score = 1.00
1 day apart    → score = 0.86
3 days apart   → score = 0.57
7+ days apart  → score = 0.00
```

**3. Semantic Similarity** (`embedding.py`)
- Uses `all-MiniLM-L6-v2` model (384-dimensional embeddings)
- Cosine similarity between description embeddings
- Threshold: 0.80 (configurable)

**4. Amount Matching Logic**
```python
# Exact match required (within tolerance)
if abs(amount1 - amount2) <= AMOUNT_TOLERANCE:  # $0.01
    return MATCHED
else:
    return BREAK
```

## Input File Format

CSV files can have **any column names** - the engine auto-detects them! Common patterns:
- **Reference/Trade ID**: `trade_id`, `ref_id`, `reference`, `record_id`, `transaction_id`, `txn_id`, `id`
- **Description**: `description`, `narrative`, `narration`, `details`, `notes`
- **Amount**: `amount`, `value`, `total`, `amount_inr`, `sum`, `balance`
- **Date** (optional): `date`, `trade_date`, `transaction_date`, `txn_date`, `booking_date`

**Example files:**
```csv
# vendor_statement.csv
record_id,date,party_name,narration,amount_inr,expense_type
V001,2025-01-03,Tata Comm Ltd,Auto generated narration 1,187621,Infrastructure

# bank_ledger.csv
transaction_id,txn_date,vendor_name,description,amount,currency
B001,2025-01-02,Amazon Web Services,Auto generated transaction 1,187621,INR
```

The engine will automatically detect:
- `record_id` → ID
- `amount_inr` → Amount
- `date` → Date
- `party_name` → Description

## Output Format

CSV with columns:
```
our_ref, bank_ref, our_amount, bank_amount, delta, match_type, status, similarity_score, notes
```

Sorted by status (breaks first, then unmatched, then matched).

## Project Structure

```
reconcile.py          # CLI entrypoint - orchestrates the reconciliation flow
config.py             # Configuration: thresholds, strategies, column patterns
column_detector.py    # Smart column detection using content analysis (NEW!)
ingestion.py          # CSV loading, column detection, ID normalization
embedding.py          # Sentence transformer embeddings (all-MiniLM-L6-v2)
matching.py           # 5-phase matching pipeline (ID → Amount+Date → Semantic → Amount-Only)
output.py             # CSV generation, audit logging, summary statistics
feedback.py           # SQLite database for analyst overrides
requirements.txt      # Python dependencies

sample_our_book.csv   # Sample vendor/firm data for testing
sample_bank_book.csv  # Sample bank data for testing

clients/
  {client_id}/
    input/           # Place input files here
    output/          # Reconciliation reports (CSV)
    feedback.db      # Analyst feedback database (SQLite)
    audit.log        # Audit trail (timestamped logs)
```

## Configuration

All settings in `config.py`:

### Matching Strategy Controls
- `ENABLE_AMOUNT_DATE_MATCHING` (default: True) - Enable Amount+Date matching phase
- `ENABLE_AMOUNT_ONLY_MATCHING` (default: True) - Enable risky Amount-Only matching
- `SEMANTIC_THRESHOLD` (default: 0.80) - Minimum similarity for semantic matches
- `AMOUNT_TOLERANCE` (default: 0.01) - Tolerance for amount comparison ($0.01)
- `DATE_PROXIMITY_WINDOW` (default: 7 days) - Date matching window
- `AMOUNT_ONLY_DATE_WINDOW` (default: 14 days) - Date window for amount-only matches

### Column Name Patterns (for fallback detection)
- `ID_FIELDS` - List of possible ID column names
- `DESCRIPTION_FIELDS` - List of possible description column names
- `AMOUNT_FIELDS` - List of possible amount column names
- `DATE_FIELDS` - List of possible date column names

**Note:** With smart column detection, you rarely need to edit these lists!

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
