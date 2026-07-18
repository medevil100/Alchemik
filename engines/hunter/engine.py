"""
Hunter Engine - Implementation

This module is responsible for identifying and selecting the best opportunities
from the results provided by other engines.
"""
from typing import Dict, List
from datetime import datetime
from data.models.hunter_result import HunterScanResult, HunterResult

class HunterEngine:
    """
    Hunter Engine implementation.
    
    Args:
        config (Dict): Configuration dictionary
    """
    def __init__(self, config: Dict):
        self.config = config

    def _calculate_hunter_score(self, instrument: Dict) -> HunterResult:
        """
        Calculate hunter score for a single instrument.
        
        Args:
            instrument (Dict): Instrument data
            
        Returns:
            HunterResult: Result with calculated hunter score and priority
        """
        inverted_risk = 1.0 - instrument.get("risk_score", 0)
        hunter_score = (
            instrument.get("ranking_score", 0) * self.config["ranking_weight"] +
            inverted_risk * self.config["risk_weight"] +
            instrument.get("confidence", 0) * self.config["confidence_weight"]
        )
        hunter_score = max(0.0, min(1.0, hunter_score))  # Ensure within 0.0-1.0 range
        
        # Determine priority based on thresholds (sorted in descending order)
        priority = 3  # Default to lowest priority
        thresholds = sorted(self.config["priority_thresholds"], reverse=True)
        for threshold in thresholds:
            if hunter_score >= threshold:
                if threshold >= 0.9:
                    priority = 1
                elif threshold >= 0.7:
                    priority = 2
                elif threshold >= 0.5:
                    priority = 3
                break
        
        return HunterResult(
            instrument_id=instrument["instrument_id"],
            hunter_score=hunter_score,
            priority=priority,
            ranking_score=instrument.get("ranking_score", 0),
            risk_score=instrument.get("risk_score", 0),
            risk_level="",  # Will be calculated later if needed
            confidence=instrument.get("confidence", 0),
            reasons=[],
            warnings=[],
            timestamp=datetime.now()
        )

    def scan(self, instruments: List[Dict]) -> HunterScanResult:
        """
        Scan instruments and return qualified opportunities.
        
        Args:
            instruments (List[Dict]): List of instrument data
            
        Returns:
            HunterScanResult: Complete scan result with opportunities and stats
        """
        opportunities = []
        analyzed = len(instruments)
        rejected = 0
        qualified = 0
        
        for instrument in instruments:
            # Check basic thresholds
            if (
                instrument.get("ranking_score", 0) < self.config["min_ranking_score"] or
                instrument.get("risk_score", 0) > self.config["max_risk_score"] or
                instrument.get("confidence", 0) < self.config["min_confidence"]
            ):
                rejected += 1
                continue
            
            # Calculate hunter score
            result = self._calculate_hunter_score(instrument)
            opportunities.append(result)
            qualified += 1
        
        # Sort by hunter_score (descending) and limit results
        opportunities.sort(key=lambda x: x.hunter_score, reverse=True)
        if len(opportunities) > self.config["max_results"]:
            opportunities = opportunities[:self.config["max_results"]]
            rejected += len(opportunities) - self.config["max_results"]
        
        return HunterScanResult(
            opportunities=opportunities,
            analyzed=analyzed,
            rejected=rejected,
            qualified=min(qualified, self.config["max_results"]),
            timestamp=datetime.now()
        )
