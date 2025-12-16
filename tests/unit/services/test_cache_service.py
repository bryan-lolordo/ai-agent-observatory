# test_cache_service.py

"""
Unit Tests - Cache Service
Location: tests/unit/services/test_cache_service.py

Tests for Story 2: Cache opportunity analysis business logic.
"""

import pytest
from api.services.cache_service import get_summary, DUPLICATE_THRESHOLD, CACHE_OPPORTUNITY_PCT
from api.models import CacheStoryResponse
from tests.fixtures.sample_calls import make_call_dict


class TestCacheSummaryEmpty:
    """Tests for empty data handling."""
    
    def test_empty_calls_returns_valid_response(self, empty_calls):
        """Empty call list returns valid response with zero counts."""
        result = get_summary(empty_calls, project=None, days=7)
        
        assert isinstance(result, CacheStoryResponse)
        assert result.summary.total_calls == 0
        assert result.summary.issue_count == 0
        assert result.summary.cache_hits == 0
        assert result.summary.cache_misses == 0
        assert result.summary.hit_rate == 0.0
        assert result.summary.duplicate_prompts == 0
        assert result.summary.potential_savings == 0.0
        assert result.health_score == 100.0
        assert result.status == "ok"
        assert result.top_offender is None
        assert result.detail_table == []


class TestCacheHitRate:
    """Tests for cache hit rate calculation."""
    
    def test_calculates_cache_hit_rate(self):
        """Cache hit rate calculated correctly."""
        calls = [
            make_call_dict(cache_metadata={'cache_hit': True, 'cache_key': 'key1'}),
            make_call_dict(cache_metadata={'cache_hit': True, 'cache_key': 'key2'}),
            make_call_dict(cache_metadata={'cache_hit': False, 'cache_key': 'key3'}),
            make_call_dict(cache_metadata={'cache_hit': False, 'cache_key': 'key4'}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.cache_hits == 2
        assert result.summary.cache_misses == 2
        assert result.summary.hit_rate == 0.5
        assert "50" in result.summary.hit_rate_formatted
    
    def test_no_cache_metadata(self):
        """Calls without cache metadata counted correctly."""
        calls = [
            make_call_dict(),
            make_call_dict(),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.cache_hits == 0
        assert result.summary.cache_misses == 0


class TestDuplicateDetection:
    """Tests for duplicate prompt detection."""
    
    def test_identifies_duplicate_prompts(self, duplicate_prompt_calls):
        """Identifies duplicate prompts correctly."""
        result = get_summary(duplicate_prompt_calls, project=None, days=7)
        
        # 3 duplicates of "Generate SQL for: find jobs in SF"
        assert result.summary.duplicate_prompts >= 3
    
    def test_case_insensitive_matching(self):
        """Duplicate detection is case insensitive."""
        calls = [
            make_call_dict(prompt="Find jobs in SF", operation="search"),
            make_call_dict(prompt="find jobs in sf", operation="search"),
            make_call_dict(prompt="FIND JOBS IN SF", operation="search"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.duplicate_prompts >= 3
    
    def test_whitespace_normalization(self):
        """Duplicate detection normalizes whitespace."""
        calls = [
            make_call_dict(prompt="Find jobs", operation="search"),
            make_call_dict(prompt=" Find jobs ", operation="search"),
            make_call_dict(prompt="Find  jobs", operation="search"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.duplicate_prompts >= 3


class TestDetailTable:
    """Tests for detail table generation."""
    
    def test_groups_by_operation(self):
        """Detail table groups calls by agent.operation."""
        calls = [
            make_call_dict(operation="op_a", agent_name="AgentA", prompt="prompt1"),
            make_call_dict(operation="op_a", agent_name="AgentA", prompt="prompt1"),
            make_call_dict(operation="op_b", agent_name="AgentB", prompt="prompt2"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.detail_table) == 2
        op_names = [row['operation'] for row in result.detail_table]
        assert "AgentA.op_a" in op_names
        assert "AgentB.op_b" in op_names
    
    def test_counts_unique_prompts(self):
        """Detail table counts unique prompts per operation."""
        calls = [
            make_call_dict(operation="search", agent_name="Agent", prompt="query1"),
            make_call_dict(operation="search", agent_name="Agent", prompt="query1"),
            make_call_dict(operation="search", agent_name="Agent", prompt="query2"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['unique_prompts'] == 2
        assert row['total_calls'] == 3
    
    def test_calculates_redundancy_percentage(self):
        """Detail table calculates redundancy percentage."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt="same"),
            make_call_dict(operation="op", agent_name="Agent", prompt="same"),
            make_call_dict(operation="op", agent_name="Agent", prompt="same"),
            make_call_dict(operation="op", agent_name="Agent", prompt="different"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        row = result.detail_table[0]
        assert row['redundancy_pct'] == 0.75  # 3 out of 4 are duplicates
    
    def test_status_indicators(self):
        """Status indicators reflect redundancy levels."""
        calls = [
            # High redundancy (>50%)
            *[make_call_dict(operation="high", agent_name="Agent", prompt="same") for _ in range(6)],
            make_call_dict(operation="high", agent_name="Agent", prompt="different"),
            # Medium redundancy (20-50%)
            *[make_call_dict(operation="med", agent_name="Agent", prompt="same") for _ in range(3)],
            *[make_call_dict(operation="med", agent_name="Agent", prompt=f"unique{i}") for i in range(7)],
            # Low redundancy (<20%)
            *[make_call_dict(operation="low", agent_name="Agent", prompt=f"unique{i}") for i in range(10)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        statuses = {row['operation']: row['status'] for row in result.detail_table}
        assert statuses["Agent.high"] == "🔴"
        assert statuses["Agent.med"] == "🟡"
        assert statuses["Agent.low"] == "🟢"
    
    def test_sorted_by_wasted_cost(self):
        """Detail table sorted by wasted cost (highest first)."""
        calls = [
            *[make_call_dict(operation="cheap", agent_name="Agent", prompt="dup", total_cost=0.001) for _ in range(5)],
            *[make_call_dict(operation="expensive", agent_name="Agent", prompt="dup", total_cost=0.10) for _ in range(5)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.detail_table[0]['operation'] == "Agent.expensive"
        assert result.detail_table[1]['operation'] == "Agent.cheap"


class TestWastedCostCalculation:
    """Tests for wasted cost calculation."""
    
    def test_calculates_wasted_cost(self):
        """Wasted cost calculated for duplicate prompts."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt="dup", total_cost=0.05),
            make_call_dict(operation="op", agent_name="Agent", prompt="dup", total_cost=0.05),
            make_call_dict(operation="op", agent_name="Agent", prompt="dup", total_cost=0.05),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        # 3 duplicates @ $0.05 each = $0.15 total
        # First is necessary, 2 are wasted = $0.10 wasted
        assert result.summary.potential_savings > 0
        row = result.detail_table[0]
        assert row['wasted_cost'] > 0


class TestTopOffender:
    """Tests for top offender identification."""
    
    def test_identifies_highest_wasted_cost(self):
        """Top offender is operation with most wasted cost."""
        calls = [
            *[make_call_dict(operation="expensive", agent_name="Agent", prompt="dup", total_cost=0.10) for _ in range(5)],
            *[make_call_dict(operation="cheap", agent_name="Agent", prompt="dup", total_cost=0.01) for _ in range(10)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.operation == "expensive"
    
    def test_top_offender_includes_diagnosis(self):
        """Top offender includes diagnostic message."""
        calls = [
            *[make_call_dict(operation="op", agent_name="Agent", prompt="dup", total_cost=0.05) for _ in range(5)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is not None
        assert result.top_offender.diagnosis is not None
        assert "duplicate" in result.top_offender.diagnosis.lower()
    
    def test_no_top_offender_without_opportunities(self):
        """No top offender when no cache opportunities."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt=f"unique{i}") 
            for i in range(10)
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.top_offender is None


class TestHealthScore:
    """Tests for health score calculation."""
    
    def test_perfect_health_with_good_hit_rate(self):
        """100% health with good cache hit rate and no issues."""
        calls = [
            make_call_dict(cache_metadata={'cache_hit': True}),
            make_call_dict(cache_metadata={'cache_hit': True}),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score == 100.0
        assert result.status == "ok"
    
    def test_health_degrades_with_opportunities(self):
        """Health score decreases with cache opportunities."""
        calls = [
            *[make_call_dict(operation="op", agent_name="Agent", prompt="dup") for _ in range(10)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.health_score < 100.0
    
    def test_status_based_on_hit_rate(self):
        """Status reflects cache hit rate."""
        # Low hit rate
        low_hit_calls = [
            make_call_dict(cache_metadata={'cache_hit': True}),
            *[make_call_dict(cache_metadata={'cache_hit': False}) for _ in range(9)],
        ]
        
        result = get_summary(low_hit_calls, project=None, days=7)
        assert result.status in ["warning", "error"]


class TestChartData:
    """Tests for chart data generation."""
    
    def test_chart_data_limited_to_10(self):
        """Chart data limited to top 10 operations."""
        calls = [
            make_call_dict(operation=f"op_{i}", agent_name="Agent", prompt="dup")
            for i in range(15)
            for _ in range(3)  # 3 duplicates each
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) <= 10
    
    def test_chart_data_structure(self):
        """Chart data has required fields."""
        calls = [
            make_call_dict(operation="op", agent_name="Agent", prompt="dup"),
            make_call_dict(operation="op", agent_name="Agent", prompt="dup"),
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert len(result.chart_data) == 1
        assert 'name' in result.chart_data[0]
        assert 'duplicates' in result.chart_data[0]
        assert 'wasted_cost' in result.chart_data[0]


class TestCacheOpportunityThreshold:
    """Tests for cache opportunity threshold."""
    
    def test_threshold_detection(self):
        """Operations above threshold marked as opportunities."""
        # 25% duplicates (above 20% threshold)
        calls = [
            *[make_call_dict(operation="op", agent_name="Agent", prompt="dup") for _ in range(5)],
            *[make_call_dict(operation="op", agent_name="Agent", prompt=f"unique{i}") for i in range(15)],
        ]
        
        result = get_summary(calls, project=None, days=7)
        
        assert result.summary.issue_count >= 1