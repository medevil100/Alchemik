"""
ComposerEngine — merges related MarketEvents into Composite Events.

Implements ETAP 7.3 as specified in docs/ETAP_7_PLAN.md section 7.3.

Algorithm:
  1. Partition input events by ticker (same instrument).
  2. Within each ticker group, sort deterministically (timestamp_utc, event_id).
  3. Use a sliding window (default 60 s) to identify clusters of 2+
     events that are close enough in time.
  4. Within each cluster, form maximal compatible subgroups based on
     the family compatibility matrix (section 7.3.1).
  5. For each compatible subgroup with 2+ events, create a Composite Event
     using the CompositeEvent model as a validated internal data container.
  6. max_composite_events limits the number of components *per* Composite
     Event. Groups larger than this limit are split deterministically.
  7. Events that cannot be assigned to any compatible group remain unchanged.
  8. No input event is duplicated in more than one Composite Event.

Family compatibility matrix (section 7.3.1):
  PRICE       <-> PRICE, VOLUME, TECHNICAL, DERIVATIVES
  VOLUME      <-> VOLUME, PRICE, TECHNICAL, DERIVATIVES
  TECHNICAL   <-> TECHNICAL, PRICE, VOLUME, DERIVATIVES
  FUNDAMENTAL <-> FUNDAMENTAL, CORPORATE, REGULATORY
  CORPORATE   <-> CORPORATE, FUNDAMENTAL, REGULATORY
  REGULATORY  <-> REGULATORY, CORPORATE, FUNDAMENTAL
  MACRO       <-> MACRO, ETF, SENTIMENT
  ETF         <-> ETF, MACRO
  DERIVATIVES <-> DERIVATIVES, PRICE, VOLUME, TECHNICAL
  SENTIMENT   <-> SENTIMENT, MACRO
  SYSTEM      <-> SYSTEM only

The matrix operates exclusively on existing EventFamily values from
data/models/event_enums.py. No new families were created.

Invariants from Kontrakt Zdarzen Rynkowych:
  - N2:  detection_source of Composite Event is empty (sources are in
         composite_events).
  - N10: priority_final = max(priorities of component events).
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, FrozenSet, List, Set, Tuple

from config.composer import get_composer_config, ComposerConfig
from data.models.composite_event import CompositeEvent
from data.models.event_enums import (
    EventFamily,
    EventOwner,
    PriorityLevel,
)
from data.models.market_event import MarketEvent

# ---------------------------------------------------------------------------
# Family compatibility pairs — section 7.3.1 of ETAP_7_PLAN.md
# ---------------------------------------------------------------------------
# Each entry defines a symmetric pair: both (A, B) and (B, A) are
# generated automatically, plus each family is always compatible with
# itself.  Adding a new relationship requires a single line — symmetry
# is guaranteed by construction.
#
# Pairs (undirected):
#   PRICE — VOLUME
#   PRICE — TECHNICAL
#   PRICE — DERIVATIVES
#   VOLUME — TECHNICAL
#   VOLUME — DERIVATIVES
#   TECHNICAL — DERIVATIVES
#   FUNDAMENTAL — CORPORATE
#   FUNDAMENTAL — REGULATORY
#   CORPORATE — REGULATORY
#   MACRO — ETF
#   MACRO — SENTIMENT
#
# SYSTEM is compatible only with SYSTEM (itself).

_COMPATIBILITY_PAIRS: Set[Tuple[EventFamily, EventFamily]] = {
    (EventFamily.PRICE, EventFamily.VOLUME),
    (EventFamily.PRICE, EventFamily.TECHNICAL),
    (EventFamily.PRICE, EventFamily.DERIVATIVES),
    (EventFamily.VOLUME, EventFamily.TECHNICAL),
    (EventFamily.VOLUME, EventFamily.DERIVATIVES),
    (EventFamily.TECHNICAL, EventFamily.DERIVATIVES),
    (EventFamily.FUNDAMENTAL, EventFamily.CORPORATE),
    (EventFamily.FUNDAMENTAL, EventFamily.REGULATORY),
    (EventFamily.CORPORATE, EventFamily.REGULATORY),
    (EventFamily.MACRO, EventFamily.ETF),
    (EventFamily.MACRO, EventFamily.SENTIMENT),
}


def _build_compatibility_matrix(
    pairs: Set[Tuple[EventFamily, EventFamily]],
) -> Dict[EventFamily, FrozenSet[EventFamily]]:
    """
    Build a full symmetric compatibility matrix from undirected pairs.

    Each family is always compatible with itself.  For every (A, B)
    pair, both A→B and B→A are added — symmetry is automatic.
    """
    matrix: Dict[EventFamily, set] = {f: {f} for f in EventFamily}
    for a, b in pairs:
        matrix.setdefault(a, set()).add(b)
        matrix.setdefault(b, set()).add(a)
    return {f: frozenset(s) for f, s in matrix.items()}


_COMPATIBILITY: Dict[EventFamily, FrozenSet[EventFamily]] = (
    _build_compatibility_matrix(_COMPATIBILITY_PAIRS)
)


def _are_compatible(family_a: EventFamily, family_b: EventFamily) -> bool:
    """Return True if two event families can be combined in a Composite Event."""
    allowed = _COMPATIBILITY.get(family_a)
    if allowed is None:
        return False
    return family_b in allowed


def _is_fully_compatible(families: Set[EventFamily]) -> bool:
    """Return True if every family in the set is compatible with every other."""
    family_list = list(families)
    for i in range(len(family_list)):
        for j in range(i + 1, len(family_list)):
            if not _are_compatible(family_list[i], family_list[j]):
                return False
    return True


# ---------------------------------------------------------------------------
# Priority ordering for deterministic sorting
# ---------------------------------------------------------------------------

_PRIORITY_ORDER: Dict[PriorityLevel, int] = {
    PriorityLevel.CRITICAL: 4,
    PriorityLevel.HIGH: 3,
    PriorityLevel.MEDIUM: 2,
    PriorityLevel.LOW: 1,
    PriorityLevel.IGNORE: 0,
}


# ---------------------------------------------------------------------------
# ComposerEngine
# ---------------------------------------------------------------------------

class ComposerEngine:
    """
    Merges related MarketEvents into Composite Events.

    Public API:
        compose(events) -> list[MarketEvent]

    The engine is stateless — each call to ``compose()`` is independent.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compose(self, events: List[MarketEvent]) -> List[MarketEvent]:
        """
        Identify clusters of related events and create Composite Events.

        Args:
            events: List of MarketEvents to process.  Input events are
                never modified.

        Returns:
            A new list containing all original events (unchanged) plus
            any newly created Composite Events.
        """
        if not events:
            return []

        config = get_composer_config()
        result: List[MarketEvent] = list(events)

        # --- 1. Partition by ticker ---------------------------------
        grouped = self._group_by_ticker(events)

        # --- 2. For each ticker group, find clusters & compose ------
        for _ticker, ticker_events in grouped.items():
            composites = self._build_composites_for_ticker(
                ticker_events, config
            )
            result.extend(composites)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _group_by_ticker(events: List[MarketEvent]) -> dict:
        """Partition events by ``ticker`` (case-sensitive)."""
        groups: dict = {}
        for evt in events:
            groups.setdefault(evt.ticker, []).append(evt)
        return groups

    def _build_composites_for_ticker(
        self,
        events: List[MarketEvent],
        config: ComposerConfig,
    ) -> List[MarketEvent]:
        """
        Find timestamp-based clusters within *events*, split each cluster
        into maximal compatible subgroups, and create Composite Events.
        """
        # Deterministic sort: timestamp_utc, then event_id
        sorted_events = sorted(
            events, key=lambda e: (e.timestamp_utc, e.event_id)
        )

        composites: List[MarketEvent] = []
        n = len(sorted_events)
        i = 0

        while i < n:
            window_start = sorted_events[i].timestamp_utc
            cluster: List[MarketEvent] = []
            j = i
            while j < n:
                delta = (
                    sorted_events[j].timestamp_utc - window_start
                ).total_seconds()
                if delta <= config.time_window_seconds:
                    cluster.append(sorted_events[j])
                    j += 1
                else:
                    break

            if len(cluster) >= 2:
                # Split cluster into maximal compatible subgroups
                subgroups = self._form_maximal_compatible_subgroups(cluster)
                for subgroup in subgroups:
                    if len(subgroup) >= 2:
                        # max_composite_events limits components per
                        # Composite Event — split oversize subgroups
                        grouped_composites = self._build_composites_from_subgroup(
                            subgroup, config
                        )
                        composites.extend(grouped_composites)

            i = j

        return composites

    # ------------------------------------------------------------------
    # Family compatibility and subgroup formation
    # ------------------------------------------------------------------

    def _form_maximal_compatible_subgroups(
        self,
        cluster: List[MarketEvent],
    ) -> List[List[MarketEvent]]:
        """
        Split *cluster* into maximal compatible subgroups.

        Algorithm (deterministic greedy):
        1. Group events by family.
        2. Within each family group, events are kept in deterministic order.
        3. Try to merge family groups greedily:
           - Start with the largest remaining family group.
           - Expand by adding compatible families, preferring larger groups.
           - Remove assigned events from consideration.
        4. Return subgroups with 2+ events.
        """
        # Group events by family, preserving deterministic order
        family_groups: Dict[EventFamily, List[MarketEvent]] = {}
        for evt in cluster:
            family_groups.setdefault(evt.event_family, []).append(evt)

        # Sort family groups by size descending, then by earliest
        # timestamp, then by family name for determinism
        sorted_families = sorted(
            family_groups.keys(),
            key=lambda f: (
                -len(family_groups[f]),
                family_groups[f][0].timestamp_utc,
                family_groups[f][0].event_id,
            ),
        )

        used_event_ids: Set[str] = set()
        subgroups: List[List[MarketEvent]] = []

        for family in sorted_families:
            # Get unassigned events for this family
            available = [
                e for e in family_groups[family]
                if e.event_id not in used_event_ids
            ]
            if len(available) < 2:
                # With fewer than 2 unassigned events, this family
                # alone cannot form a subgroup. Try to pair with
                # compatible families.
                pass
            # Build the largest compatible group starting from this family
            subgroup = self._grow_subgroup(
                family, family_groups, used_event_ids
            )
            if len(subgroup) >= 2:
                for evt in subgroup:
                    used_event_ids.add(evt.event_id)
                subgroups.append(subgroup)

        # Handle remaining unassigned events — try to form groups
        # from families that were skipped
        remaining_families = [
            f for f in sorted_families
            if any(
                e.event_id not in used_event_ids
                for e in family_groups[f]
            )
        ]
        for family in remaining_families:
            subgroup = self._grow_subgroup(
                family, family_groups, used_event_ids
            )
            if len(subgroup) >= 2:
                for evt in subgroup:
                    used_event_ids.add(evt.event_id)
                subgroups.append(subgroup)

        return subgroups

    def _grow_subgroup(
        self,
        start_family: EventFamily,
        family_groups: Dict[EventFamily, List[MarketEvent]],
        used_event_ids: Set[str],
    ) -> List[MarketEvent]:
        """
        Greedily grow a compatible subgroup starting from *start_family*.

        Collects all available events from *start_family*, then iteratively
        adds events from compatible families that are fully pairwise
        compatible with all families already in the subgroup.
        """
        # Start with all unassigned events from the start family
        subgroup: List[MarketEvent] = [
            e for e in family_groups.get(start_family, [])
            if e.event_id not in used_event_ids
        ]

        if not subgroup:
            return []

        subgroup_families: Set[EventFamily] = {start_family}

        # Get candidate families that are compatible with all current families
        compatible_families = self._get_compatible_families(
            subgroup_families, family_groups, used_event_ids
        )

        # Sort candidates by group size descending, then deterministically
        sorted_candidates = sorted(
            compatible_families,
            key=lambda f: (
                -sum(
                    1 for e in family_groups.get(f, [])
                    if e.event_id not in used_event_ids
                ),
                family_groups[f][0].timestamp_utc
                if family_groups.get(f) else datetime.max.replace(tzinfo=timezone.utc),
                str(f.value),
            ),
        )

        for candidate_family in sorted_candidates:
            candidate_events = [
                e for e in family_groups.get(candidate_family, [])
                if e.event_id not in used_event_ids
            ]
            if not candidate_events:
                continue

            # Check if candidate_family is compatible with ALL
            # families already in the subgroup
            if all(
                _are_compatible(candidate_family, f)
                for f in subgroup_families
            ):
                subgroup.extend(candidate_events)
                subgroup_families.add(candidate_family)

        # Re-sort subgroup deterministically
        subgroup.sort(key=lambda e: (e.timestamp_utc, e.event_id))
        return subgroup

    def _get_compatible_families(
        self,
        current_families: Set[EventFamily],
        family_groups: Dict[EventFamily, List[MarketEvent]],
        used_event_ids: Set[str],
    ) -> Set[EventFamily]:
        """
        Return families that are compatible with ALL *current_families*
        and still have unassigned events.
        """
        candidates: Set[EventFamily] = set()
        for family, events in family_groups.items():
            if family in current_families:
                continue
            if not any(
                e.event_id not in used_event_ids for e in events
            ):
                continue
            if all(
                _are_compatible(family, cf) for cf in current_families
            ):
                candidates.add(family)
        return candidates

    # ------------------------------------------------------------------
    # Splitting oversized subgroups (max_composite_events limit)
    # ------------------------------------------------------------------

    def _build_composites_from_subgroup(
        self,
        subgroup: List[MarketEvent],
        config: ComposerConfig,
    ) -> List[MarketEvent]:
        """
        Split *subgroup* into chunks of at most
        ``config.max_composite_events`` components each, create one
        Composite Event per chunk, and return the list of resulting
        Composite MarketEvents.

        Subgroup is already sorted deterministically (timestamp_utc,
        event_id). Chunks are taken in order.  If the final chunk has
        only 1 event, it is NOT turned into a Composite Event.
        """
        limit = config.max_composite_events
        if limit < 2:
            limit = 2  # enforce minimum — a composite must have ≥ 2 components

        composites: List[MarketEvent] = []
        idx = 0
        n = len(subgroup)

        while idx < n:
            chunk = subgroup[idx:idx + limit]
            idx += limit
            if len(chunk) >= 2:
                ce = self._create_composite_event(chunk, config)
                composites.append(ce)
            # Single-element chunks are silently dropped —
            # the original event is already in the result list.

        return composites

    # ------------------------------------------------------------------
    # Composite Event creation — uses CompositeEvent model
    # ------------------------------------------------------------------

    def _create_composite_event(
        self,
        cluster: List[MarketEvent],
        config: ComposerConfig,
    ) -> MarketEvent:
        """
        Build a single Composite MarketEvent from a cluster of 2+ events.

        Uses the CompositeEvent model as a validated internal data
        container, then converts it into a MarketEvent.
        """
        first = cluster[0]
        component_ids = [evt.event_id for evt in cluster]

        max_priority = self._max_priority(cluster)
        avg_confidence = self._average_confidence(cluster)
        family = self._resolve_event_family(cluster, config)

        # --- Build and validate via CompositeEvent model ---
        composite = CompositeEvent.create(
            ticker=first.ticker,
            component_event_ids=component_ids,
            priority_final=max_priority,
            event_family=family,
            confidence_level=avg_confidence,
            timestamp_utc=datetime.now(timezone.utc),
            event_type=config.default_event_type,
        )
        # validation already ran inside create() — composite is known-good

        # --- Convert to MarketEvent ---
        market_event = MarketEvent.create_new(
            ticker=composite.ticker,
            market=first.market,
            instrument_type=first.instrument_type,
            timestamp_utc=composite.timestamp_utc,
        )

        market_event.set_detection(
            event_family=composite.event_family,
            event_category="Composite",
            event_type=composite.event_type,
            priority_raw=composite.priority_final,
            confidence_level=composite.confidence_level,
            detection_source="ComposerEngine",
            event_owner=EventOwner.Multi_Engine,
        )
        # N2: detection_source must be empty for Composite Events
        market_event.detection_source = ""

        market_event.set_normalization(
            priority_final=composite.priority_final,
            is_composite=True,
            composite_events=list(composite.component_event_ids),
        )

        market_event.add_history_entry(
            module="ComposerEngine",
            action=(
                f"Composite Event utworzony z "
                f"{composite.component_count} zdarzen "
                f"dla {composite.ticker} "
                f"— priority_final = {composite.priority_final.value}"
            ),
            fields_changed=[
                "is_composite", "composite_events", "priority_final"
            ],
        )

        return market_event

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _max_priority(events: List[MarketEvent]) -> PriorityLevel:
        """Return the highest priority among the component events (N10)."""
        best = PriorityLevel.LOW
        best_val = 1
        for evt in events:
            val = _PRIORITY_ORDER.get(evt.priority_raw, 1)
            if val > best_val:
                best_val = val
                best = evt.priority_raw
        return best

    @staticmethod
    def _average_confidence(events: List[MarketEvent]) -> float:
        """Return the arithmetic mean of component confidence levels."""
        if not events:
            return 0.0
        total = sum(evt.confidence_level for evt in events)
        return total / len(events)

    @staticmethod
    def _resolve_event_family(
        events: List[MarketEvent],
        config: ComposerConfig,
    ) -> EventFamily:
        """
        Determine the event_family for the Composite Event.

        Strategy: pick the most frequent family among component events.
        Falls back to the configured default (SYSTEM) if no consensus.
        """
        family_counts = Counter(evt.event_family for evt in events)
        if family_counts:
            top_family, _ = family_counts.most_common(1)[0]
            return top_family

        try:
            return EventFamily(config.default_event_family)
        except (ValueError, KeyError):
            return EventFamily.SYSTEM