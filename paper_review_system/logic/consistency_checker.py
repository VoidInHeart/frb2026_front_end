from __future__ import annotations

from paper_review_system.models import CoreArgumentConsistency, LogicDetail


class ConsistencyChecker:
    """Compare abstract-like sections with method/result-like sections."""

    def evaluate(self, claims: dict[str, dict[str, object]]) -> CoreArgumentConsistency:
        abstract_claim = self._pick_section(claims, include=("abstract", "摘要"))
        method_claim = self._pick_section(claims, include=("method", "方法", "approach"))
        result_claim = self._pick_section(claims, include=("result", "experiment", "实验", "结论", "conclusion"))

        if not abstract_claim or not result_claim:
            return CoreArgumentConsistency(
                is_consistent=True,
                conflict_summary="未检测到足够多的结构化章节，暂未发现明确的核心论点冲突。",
                details=[],
            )

        abstract_keywords = set(abstract_claim["keywords"])
        result_keywords = set(result_claim["keywords"])
        overlap = abstract_keywords & result_keywords

        details: list[LogicDetail] = []
        consistent = len(overlap) >= 2
        if not consistent:
            evidence_links = list(abstract_claim["anchors"][:1]) + list(result_claim["anchors"][:1])
            details.append(
                LogicDetail(
                    logical_node="研究目标 vs. 结果支撑",
                    severity="critical",
                    analysis="摘要或前置章节强调的核心关键词，与结果或结论章节中的关键词重合过少，说明论证链条可能存在目标、方法与验证脱节。",
                    evidence_links=evidence_links,
                )
            )

        if method_claim:
            method_keywords = set(method_claim["keywords"])
            bridge_overlap = (abstract_keywords & method_keywords) | (method_keywords & result_keywords)
            if len(bridge_overlap) <= 1:
                details.append(
                    LogicDetail(
                        logical_node="方法设计 vs. 实验验证",
                        severity="major",
                        analysis="方法章节与实验或结论章节之间共享概念较少，可能存在方法没有被充分验证，或实验指标没有真正回应方法目标的问题。",
                        evidence_links=list(method_claim["anchors"][:1]) + list(result_claim["anchors"][:1]),
                    )
                )

        if details:
            return CoreArgumentConsistency(
                is_consistent=False,
                conflict_summary="论文核心章节之间的术语桥接较弱，目标、方法与结果存在潜在脱节。",
                details=details,
            )

        return CoreArgumentConsistency(
            is_consistent=True,
            conflict_summary="核心章节关键词和论证路径基本一致，未发现明显冲突。",
            details=[],
        )

    @staticmethod
    def _pick_section(claims: dict[str, dict[str, object]], include: tuple[str, ...]) -> dict[str, object] | None:
        for section_id, payload in claims.items():
            lower_section = section_id.lower()
            if any(token in lower_section for token in include):
                return payload
        return None
