from __future__ import annotations

from paper_review_system.models import ImprovementPlan, LogicAnalysis, ReviewReport, Violation
from paper_review_system.report.validator import ReportValidator


class ReportAssembler:
    def __init__(self) -> None:
        self.validator = ReportValidator()

    def assemble(
        self,
        logic_analysis: LogicAnalysis,
        violations: list[Violation],
        improvement_plan: ImprovementPlan,
    ) -> ReviewReport:
        report = ReviewReport(
            project_metadata={"version": "1.2", "focus": "Deep Semantic & Logic Audit"},
            logic_analysis=logic_analysis,
            rule_violations=violations,
            improvement_plan=improvement_plan,
        )
        payload = report.to_dict()
        self.validator.validate(payload)
        return report
