"""
Unit Tests - Cost Service
Location: tests/unit/services/test_cost_service.py

Tests for Story 7: Cost analysis business logic.
"""

import pytest
from api.services.cost_service import (
    get_summary,
    get_operation_detail,
    _get_status,
    COST_CONCENTRATION_THRESHOLD,
    HIGH_COST_THRESHOLD,
    MEDIUM_COST_THRESHOLD,
)
from api.models import CostStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestCostSummaryEmpty:
    """Tests for empty data handling."""

    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response with zero counts."""
        result = get_summary(empty_calls, project=None, days=7)

        assert isinstance(result, CostStoryResponse)
        assert result.summary.total_calls == 0
        assert result.summary.issue_count == 0
        assert result.summary.total_cost == 0.0
        assert result.summary.avg_cost_per_call == 0.0
        assert result.health_score == 100.0
        assert result.status == "ok"
        assert result.top_offender is None
        assert result.detail_table == []

    def test_empty_calls_has_recommendations(self, empty_calls):
        """Empty data should still return recommendations list."""
        result = get_summary(empty_calls, project=None, days=7)

        assert isinstance(result.recommendations, list)

    def test_zero_cost_calls_returns_valid_response(self):
        """Calls with zero cost return valid response."""
        calls = [
            make_call_dict(total_cost=0.0, operation="free_op", agent_name="Agent"),
            make_call_dict(total_cost=0.0, operation="free_op", agent_name="Agent"),
        ]

        result = get_summary(calls, project=None, days=7)

        assert result.summary.total_calls == 2
        assert result.summary.total_cost == 0.0
        assert result.status == "ok"


class TestCostSummaryBasic:
    """Tests for basic cost calculations."""

    def test_single_call_cost(self):
        """Single call shows correct cost metrics."""
        calls = [make_call_dict(total_cost=0.05, operation="test_op", agent_name="Agent")]

        result = get_summary(calls, project=None, days=7)

        assert result.summary.total_calls == 1
        assert result.summary.total_cost == 0.05
        assert result.summary.avg_cost_per_call == 0.05

    def test_calculates_correct_total_cost(self):
        """Total cost is sum of all call costs."""
        calls = [
            make_call_dict(total_cost=0.10, operation="op", agent_name="Agent"),
            make_call_dict(total_cost=0.20, operation="op", agent_name="Agent"),
            make_call_dict(total_cost=0.30, operation="op", agent_name="Agent"),
        ]

        result = get_summary(calls, project=None, days=7)

        assert result.summary.total_cost == 0.60
        assert result.summary.avg_cost_per_call == 0.20

    def test_calculates_potential_savings(self):
        """Potential savings is 20% of total cost."""
        calls = [make_call_dict(total_cost=1.00, operation="op", agent_name="Agent")]

        result = get_summary(calls, project=None, days=7)

        assert result.summary.potential_savings == 0.20


class TestCostThresholds:
    """Tests for high/medium/low cost threshold detection."""

    def test_get_status_high(self):
        """Cost share >= 15% returns high status."""
        status, emoji = _get_status(0.20)
        assert status == "high"
        assert emoji == "🔴"

    def test_get_status_medium(self):
        """Cost share >= 5% but < 15% returns medium status."""
        status, emoji = _get_status(0.10)
        assert status == "medium"
        assert emoji == "🟡"

    def test_get_status_low(self):
        """Cost share < 5% returns low status."""
        status, emoji = _get_status(0.03)
        assert status == "low"
        assert emoji == "🟢"

    def test_high_cost_operation_counted_as_issue(self):
        """Operations with >15% cost share are counted as issues."""
        calls = [
            # One expensive operation (100% of cost)
            make_call_dict(total_cost=1.00, operation="expensive", agent_name="Agent"),
        ]

        result = get_summary(calls, project=None, days=7)

        assert result.summary.issue_count == 1


class TestCostDetailTable:
    """Tests for detail table generation."""

    def test_detail_table_groups_by_operation(self):
        """Detail table groups calls by agent.operation."""
        calls = [
            make_call_dict(operation="op_a", agent_name="AgentA", total_cost=0.10),
            make_call_dict(operation="op_a", agent_name="AgentA", total_cost=0.12),
            make_call_dict(operation="op_b", agent_name="AgentB", total_cost=0.20),
        ]

        result = get_summary(calls, project=None, days=7)

        assert len(result.detail_table) == 2

        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names

    def test_detail_table_sorted_by_cost(self):
        """Detail table is sorted by total cost (highest first)."""
        calls = [
            make_call_dict(operation="cheap", agent_name="Agent", total_cost=0.01),
            make_call_dict(operation="expensive", agent_name="Agent", total_cost=0.50),
            make_call_dict(operation="medium", agent_name="Agent", total_cost=0.10),
        ]

        result = get_summary(calls, project=None, days=7)

        costs = [row['total_cost'] for row in result.detail_table]
        assert costs == sorted(costs, reverse=True)

    def test_detail_table_includes_call_count(self):
        """Each row includes correct call count."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.10),
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.10),
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.10),
        ]

        result = get_summary(calls, project=None, days=7)

        assert result.detail_table[0]['call_count'] == 3

    def test_detail_table_calculates_cost_percentage(self):
        """Cost percentage is calculated correctly."""
        calls = [
            make_call_dict(operation="half", agent_name="Agent", total_cost=0.50),
            make_call_dict(operation="other_half", agent_name="Agent", total_cost=0.50),
        ]

        result = get_summary(calls, project=None, days=7)

        for row in result.detail_table:
            assert abs(row['cost_pct'] - 0.50) < 0.01

    def test_detail_table_includes_token_counts(self):
        """Detail table includes total prompt and completion tokens."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=100, completion_tokens=50),
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=200, completion_tokens=100),
        ]

        result = get_summary(calls, project=None, days=7)

        assert result.detail_table[0]['total_prompt_tokens'] == 300
        assert result.detail_table[0]['total_completion_tokens'] == 150


class TestCostConcentration:
    """Tests for cost concentration detection."""

    def test_calculates_top_3_concentration(self):
        """Top 3 concentration is calculated correctly."""
        calls = [
            make_call_dict(operation="op1", agent_name="Agent", total_cost=0.40),
            make_call_dict(operation="op2", agent_name="Agent", total_cost=0.30),
            make_call_dict(operation="op3", agent_name="Agent", total_cost=0.20),
            make_call_dict(operation="op4", agent_name="Agent", total_cost=0.10),
        ]

        result = get_summary(calls, project=None, days=7)

        # Top 3 = 0.40 + 0.30 + 0.20 = 0.90 = 90%
        assert abs(result.summary.top_3_concentration - 0.90) < 0.01

    def test_high_concentration_triggers_warning(self, cost_concentration_calls):
        """High cost concentration (>70%) triggers warning status."""
        result = get_summary(cost_concentration_calls, project=None, days=7)

        # deep_analyze calls dominate the cost
        assert result.summary.top_3_concentration > COST_CONCENTRATION_THRESHOLD
        assert result.status == "warning"
        assert result.health_score < 100.0


class TestTopOffender:
    """Tests for top offender identification."""

    def test_top_offender_identifies_most_expensive(self):
        """Top offender is the most expensive operation."""
        calls = [
            make_call_dict(operation="cheap", agent_name="CheapAgent", total_cost=0.01),
            make_call_dict(operation="expensive", agent_name="ExpensiveAgent", total_cost=0.50),
            make_call_dict(operation="medium", agent_name="MediumAgent", total_cost=0.10),
        ]

        result = get_summary(calls, project=None, days=7)

        assert result.top_offender is not None
        assert result.top_offender.operation == "expensive"
        assert result.top_offender.agent == "ExpensiveAgent"

    def test_top_offender_includes_value(self):
        """Top offender includes cost value."""
        calls = [make_call_dict(operation="op", agent_name="Agent", total_cost=0.25)]

        result = get_summary(calls, project=None, days=7)

        assert result.top_offender is not None
        assert result.top_offender.value == 0.25

    def test_top_offender_includes_diagnosis(self):
        """Top offender includes diagnostic message."""
        calls = [make_call_dict(operation="op", agent_name="Agent", total_cost=0.25)]

        result = get_summary(calls, project=None, days=7)

        assert result.top_offender is not None
        assert result.top_offender.diagnosis is not None
        assert "%" in result.top_offender.diagnosis  # Contains percentage


class TestChartData:
    """Tests for chart data generation."""

    def test_chart_data_limited_to_10(self):
        """Chart data is limited to top 10 operations."""
        calls = [
            make_call_dict(operation=f"op_{i}", agent_name="Agent", total_cost=0.01 * (i + 1))
            for i in range(15)
        ]

        result = get_summary(calls, project=None, days=7)

        assert len(result.chart_data) <= 10

    def test_chart_data_structure(self):
        """Chart data has required fields."""
        calls = [make_call_dict(operation="op", agent_name="Agent", total_cost=0.10)]

        result = get_summary(calls, project=None, days=7)

        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'value' in result.chart_data[0]
        assert 'cost' in result.chart_data[0]
        assert 'calls' in result.chart_data[0]
        assert 'percentage' in result.chart_data[0]


class TestHealthScore:
    """Tests for health score calculation."""

    def test_perfect_health_no_concentration(self):
        """100% health when cost is well distributed."""
        calls = [
            make_call_dict(operation=f"op_{i}", agent_name="Agent", total_cost=0.10)
            for i in range(10)  # 10% each, no concentration
        ]

        result = get_summary(calls, project=None, days=7)

        # Top 3 = 30%, well under 70% threshold
        assert result.health_score == 100.0
        assert result.status == "ok"

    def test_health_degrades_with_concentration(self, cost_concentration_calls):
        """Health score decreases with high cost concentration."""
        result = get_summary(cost_concentration_calls, project=None, days=7)

        assert result.health_score < 100.0


class TestCostFormatting:
    """Tests for cost string formatting."""

    def test_formats_total_cost(self):
        """Total cost is formatted as currency."""
        calls = [make_call_dict(operation="op", agent_name="Agent", total_cost=1.50)]

        result = get_summary(calls, project=None, days=7)

        assert "$" in result.summary.total_cost_formatted

    def test_formats_average_cost(self):
        """Average cost is formatted as currency."""
        calls = [make_call_dict(operation="op", agent_name="Agent", total_cost=0.05)]

        result = get_summary(calls, project=None, days=7)

        assert "$" in result.summary.avg_cost_formatted


class TestOperationDetail:
    """Tests for Layer 2 operation detail."""

    def test_returns_none_for_nonexistent_operation(self):
        """Returns None if operation doesn't exist."""
        calls = [make_call_dict(operation="op", agent_name="Agent", total_cost=0.10)]

        result = get_operation_detail(calls, agent="NonExistent", operation="fake_op")

        assert result is None

    def test_filters_by_agent_and_operation(self):
        """Filters calls correctly by agent and operation."""
        calls = [
            make_call_dict(operation="target", agent_name="TargetAgent", total_cost=0.10),
            make_call_dict(operation="target", agent_name="TargetAgent", total_cost=0.15),
            make_call_dict(operation="other", agent_name="OtherAgent", total_cost=0.50),
        ]

        result = get_operation_detail(calls, agent="TargetAgent", operation="target")

        assert result is not None
        assert result['call_count'] == 2
        assert result['total_cost'] == 0.25

    def test_calculates_averages(self):
        """Calculates average cost and tokens."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.10, prompt_tokens=100, completion_tokens=50),
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.20, prompt_tokens=200, completion_tokens=100),
        ]

        result = get_operation_detail(calls, agent="Agent", operation="op")

        assert result['avg_cost'] == 0.15
        assert result['avg_prompt_tokens'] == 150
        assert result['avg_completion_tokens'] == 75

    def test_calculates_min_max_cost(self):
        """Calculates min and max cost."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.05),
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.15),
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.10),
        ]

        result = get_operation_detail(calls, agent="Agent", operation="op")

        assert result['min_cost'] == 0.05
        assert result['max_cost'] == 0.15

    def test_includes_formatted_values(self):
        """Includes formatted cost strings."""
        calls = [make_call_dict(operation="op", agent_name="Agent", total_cost=0.10)]

        result = get_operation_detail(calls, agent="Agent", operation="op")

        assert "$" in result['total_cost_formatted']
        assert "$" in result['avg_cost_formatted']
        assert "$" in result['min_cost_formatted']
        assert "$" in result['max_cost_formatted']
