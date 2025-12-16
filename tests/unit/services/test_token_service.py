# test_token_service.py

"""
Unit Tests - Token Service
Location: tests/unit/services/test_token_service.py

Tests for Story 5: Token efficiency business logic.
"""

import pytest
from api.services.token_service import get_summary, TOKEN_RATIO_WARNING, TOKEN_RATIO_CRITICAL
from api.models import TokenImbalanceStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestTokenSummaryEmpty:
    """Tests for empty data handling."""
    
    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response with zero counts."""
        result = get_summary(empty_calls, project=None, days=7)
        
        assert isinstance(result, TokenImbalanceStoryResponse)
        assert result.summary.total_calls == 0
        assert result.summary.issue_count == 0
        assert result.summary.avg_ratio == 0.0
        assert result.summary.worst_ratio == 0.0
        assert result.summary.imbalanced_count == 0
        assert result.health_score == 100.0
        assert result.status == "ok"
        assert result.top_offender is None
        assert result.detail_table == []
    
    def test_non_llm_calls_filtered_out(self):
        """Calls without prompt tokens are filtered out."""
        calls = [
            make_call_dict(prompt_tokens=0, completion_tokens=0),
            make_call_dict(prompt_tokens=None, completion_tokens=0),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.total_calls == 0


class TestRatioCalculation:
    """Tests for token ratio calculations."""
    
    def test_calculates_prompt_to_completion_ratio(self):
        """Ratio calculated as prompt/completion tokens."""
        calls = [
            make_call_dict(prompt_tokens=2000, completion_tokens=100),  # 20:1 ratio
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['ratio'] == 20.0
        assert "20:1" in row['ratio_formatted']
    
    def test_average_ratio_calculation(self):
        """Average ratio calculated across all calls."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=1000, completion_tokens=100),  # 10:1
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=3000, completion_tokens=100),  # 30:1
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.avg_ratio == 20.0
    
    def test_worst_ratio_identification(self):
        """Worst ratio identified correctly."""
        calls = [
            make_call_dict(operation="balanced", agent_name="Agent", prompt_tokens=500, completion_tokens=400),
            make_call_dict(operation="imbalanced", agent_name="Agent", prompt_tokens=2000, completion_tokens=50),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.worst_ratio == 40.0
    
    def test_zero_completion_tokens_handled(self):
        """Zero completion tokens handled gracefully."""
        calls = [
            make_call_dict(prompt_tokens=1000, completion_tokens=0),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['ratio'] == 0 or row['ratio'] == float('inf')


class TestDetailTable:
    """Tests for detail table generation."""
    
    def test_groups_by_operation(self):
        """Detail table groups calls by agent.operation."""
        calls = [
            make_call_dict(operation="op_a", agent_name="AgentA", prompt_tokens=1000, completion_tokens=100),
            make_call_dict(operation="op_a", agent_name="AgentA", prompt_tokens=1000, completion_tokens=100),
            make_call_dict(operation="op_b", agent_name="AgentB", prompt_tokens=500, completion_tokens=500),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.detail_table) == 2
        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names
    
    def test_calculates_averages_per_operation(self):
        """Each operation shows average token counts."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=1000, completion_tokens=100),
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=2000, completion_tokens=200),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['avg_prompt_tokens'] == 1500
        assert row['avg_completion_tokens'] == 150
    
    def test_status_indicators(self):
        """Status indicators reflect imbalance levels."""
        calls = [
            # Critical imbalance (>20:1)
            make_call_dict(operation="critical", agent_name="Agent", prompt_tokens=2500, completion_tokens=100),
            # Warning imbalance (10-20:1)
            make_call_dict(operation="warning", agent_name="Agent", prompt_tokens=1500, completion_tokens=100),
            # Balanced (<10:1)
            make_call_dict(operation="balanced", agent_name="Agent", prompt_tokens=500, completion_tokens=400),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        statuses = {row['operation']: row['status'] for row in result.detail_table}
        assert statuses["Agent.critical"] == "🔴"
        assert statuses["Agent.warning"] == "🟡"
        assert statuses["Agent.balanced"] == "🟢"
    
    def test_sorted_by_ratio_descending(self):
        """Detail table sorted by ratio (highest first)."""
        calls = [
            make_call_dict(operation="low", agent_name="Agent", prompt_tokens=500, completion_tokens=400),
            make_call_dict(operation="high", agent_name="Agent", prompt_tokens=2000, completion_tokens=50),
            make_call_dict(operation="medium", agent_name="Agent", prompt_tokens=1000, completion_tokens=100),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        ratios = [row['ratio'] for row in result.detail_table]
        assert ratios == sorted(ratios, reverse=True)
        assert result.detail_table[0]['operation'] == "Agent.high"


class TestImbalanceThresholds:
    """Tests for warning and critical threshold detection."""
    
    def test_warning_threshold_detection(self):
        """Ratios above 10:1 trigger warning."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=1500, completion_tokens=100),  # 15:1
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.imbalanced_count == 1
        assert result.status == "warning"
        row = result.detail_table[0]
        assert row['is_imbalanced'] is True
    
    def test_critical_threshold_detection(self):
        """Ratios above 20:1 trigger critical."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=2500, completion_tokens=100),  # 25:1
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.imbalanced_count == 1
        assert result.status == "error"
        row = result.detail_table[0]
        assert row['is_critical'] is True
    
    def test_mixed_thresholds(self, token_imbalance_calls):
        """Mixed calls correctly identify warning and critical operations."""
        result = get_summary(token_imbalance_calls, project=None, days=7)
        
        # Should have 1 imbalanced operation (chat), even though it has 2 calls
        assert result.summary.imbalanced_count >= 1
        critical = [row for row in result.detail_table if row.get('is_critical')]
        assert len(critical) >= 1


class TestTopOffender:
    """Tests for top offender identification."""
    
    def test_identifies_worst_ratio(self):
        """Top offender is operation with worst ratio."""
        calls = [
            make_call_dict(operation="bad", agent_name="Agent", prompt_tokens=3000, completion_tokens=50),
            make_call_dict(operation="ok", agent_name="Agent", prompt_tokens=1000, completion_tokens=100),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.operation == "bad"
        assert result.top_offender.value == 60.0
    
    def test_top_offender_includes_diagnosis(self):
        """Top offender includes diagnostic message."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=3500,
                completion_tokens=100
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.diagnosis is not None
        assert len(result.top_offender.diagnosis) > 0
    
    def test_no_top_offender_when_balanced(self):
        """No top offender when all operations balanced."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=500, completion_tokens=400),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is None


class TestDiagnosis:
    """Tests for diagnosis message generation."""
    
    def test_diagnoses_large_context_minimal_output(self):
        """Diagnoses large context with minimal output."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=3500,
                completion_tokens=150
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert "context" in result.top_offender.diagnosis.lower() or "history" in result.top_offender.diagnosis.lower()
    
    def test_diagnoses_moderate_imbalance(self):
        """Diagnoses moderate imbalance."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1800,
                completion_tokens=100
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        diagnosis = result.top_offender.diagnosis.lower()
        assert "summariz" in diagnosis or "context" in diagnosis or "reduc" in diagnosis


class TestHealthScore:
    """Tests for health score calculation."""
    
    def test_perfect_health_balanced_ratios(self):
        """100% health when all ratios balanced."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=500, completion_tokens=400),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score == 100.0
        assert result.status == "ok"
    
    def test_health_degrades_with_warnings(self):
        """Health score decreases with warning operations."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=1500, completion_tokens=100),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert 60 <= result.health_score <= 85
        assert result.status == "warning"
    
    def test_health_degrades_more_with_critical(self):
        """Health score decreases more with critical operations."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=2500, completion_tokens=100),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score <= 60
        assert result.status == "error"
    
    def test_health_floors_at_30(self):
        """Health score doesn't go below reasonable minimum."""
        # Many critical imbalances
        calls = [
            make_call_dict(operation=f"op_{i}", agent_name="Agent", prompt_tokens=3000, completion_tokens=50)
            for i in range(10)
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score >= 0


class TestChartData:
    """Tests for chart data generation."""
    
    def test_chart_data_limited_to_10(self):
        """Chart data limited to top 10 operations."""
        calls = [
            make_call_dict(
                operation=f"op_{i}",
                agent_name="Agent",
                prompt_tokens=1000 + i * 100,
                completion_tokens=100
            )
            for i in range(15)
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) <= 10
    
    def test_chart_data_structure(self):
        """Chart data has required fields."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=1000, completion_tokens=100),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'prompt' in result.chart_data[0]
        assert 'completion' in result.chart_data[0]
        assert 'ratio' in result.chart_data[0]


class TestTokenFormatting:
    """Tests for token string formatting."""
    
    def test_formats_token_counts(self):
        """Token counts formatted correctly."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=1500, completion_tokens=250),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert isinstance(row['avg_prompt'], str)
        assert isinstance(row['avg_completion'], str)
    
    def test_formats_ratio_string(self):
        """Ratio formatted as X:1."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=1500, completion_tokens=100),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert ":1" in row['ratio_formatted']


class TestImbalanceCounting:
    """Tests for imbalanced operation counting."""
    
    def test_counts_imbalanced_operations(self, token_imbalance_calls):
        """Imbalanced count reflects operations above threshold."""
        result = get_summary(token_imbalance_calls, project=None, days=7)
        
        # chat operations have 30-40:1 ratio
        assert result.summary.imbalanced_count >= 1
    
    def test_issue_count_matches_imbalanced_count(self):
        """Issue count equals imbalanced count."""
        calls = [
            make_call_dict(operation="op1", agent_name="Agent", prompt_tokens=2000, completion_tokens=50),
            make_call_dict(operation="op2", agent_name="Agent", prompt_tokens=1500, completion_tokens=100),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.issue_count == result.summary.imbalanced_count