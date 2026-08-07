from datetime import datetime
from typing import Dict, List

from data.models.ai_signal import AISignal
from data.models.analysis_result import AnalysisResult
from data.models.ranking_result import RankingResult
from data.models.full_ranking import FullRanking
from data.models.risk_result import RiskResult


class RiskEngine:
    """
    Main engine for risk assessment in the ALCHEMIK project.
    """
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict:
        """Load and validate the risk engine configuration."""
        # TODO: Implement configuration loading
        return {
            "weights": {
                "ai_signal": 0.3,
                "technical": 0.4,
                "ranking": 0.3,
            },
            "risk_thresholds": {
                "LOW": 0.25,
                "MEDIUM": 0.5,
                "HIGH": 0.75,
                "CRITICAL": 1.0,
            },
            "position_limits": {
                "min": 0.01,
                "max": 0.1,
            },
            "stop_loss": 0.05,
            "take_profit": 0.1,
        }

    def assess_risk(self, analysis_result: AnalysisResult, ranking_result: FullRanking) -> RiskResult:
        """
        Perform risk assessment based on analysis and ranking results.

        Args:
            analysis_result (AnalysisResult): Results from other engines
            ranking_result (FullRanking): Ranking results

        Returns:
            RiskResult: Complete risk assessment
        """
        # Calculate weighted risk score
        risk_score = self._calculate_risk_score(analysis_result, ranking_result)

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(analysis_result, ranking_result)

        # Calculate position management parameters
        position_size = self._calculate_position_size(risk_score)
        stop_loss, take_profit = self._calculate_stop_loss_take_profit(risk_score)

        return RiskResult(
            instrument_id=analysis_result.company.symbol,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=analysis_result.signals[0].confidence if analysis_result.signals else 0.5,
            risk_factors=risk_factors,
            max_position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=datetime.now(),
        )
    
    def _calculate_risk_score(self, analysis_result: AnalysisResult, ranking_result: FullRanking) -> float:
        """Calculate weighted risk score based on configured weights.

        The score is a weighted combination of:
          - market volatility (variance in close prices),
          - AI signal confidence avg,
          - ranking position penalty.

        All components are normalised into [0.0, 1.0] and blended
        using the configured weights.
        """
        w = self.config["weights"]

        # --- Market volatility component (0 – high vol = higher risk) ---
        if analysis_result.market_data:
            closes = [d.close for d in analysis_result.market_data if d.close is not None]
            if len(closes) >= 2:
                avg = sum(closes) / len(closes)
                var = sum((c - avg) ** 2 for c in closes) / len(closes)
                # Normalise: normalise volatility relative to average price
                raw_vol = (var ** 0.5) / avg if avg > 0 else 0.0
                vol_norm = min(raw_vol, 1.0)
            else:
                vol_norm = 0.0
        else:
            vol_norm = 0.0

        # --- AI signal confidence component (low confidence = higher risk) ---
        if analysis_result.signals:
            avg_confidence = sum(
                s.confidence for s in analysis_result.signals
            ) / len(analysis_result.signals)
        else:
            avg_confidence = 0.0
        # Invert: high confidence → low risk
        confidence_risk = 1.0 - min(avg_confidence, 1.0)

        # --- Ranking position penalty ---
        ranking_penalty = 0.0
        if ranking_result and ranking_result.results:
            for idx, item in enumerate(ranking_result.results):
                if item.instrument_id == analysis_result.company.symbol:
                    ranking_penalty = idx / max(len(ranking_result.results), 1)
                    break

        score = (
            w["technical"] * vol_norm
            + w["ai_signal"] * confidence_risk
            + w["ranking"] * ranking_penalty
        )
        return max(0.0, min(score, 1.0))
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk category based on configured thresholds."""
        for level, threshold in self.config["risk_thresholds"].items():
            if risk_score <= threshold:
                return level
        return "CRITICAL"
    
    def _identify_risk_factors(self, analysis_result: AnalysisResult, ranking_result: FullRanking) -> List[str]:
        """Identify and list all detected risk factors.

        Checks thresholds for:
          - high market volatility,
          - low AI signal confidence,
          - poor ranking position,
          - insufficient data.
        """
        factors: List[str] = []

        # --- Volatility check ---
        if analysis_result.market_data:
            closes = [d.close for d in analysis_result.market_data if d.close is not None]
            if len(closes) >= 2:
                avg = sum(closes) / len(closes)
                var = sum((c - avg) ** 2 for c in closes) / len(closes)
                vol_ratio = (var ** 0.5) / avg if avg > 0 else 0.0
                if vol_ratio > 0.05:
                    factors.append("High market volatility")
            else:
                factors.append("Insufficient market data for volatility check")
        else:
            factors.append("No market data available")

        # --- AI signal confidence check ---
        if analysis_result.signals:
            avg_conf = sum(s.confidence for s in analysis_result.signals) / len(analysis_result.signals)
            if avg_conf < 0.5:
                factors.append(f"Low AI signal confidence ({avg_conf:.0%})")
        else:
            factors.append("No AI signals available")

        # --- Ranking check ---
        if ranking_result and ranking_result.results:
            if len(ranking_result.results) > 1:
                for idx, item in enumerate(ranking_result.results):
                    if item.instrument_id == analysis_result.company.symbol:
                        if idx >= len(ranking_result.results) // 2:
                            factors.append("Poor ranking position (bottom half)")
                        break

        if not factors:
            factors.append("No significant risk factors detected")

        return factors
    
    def _calculate_position_size(self, risk_score: float) -> float:
        """Calculate recommended max position size based on risk."""
        min_size = self.config["position_limits"]["min"]
        max_size = self.config["position_limits"]["max"]
        return max_size - (risk_score * (max_size - min_size))
    
    def _calculate_stop_loss_take_profit(self, risk_score: float) -> tuple[float, float]:
        """Calculate stop loss and take profit levels based on risk."""
        base_sl = self.config["stop_loss"]
        base_tp = self.config["take_profit"]
        return (base_sl * (1 + risk_score), base_tp * (1 - risk_score))