"""
Core matching logic: ID-first with semantic fallback.
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Optional
import config
from embedding import EmbeddingEngine


class MatchResult:
    """Represents a match result between our book and bank book."""

    def __init__(
        self,
        our_index: int,
        bank_index: Optional[int],
        our_ref: str,
        bank_ref: Optional[str],
        our_amount: float,
        bank_amount: Optional[float],
        match_type: str,
        status: str,
        similarity_score: float = 0.0,
        notes: str = ""
    ):
        self.our_index = our_index
        self.bank_index = bank_index
        self.our_ref = our_ref
        self.bank_ref = bank_ref
        self.our_amount = our_amount
        self.bank_amount = bank_amount
        self.match_type = match_type
        self.status = status
        self.similarity_score = similarity_score
        self.notes = notes

    @property
    def delta(self) -> Optional[float]:
        """Calculate the amount delta."""
        if self.bank_amount is None or self.our_amount is None:
            return None
        return self.our_amount - self.bank_amount


class ReconciliationEngine:
    """
    Core reconciliation engine.

    Matching strategy:
    1. Attempt exact match on normalized reference/trade ID
    2. If no ID match found, fall back to semantic similarity on description
    3. Semantic similarity is used to find the candidate, not to excuse a break
    4. Amount is a hard constraint - amounts match exactly → MATCHED, differ → BREAK
    """

    def __init__(self):
        """Initialize the reconciliation engine."""
        self.embedding_engine = EmbeddingEngine()

    def _amounts_match(self, amount1: float, amount2: float) -> bool:
        """
        Check if two amounts match within tolerance.

        Args:
            amount1: First amount
            amount2: Second amount

        Returns:
            True if amounts match within tolerance
        """
        if pd.isna(amount1) or pd.isna(amount2):
            return False

        return abs(amount1 - amount2) <= config.AMOUNT_TOLERANCE

    def _compute_date_proximity(self, date1: Optional[pd.Timestamp], date2: Optional[pd.Timestamp]) -> float:
        """
        Compute date proximity score.

        Args:
            date1: First date
            date2: Second date

        Returns:
            Proximity score (0-1), or 0 if dates are missing
        """
        if pd.isna(date1) or pd.isna(date2):
            return 0.0

        days_diff = abs((date1 - date2).days)

        if days_diff > config.DATE_PROXIMITY_WINDOW:
            return 0.0

        # Linear decay: full score at 0 days, 0 score at window boundary
        return 1.0 - (days_diff / config.DATE_PROXIMITY_WINDOW)

    def reconcile(self, our_book: pd.DataFrame, bank_book: pd.DataFrame) -> list[MatchResult]:
        """
        Perform full reconciliation between our book and bank book.

        Args:
            our_book: Our book dataframe (from ingestion.py)
            bank_book: Bank book dataframe (from ingestion.py)

        Returns:
            List of MatchResult objects
        """
        results = []
        matched_bank_indices = set()

        print("\nPhase 1: ID-based matching")
        print("-" * 50)

        # Build ID lookup for bank book (normalized ID -> list of indices)
        bank_id_lookup = {}
        for idx, row in bank_book.iterrows():
            normalized_id = row['id_normalized']
            if normalized_id and normalized_id.strip():
                if normalized_id not in bank_id_lookup:
                    bank_id_lookup[normalized_id] = []
                bank_id_lookup[normalized_id].append(idx)

        # Phase 1: ID-based matching
        our_unmatched_indices = []

        for our_idx, our_row in our_book.iterrows():
            our_id = our_row['id_normalized']

            # Try ID match
            if our_id and our_id.strip() and our_id in bank_id_lookup:
                # Found ID match - take first unmatched candidate
                matched = False
                for bank_idx in bank_id_lookup[our_id]:
                    if bank_idx not in matched_bank_indices:
                        # ID match found
                        bank_row = bank_book.loc[bank_idx]
                        matched_bank_indices.add(bank_idx)

                        # Check if amounts match
                        amounts_match = self._amounts_match(our_row['amount'], bank_row['amount'])

                        if amounts_match:
                            status = config.STATUS_MATCHED
                            notes = "ID match, amounts agree"
                        else:
                            status = config.STATUS_BREAK
                            notes = "ID match, but amounts differ"

                        result = MatchResult(
                            our_index=our_idx,
                            bank_index=bank_idx,
                            our_ref=our_row['id_raw'],
                            bank_ref=bank_row['id_raw'],
                            our_amount=our_row['amount'],
                            bank_amount=bank_row['amount'],
                            match_type=config.MATCH_TYPE_ID,
                            status=status,
                            similarity_score=1.0,  # Perfect ID match
                            notes=notes
                        )
                        results.append(result)
                        matched = True
                        break

                if matched:
                    continue

            # No ID match found
            our_unmatched_indices.append(our_idx)

        print(f"ID matches found: {len(results)}")
        print(f"Our records without ID match: {len(our_unmatched_indices)}")

        # Phase 2: Semantic matching for unmatched records
        if our_unmatched_indices:
            print("\nPhase 2: Semantic matching")
            print("-" * 50)

            # Get unmatched bank records
            bank_unmatched_indices = [idx for idx in bank_book.index if idx not in matched_bank_indices]
            print(f"Bank records without ID match: {len(bank_unmatched_indices)}")

            if bank_unmatched_indices:
                # Generate embeddings
                print("Generating embeddings for unmatched records...")
                our_descriptions = [our_book.loc[idx, 'description'] for idx in our_unmatched_indices]
                bank_descriptions = [bank_book.loc[idx, 'description'] for idx in bank_unmatched_indices]

                our_embeddings = self.embedding_engine.generate_embeddings(our_descriptions)
                bank_embeddings = self.embedding_engine.generate_embeddings(bank_descriptions)

                # Compute similarity matrix
                print("Computing semantic similarities...")
                similarity_matrix = self.embedding_engine.compute_similarity_matrix(our_embeddings, bank_embeddings)

                # Match based on semantic similarity
                for i, our_idx in enumerate(our_unmatched_indices):
                    our_row = our_book.loc[our_idx]

                    # Find best semantic match
                    best_sim_idx = np.argmax(similarity_matrix[i])
                    best_sim_score = similarity_matrix[i][best_sim_idx]

                    if best_sim_score >= config.SEMANTIC_THRESHOLD:
                        # Semantic match found
                        bank_idx = bank_unmatched_indices[best_sim_idx]
                        bank_row = bank_book.loc[bank_idx]

                        # Adjust score with date proximity if available
                        final_score = best_sim_score
                        if not pd.isna(our_row['date']) and not pd.isna(bank_row['date']):
                            date_proximity = self._compute_date_proximity(our_row['date'], bank_row['date'])
                            final_score = (config.W1_SEMANTIC * best_sim_score +
                                         config.W3_DATE_PROXIMITY * date_proximity)

                        # Check if amounts match
                        amounts_match = self._amounts_match(our_row['amount'], bank_row['amount'])

                        if amounts_match:
                            status = config.STATUS_MATCHED
                            notes = f"Semantic match (similarity: {best_sim_score:.3f}), amounts agree"
                        else:
                            status = config.STATUS_BREAK
                            notes = f"Semantic match (similarity: {best_sim_score:.3f}), but amounts differ"

                        result = MatchResult(
                            our_index=our_idx,
                            bank_index=bank_idx,
                            our_ref=our_row['id_raw'],
                            bank_ref=bank_row['id_raw'],
                            our_amount=our_row['amount'],
                            bank_amount=bank_row['amount'],
                            match_type=config.MATCH_TYPE_SEMANTIC,
                            status=status,
                            similarity_score=final_score,
                            notes=notes
                        )
                        results.append(result)

                        # Mark bank record as matched
                        matched_bank_indices.add(bank_idx)

                        # Remove from similarity matrix to prevent double matching
                        similarity_matrix[:, best_sim_idx] = -1
                    else:
                        # No semantic match above threshold
                        result = MatchResult(
                            our_index=our_idx,
                            bank_index=None,
                            our_ref=our_row['id_raw'],
                            bank_ref=None,
                            our_amount=our_row['amount'],
                            bank_amount=None,
                            match_type=config.MATCH_TYPE_NONE,
                            status=config.STATUS_UNMATCHED_OURS,
                            similarity_score=best_sim_score,
                            notes=f"No match found (best similarity: {best_sim_score:.3f} < threshold {config.SEMANTIC_THRESHOLD})"
                        )
                        results.append(result)
            else:
                # No bank records left to match
                for our_idx in our_unmatched_indices:
                    our_row = our_book.loc[our_idx]
                    result = MatchResult(
                        our_index=our_idx,
                        bank_index=None,
                        our_ref=our_row['id_raw'],
                        bank_ref=None,
                        our_amount=our_row['amount'],
                        bank_amount=None,
                        match_type=config.MATCH_TYPE_NONE,
                        status=config.STATUS_UNMATCHED_OURS,
                        similarity_score=0.0,
                        notes="No bank records available to match"
                    )
                    results.append(result)

        # Phase 3: Mark unmatched bank records
        print("\nPhase 3: Identifying unmatched bank records")
        print("-" * 50)

        bank_unmatched_final = [idx for idx in bank_book.index if idx not in matched_bank_indices]
        print(f"Unmatched bank records: {len(bank_unmatched_final)}")

        for bank_idx in bank_unmatched_final:
            bank_row = bank_book.loc[bank_idx]
            result = MatchResult(
                our_index=None,
                bank_index=bank_idx,
                our_ref=None,
                bank_ref=bank_row['id_raw'],
                our_amount=None,
                bank_amount=bank_row['amount'],
                match_type=config.MATCH_TYPE_NONE,
                status=config.STATUS_UNMATCHED_BANK,
                similarity_score=0.0,
                notes="No matching record in our book"
            )
            results.append(result)

        return results
