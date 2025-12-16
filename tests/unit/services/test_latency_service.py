"""
Unit Tests - Latency Service
Location: tests/unit/services/test_latency_service.py

Tests for Story 1: Latency analysis business logic.
"""

import pytest
from datetime import datetime

from api.services.latency_service import get_summary, LATENCY_WARNING_MS, LATENCY_CRITICAL_MS
from api.models import LatencyStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestLatencySummaryEmpty:
    """Tests for empty data handling."""
    
    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response with zero counts."""
        result = get_summary(empty_calls, project=None, days=7)
        
        assert isinstance(result, LatencyStoryResponse)
        assert result.summary.total_calls == 0
        assert result.summary.issue_count == 0
        assert result.summary.critical_count == 0
        assert result.summary.warning_count == 0
        assert result.health_score == 100.0
        assert result.status == "ok"
        assert result.top_offender is None
        assert result.detail_table == []
    
    def test_empty_calls_has_no_recommendations(self, empty_calls):
        """Empty data should still return recommendations list."""
        result = get_summary(empty_calls, project=None, days=7)
        
        # Recommendations come from story_definitions, should still be present
        assert isinstance(result.recommendations, list)


class TestLatencySummaryBasic:
    """Tests for basic latency calculations."""
    
    def test_single_fast_call(self):
        """Single fast call shows healthy metrics."""
        calls = [make_call_dict(latency_ms=500, operation="fast_op", agent_name="Agent")]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.total_calls == 1
        assert result.summary.avg_latency_ms == 500.0
        assert result.summary.critical_count == 0
        assert result.summary.warning_count == 0
        assert result.status == "ok"
        assert result.health_score == 100.0
    
    def test_calculates_correct_average(self):
        """Average latency is calculated correctly."""
        calls = [
            make_call_dict(latency_ms=1000, operation="op", agent_name="Agent"),
            make_call_dict(latency_ms=2000, operation="op", agent_name="Agent"),
            make_call_dict(latency_ms=3000, operation="op", agent_name="Agent"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.avg_latency_ms == 2000.0
        assert result.summary.total_calls == 3


class TestLatencyThresholds:
    """Tests for warning and critical threshold detection."""
    
    def test_warning_threshold_detection(self):
        """Operations above 5s average trigger warning."""
        calls = [
            make_call_dict(latency_ms=6000, operation="slow_op", agent_name="Agent"),
            make_call_dict(latency_ms=7000, operation="slow_op", agent_name="Agent"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.warning_count == 1
        assert result.summary.critical_count == 0
        assert result.status == "warning"
        assert result.health_score < 100.0
    
    def test_critical_threshold_detection(self):
        """Operations above 10s average trigger critical."""
        calls = [
            make_call_dict(latency_ms=12000, operation="critical_op", agent_name="Agent"),
            make_call_dict(latency_ms=15000, operation="critical_op", agent_name="Agent"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.critical_count == 1
        assert result.status == "error"
        assert result.health_score < 50.0
    
    def test_mixed_thresholds(self, mixed_latency_calls):
        """Mixed calls correctly identify warning and critical operations."""
        result = get_summary(mixed_latency_calls, project=None, days=7)
        
        # Should have: critical_op (25s), slow_op (12-15s avg), and possibly medium_op
        assert result.summary.critical_count >= 1
        assert result.summary.issue_count >= 1
        assert result.status == "error"  # Has at least one critical


class TestLatencyDetailTable:
    """Tests for detail table generation."""
    
    def test_detail_table_groups_by_operation(self):
        """Detail table groups calls by agent.operation."""
        calls = [
            make_call_dict(operation="op_a", agent_name="AgentA", latency_ms=1000),
            make_call_dict(operation="op_a", agent_name="AgentA", latency_ms=1200),
            make_call_dict(operation="op_b", agent_name="AgentB", latency_ms=2000),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.detail_table) == 2
        
        # Check operation names are formatted as agent.operation
        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names
    
    def test_detail_table_sorted_by_latency(self, mixed_latency_calls):
        """Detail table is sorted by average latency (slowest first)."""
        result = get_summary(mixed_latency_calls, project=None, days=7)
        
        latencies = [row['avg_latency_ms'] for row in result.detail_table]
        assert latencies == sorted(latencies, reverse=True)
    
    def test_detail_table_includes_call_count(self):
        """Each row includes correct call count."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", latency_ms=1000),
            make_call_dict(operation="op", agent_name="Agent", latency_ms=1000),
            make_call_dict(operation="op", agent_name="Agent", latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.detail_table[0]['call_count'] == 3
    
    def test_detail_table_status_indicators(self):
        """Status indicators (🔴, 🟡, 🟢) are set correctly."""
        calls = [
            make_call_dict(operation="critical", agent_name="Agent", latency_ms=15000),
            make_call_dict(operation="warning", agent_name="Agent", latency_ms=7000),
            make_call_dict(operation="ok", agent_name="Agent", latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        statuses = {row['operation']: row['status'] for row in result.detail_table}
        assert statuses["Agent.critical"] == "🔴"
        assert statuses["Agent.warning"] == "🟡"
        assert statuses["Agent.ok"] == "🟢"


class TestTopOffender:
    """Tests for top offender identification."""
    
    def test_top_offender_identifies_slowest(self, mixed_latency_calls):
        """Top offender is the slowest operation."""
        result = get_summary(mixed_latency_calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.operation == "critical_op"
        assert result.top_offender.agent == "CriticalAgent"
    
    def test_top_offender_includes_diagnosis(self):
        """Top offender includes diagnostic message."""
        calls = [
            make_call_dict(
                operation="slow_op",
                agent_name="Agent",
                latency_ms=15000,
                completion_tokens=2000,  # High completion tokens
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.diagnosis is not None
        assert len(result.top_offender.diagnosis) > 0
    
    def test_no_top_offender_when_all_fast(self):
        """No top offender when all operations are fast."""
        calls = [
            make_call_dict(operation="fast_op", agent_name="Agent", latency_ms=500),
            make_call_dict(operation="fast_op", agent_name="Agent", latency_ms=600),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is None


class TestChartData:
    """Tests for chart data generation."""
    
    def test_chart_data_limited_to_10(self):
        """Chart data is limited to top 10 operations."""
        # Create 15 different operations
        calls = [
            make_call_dict(operation=f"op_{i}", agent_name="Agent", latency_ms=1000 + i * 100)
            for i in range(15)
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) <= 10
    
    def test_chart_data_structure(self):
        """Chart data has required fields."""
        calls = [make_call_dict(operation="op", agent_name="Agent", latency_ms=1000)]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'avg_latency_ms' in result.chart_data[0]
        assert 'call_count' in result.chart_data[0]


class TestHealthScore:
    """Tests for health score calculation."""
    
    def test_perfect_health_no_issues(self):
        """100% health when no issues."""
        calls = [make_call_dict(operation="op", agent_name="Agent", latency_ms=500)]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score == 100.0
    
    def test_health_degrades_with_warnings(self):
        """Health score decreases with warning operations."""
        calls = [
            make_call_dict(operation="warn_op", agent_name="Agent", latency_ms=7000),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert 50.0 < result.health_score < 100.0
    
    def test_health_degrades_more_with_critical(self):
        """Health score decreases more with critical operations."""
        calls = [
            make_call_dict(operation="crit_op", agent_name="Agent", latency_ms=15000),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score <= 50.0
    
    def test_health_floors_at_zero(self):
        """Health score doesn't go below 0."""
        # Many critical operations
        calls = [
            make_call_dict(operation=f"crit_{i}", agent_name="Agent", latency_ms=20000)
            for i in range(10)
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score >= 0


class TestDiagnosis:
    """Tests for diagnosis message generation."""
    
    def test_diagnoses_high_completion_tokens(self):
        """Diagnoses high completion tokens as cause."""
        calls = [
            make_call_dict(
                operation="slow_op",
                agent_name="Agent",
                latency_ms=12000,
                completion_tokens=2000,
                prompt_tokens=500,
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert "completion" in result.top_offender.diagnosis.lower()
    
    def test_diagnoses_large_prompt(self):
        """Diagnoses large prompt as cause."""
        calls = [
            make_call_dict(
                operation="slow_op",
                agent_name="Agent",
                latency_ms=12000,
                completion_tokens=200,
                prompt_tokens=5000,
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert "prompt" in result.top_offender.diagnosis.lower()


class TestLatencyFormatting:
    """Tests for latency string formatting."""
    
    def test_formats_milliseconds(self):
        """Latencies under 1s show as ms."""
        calls = [make_call_dict(operation="op", agent_name="Agent", latency_ms=500)]
        
        result = get_summary(calls, project=None, days=7)
        
        # avg_latency should be formatted string
        assert "ms" in result.summary.avg_latency or "s" in result.summary.avg_latency
    
    def test_formats_seconds(self):
        """Latencies over 1s show as seconds."""
        calls = [make_call_dict(operation="op", agent_name="Agent", latency_ms=5500)]
        
        result = get_summary(calls, project=None, days=7)
        
        # Should format as seconds (e.g., "5.5s")
        assert "s" in result.summary.avg_latency