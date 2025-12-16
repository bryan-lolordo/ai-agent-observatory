# test_prompt_service.py

"""
Unit Tests - Prompt Service
Location: tests/unit/services/test_prompt_service.py

Tests for Story 6: Prompt composition business logic.
"""

import pytest
from api.services.prompt_service import get_summary, SYSTEM_PROMPT_WASTE_PCT, SYSTEM_PROMPT_HIGH_TOKENS
from api.models import SystemPromptStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestPromptSummaryEmpty:
    """Tests for empty data handling."""
    
    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response with zero counts."""
        result = get_summary(empty_calls, project=None, days=7)
        
        assert isinstance(result, SystemPromptStoryResponse)
        assert result.summary.total_calls == 0
        assert result.summary.issue_count == 0
        assert result.summary.avg_system_tokens == 0
        assert result.summary.avg_user_tokens == 0
        assert result.summary.avg_context_tokens == 0
        assert result.summary.total_system_tokens == 0
        assert result.summary.largest_system_prompt == 0
        assert result.summary.total_redundant_tokens == 0
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


class TestPromptBreakdown:
    """Tests for prompt component breakdown."""
    
    def test_uses_prompt_breakdown_when_available(self):
        """Uses prompt_breakdown fields when available."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={
                    'system_prompt_tokens': 400,
                    'user_message_tokens': 300,
                    'chat_history_tokens': 300,
                }
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['avg_system_tokens'] == 400
        assert row['avg_user_tokens'] == 300
        assert row['avg_context_tokens'] == 300
    
    def test_estimates_when_breakdown_missing(self):
        """Estimates system prompt when breakdown not available."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown=None
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        # Should estimate ~40% as system prompt
        assert row['avg_system_tokens'] > 0


class TestDetailTable:
    """Tests for detail table generation."""
    
    def test_groups_by_operation(self):
        """Detail table groups calls by agent.operation."""
        calls = [
            make_call_dict(
                operation="op_a",
                agent_name="AgentA",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
            make_call_dict(
                operation="op_a",
                agent_name="AgentA",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
            make_call_dict(
                operation="op_b",
                agent_name="AgentB",
                prompt_tokens=500,
                prompt_breakdown={'system_prompt_tokens': 200}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.detail_table) == 2
        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names
    
    def test_calculates_averages_per_operation(self):
        """Each operation shows average token counts."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={
                    'system_prompt_tokens': 400,
                    'user_message_tokens': 300,
                    'chat_history_tokens': 300,
                }
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1200,
                prompt_breakdown={
                    'system_prompt_tokens': 600,
                    'user_message_tokens': 300,
                    'chat_history_tokens': 300,
                }
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['avg_system_tokens'] == 500
        assert row['avg_user_tokens'] == 300
        assert row['avg_context_tokens'] == 300
    
    def test_calculates_system_prompt_percentage(self):
        """System prompt percentage calculated correctly."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['system_pct'] == 0.4
        assert "40" in row['system_pct_formatted']
    
    def test_sorted_by_redundant_tokens(self):
        """Detail table sorted by redundant tokens (most waste first)."""
        calls = [
            # Low waste: small system prompt
            make_call_dict(
                operation="low",
                agent_name="Agent",
                prompt_tokens=500,
                prompt_breakdown={'system_prompt_tokens': 100}
            ),
            # High waste: large system prompt, many calls
            *[make_call_dict(
                operation="high",
                agent_name="Agent",
                prompt_tokens=1500,
                prompt_breakdown={'system_prompt_tokens': 800}
            ) for _ in range(5)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        redundant = [row['redundant_tokens'] for row in result.detail_table]
        assert redundant == sorted(redundant, reverse=True)
        assert result.detail_table[0]['operation'] == "Agent.high"


class TestRedundantTokenCalculation:
    """Tests for redundant token calculation."""
    
    def test_calculates_redundant_tokens(self):
        """Redundant tokens = (N-1) * avg_system_tokens."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        # 3 calls with 400 token system prompt = 2 * 400 = 800 redundant
        row = result.detail_table[0]
        assert row['redundant_tokens'] == 800
        assert result.summary.total_redundant_tokens == 800
    
    def test_single_call_has_no_redundancy(self):
        """Single call has zero redundant tokens."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['redundant_tokens'] == 0


class TestWasteDetection:
    """Tests for prompt waste detection."""
    
    def test_high_system_prompt_percentage_flagged(self):
        """System prompt >30% of total flagged as waste."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}  # 40%
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['has_waste'] is True
        assert result.summary.issue_count == 1
    
    def test_large_system_prompt_flagged(self):
        """System prompt >1000 tokens flagged as waste."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=5000,
                prompt_breakdown={'system_prompt_tokens': 1200}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['has_waste'] is True
        assert result.summary.issue_count == 1
    
    def test_efficient_prompt_not_flagged(self):
        """Efficient prompts not flagged."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 200}  # 20%
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['has_waste'] is False
        assert result.summary.issue_count == 0


class TestStatusIndicators:
    """Tests for status indicator assignment."""
    
    def test_red_status_for_waste(self):
        """Red status for operations with waste."""
        calls = [
            make_call_dict(
                operation="wasteful",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 500}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['status'] == "🔴"
    
    def test_green_status_for_efficient(self):
        """Green status for efficient operations."""
        calls = [
            make_call_dict(
                operation="efficient",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 200}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['status'] == "🟢"


class TestGlobalMetrics:
    """Tests for global summary metrics."""
    
    def test_calculates_total_system_tokens(self):
        """Total system tokens summed across all calls."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.total_system_tokens == 800
    
    def test_identifies_largest_system_prompt(self):
        """Largest system prompt identified correctly."""
        calls = [
            make_call_dict(
                operation="small",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 300}
            ),
            make_call_dict(
                operation="large",
                agent_name="Agent",
                prompt_tokens=2000,
                prompt_breakdown={'system_prompt_tokens': 1200}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.largest_system_prompt == 1200
    
    def test_calculates_average_tokens(self):
        """Average tokens calculated across all calls."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={
                    'system_prompt_tokens': 400,
                    'user_message_tokens': 300,
                    'chat_history_tokens': 300,
                }
            ),
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={
                    'system_prompt_tokens': 600,
                    'user_message_tokens': 200,
                    'chat_history_tokens': 200,
                }
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.avg_system_tokens == 500
        assert result.summary.avg_user_tokens == 250
        assert result.summary.avg_context_tokens == 250


class TestTopOffender:
    """Tests for top offender identification."""
    
    def test_identifies_most_redundant_tokens(self):
        """Top offender is operation with most redundant tokens."""
        calls = [
            *[make_call_dict(
                operation="high_waste",
                agent_name="Agent",
                prompt_tokens=1500,
                prompt_breakdown={'system_prompt_tokens': 800}
            ) for _ in range(5)],
            *[make_call_dict(
                operation="low_waste",
                agent_name="Agent",
                prompt_tokens=500,
                prompt_breakdown={'system_prompt_tokens': 100}
            ) for _ in range(3)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.operation == "high_waste"
    
    def test_top_offender_includes_recommendation(self):
        """Top offender includes optimization recommendation."""
        calls = [
            *[make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=2000,
                prompt_breakdown={'system_prompt_tokens': 1600}
            ) for _ in range(5)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.diagnosis is not None
        assert len(result.top_offender.diagnosis) > 0
    
    def test_no_top_offender_without_waste(self):
        """No top offender when no waste detected."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 200}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is None


class TestRecommendations:
    """Tests for optimization recommendations."""
    
    def test_compress_recommendation_for_large_prompts(self):
        """Recommends compression for very large system prompts."""
        calls = [
            *[make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=2000,
                prompt_breakdown={'system_prompt_tokens': 1600}
            ) for _ in range(3)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert "compress" in result.top_offender.diagnosis.lower()
    
    def test_caching_recommendation_for_repeated_prompts(self):
        """Recommends caching for repeated system prompts."""
        calls = [
            *[make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 600}
            ) for _ in range(15)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        diagnosis = result.top_offender.diagnosis.lower()
        assert "cach" in diagnosis or "compress" in diagnosis


class TestHealthScore:
    """Tests for health score calculation."""
    
    def test_perfect_health_efficient_prompts(self):
        """100% health with efficient prompts."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 200}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score == 100.0
        assert result.status == "ok"
    
    def test_warning_status_moderate_waste(self):
        """Warning status with moderate waste."""
        calls = [
            make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.status == "warning"
        assert 70 <= result.health_score <= 90
    
    def test_error_status_severe_waste(self):
        """Error status with severe waste."""
        calls = [
            *[make_call_dict(
                operation="op",
                agent_name="Agent",
                prompt_tokens=2000,
                prompt_breakdown={'system_prompt_tokens': 1200}
            ) for _ in range(50)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.total_redundant_tokens > 50000
        assert result.status == "error"
        assert result.health_score <= 60


class TestChartData:
    """Tests for chart data generation."""
    
    def test_chart_data_limited_to_10(self):
        """Chart data limited to top 10 operations."""
        calls = [
            make_call_dict(
                operation=f"op_{i}",
                agent_name="Agent",
                prompt_tokens=1000,
                prompt_breakdown={'system_prompt_tokens': 400}
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
                prompt_tokens=1000,
                prompt_breakdown={
                    'system_prompt_tokens': 400,
                    'user_message_tokens': 300,
                    'chat_history_tokens': 300,
                }
            ),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'system' in result.chart_data[0]
        assert 'user' in result.chart_data[0]
        assert 'context' in result.chart_data[0]