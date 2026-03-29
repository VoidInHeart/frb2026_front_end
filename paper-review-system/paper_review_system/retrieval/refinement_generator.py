from __future__ import annotations

from paper_review_system.models import SemanticRefinement, Violation


class RefinementGenerator:
    """Generate actionable suggestions bound to violation IDs."""

    def generate(self, violations: list[Violation]) -> list[SemanticRefinement]:
        refinements: list[SemanticRefinement] = []
        for violation in violations:
            if violation.category == "Citation_Consistency":
                refinements.append(
                    SemanticRefinement(
                        target_ref=violation.id,
                        action="补齐引用映射",
                        content="请核对正文引用编号与参考文献条目是否一一对应；若文献遗漏，请补充条目并重新编号。",
                    )
                )
                continue
            if violation.category == "Structural_Format":
                refinements.append(
                    SemanticRefinement(
                        target_ref=violation.id,
                        action="修复章节结构",
                        content="请检查章节编号与标题层级，保证目录、正文标题和章节顺序一致，避免出现章节跳号或标题缺失。",
                    )
                )
                continue
            refinements.append(
                SemanticRefinement(
                    target_ref=violation.id,
                    action="润色表达",
                    content="请根据上下文压缩冗余表达、拆分长句并清理重复标点，保证学术写作语气稳定。",
                )
            )
        return refinements
