# test_optimization_service.py

"""
Unit Tests - Optimization Service
Location: tests/unit/services/test_optimization_service.py

Tests for Story 8: Optimization impact business logic.
"""

import pytest
from datetime import datetime, timedelta
from api.services.optimization_service import get_summary
from api.models import OptimizationStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestOptimizationSummaryEmpty:
    """Tests for empty data handling."""
    
    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response."""
        result = get_summary(empty_calls, project=None, days=7)
        
        assert isinstance(result, OptimizationStoryResponse)
        assert result.mode == "baseline"
        assert result.summary.total_optimizations == 0
        assert result.summary.total_cost_saved == 0.0
        assert result.summary.total_latency_reduction == 0.0
        assert result.summary.avg_quality_improvement == 0.0
        assert result.baseline is None
        assert result.optimizations == []
        assert result.health_score == 100.0
        assert result.status == "ok"


class TestBaselineMode:
    """Tests for baseline mode (no optimization_date)."""
    
    def test_baseline_mode_without_date(self):
        """Returns baseline mode when no optimization_date provided."""
        calls = [
            make_call_dict(total_cost=0.10, latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert result.mode == "baseline"
        assert result.baseline is not None
        assert result.optimizations == []
    
    def test_baseline_calculates_metrics(self):
        """Baseline mode calculates current metrics."""
        calls = [
            make_call_dict(total_cost=0.10, latency_ms=1000, quality_evaluation={'judge_score': 8.0}),
            make_call_dict(total_cost=0.20, latency_ms=2000, quality_evaluation={'judge_score': 9.0}),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert result.baseline.total_calls == 2
        assert result.baseline.total_cost == pytest.approx(0.30)
        assert result.baseline.avg_latency_ms == 1500.0
        assert result.baseline.avg_quality_score == 8.5
    
    def test_baseline_calculates_cache_hit_rate(self):
        """Baseline includes cache hit rate."""
        calls = [
            make_call_dict(cache_metadata={'cache_hit': True}),
            make_call_dict(cache_metadata={'cache_hit': True}),
            make_call_dict(cache_metadata={'cache_hit': False}),
            make_call_dict(cache_metadata={'cache_hit': False}),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert result.baseline.cache_hit_rate == 0.5
        assert "50" in result.baseline.cache_hit_rate_formatted
    
    def test_baseline_calculates_error_rate(self):
        """Baseline includes error rate."""
        calls = [
            make_call_dict(success=True),
            make_call_dict(success=True),
            make_call_dict(success=True),
            make_call_dict(success=False),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert result.baseline.error_rate == 0.25
        assert "25" in result.baseline.error_rate_formatted


class TestBaselineDetailTable:
    """Tests for baseline detail table."""
    
    def test_baseline_detail_table_groups_by_operation(self):
        """Baseline detail table groups by operation."""
        calls = [
            make_call_dict(operation="op_a", agent_name="AgentA", total_cost=0.10, latency_ms=1000),
            make_call_dict(operation="op_a", agent_name="AgentA", total_cost=0.10, latency_ms=1000),
            make_call_dict(operation="op_b", agent_name="AgentB", total_cost=0.20, latency_ms=2000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert len(result.detail_table) == 2
        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names
    
    def test_baseline_detail_table_sorted_by_cost(self):
        """Baseline detail table sorted by total cost."""
        calls = [
            make_call_dict(operation="cheap", agent_name="Agent", total_cost=0.10),
            make_call_dict(operation="expensive", agent_name="Agent", total_cost=0.50),
            make_call_dict(operation="medium", agent_name="Agent", total_cost=0.30),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        costs = [row['total_cost'] for row in result.detail_table]
        assert costs == sorted(costs, reverse=True)
        assert result.detail_table[0]['operation'] == "Agent.expensive"


class TestImpactMode:
    """Tests for impact mode (with optimization_date)."""
    
    def test_impact_mode_with_date(self):
        """Returns impact mode when optimization_date provided."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), total_cost=0.20, latency_ms=2000),
            make_call_dict(timestamp=now - timedelta(days=1), total_cost=0.10, latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.mode == "impact"
        assert result.baseline is None
        assert len(result.optimizations) == 1
    
    def test_splits_calls_before_after(self):
        """Impact mode splits calls into before/after optimization date."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            # Before optimization
            make_call_dict(timestamp=now - timedelta(days=5), total_cost=0.20, latency_ms=2000),
            make_call_dict(timestamp=now - timedelta(days=4), total_cost=0.20, latency_ms=2000),
            # After optimization
            make_call_dict(timestamp=now - timedelta(days=2), total_cost=0.10, latency_ms=1000),
            make_call_dict(timestamp=now - timedelta(days=1), total_cost=0.10, latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.mode == "impact"
        optimization = result.optimizations[0]
        assert optimization.before_total_cost == 0.40
        assert optimization.after_total_cost == 0.20
    
    def test_calculates_cost_savings(self):
        """Impact mode calculates cost saved."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), total_cost=0.30),
            make_call_dict(timestamp=now - timedelta(days=1), total_cost=0.20),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        optimization = result.optimizations[0]
        assert optimization.cost_saved == pytest.approx(0.10)
        assert result.summary.total_cost_saved == pytest.approx(0.10)
    
    def test_calculates_latency_reduction(self):
        """Impact mode calculates latency reduction percentage."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), latency_ms=2000),
            make_call_dict(timestamp=now - timedelta(days=1), latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        optimization = result.optimizations[0]
        assert optimization.latency_reduction_pct == 0.5  # 50% reduction
        assert result.summary.total_latency_reduction == 0.5
    
    def test_calculates_quality_improvement(self):
        """Impact mode calculates quality improvement."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(
                timestamp=now - timedelta(days=5),
                quality_evaluation={'judge_score': 6.0}
            ),
            make_call_dict(
                timestamp=now - timedelta(days=1),
                quality_evaluation={'judge_score': 8.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        optimization = result.optimizations[0]
        assert optimization.quality_improvement == 2.0
        assert result.summary.avg_quality_improvement == 2.0


class TestImpactInsufficientData:
    """Tests for impact mode with insufficient data."""
    
    def test_falls_back_to_baseline_no_before_data(self):
        """Falls back to baseline when no before data."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=10)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=1), total_cost=0.10),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        # Should fall back to baseline
        assert result.mode == "baseline"
    
    def test_falls_back_to_baseline_no_after_data(self):
        """Falls back to baseline when no after data."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=1)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), total_cost=0.10),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        # Should fall back to baseline
        assert result.mode == "baseline"


class TestImpactHealthScore:
    """Tests for impact mode health score."""
    
    def test_perfect_health_all_improvements(self):
        """100% health with cost, latency, and quality improvements."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            # Before: expensive, slow, low quality
            make_call_dict(
                timestamp=now - timedelta(days=5),
                total_cost=0.30,
                latency_ms=3000,
                quality_evaluation={'judge_score': 6.0}
            ),
            # After: cheap, fast, high quality
            make_call_dict(
                timestamp=now - timedelta(days=1),
                total_cost=0.10,
                latency_ms=1000,
                quality_evaluation={'judge_score': 9.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.health_score == 100.0
        assert result.status == "ok"
    
    def test_good_health_cost_and_latency_improvements(self):
        """Good health with cost and latency improvements."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(
                timestamp=now - timedelta(days=5),
                total_cost=0.30,
                latency_ms=3000
            ),
            make_call_dict(
                timestamp=now - timedelta(days=1),
                total_cost=0.20,
                latency_ms=2000
            ),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.health_score >= 85.0
        assert result.status == "ok"
    
    def test_warning_status_no_improvements(self):
        """Warning status when no improvements."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(
                timestamp=now - timedelta(days=5),
                total_cost=0.20,
                latency_ms=2000
            ),
            make_call_dict(
                timestamp=now - timedelta(days=1),
                total_cost=0.20,
                latency_ms=2000
            ),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.health_score <= 60.0
        assert result.status == "warning"


class TestOptimizationObject:
    """Tests for optimization impact object."""
    
    def test_optimization_has_required_fields(self):
        """Optimization object has all required fields."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), total_cost=0.30, latency_ms=2000),
            make_call_dict(timestamp=now - timedelta(days=1), total_cost=0.10, latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        optimization = result.optimizations[0]
        assert optimization.id is not None
        assert optimization.name is not None
        assert optimization.target_operation is not None
        assert optimization.implemented_date == optimization_date
        assert hasattr(optimization, 'before_avg_latency_ms')
        assert hasattr(optimization, 'after_avg_latency_ms')
        assert hasattr(optimization, 'before_total_cost')
        assert hasattr(optimization, 'after_total_cost')
        assert hasattr(optimization, 'cost_saved')
        assert hasattr(optimization, 'latency_reduction_pct')


class TestSummaryMetrics:
    """Tests for summary metrics calculation."""
    
    def test_summary_total_optimizations(self):
        """Summary shows correct optimization count."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), total_cost=0.30),
            make_call_dict(timestamp=now - timedelta(days=1), total_cost=0.10),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.summary.total_optimizations == 1
    
    def test_summary_aggregates_savings(self):
        """Summary aggregates all savings."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), total_cost=0.50, latency_ms=5000),
            make_call_dict(timestamp=now - timedelta(days=1), total_cost=0.20, latency_ms=2000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.summary.total_cost_saved == 0.30
        assert result.summary.total_latency_reduction == 0.6  # 60% reduction


class TestBaselineChartData:
    """Tests for baseline chart data."""
    
    def test_baseline_chart_data_limited_to_10(self):
        """Baseline chart data limited to top 10 operations."""
        calls = [
            make_call_dict(operation=f"op_{i}", agent_name="Agent", total_cost=0.10)
            for i in range(15)
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert len(result.chart_data) <= 10
    
    def test_baseline_chart_data_structure(self):
        """Baseline chart data has required fields."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", total_cost=0.10, latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'latency' in result.chart_data[0]
        assert 'cost' in result.chart_data[0]


class TestFormatting:
    """Tests for metric formatting."""
    
    def test_baseline_formats_cost(self):
        """Baseline cost formatted correctly."""
        calls = [
            make_call_dict(total_cost=1.25),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert "$" in result.baseline.total_cost_formatted
        assert "1.25" in result.baseline.total_cost_formatted
    
    def test_baseline_formats_latency(self):
        """Baseline latency formatted correctly."""
        calls = [
            make_call_dict(latency_ms=1500),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert "s" in result.baseline.avg_latency or "ms" in result.baseline.avg_latency
    
    def test_baseline_formats_percentages(self):
        """Baseline percentages formatted correctly."""
        calls = [
            make_call_dict(cache_metadata={'cache_hit': True}),
            make_call_dict(cache_metadata={'cache_hit': False}),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=None)
        
        assert "%" in result.baseline.cache_hit_rate_formatted
        assert "%" in result.baseline.error_rate_formatted


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_handles_zero_latency_in_before(self):
        """Handles zero latency in before period."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), latency_ms=0),
            make_call_dict(timestamp=now - timedelta(days=1), latency_ms=1000),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        # Should not crash, reduction calculation handles division by zero
        assert result.mode == "impact"
    
    def test_handles_missing_quality_scores(self):
        """Handles missing quality scores gracefully."""
        now = datetime.utcnow()
        optimization_date = now - timedelta(days=3)
        
        calls = [
            make_call_dict(timestamp=now - timedelta(days=5), quality_evaluation=None),
            make_call_dict(timestamp=now - timedelta(days=1), quality_evaluation=None),
        ]
        
        result = get_summary(calls, project=None, days=7, optimization_date=optimization_date)
        
        assert result.mode == "impact"
        optimization = result.optimizations[0]
        assert optimization.before_avg_quality == 0.0
        assert optimization.after_avg_quality == 0.0