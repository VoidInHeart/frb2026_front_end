from __future__ import annotations

from paper_review_system.models import PaperBlock, Violation
from paper_review_system.rules.citation_rules import CitationRuleChecker
from paper_review_system.rules.format_rules import FormatRuleChecker
from paper_review_system.rules.grammar_rules import GrammarRuleChecker
from paper_review_system.rules.violation_id import ViolationIdAllocator


class RuleEngine:
    """Run all rule-based scanners and allocate stable IDs."""

    def __init__(self) -> None:
        self.format_checker = FormatRuleChecker()
        self.citation_checker = CitationRuleChecker()
        self.grammar_checker = GrammarRuleChecker()

    def scan(self, clean_blocks: list[PaperBlock]) -> list[Violation]:
        allocator = ViolationIdAllocator()
        violations: list[Violation] = []
        violations.extend(self.format_checker.check(clean_blocks, allocator))
        violations.extend(self.citation_checker.check(clean_blocks, allocator))
        violations.extend(self.grammar_checker.check(clean_blocks, allocator))
        return violations
