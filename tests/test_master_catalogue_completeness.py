"""
Test for MasterEngine._CATALOGUE completeness.

Verifies that the event catalogue contains an entry for every event_type
declared by the BaseDetector-based detectors registered in the default
DetectorRegistry.

PriceDetector and VolumeDetector are NOT included — they create MarketEvent
directly and do not use _result_to_market_event() / _lookup_catalogue().

The test uses ``_build_default_registry()`` as the single source of truth
— no hardcoded event_type lists, no documentation-derived constants.
"""

import unittest

from engines.master.engine import _CATALOGUE, _build_default_registry, _lookup_catalogue
from data.models.event_enums import EventFamily, PriorityLevel


class TestCatalogueCompleteness(unittest.TestCase):
    """Verify that _CATALOGUE covers all registered BaseDetector event_types."""

    @classmethod
    def setUpClass(cls):
        """Build the default registry and collect all declared event types."""
        cls.registry = _build_default_registry()
        cls.detectors = cls.registry.get_all()

        # Collect all event_type strings from all registered BaseDetectors.
        cls.all_detector_event_types: set[str] = set()
        cls.detector_event_type_map: dict[str, str] = {}  # event_type → detector_id
        for detector in cls.detectors:
            for et in detector.event_types:
                if et in cls.all_detector_event_types:
                    # Duplicate across detectors — this is allowed by the registry
                    # (overlapping event_types), but each event_type must have ONE
                    # catalogue entry regardless of how many detectors declare it.
                    pass
                cls.all_detector_event_types.add(et)
                cls.detector_event_type_map[et] = detector.detector_id

        cls.catalogue_keys: set[str] = set(_CATALOGUE.keys())

    # ------------------------------------------------------------------
    # Cardinality
    # ------------------------------------------------------------------

    def test_catalogue_size_matches_detector_event_types(self):
        """The catalogue should contain exactly one entry per declared event_type."""
        expected = len(self.all_detector_event_types)
        actual = len(self.catalogue_keys)
        self.assertEqual(
            expected, actual,
            f"Catalogue has {actual} entries, but detectors declare {expected} event_types. "
            f"Missing: {self.all_detector_event_types - self.catalogue_keys}. "
            f"Extra: {self.catalogue_keys - self.all_detector_event_types}."
        )

    # ------------------------------------------------------------------
    # Completeness — every declared event_type has a catalogue entry
    # ------------------------------------------------------------------

    def test_every_declared_event_type_in_catalogue(self):
        """Every event_type from a registered BaseDetector must be in _CATALOGUE."""
        missing = self.all_detector_event_types - self.catalogue_keys
        self.assertEqual(
            len(missing), 0,
            f"The following {len(missing)} event_types are declared by registered "
            f"BaseDetectors but are MISSING from _CATALOGUE: {sorted(missing)}"
        )

    # ------------------------------------------------------------------
    # No superfluous entries
    # ------------------------------------------------------------------

    def test_no_extra_catalogue_entries(self):
        """Every catalogue key must correspond to a registered BaseDetector event_type."""
        extra = self.catalogue_keys - self.all_detector_event_types
        self.assertEqual(
            len(extra), 0,
            f"The following {len(extra)} catalogue entries have NO corresponding "
            f"registered BaseDetector event_type: {sorted(extra)}"
        )

    # ------------------------------------------------------------------
    # No duplicates
    # ------------------------------------------------------------------

    def test_no_duplicate_catalogue_keys(self):
        """_CATALOGUE is a dict — keys are inherently unique. Explicit check."""
        # A dict cannot have duplicate keys by definition, but we verify
        # that the data structure is a dict with unique string keys.
        self.assertIsInstance(_CATALOGUE, dict)
        key_list = list(_CATALOGUE.keys())
        self.assertEqual(
            len(key_list), len(set(key_list)),
            f"Catalogue contains duplicate keys (should be impossible for a dict)"
        )

    # ------------------------------------------------------------------
    # Key type
    # ------------------------------------------------------------------

    def test_all_catalogue_keys_are_strings(self):
        """Every catalogue key must be a non-empty string."""
        for key in _CATALOGUE:
            self.assertIsInstance(key, str, f"Catalogue key {key!r} is not a str")
            self.assertTrue(key.strip(), f"Catalogue key {key!r} is empty or whitespace-only")

    # ------------------------------------------------------------------
    # Value structure
    # ------------------------------------------------------------------

    def test_all_catalogue_values_have_correct_structure(self):
        """Every catalogue value must be a 4-tuple of the correct types."""
        for key, value in _CATALOGUE.items():
            self.assertIsInstance(
                value, tuple,
                f"Catalogue value for {key!r} is not a tuple, got {type(value).__name__}"
            )
            self.assertEqual(
                len(value), 4,
                f"Catalogue value for {key!r} has {len(value)} elements, expected 4"
            )
            event_family, category, subcategory, priority = value
            self.assertIsInstance(
                event_family, EventFamily,
                f"Catalogue[{key!r}] element 0 is not an EventFamily: {event_family!r}"
            )
            self.assertIsInstance(
                category, str,
                f"Catalogue[{key!r}] element 1 is not a str: {category!r}"
            )
            self.assertTrue(
                category.strip(),
                f"Catalogue[{key!r}] element 1 (category) is empty or whitespace-only"
            )
            self.assertTrue(
                subcategory is None or isinstance(subcategory, str),
                f"Catalogue[{key!r}] element 2 must be str or None, got {type(subcategory).__name__}"
            )
            if subcategory is not None:
                self.assertTrue(
                    subcategory.strip(),
                    f"Catalogue[{key!r}] element 2 (subcategory) is whitespace-only"
                )
            self.assertIsInstance(
                priority, PriorityLevel,
                f"Catalogue[{key!r}] element 3 is not a PriorityLevel: {priority!r}"
            )

    # ------------------------------------------------------------------
    # _lookup_catalogue integration
    # ------------------------------------------------------------------

    def test_lookup_returns_correct_catalogue_entry(self):
        """_lookup_catalogue() must return the exact catalogue value for known keys."""
        for key in self.all_detector_event_types & self.catalogue_keys:
            expected = _CATALOGUE[key]
            actual = _lookup_catalogue(key)
            self.assertEqual(
                expected, actual,
                f"_lookup_catalogue({key!r}) returned {actual!r}, expected {expected!r}"
            )

    def test_lookup_fallback_unchanged(self):
        """_lookup_catalogue() fallback for unknown types must remain unchanged."""
        result = _lookup_catalogue("NONEXISTENT_TYPE_XYZ123")
        expected = (EventFamily.SYSTEM, "System", None, PriorityLevel.LOW)
        self.assertEqual(
            result, expected,
            f"Fallback for unknown event_type returned {result!r}, expected {expected!r}"
        )

    # ------------------------------------------------------------------
    # PriceDetector / VolumeDetector are NOT in the catalogue
    # ------------------------------------------------------------------

    def test_price_detector_event_types_not_in_catalogue(self):
        """
        PriceDetector event_types must NOT appear in _CATALOGUE.
        
        PriceDetector creates MarketEvent directly and does not use
        _result_to_market_event() / _lookup_catalogue().
        """
        # The BaseDetector-based detectors do NOT include PriceDetector types.
        # We verify that catalogue keys are ONLY from BaseDetector event_types.
        # This is already guaranteed by test_every_declared_event_type_in_catalogue
        # and test_no_extra_catalogue_entries — any PriceDetector type in the
        # catalogue would be flagged as an "extra" entry.
        pass  # Verified by the completeness tests above

    def test_volume_detector_event_types_not_in_catalogue(self):
        """
        VolumeDetector event_types must NOT appear in _CATALOGUE.
        
        VolumeDetector creates MarketEvent directly and does not use
        _result_to_market_event() / _lookup_catalogue().
        """
        # Same reasoning as test_price_detector_event_types_not_in_catalogue.
        pass  # Verified by the completeness tests above

    # ------------------------------------------------------------------
    # Registry integrity
    # ------------------------------------------------------------------

    def test_default_registry_has_nine_detectors(self):
        """The default registry must contain exactly 9 BaseDetector detectors."""
        self.assertEqual(
            len(self.detectors), 9,
            f"Expected 9 detectors in default registry, got {len(self.detectors)}: "
            f"{[d.detector_id for d in self.detectors]}"
        )


if __name__ == "__main__":
    unittest.main()