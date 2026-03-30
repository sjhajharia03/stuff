"""
Configuration settings for the reconciliation engine.
"""

# Semantic similarity threshold for considering a match candidate
SEMANTIC_THRESHOLD = 0.80

# Possible column names for reference/trade IDs in input files
# The engine will try these in order when looking for ID fields
ID_FIELDS = [
    "trade_id",
    "ref_id",
    "reference",
    "trade_ref",
    "transaction_id",
    "txn_id",
    "id",
    "reference_id",
    "record_id"
]

# Possible column names for description fields
DESCRIPTION_FIELDS = [
    "description",
    "desc",
    "narrative",
    "narration",
    "details",
    "notes"
]

# Possible column names for amount fields
AMOUNT_FIELDS = [
    "amount",
    "value",
    "total",
    "sum",
    "balance",
    "amount_inr"
]

# Possible column names for date fields (optional)
DATE_FIELDS = [
    "date",
    "trade_date",
    "transaction_date",
    "txn_date",
    "value_date",
    "booking_date"
]

# Weights for scoring (only used when date proximity is available)
# Note: Amount is a hard constraint, not a weight
W1_SEMANTIC = 0.7      # Weight for semantic similarity
W3_DATE_PROXIMITY = 0.3  # Weight for date proximity (if date available)

# Date proximity window in days (if dates differ by more than this, proximity score = 0)
DATE_PROXIMITY_WINDOW = 7

# Model for sentence transformers
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Base directory for client data
CLIENTS_DIR = "clients"

# Amount comparison tolerance (for floating point comparison)
AMOUNT_TOLERANCE = 0.01  # $0.01 tolerance

# Match type constants
MATCH_TYPE_ID = "ID"
MATCH_TYPE_AMOUNT_DATE = "AMOUNT+DATE"
MATCH_TYPE_AMOUNT_ONLY = "AMOUNT_ONLY"
MATCH_TYPE_SEMANTIC = "SEMANTIC"
MATCH_TYPE_NONE = "NONE"

# Matching strategy configuration
ENABLE_AMOUNT_DATE_MATCHING = True  # Match by amount + date proximity
ENABLE_AMOUNT_ONLY_MATCHING = True  # Match by amount only (risky, enables warnings)
AMOUNT_ONLY_DATE_WINDOW = 14  # Only match by amount if dates are within N days

# Status constants
STATUS_MATCHED = "MATCHED"
STATUS_BREAK = "BREAK"
STATUS_UNMATCHED_OURS = "UNMATCHED_OURS"
STATUS_UNMATCHED_BANK = "UNMATCHED_BANK"
