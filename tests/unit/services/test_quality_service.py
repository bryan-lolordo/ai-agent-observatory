# test_quality_service.py

"""
Unit Tests - Quality Service
Location: tests/unit/services/test_quality_service.py

Tests for Story 4: Quality monitoring business logic.
"""

import pytest
from api.services.quality_service import get_summary, ERROR_RATE_WARNING, ERROR_RATE_CRITICAL
from api.models import QualityStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestQualitySummaryEmpty:
    """Tests for empty data handling."""
    
    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response with zero errors."""
        result = get_summary(empty_calls, project=None, days=7)
        
        assert isinstance(result, QualityStoryResponse)
        assert result.summary.total_calls == 0
        assert result.summary.issue_count == 0
        assert result.summary.error_count == 0
        assert result.summary.error_rate == 0.0
        assert result.summary.success_count == 0
        assert result.summary.success_rate == 1.0
        assert result.summary.avg_quality_score == 0.0
        assert result.summary.hallucination_count == 0
        assert result.summary.operations_affected == 0
        assert result.health_score == 100.0
        assert result.status == "ok"
        assert result.top_offender is None
        assert result.detail_table == []


class TestErrorDetection:
    """Tests for error detection and counting."""
    
    def test_counts_failed_calls(self):
        """Failed calls counted correctly."""
        calls = [
            make_call_dict(success=True),
            make_call_dict(success=False, error="API Error"),
            make_call_dict(success=False, error="Timeout"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.error_count == 2
        assert result.summary.success_count == 1
        assert result.summary.error_rate == 2/3
    
    def test_error_with_message(self):
        """Calls with error messages counted as errors."""
        calls = [
            make_call_dict(success=True, error=None),
            make_call_dict(success=True, error="Something went wrong"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.error_count == 1
    
    def test_calculates_success_rate(self):
        """Success rate calculated correctly."""
        calls = [
            make_call_dict(success=True),
            make_call_dict(success=True),
            make_call_dict(success=True),
            make_call_dict(success=False),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.success_rate == 0.75
        assert "75" in result.summary.error_rate_formatted or "25" in result.summary.error_rate_formatted


class TestHallucinationDetection:
    """Tests for hallucination detection."""
    
    def test_counts_hallucinations(self, quality_issue_calls):
        """Hallucinations counted correctly."""
        result = get_summary(quality_issue_calls, project=None, days=7)
        
        # One call has hallucination_flag=True
        assert result.summary.hallucination_count >= 1
    
    def test_hallucination_flag(self):
        """Hallucination flag detected."""
        calls = [
            make_call_dict(
                quality_evaluation={'judge_score': 4.0, 'hallucination_flag': True}
            ),
            make_call_dict(
                quality_evaluation={'judge_score': 8.0, 'hallucination_flag': False}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.hallucination_count == 1


class TestQualityScores:
    """Tests for quality score calculations."""
    
    def test_calculates_average_quality_score(self):
        """Average quality score calculated correctly."""
        calls = [
            make_call_dict(quality_evaluation={'judge_score': 8.0}),
            make_call_dict(quality_evaluation={'judge_score': 6.0}),
            make_call_dict(quality_evaluation={'judge_score': 10.0}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.avg_quality_score == 8.0
    
    def test_ignores_calls_without_quality_eval(self):
        """Calls without quality evaluation not included in average."""
        calls = [
            make_call_dict(quality_evaluation={'judge_score': 8.0}),
            make_call_dict(quality_evaluation={'judge_score': 6.0}),
            make_call_dict(quality_evaluation=None),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.avg_quality_score == 7.0
    
    def test_handles_missing_judge_score(self):
        """Handles quality evaluations without judge_score."""
        calls = [
            make_call_dict(quality_evaluation={'hallucination_flag': True}),
            make_call_dict(quality_evaluation={'judge_score': 8.0}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.avg_quality_score == 8.0


class TestDetailTable:
    """Tests for detail table generation."""
    
    def test_groups_by_operation(self):
        """Detail table groups calls by agent.operation."""
        calls = [
            make_call_dict(operation="op_a", agent_name="AgentA", success=True),
            make_call_dict(operation="op_a", agent_name="AgentA", success=False),
            make_call_dict(operation="op_b", agent_name="AgentB", success=True),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.detail_table) == 2
        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names
    
    def test_counts_errors_per_operation(self):
        """Each operation shows error count."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", success=False),
            make_call_dict(operation="op", agent_name="Agent", success=False),
            make_call_dict(operation="op", agent_name="Agent", success=True),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['error_count'] == 2
        assert row['call_count'] == 3
    
    def test_calculates_quality_metrics_per_operation(self):
        """Each operation shows avg and min quality scores."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", quality_evaluation={'judge_score': 8.0}),
            make_call_dict(operation="op", agent_name="Agent", quality_evaluation={'judge_score': 6.0}),
            make_call_dict(operation="op", agent_name="Agent", quality_evaluation={'judge_score': 10.0}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['avg_score'] == 8.0
        assert row['min_score'] == 6.0
    
    def test_status_indicators(self):
        """Status indicators reflect quality issues."""
        calls = [
            # Operation with errors
            make_call_dict(operation="errors", agent_name="Agent", success=False),
            make_call_dict(operation="errors", agent_name="Agent", success=False),
            # Operation with low quality
            make_call_dict(operation="low_quality", agent_name="Agent", quality_evaluation={'judge_score': 5.0}),
            # Operation with good quality
            make_call_dict(operation="good", agent_name="Agent", quality_evaluation={'judge_score': 9.0}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        statuses = {row['operation']: row['status'] for row in result.detail_table}
        assert statuses["Agent.errors"] == "🔴"
        assert statuses["Agent.low_quality"] == "🔴"
        assert statuses["Agent.good"] == "🟢"
    
    def test_sorted_by_error_count(self):
        """Detail table sorted by error count (most errors first)."""
        calls = [
            *[make_call_dict(operation="many_errors", agent_name="Agent", success=False) for _ in range(5)],
            *[make_call_dict(operation="few_errors", agent_name="Agent", success=False) for _ in range(2)],
            make_call_dict(operation="no_errors", agent_name="Agent", success=True),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        error_counts = [row['error_count'] for row in result.detail_table]
        assert error_counts == sorted(error_counts, reverse=True)
        assert result.detail_table[0]['operation'] == "Agent.many_errors"


class TestOperationsAffected:
    """Tests for operations affected count."""
    
    def test_counts_operations_with_errors(self):
        """Operations affected counts distinct operations with errors."""
        calls = [
            make_call_dict(operation="op1", agent_name="Agent", success=False),
            make_call_dict(operation="op1", agent_name="Agent", success=False),
            make_call_dict(operation="op2", agent_name="Agent", success=False),
            make_call_dict(operation="op3", agent_name="Agent", success=True),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.operations_affected == 2


class TestTopOffender:
    """Tests for top offender identification."""
    
    def test_identifies_most_errors(self):
        """Top offender is operation with most errors."""
        calls = [
            *[make_call_dict(operation="many", agent_name="Agent", success=False) for _ in range(5)],
            *[make_call_dict(operation="few", agent_name="Agent", success=False) for _ in range(2)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.operation == "many"
        assert result.top_offender.value == 5
    
    def test_top_offender_includes_quality_score(self):
        """Top offender diagnosis includes quality score if available."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                success=False,
                quality_evaluation={'judge_score': 4.0}
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                success=False,
                quality_evaluation={'judge_score': 5.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert "quality" in result.top_offender.diagnosis.lower() or "4." in result.top_offender.diagnosis
    
    def test_no_top_offender_without_issues(self):
        """No top offender when no quality issues."""
        calls = [
            make_call_dict(success=True, quality_evaluation={'judge_score': 9.0}),
            make_call_dict(success=True, quality_evaluation={'judge_score': 8.0}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is None


class TestErrorRateThresholds:
    """Tests for error rate threshold detection."""
    
    def test_warning_threshold(self):
        """Error rate above 2% triggers warning."""
        # 3 errors out of 100 = 3% error rate
        calls = [
            *[make_call_dict(success=False) for _ in range(3)],
            *[make_call_dict(success=True) for _ in range(97)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.error_rate >= ERROR_RATE_WARNING
        assert result.status == "warning"
    
    def test_critical_threshold(self):
        """Error rate above 5% triggers critical."""
        # 6 errors out of 100 = 6% error rate
        calls = [
            *[make_call_dict(success=False) for _ in range(6)],
            *[make_call_dict(success=True) for _ in range(94)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.error_rate >= ERROR_RATE_CRITICAL
        assert result.status == "error"
    
    def test_below_warning_threshold(self):
        """Error rate below 2% shows ok status."""
        # 1 error out of 100 = 1% error rate
        calls = [
            make_call_dict(success=False),
            *[make_call_dict(success=True) for _ in range(99)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.error_rate < ERROR_RATE_WARNING
        assert result.status == "ok"


class TestHealthScore:
    """Tests for health score calculation."""
    
    def test_perfect_health_no_errors(self):
        """100% health with no errors."""
        calls = [
            make_call_dict(success=True, quality_evaluation={'judge_score': 9.0}),
            make_call_dict(success=True, quality_evaluation={'judge_score': 8.0}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score == 100.0
        assert result.status == "ok"
    
    def test_health_degrades_with_critical_error_rate(self):
        """Health score severely degraded with critical error rate."""
        calls = [
            *[make_call_dict(success=False) for _ in range(10)],
            *[make_call_dict(success=True) for _ in range(90)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score <= 30
        assert result.status == "error"
    
    def test_health_degrades_with_warnings(self):
        """Health score moderately degraded with warnings."""
        calls = [
            *[make_call_dict(success=False) for _ in range(3)],
            *[make_call_dict(success=True) for _ in range(97)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert 50 <= result.health_score <= 70
        assert result.status == "warning"


class TestChartData:
    """Tests for chart data generation."""
    
    def test_chart_data_limited_to_10(self):
        """Chart data limited to top 10 operations."""
        calls = [
            make_call_dict(operation=f"op_{i}", agent_name="Agent", success=False)
            for i in range(15)
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) <= 10
    
    def test_chart_data_structure(self):
        """Chart data has required fields."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", success=False, quality_evaluation={'judge_score': 5.0}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'errors' in result.chart_data[0]
        assert 'quality' in result.chart_data[0]


class TestMixedQualityIssues:
    """Tests for mixed quality issues."""
    
    def test_quality_issue_calls_fixture(self, quality_issue_calls):
        """Quality issue calls fixture works correctly."""
        result = get_summary(quality_issue_calls, project=None, days=7)
        
        # Should have hallucinations and errors
        assert result.summary.hallucination_count >= 1
        assert result.summary.error_count >= 1
        assert result.summary.issue_count >= 1