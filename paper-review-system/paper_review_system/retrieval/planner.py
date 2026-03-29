from __future__ import annotations

from paper_review_system.models import ImprovementPlan, LogicAnalysis, Violation
from paper_review_system.retrieval.expert_samples import ExpertSampleRetriever
from paper_review_system.retrieval.refinement_generator import RefinementGenerator


class ImprovementPlanner:
    def __init__(self) -> None:
        self.refinement_generator = RefinementGenerator()
        self.expert_sample_retriever = ExpertSampleRetriever()

    def plan(self, logic_analysis: LogicAnalysis, violations: list[Violation]) -> ImprovementPlan:
        return ImprovementPlan(
            semantic_refinement=self.refinement_generator.generate(violations),
            expert_samples=self.expert_sample_retriever.retrieve(logic_analysis, violations),
        )
