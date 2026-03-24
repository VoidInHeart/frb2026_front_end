from __future__ import annotations

from paper_review_system.models import ExpertSample, LogicAnalysis, Violation


class ExpertSampleRetriever:
    """Return curated sample hints based on detected issues."""

    SAMPLE_LIBRARY = [
        ExpertSample(
            topic="实验支撑逻辑优化",
            source_paper="Gold_Paper_003",
            value_proposition="可参考其如何把研究目标、实验指标与结论逐一对齐，避免只展示结果不回应核心问题。",
        ),
        ExpertSample(
            topic="参考文献与正文一致性",
            source_paper="Gold_Paper_011",
            value_proposition="可参考其正文引用、图表引用与参考文献编号保持一致的写法，适合作为格式自检样例。",
        ),
        ExpertSample(
            topic="章节结构组织",
            source_paper="Gold_Paper_021",
            value_proposition="可参考其摘要、方法、实验、结论的章节层级安排，适合修复结构断裂或跳号问题。",
        ),
    ]

    def retrieve(self, logic_analysis: LogicAnalysis, violations: list[Violation]) -> list[ExpertSample]:
        selected: list[ExpertSample] = []
        if not logic_analysis.core_argument_consistency.is_consistent:
            selected.append(self.SAMPLE_LIBRARY[0])
        if any(item.category == "Citation_Consistency" for item in violations):
            selected.append(self.SAMPLE_LIBRARY[1])
        if any(item.category == "Structural_Format" for item in violations):
            selected.append(self.SAMPLE_LIBRARY[2])
        return selected or [self.SAMPLE_LIBRARY[0]]
