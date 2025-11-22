import statistics
from collections import defaultdict
from typing import List

from observatory.models import Session, LatencyBreakdown, LLMCall


class LatencyAnalyzer:
    def analyze(self, session: Session) -> LatencyBreakdown:
        """Analyze latency breakdown for a session."""
        if not session.llm_calls:
            return LatencyBreakdown(
                total_latency_ms=0.0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                by_agent={},
                by_operation={},
            )
        
        latencies = [call.latency_ms for call in session.llm_calls]
        sorted_latencies = sorted(latencies)
        
        by_agent = defaultdict(list)
        by_operation = defaultdict(list)
        
        for call in session.llm_calls:
            if call.agent_name:
                by_agent[call.agent_name].append(call.latency_ms)
            if call.operation:
                by_operation[call.operation].append(call.latency_ms)
        
        return LatencyBreakdown(
            total_latency_ms=session.total_latency_ms,
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=self._percentile(sorted_latencies, 50),
            p95_latency_ms=self._percentile(sorted_latencies, 95),
            p99_latency_ms=self._percentile(sorted_latencies, 99),
            by_agent={k: sum(v) for k, v in by_agent.items()},
            by_operation={k: sum(v) for k, v in by_operation.items()},
        )

    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile of sorted values."""
        if not sorted_values:
            return 0.0
        
        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1
        
        if c >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])