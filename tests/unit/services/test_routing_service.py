# test_routing_service.py

"""
Unit Tests - Routing Service
Location: tests/unit/services/test_routing_service.py

Tests for Story 3: Model routing opportunity business logic.
"""

import pytest
from api.services.routing_service import get_summary, HIGH_COMPLEXITY_THRESHOLD, CHEAP_MODELS
from api.models import RoutingStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestRoutingSummaryEmpty:
    """Tests for empty data handling."""
    
    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response with zero counts."""
        result = get_summary(empty_calls, project=None, days=7)
        
        assert isinstance(result, RoutingStoryResponse)
        assert result.summary.total_calls == 0
        assert result.summary.issue_count == 0
        assert result.summary.upgrade_candidates == 0
        assert result.summary.downgrade_candidates == 0
        assert result.summary.high_complexity_calls == 0
        assert result.summary.misrouted_calls == 0
        assert result.summary.potential_savings == 0.0
        assert result.health_score == 100.0
        assert result.status == "ok"
        assert result.top_offender is None
        assert result.detail_table == []
    
    def test_filters_non_llm_calls(self):
        """Calls without prompt tokens filtered out."""
        calls = [
            make_call_dict(prompt_tokens=0),
            make_call_dict(prompt_tokens=None),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.total_calls == 0


class TestComplexityScoring:
    """Tests for complexity score analysis."""
    
    def test_counts_high_complexity_calls(self):
        """High complexity calls (>0.7) counted correctly."""
        calls = [
            make_call_dict(
                operation="complex",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.8}
            ),
            make_call_dict(
                operation="complex",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.9}
            ),
            make_call_dict(
                operation="simple",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.3}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.high_complexity_calls == 2
    
    def test_calculates_average_complexity(self):
        """Average complexity calculated per operation."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.6}
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.8}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['avg_complexity'] == 0.7
    
    def test_handles_missing_complexity(self):
        """Calls without complexity score handled gracefully."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision=None
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['avg_complexity'] is None


class TestModelDetection:
    """Tests for model detection and classification."""
    
    def test_identifies_primary_model(self):
        """Primary model identified correctly."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=100, model_name="gpt-4o-mini"),
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=100, model_name="gpt-4o-mini"),
            make_call_dict(operation="op", agent_name="Agent", prompt_tokens=100, model_name="gpt-4o"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['primary_model'] == "gpt-4o-mini"
    
    def test_cheap_model_detection(self):
        """Cheap models identified correctly."""
        for cheap_model in CHEAP_MODELS:
            calls = [
                make_call_dict(
                    operation="op",
                    agent_name="Agent",
                    prompt_tokens=100,
                    model_name=cheap_model
                ),
            ]
            
            result = get_summary(calls, project=None, days=7)
            # Should be recognized as cheap model
            assert result.summary.total_calls == 1


class TestUpgradeCandidates:
    """Tests for upgrade candidate detection."""
    
    def test_identifies_upgrade_candidates(self):
        """High complexity on cheap model = upgrade candidate."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.8}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.upgrade_candidates == 1
        assert result.summary.misrouted_calls == 1
        row = result.detail_table[0]
        assert row['is_upgrade_candidate'] is True
    
    def test_multiple_upgrade_candidates(self, routing_opportunity_calls):
        """Multiple upgrade candidates identified."""
        result = get_summary(routing_opportunity_calls, project=None, days=7)
        
        # critique_match operations have high complexity on cheap model
        assert result.summary.upgrade_candidates >= 1
    
    def test_no_upgrade_for_expensive_model(self):
        """High complexity on expensive model not flagged."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o",
                routing_decision={'complexity_score': 0.8}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.upgrade_candidates == 0


class TestDowngradeCandidates:
    """Tests for downgrade candidate detection."""
    
    def test_identifies_downgrade_candidates(self):
        """Low complexity with high quality = downgrade candidate."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o",
                routing_decision={'complexity_score': 0.3},
                quality_evaluation={'judge_score': 9.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.downgrade_candidates == 1
        row = result.detail_table[0]
        assert row['is_downgrade_candidate'] is True
    
    def test_no_downgrade_without_high_quality(self):
        """Low complexity but low quality not flagged for downgrade."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o",
                routing_decision={'complexity_score': 0.3},
                quality_evaluation={'judge_score': 6.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.downgrade_candidates == 0
    
    def test_multiple_downgrade_candidates(self, routing_opportunity_calls):
        """Multiple downgrade candidates identified."""
        result = get_summary(routing_opportunity_calls, project=None, days=7)
        
        # generate_sql operations have low complexity and high quality
        assert result.summary.downgrade_candidates >= 1


class TestDetailTable:
    """Tests for detail table generation."""
    
    def test_groups_by_operation(self):
        """Detail table groups calls by agent.operation."""
        calls = [
            make_call_dict(
                operation="op_a",
                agent_name="AgentA",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.5}
            ),
            make_call_dict(
                operation="op_a",
                agent_name="AgentA",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.5}
            ),
            make_call_dict(
                operation="op_b",
                agent_name="AgentB",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.6}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.detail_table) == 2
        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names
    
    def test_includes_quality_metrics(self):
        """Detail table includes average quality score."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                quality_evaluation={'judge_score': 8.0}
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                quality_evaluation={'judge_score': 9.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['avg_quality'] == 8.5
    
    def test_includes_cost_metrics(self):
        """Detail table includes total cost."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                total_cost=0.05
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                total_cost=0.05
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['total_cost'] == 0.10
    
    def test_sorted_by_complexity_descending(self):
        """Detail table sorted by complexity (highest first)."""
        calls = [
            make_call_dict(
                operation="low",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.3}
            ),
            make_call_dict(
                operation="high",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.9}
            ),
            make_call_dict(
                operation="medium",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.6}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        complexities = [row['avg_complexity'] or 0 for row in result.detail_table]
        assert complexities == sorted(complexities, reverse=True)
        assert result.detail_table[0]['operation'] == "Agent.high"


class TestStatusIndicators:
    """Tests for status indicator assignment."""
    
    def test_red_status_for_upgrade_candidates(self):
        """Red status for upgrade candidates."""
        calls = [
            make_call_dict(
                operation="upgrade",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.8}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['status'] == "🔴"
    
    def test_yellow_status_for_downgrade_candidates(self):
        """Yellow status for downgrade candidates."""
        calls = [
            make_call_dict(
                operation="downgrade",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o",
                routing_decision={'complexity_score': 0.3},
                quality_evaluation={'judge_score': 9.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['status'] == "🟡"
    
    def test_green_status_for_well_routed(self):
        """Green status for well-routed operations."""
        calls = [
            make_call_dict(
                operation="good",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.4}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['status'] == "🟢"


class TestTopOffender:
    """Tests for top offender identification."""
    
    def test_identifies_highest_complexity_on_cheap_model(self):
        """Top offender is highest complexity on cheap model."""
        calls = [
            make_call_dict(
                operation="very_complex",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.95}
            ),
            make_call_dict(
                operation="somewhat_complex",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.75}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.operation == "very_complex"
        assert result.top_offender.value == 0.95
    
    def test_top_offender_includes_recommendation(self):
        """Top offender includes upgrade recommendation."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.85}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert "upgrade" in result.top_offender.diagnosis.lower()
    
    def test_no_top_offender_without_misrouting(self):
        """No top offender when routing is optimal."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.4}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is None


class TestPotentialSavings:
    """Tests for potential savings calculation."""
    
    def test_calculates_potential_savings(self):
        """Potential savings estimated for downgrade opportunities."""
        calls = [
            make_call_dict(
                operation="downgrade1",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o",
                routing_decision={'complexity_score': 0.3},
                quality_evaluation={'judge_score': 9.0}
            ),
            make_call_dict(
                operation="downgrade2",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o",
                routing_decision={'complexity_score': 0.2},
                quality_evaluation={'judge_score': 8.5}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        # 2 downgrade candidates * ~$0.02 = ~$0.04
        assert result.summary.potential_savings > 0


class TestHealthScore:
    """Tests for health score calculation."""
    
    def test_perfect_health_optimal_routing(self):
        """100% health with optimal routing."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.4}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score == 100.0
        assert result.status == "ok"
    
    def test_health_degrades_with_upgrade_candidates(self):
        """Health score decreases with upgrade candidates."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.85}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score < 100.0
        assert result.status == "warning"
    
    def test_downgrade_candidates_better_than_upgrades(self):
        """Downgrade candidates less severe than upgrade candidates."""
        upgrade_calls = [
            make_call_dict(
                operation="upgrade",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.85}
            ),
        ]
        
        downgrade_calls = [
            make_call_dict(
                operation="downgrade",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o",
                routing_decision={'complexity_score': 0.3},
                quality_evaluation={'judge_score': 9.0}
            ),
        ]
        
        upgrade_result = get_summary(upgrade_calls, project=None, days=7)
        downgrade_result = get_summary(downgrade_calls, project=None, days=7)
        
        assert upgrade_result.health_score < downgrade_result.health_score


class TestChartData:
    """Tests for chart data generation."""
    
    def test_chart_data_limited_to_10(self):
        """Chart data limited to top 10 operations."""
        calls = [
            make_call_dict(
                operation=f"op_{i}",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.5 + (i * 0.01)}
            )
            for i in range(15)
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) <= 10
    
    def test_chart_data_structure(self):
        """Chart data has required fields."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=100,
                routing_decision={'complexity_score': 0.5},
                quality_evaluation={'judge_score': 8.0}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'complexity' in result.chart_data[0]
        assert 'quality' in result.chart_data[0]


class TestMisroutedCallsCounting:
    """Tests for misrouted calls counting."""
    
    def test_counts_all_calls_in_upgrade_operations(self):
        """Misrouted count includes all calls in upgrade candidate operations."""
        calls = [
            *[make_call_dict(
                operation="misrouted",
                agent_name="Agent",
                prompt_tokens=100,
                model_name="gpt-4o-mini",
                routing_decision={'complexity_score': 0.85}
            ) for _ in range(5)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.misrouted_calls == 5