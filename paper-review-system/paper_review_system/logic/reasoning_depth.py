from __future__ import annotations

from paper_review_system.models import ReasoningDepth


class ReasoningDepthEvaluator:
    """Estimate reasoning depth from section coverage and evidence density."""

    def evaluate(self, claims: dict[str, dict[str, object]]) -> ReasoningDepth:
        section_count = len(claims)
        average_keywords = 0
        if claims:
            average_keywords = round(sum(len(item["keywords"]) for item in claims.values()) / len(claims), 2)

        if section_count >= 4 and average_keywords >= 5:
            return ReasoningDepth(
                assessment="论文具备较完整的章节展开，论证覆盖面尚可，但仍需检查关键结论是否有直接证据支撑。",
                suggestion="建议在实验与结论之间增加更明确的指标解释，确保每个主要主张都能映射到可验证证据。",
            )

        return ReasoningDepth(
            assessment="当前文本呈现出的论证层次偏薄，章节之间的支撑关系不够充分。",
            suggestion="建议补充问题定义、方法选择依据与实验指标之间的关联说明，避免只给结论不展示推导过程。",
        )
