from __future__ import annotations

from paper_review_system.logic.claim_extractor import ClaimExtractor
from paper_review_system.logic.consistency_checker import ConsistencyChecker
from paper_review_system.logic.reasoning_depth import ReasoningDepthEvaluator
from paper_review_system.models import LogicAnalysis, PaperAnchor, PaperBlock


class LogicAnalyzer:
    """Orchestrate heuristic logic analysis."""

    def __init__(self) -> None:
        self.claim_extractor = ClaimExtractor()
        self.consistency_checker = ConsistencyChecker()
        self.reasoning_evaluator = ReasoningDepthEvaluator()

    def analyze(self, clean_blocks: list[PaperBlock], anchors: list[PaperAnchor]) -> LogicAnalysis:
        claims = self.claim_extractor.extract(clean_blocks, anchors)
        consistency = self.consistency_checker.evaluate(claims)
        reasoning_depth = self.reasoning_evaluator.evaluate(claims)
        score = 88
        if not consistency.is_consistent:
            score -= 18
        score -= max(0, len(consistency.details) - 1) * 5
        score = max(40, min(95, score))
        return LogicAnalysis(
            academic_integrity_score=score,
            core_argument_consistency=consistency,
            reasoning_depth=reasoning_depth,
        )
