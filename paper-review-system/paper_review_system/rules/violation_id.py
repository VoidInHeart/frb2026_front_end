from __future__ import annotations


class ViolationIdAllocator:
    def __init__(self) -> None:
        self._counters = {"FMT": 0, "CIT": 0, "GRM": 0}

    def next(self, prefix: str) -> str:
        if prefix not in self._counters:
            raise ValueError(f"Unsupported violation prefix: {prefix}")
        self._counters[prefix] += 1
        return f"R-{prefix}-{self._counters[prefix]:03d}"
