"""
Optimization Service - Story 8 Business Logic
Location: api/services/optimization_service.py

Builds the hierarchical expandable rows view:
  Agent → Operation → Story → Fixes → Calls

Combines:
1. Detected issues from call data (auto-generated optimization_stories)
2. Tracked fixes from applied_fixes table
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
import uuid

from observatory.storage import ObservatoryStorage
from api.models.optimization import (
    STORY_METADATA,
    format_metric,
    format_improvement,
    get_story_metadata,
    OptimizationStory,
    AppliedFix,
    CallReference,
    OperationNode,
    AgentNode,
    OptimizationHierarchy,
)


# =============================================================================
# DETECTION THRESHOLDS
# =============================================================================

THRESHOLDS = {
    "latency": {
        "warning_ms": 5000,   # > 5 seconds
        "critical_ms": 10000, # > 10 seconds
    },
    "cache": {
        "min_duplicates": 3,  # 3+ identical prompts
    },
    "cost": {
        "high_single_call": 0.10,  # > $0.10 per call
    },
    "quality": {
        "low_score": 7.0,     # < 7.0 judge score
        "critical_score": 5.0,
    },
    "token": {
        "warning_ratio": 20.0,   # > 20:1 prompt:completion
        "critical_ratio": 50.0,
    },
    "prompt": {
        "system_pct_warning": 50.0,  # > 50% system prompt
    },
}


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def get_summary(
    calls: List[Dict],
    project: str = None,
    days: int = 7,
) -> Dict:
    """
    Build the hierarchical optimization view.

    Returns the full tree structure for the expandable rows table.
    """
    # Filter to LLM calls only
    llm_calls = [c for c in calls if (c.get("prompt_tokens") or 0) > 0]

    if not llm_calls:
        return _empty_response()

    # Step 1: Detect optimization opportunities from call data
    detected_stories = _detect_optimization_stories(llm_calls)

    # Step 2: Load existing tracked stories from database
    tracked_stories = ObservatoryStorage.get_all_optimization_stories()

    # Step 3: Merge detected with tracked (update existing, add new)
    merged_stories = _merge_stories(detected_stories, tracked_stories)

    # Step 4: Load applied fixes for each story
    for story in merged_stories:
        fixes = ObservatoryStorage.get_applied_fixes(story["id"])
        story["fixes"] = fixes
        story["fix_count"] = len(fixes)

    # Step 5: Build hierarchy
    hierarchy = _build_hierarchy(merged_stories, llm_calls)

    # Step 6: Calculate KPIs
    kpis = _calculate_kpis(llm_calls, merged_stories)

    # Step 7: Calculate comparison data (baseline vs optimized)
    comparison = _calculate_comparison(llm_calls, merged_stories)

    # Step 8: Calculate health score
    total_stories = len(merged_stories)
    complete_stories = sum(1 for s in merged_stories if s.get("status") == "complete")
    health_score = (complete_stories / total_stories * 100) if total_stories > 0 else 100

    status = "ok" if health_score >= 60 else "warning" if health_score >= 30 else "error"

    return {
        "status": status,
        "health_score": round(health_score, 1),
        "mode": "tracking",
        "hierarchy": hierarchy,
        "kpis": kpis,
        "comparison": comparison,
    }


def _empty_response() -> Dict:
    """Return empty response when no data."""
    return {
        "status": "ok",
        "health_score": 100.0,
        "mode": "tracking",
        "hierarchy": {
            "agents": [],
            "total_agents": 0,
            "total_operations": 0,
            "total_stories": 0,
            "total_pending": 0,
            "total_complete": 0,
        },
        "kpis": {},
        "comparison": {
            "baseline": {},
            "optimized": {},
            "improvements": {},
        },
    }


# =============================================================================
# DETECTION: Find optimization opportunities from call data
# =============================================================================

def _detect_optimization_stories(calls: List[Dict]) -> List[Dict]:
    """
    Analyze calls and detect optimization opportunities.
    Groups by (agent, operation) and checks each story type.
    """
    stories = []

    # Group calls by (agent, operation)
    by_agent_op = defaultdict(list)
    for call in calls:
        agent = call.get("agent_name") or "Unknown"
        op = call.get("operation") or "unknown"
        by_agent_op[(agent, op)].append(call)

    for (agent, op), op_calls in by_agent_op.items():
        # Check each story type
        stories.extend(_detect_latency_issues(agent, op, op_calls))
        stories.extend(_detect_cache_opportunities(agent, op, op_calls))
        stories.extend(_detect_cost_issues(agent, op, op_calls))
        stories.extend(_detect_quality_issues(agent, op, op_calls))
        stories.extend(_detect_token_issues(agent, op, op_calls))
        stories.extend(_detect_prompt_issues(agent, op, op_calls))

    return stories


def _detect_latency_issues(agent: str, op: str, calls: List[Dict]) -> List[Dict]:
    """Detect latency optimization opportunities."""
    latencies = [c.get("latency_ms") or 0 for c in calls if c.get("latency_ms")]
    if not latencies:
        return []

    avg_latency = sum(latencies) / len(latencies)
    if avg_latency < THRESHOLDS["latency"]["warning_ms"]:
        return []

    # Find calls that exceed threshold
    high_latency_calls = [
        c for c in calls
        if (c.get("latency_ms") or 0) > THRESHOLDS["latency"]["warning_ms"]
    ]

    if not high_latency_calls:
        return []

    # Calculate P95
    sorted_latencies = sorted(latencies)
    p95_idx = int(len(sorted_latencies) * 0.95)
    p95 = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]

    story_id = f"{agent}_{op}_latency"
    return [{
        "id": story_id,
        "agent_name": agent,
        "operation": op,
        "story_id": "latency",
        "call_count": len(high_latency_calls),
        "call_ids": [c.get("id") for c in high_latency_calls[:10]],  # Limit to 10
        "baseline_value": avg_latency / 1000,  # Convert to seconds
        "baseline_unit": "s",
        "baseline_p95": p95 / 1000,
        "baseline_date": datetime.utcnow(),
        "baseline_call_count": len(calls),
        "status": "pending",
        "_calls_data": high_latency_calls,  # Temp for building CallReference
    }]


def _detect_cache_opportunities(agent: str, op: str, calls: List[Dict]) -> List[Dict]:
    """Detect caching opportunities (duplicate prompts)."""
    # Group by content hash or prompt
    by_hash = defaultdict(list)
    for call in calls:
        key = call.get("content_hash") or call.get("prompt", "")[:100]
        if key:
            by_hash[key].append(call)

    # Find duplicates
    duplicates = {k: v for k, v in by_hash.items() if len(v) >= THRESHOLDS["cache"]["min_duplicates"]}
    if not duplicates:
        return []

    # Calculate wasted cost
    total_wasted = 0
    duplicate_calls = []
    for calls_list in duplicates.values():
        # First call is "original", rest are wasted
        for c in calls_list[1:]:
            total_wasted += c.get("total_cost") or 0
            duplicate_calls.append(c)

    if not duplicate_calls:
        return []

    story_id = f"{agent}_{op}_cache"
    return [{
        "id": story_id,
        "agent_name": agent,
        "operation": op,
        "story_id": "cache",
        "call_count": len(duplicate_calls),
        "call_ids": [c.get("id") for c in duplicate_calls[:10]],
        "baseline_value": total_wasted,
        "baseline_unit": "$",
        "baseline_date": datetime.utcnow(),
        "baseline_call_count": len(calls),
        "status": "pending",
        "_calls_data": duplicate_calls,
    }]


def _detect_cost_issues(agent: str, op: str, calls: List[Dict]) -> List[Dict]:
    """Detect high-cost calls."""
    high_cost_calls = [
        c for c in calls
        if (c.get("total_cost") or 0) > THRESHOLDS["cost"]["high_single_call"]
    ]

    if not high_cost_calls:
        return []

    total_cost = sum(c.get("total_cost") or 0 for c in high_cost_calls)

    story_id = f"{agent}_{op}_cost"
    return [{
        "id": story_id,
        "agent_name": agent,
        "operation": op,
        "story_id": "cost",
        "call_count": len(high_cost_calls),
        "call_ids": [c.get("id") for c in high_cost_calls[:10]],
        "baseline_value": total_cost,
        "baseline_unit": "$",
        "baseline_date": datetime.utcnow(),
        "baseline_call_count": len(calls),
        "status": "pending",
        "_calls_data": high_cost_calls,
    }]


def _detect_quality_issues(agent: str, op: str, calls: List[Dict]) -> List[Dict]:
    """Detect quality issues (low scores, hallucinations)."""
    quality_calls = [
        c for c in calls
        if c.get("judge_score") is not None and c.get("judge_score") < THRESHOLDS["quality"]["low_score"]
    ]

    # Also include hallucination flags
    hallucination_calls = [c for c in calls if c.get("hallucination_flag")]
    quality_calls = list({c.get("id"): c for c in quality_calls + hallucination_calls}.values())

    if not quality_calls:
        return []

    scores = [c.get("judge_score") or 0 for c in quality_calls if c.get("judge_score")]
    avg_score = sum(scores) / len(scores) if scores else 0

    story_id = f"{agent}_{op}_quality"
    return [{
        "id": story_id,
        "agent_name": agent,
        "operation": op,
        "story_id": "quality",
        "call_count": len(quality_calls),
        "call_ids": [c.get("id") for c in quality_calls[:10]],
        "baseline_value": avg_score,
        "baseline_unit": "score",
        "baseline_date": datetime.utcnow(),
        "baseline_call_count": len(calls),
        "status": "pending",
        "_calls_data": quality_calls,
    }]


def _detect_token_issues(agent: str, op: str, calls: List[Dict]) -> List[Dict]:
    """Detect token imbalance (high prompt:completion ratio)."""
    imbalanced_calls = []

    for call in calls:
        prompt_tokens = call.get("prompt_tokens") or 0
        completion_tokens = call.get("completion_tokens") or 1
        ratio = prompt_tokens / completion_tokens

        if ratio > THRESHOLDS["token"]["warning_ratio"]:
            call["_ratio"] = ratio
            imbalanced_calls.append(call)

    if not imbalanced_calls:
        return []

    avg_ratio = sum(c["_ratio"] for c in imbalanced_calls) / len(imbalanced_calls)

    story_id = f"{agent}_{op}_token"
    return [{
        "id": story_id,
        "agent_name": agent,
        "operation": op,
        "story_id": "token",
        "call_count": len(imbalanced_calls),
        "call_ids": [c.get("id") for c in imbalanced_calls[:10]],
        "baseline_value": avg_ratio,
        "baseline_unit": "ratio",
        "baseline_date": datetime.utcnow(),
        "baseline_call_count": len(calls),
        "status": "pending",
        "_calls_data": imbalanced_calls,
    }]


def _detect_prompt_issues(agent: str, op: str, calls: List[Dict]) -> List[Dict]:
    """Detect prompt composition issues (large system prompts)."""
    issue_calls = []

    for call in calls:
        system_tokens = call.get("system_prompt_tokens") or 0
        total_tokens = call.get("prompt_tokens") or 1
        if total_tokens == 0:
            continue

        system_pct = (system_tokens / total_tokens) * 100
        if system_pct > THRESHOLDS["prompt"]["system_pct_warning"]:
            call["_system_pct"] = system_pct
            issue_calls.append(call)

    if not issue_calls:
        return []

    avg_pct = sum(c["_system_pct"] for c in issue_calls) / len(issue_calls)

    story_id = f"{agent}_{op}_prompt"
    return [{
        "id": story_id,
        "agent_name": agent,
        "operation": op,
        "story_id": "prompt",
        "call_count": len(issue_calls),
        "call_ids": [c.get("id") for c in issue_calls[:10]],
        "baseline_value": avg_pct,
        "baseline_unit": "%",
        "baseline_date": datetime.utcnow(),
        "baseline_call_count": len(calls),
        "status": "pending",
        "_calls_data": issue_calls,
    }]


# =============================================================================
# MERGE: Combine detected with tracked stories
# =============================================================================

def _merge_stories(detected: List[Dict], tracked: List[Dict]) -> List[Dict]:
    """
    Merge detected stories with tracked stories from database.
    - If story exists in DB, use DB version (preserves status, fixes, etc.)
    - If story is new, save to DB
    """
    tracked_by_id = {s["id"]: s for s in tracked}
    merged = []

    for story in detected:
        story_id = story["id"]

        if story_id in tracked_by_id:
            # Use tracked version but update call count/ids
            tracked_story = tracked_by_id[story_id]
            tracked_story["call_count"] = story["call_count"]
            tracked_story["call_ids"] = story["call_ids"]
            tracked_story["_calls_data"] = story.get("_calls_data", [])

            # Update baseline if significantly different (re-detection)
            # This allows baselines to update as new data comes in for pending stories
            if tracked_story.get("status") == "pending":
                tracked_story["baseline_value"] = story["baseline_value"]
                tracked_story["baseline_date"] = story["baseline_date"]
                tracked_story["baseline_call_count"] = story["baseline_call_count"]

            merged.append(tracked_story)
        else:
            # New story - save to DB
            story_to_save = {
                "id": story_id,
                "agent_name": story["agent_name"],
                "operation": story["operation"],
                "story_id": story["story_id"],
                "call_count": story["call_count"],
                "call_ids": story["call_ids"],
                "baseline_value": story["baseline_value"],
                "baseline_unit": story["baseline_unit"],
                "baseline_p95": story.get("baseline_p95"),
                "baseline_date": story["baseline_date"],
                "baseline_call_count": story["baseline_call_count"],
                "status": "pending",
            }
            ObservatoryStorage.save_optimization_story(story_to_save)
            story["status"] = "pending"
            merged.append(story)

    return merged


# =============================================================================
# HIERARCHY: Build the tree structure
# =============================================================================

def _build_hierarchy(stories: List[Dict], calls: List[Dict]) -> Dict:
    """Build the Agent → Operation → Story hierarchy."""

    # Group stories by agent then operation
    by_agent = defaultdict(lambda: defaultdict(list))
    for story in stories:
        agent = story["agent_name"]
        op = story["operation"]
        by_agent[agent][op].append(story)

    # Count calls by agent/operation
    call_counts = defaultdict(lambda: defaultdict(int))
    for call in calls:
        agent = call.get("agent_name") or "Unknown"
        op = call.get("operation") or "unknown"
        call_counts[agent][op] += 1

    # Build agent nodes
    agents = []
    total_stories = 0
    total_pending = 0
    total_complete = 0

    for agent_name in sorted(by_agent.keys()):
        operations_dict = by_agent[agent_name]
        operations = []

        agent_stories = 0
        agent_pending = 0
        agent_complete = 0
        agent_calls = 0

        for op_name in sorted(operations_dict.keys()):
            op_stories = operations_dict[op_name]
            op_call_count = call_counts[agent_name][op_name]
            agent_calls += op_call_count

            # Build story objects with formatting
            formatted_stories = []
            for s in op_stories:
                meta = get_story_metadata(s["story_id"])
                unit = s.get("baseline_unit") or meta["unit"]

                # Build call references
                calls_refs = []
                for call_data in s.get("_calls_data", [])[:10]:
                    metric_val = _get_call_metric(call_data, s["story_id"])
                    calls_refs.append({
                        "id": call_data.get("id"),
                        "metric_value": metric_val,
                        "metric_formatted": format_metric(metric_val, unit),
                        "timestamp": call_data.get("timestamp"),
                    })

                formatted_story = {
                    "id": s["id"],
                    "agent_name": s["agent_name"],
                    "operation": s["operation"],
                    "story_id": s["story_id"],
                    "story_icon": meta["icon"],
                    "story_color": meta["color"],
                    "call_count": s["call_count"],
                    "call_ids": s.get("call_ids", []),
                    "calls": calls_refs,
                    "baseline_value": s["baseline_value"],
                    "baseline_value_formatted": format_metric(s["baseline_value"], unit),
                    "baseline_unit": unit,
                    "baseline_p95": s.get("baseline_p95"),
                    "baseline_p95_formatted": format_metric(s["baseline_p95"], unit) if s.get("baseline_p95") else None,
                    "baseline_date": s.get("baseline_date"),
                    "baseline_call_count": s.get("baseline_call_count", 0),
                    "current_value": s.get("current_value"),
                    "current_value_formatted": format_metric(s["current_value"], unit) if s.get("current_value") else None,
                    "current_date": s.get("current_date"),
                    "improvement_pct": s.get("improvement_pct"),
                    "improvement_formatted": format_improvement(
                        s["baseline_value"],
                        s["current_value"],
                        meta["lower_is_better"]
                    ) if s.get("current_value") else None,
                    "status": s.get("status", "pending"),
                    "skip_reason": s.get("skip_reason"),
                    "fixes": s.get("fixes", []),
                    "fix_count": s.get("fix_count", 0),
                    "created_at": s.get("created_at"),
                    "updated_at": s.get("updated_at"),
                }
                formatted_stories.append(formatted_story)

                # Count statuses
                if s.get("status") == "complete":
                    agent_complete += 1
                else:
                    agent_pending += 1

            agent_stories += len(op_stories)

            operations.append({
                "operation": op_name,
                "call_count": op_call_count,
                "stories": formatted_stories,
                "total_stories": len(op_stories),
                "pending_count": sum(1 for s in op_stories if s.get("status") != "complete"),
                "complete_count": sum(1 for s in op_stories if s.get("status") == "complete"),
            })

        agents.append({
            "agent_name": agent_name,
            "call_count": agent_calls,
            "operations": operations,
            "total_stories": agent_stories,
            "pending_count": agent_pending,
            "complete_count": agent_complete,
        })

        total_stories += agent_stories
        total_pending += agent_pending
        total_complete += agent_complete

    return {
        "agents": agents,
        "total_agents": len(agents),
        "total_operations": sum(len(a["operations"]) for a in agents),
        "total_stories": total_stories,
        "total_pending": total_pending,
        "total_complete": total_complete,
    }


def _get_call_metric(call: Dict, story_id: str) -> float:
    """Get the relevant metric value for a call based on story type."""
    if story_id == "latency":
        return (call.get("latency_ms") or 0) / 1000  # Convert to seconds
    elif story_id == "cache":
        return call.get("total_cost") or 0
    elif story_id == "cost":
        return call.get("total_cost") or 0
    elif story_id == "quality":
        return call.get("judge_score") or 0
    elif story_id == "token":
        prompt = call.get("prompt_tokens") or 0
        completion = call.get("completion_tokens") or 1
        return prompt / completion
    elif story_id == "prompt":
        return call.get("_system_pct") or 0
    else:
        return 0


# =============================================================================
# KPIs: Calculate overall metrics
# =============================================================================

def _calculate_kpis(calls: List[Dict], stories: List[Dict]) -> Dict:
    """Calculate KPIs for the summary."""
    # Overall call metrics
    latencies = [c.get("latency_ms") or 0 for c in calls if c.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    total_cost = sum(c.get("total_cost") or 0 for c in calls)

    quality_scores = [c.get("judge_score") for c in calls if c.get("judge_score") is not None]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    cache_hits = sum(1 for c in calls if c.get("cache_hit"))
    cache_rate = (cache_hits / len(calls) * 100) if calls else 0

    # Story progress
    total_stories = len(stories)
    complete = sum(1 for s in stories if s.get("status") == "complete")
    pending = total_stories - complete

    # Calculate total savings from complete stories
    total_cost_saved = 0
    total_latency_saved = 0

    for story in stories:
        if story.get("status") == "complete" and story.get("current_value") is not None:
            baseline = story.get("baseline_value", 0)
            current = story.get("current_value", 0)
            improvement = baseline - current

            if story.get("story_id") in ["cache", "cost"]:
                total_cost_saved += improvement
            elif story.get("story_id") == "latency":
                total_latency_saved += improvement * 1000  # Convert to ms

    return {
        "total_calls": len(calls),
        "avg_latency_ms": avg_latency,
        "avg_latency_formatted": f"{avg_latency / 1000:.2f}s",
        "total_cost": total_cost,
        "total_cost_formatted": f"${total_cost:.2f}",
        "avg_quality": avg_quality,
        "avg_quality_formatted": f"{avg_quality:.1f}/10" if avg_quality else "—",
        "cache_hit_rate": cache_rate,
        "cache_hit_rate_formatted": f"{cache_rate:.0f}%",
        "total_stories": total_stories,
        "complete_stories": complete,
        "pending_stories": pending,
        "progress_pct": (complete / total_stories * 100) if total_stories > 0 else 0,
        "total_cost_saved": total_cost_saved,
        "total_cost_saved_formatted": f"${total_cost_saved:.2f}",
        "total_latency_saved_ms": total_latency_saved,
        "total_latency_saved_formatted": f"{total_latency_saved / 1000:.1f}s",
    }


# =============================================================================
# COMPARISON: Calculate baseline vs optimized metrics for Impact View
# =============================================================================

def _calculate_comparison(calls: List[Dict], stories: List[Dict]) -> Dict:
    """
    Calculate comparison data between baseline and optimized metrics.

    Aggregates baseline values from stories and computes current (optimized)
    values from the actual call data or completed story metrics.
    """
    # Group stories by type to aggregate baselines
    baselines_by_type = defaultdict(list)
    optimized_by_type = defaultdict(list)

    for story in stories:
        story_type = story.get("story_id")
        baseline_val = story.get("baseline_value")
        current_val = story.get("current_value")

        if baseline_val is not None:
            baselines_by_type[story_type].append(baseline_val)

        # For completed stories, use current_value as optimized
        if story.get("status") == "complete" and current_val is not None:
            optimized_by_type[story_type].append(current_val)

    # Calculate current metrics from calls (for metrics not yet optimized)
    latencies = [c.get("latency_ms") or 0 for c in calls if c.get("latency_ms")]
    avg_latency_current = sum(latencies) / len(latencies) if latencies else None

    total_cost_current = sum(c.get("total_cost") or 0 for c in calls)

    quality_scores = [c.get("judge_score") for c in calls if c.get("judge_score") is not None]
    avg_quality_current = sum(quality_scores) / len(quality_scores) if quality_scores else None

    cache_hits = sum(1 for c in calls if c.get("cache_hit"))
    cache_rate_current = (cache_hits / len(calls) * 100) if calls else None

    # Calculate token ratios
    token_ratios = []
    for c in calls:
        prompt = c.get("prompt_tokens") or 0
        completion = c.get("completion_tokens") or 1
        if prompt > 0 and completion > 0:
            token_ratios.append(prompt / completion)
    avg_token_ratio_current = sum(token_ratios) / len(token_ratios) if token_ratios else None

    # Calculate prompt percentages (system prompt % of total)
    prompt_pcts = []
    for c in calls:
        prompt = c.get("prompt_tokens") or 0
        completion = c.get("completion_tokens") or 0
        total = prompt + completion
        if total > 0:
            # Estimate system prompt as ~50% of prompt tokens if not available directly
            system_pct = c.get("_system_pct") or (prompt / total * 100 * 0.5)
            prompt_pcts.append(system_pct)
    avg_prompt_pct_current = sum(prompt_pcts) / len(prompt_pcts) if prompt_pcts else None

    # Aggregate baseline averages
    def avg_baseline(story_type):
        vals = baselines_by_type.get(story_type, [])
        return sum(vals) / len(vals) if vals else None

    def avg_optimized(story_type, fallback):
        vals = optimized_by_type.get(story_type, [])
        if vals:
            return sum(vals) / len(vals)
        return fallback

    # Build baseline object (from story baselines)
    baseline = {
        "avg_latency_ms": avg_baseline("latency"),
        "total_cost": avg_baseline("cost"),
        "avg_quality": avg_baseline("quality"),
        "cache_hit_rate": avg_baseline("cache"),
        "avg_token_ratio": avg_baseline("token"),
        "avg_prompt_pct": avg_baseline("prompt"),
    }

    # Build optimized object (prefer completed story values, fallback to current)
    optimized = {
        "avg_latency_ms": avg_optimized("latency", avg_latency_current),
        "total_cost": avg_optimized("cost", total_cost_current),
        "avg_quality": avg_optimized("quality", avg_quality_current),
        "cache_hit_rate": avg_optimized("cache", cache_rate_current),
        "avg_token_ratio": avg_optimized("token", avg_token_ratio_current),
        "avg_prompt_pct": avg_optimized("prompt", avg_prompt_pct_current),
    }

    # Calculate improvement percentages
    def calc_improvement(baseline_val, optimized_val, higher_is_better=False):
        if baseline_val is None or optimized_val is None or baseline_val == 0:
            return None
        change = ((optimized_val - baseline_val) / baseline_val) * 100
        return change if higher_is_better else -change

    improvements = {
        "latency_pct": calc_improvement(baseline["avg_latency_ms"], optimized["avg_latency_ms"], False),
        "cost_pct": calc_improvement(baseline["total_cost"], optimized["total_cost"], False),
        "quality_pct": calc_improvement(baseline["avg_quality"], optimized["avg_quality"], True),
        "cache_pct": calc_improvement(baseline["cache_hit_rate"], optimized["cache_hit_rate"], True),
        "token_ratio_pct": calc_improvement(baseline["avg_token_ratio"], optimized["avg_token_ratio"], False),
        "prompt_pct": calc_improvement(baseline["avg_prompt_pct"], optimized["avg_prompt_pct"], False),
    }

    return {
        "baseline": baseline,
        "optimized": optimized,
        "improvements": improvements,
    }


# =============================================================================
# DETAIL: Get single optimization story with full details
# =============================================================================

def get_optimization_detail(story_id: str) -> Optional[Dict]:
    """Get detailed view of a single optimization story."""
    story = ObservatoryStorage.get_optimization_story(story_id)
    if not story:
        return None

    fixes = ObservatoryStorage.get_applied_fixes(story_id)

    # Get call details
    calls = []
    for call_id in story.get("call_ids", [])[:20]:
        call = ObservatoryStorage.get_llm_call_by_id(call_id)
        if call:
            meta = get_story_metadata(story["story_id"])
            metric_val = _get_call_metric(call.__dict__, story["story_id"])
            calls.append({
                "id": call.id,
                "metric_value": metric_val,
                "metric_formatted": format_metric(metric_val, story.get("baseline_unit", "")),
                "timestamp": call.timestamp,
            })

    return {
        "story": story,
        "fixes": fixes,
        "calls": calls,
    }


# =============================================================================
# ACTIONS: Update story status, add fixes
# =============================================================================

def update_story_status(
    story_id: str,
    status: str,
    skip_reason: Optional[str] = None,
    current_value: Optional[float] = None,
) -> bool:
    """Update the status of an optimization story."""
    return ObservatoryStorage.update_optimization_story_status(
        story_id=story_id,
        status=status,
        skip_reason=skip_reason,
        current_value=current_value,
    )


def add_applied_fix(
    optimization_story_id: str,
    fix_type: str,
    before_value: float,
    after_value: Optional[float] = None,
    applied_date: Optional[datetime] = None,
    git_commit: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """Add an applied fix to an optimization story."""
    fix_id = str(uuid.uuid4())

    # Calculate improvement if after_value provided
    improvement_pct = None
    if after_value is not None and before_value != 0:
        improvement_pct = ((before_value - after_value) / before_value) * 100

    fix = {
        "id": fix_id,
        "optimization_story_id": optimization_story_id,
        "fix_type": fix_type,
        "before_value": before_value,
        "after_value": after_value,
        "improvement_pct": improvement_pct,
        "applied_date": applied_date or datetime.utcnow(),
        "git_commit": git_commit,
        "notes": notes,
    }

    ObservatoryStorage.save_applied_fix(fix)

    # If after_value provided, update the story's current value
    if after_value is not None:
        ObservatoryStorage.update_optimization_story_status(
            story_id=optimization_story_id,
            status="complete",
            current_value=after_value,
        )

    return fix_id


def delete_fix(fix_id: str) -> bool:
    """Delete an applied fix."""
    return ObservatoryStorage.delete_applied_fix(fix_id)


# =============================================================================
# DETAILED COMPARISON: Rich baseline vs optimized comparison
# =============================================================================

def get_detailed_comparison(
    project: str = None,
    baseline_start: str = None,
    baseline_end: str = None,
    optimized_start: str = None,
    optimized_end: str = None,
    limit: int = 5000,
) -> Dict:
    """
    Get comprehensive baseline vs optimized comparison with detailed metrics.

    Returns the full comparison table matching the console output format:
    - Cost metrics (total, per call, per session, daily avg)
    - Performance metrics (latency, P95, TTFT)
    - Quality metrics (avg score, quality per dollar, success rate)
    - Caching metrics (hit rate, hits, cost savings)
    - Token metrics (total, avg prompt/completion, ratio)
    - Routing metrics (decisions, routed to cheaper, savings)
    - Operation-specific metrics breakdown
    """
    from datetime import datetime, timedelta

    # Get all calls
    all_calls = ObservatoryStorage.get_llm_calls(limit=limit)

    # Filter by phase metadata or date range
    baseline_calls = []
    optimized_calls = []

    for call in all_calls:
        call_dict = call.__dict__ if hasattr(call, '__dict__') else call

        # Get phase - now a direct column, with fallbacks for backward compatibility
        phase = call_dict.get('phase')

        # Fallback to metadata.phase if direct column is empty
        if not phase:
            import json
            metadata = call_dict.get('metadata') or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            phase = metadata.get('phase')

        # Fallback to experiment_metadata.phase
        if not phase:
            experiment_metadata = call_dict.get('experiment_metadata') or {}
            if isinstance(experiment_metadata, str):
                try:
                    experiment_metadata = json.loads(experiment_metadata)
                except:
                    experiment_metadata = {}
            phase = experiment_metadata.get('phase')

        # Final fallback to environment
        if not phase:
            phase = call_dict.get('environment')

        # Also check explicit date ranges if provided
        call_date = call_dict.get('timestamp')
        if isinstance(call_date, str):
            call_date = datetime.fromisoformat(call_date.replace('Z', '+00:00'))

        if phase == 'baseline':
            baseline_calls.append(call_dict)
        elif phase == 'optimized':
            optimized_calls.append(call_dict)
        elif baseline_start and baseline_end and call_date:
            # Date-based filtering
            b_start = datetime.strptime(baseline_start, '%Y-%m-%d')
            b_end = datetime.strptime(baseline_end, '%Y-%m-%d') + timedelta(days=1)
            o_start = datetime.strptime(optimized_start, '%Y-%m-%d') if optimized_start else None
            o_end = datetime.strptime(optimized_end, '%Y-%m-%d') + timedelta(days=1) if optimized_end else None

            if b_start <= call_date < b_end:
                baseline_calls.append(call_dict)
            elif o_start and o_end and o_start <= call_date < o_end:
                optimized_calls.append(call_dict)

    # If no phase data, split by date (first half = baseline, second half = optimized)
    if not baseline_calls and not optimized_calls and all_calls:
        all_dicts = [c.__dict__ if hasattr(c, '__dict__') else c for c in all_calls]
        sorted_calls = sorted(all_dicts, key=lambda x: x.get('timestamp', ''))
        midpoint = len(sorted_calls) // 2
        baseline_calls = sorted_calls[:midpoint] if midpoint > 0 else sorted_calls
        optimized_calls = sorted_calls[midpoint:] if midpoint > 0 else []

    # Calculate comprehensive metrics for each period
    baseline_metrics = _calculate_period_metrics(baseline_calls, 'baseline')
    optimized_metrics = _calculate_period_metrics(optimized_calls, 'optimized')

    # Calculate improvements
    comparison_rows = _build_comparison_rows(baseline_metrics, optimized_metrics)

    # Get date ranges
    baseline_dates = _get_date_range(baseline_calls)
    optimized_dates = _get_date_range(optimized_calls)

    return {
        'baseline_period': baseline_dates,
        'optimized_period': optimized_dates,
        'baseline': baseline_metrics,
        'optimized': optimized_metrics,
        'comparison': comparison_rows,
        'summary': {
            'total_cost_saved': max(0, baseline_metrics.get('total_cost', 0) - optimized_metrics.get('total_cost', 0)),
            'total_latency_saved_ms': max(0, baseline_metrics.get('avg_latency_ms', 0) - optimized_metrics.get('avg_latency_ms', 0)),
            'cache_improvement_pp': optimized_metrics.get('cache_hit_rate', 0) - baseline_metrics.get('cache_hit_rate', 0),
        }
    }


def _get_date_range(calls: List[Dict]) -> Dict:
    """Get date range from calls."""
    if not calls:
        return {'start': None, 'end': None, 'days': 0}

    timestamps = []
    for c in calls:
        ts = c.get('timestamp')
        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except:
                    continue
            timestamps.append(ts)

    if not timestamps:
        return {'start': None, 'end': None, 'days': 0}

    min_ts = min(timestamps)
    max_ts = max(timestamps)
    days = (max_ts - min_ts).days + 1

    return {
        'start': min_ts.strftime('%Y-%m-%d'),
        'end': max_ts.strftime('%Y-%m-%d'),
        'days': days,
    }


def _calculate_period_metrics(calls: List[Dict], period_name: str) -> Dict:
    """Calculate comprehensive metrics for a period."""
    if not calls:
        return {
            'period': period_name,
            'total_calls': 0,
            'total_cost': 0,
            'avg_latency_ms': 0,
        }

    total_calls = len(calls)

    # Cost metrics
    total_cost = sum(c.get('total_cost') or 0 for c in calls)
    costs = [c.get('total_cost') or 0 for c in calls]
    avg_cost_per_call = total_cost / total_calls if total_calls else 0

    # Session-based cost (group by session_id)
    sessions = set(c.get('session_id') for c in calls if c.get('session_id'))
    cost_per_session = total_cost / len(sessions) if sessions else total_cost

    # Daily cost
    dates = set()
    for c in calls:
        ts = c.get('timestamp')
        if ts:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except:
                    continue
            dates.add(ts.date())
    num_days = len(dates) or 1
    daily_cost = total_cost / num_days

    # Latency metrics
    latencies = [c.get('latency_ms') or 0 for c in calls if c.get('latency_ms')]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    sorted_latencies = sorted(latencies)
    p95_idx = int(len(sorted_latencies) * 0.95) if sorted_latencies else 0
    p95_latency = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else (sorted_latencies[-1] if sorted_latencies else 0)

    # TTFT (time to first token) - estimate from streaming_metrics or use ~30% of latency
    ttft_values = []
    for c in calls:
        streaming = c.get('streaming_metrics')
        if streaming:
            if isinstance(streaming, str):
                try:
                    import json
                    streaming = json.loads(streaming)
                except:
                    streaming = {}
            ttft = streaming.get('time_to_first_token_ms')
            if ttft:
                ttft_values.append(ttft)
    avg_ttft = sum(ttft_values) / len(ttft_values) if ttft_values else avg_latency * 0.3

    # Calls per second (max throughput estimate)
    calls_per_second = 1000 / avg_latency if avg_latency > 0 else 0

    # Quality metrics
    quality_scores = [c.get('judge_score') for c in calls if c.get('judge_score') is not None]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    quality_per_dollar = avg_quality / avg_cost_per_call if avg_quality and avg_cost_per_call else None

    # Success/Error rate
    successes = sum(1 for c in calls if c.get('success', True))
    success_rate = (successes / total_calls * 100) if total_calls else 100
    error_rate = 100 - success_rate

    # Cache metrics - check both direct cache_hit and cache_metadata.cache_hit
    cache_hits = 0
    for c in calls:
        # Direct cache_hit field (from DB column)
        if c.get('cache_hit'):
            cache_hits += 1
        else:
            # Check cache_metadata object
            cache_meta = c.get('cache_metadata')
            if cache_meta:
                if isinstance(cache_meta, dict):
                    if cache_meta.get('cache_hit'):
                        cache_hits += 1
                elif hasattr(cache_meta, 'cache_hit') and cache_meta.cache_hit:
                    cache_hits += 1

    cache_hit_rate = (cache_hits / total_calls * 100) if total_calls else 0

    # Estimate cache cost savings (avg cost * cache hits)
    cache_cost_savings = avg_cost_per_call * cache_hits

    # Cache latency (typically ~1ms for cache hits)
    cache_latency = 1 if cache_hits > 0 else None

    # Token metrics
    total_tokens = sum((c.get('prompt_tokens') or 0) + (c.get('completion_tokens') or 0) for c in calls)
    prompt_tokens = [c.get('prompt_tokens') or 0 for c in calls]
    completion_tokens = [c.get('completion_tokens') or 0 for c in calls]
    avg_prompt_tokens = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0
    avg_completion_tokens = sum(completion_tokens) / len(completion_tokens) if completion_tokens else 0
    prompt_completion_ratio = avg_prompt_tokens / avg_completion_tokens if avg_completion_tokens else 0
    tokens_per_dollar = total_tokens / total_cost if total_cost else 0

    # Routing metrics
    routing_decisions = sum(1 for c in calls if c.get('routing_decision'))
    routed_to_cheaper = sum(
        1 for c in calls
        if c.get('routing_decision') and 'cheaper' in str(c.get('routing_decision', '')).lower()
    )
    routed_to_cheaper_pct = (routed_to_cheaper / total_calls * 100) if total_calls else 0

    # Estimate routing savings (routed calls * avg cost difference)
    routing_cost_savings = routed_to_cheaper * avg_cost_per_call * 0.3  # Assume 30% savings

    # Routing overhead (estimate ~50ms)
    routing_overhead = 50 if routing_decisions > 0 else None

    # Operation-specific metrics
    ops = defaultdict(lambda: {'count': 0, 'cost': 0, 'latency': 0, 'prompt_tokens': 0})
    for c in calls:
        op = c.get('operation') or 'unknown'
        agent = c.get('agent_name') or 'unknown'
        key = f"{agent}_{op}"
        ops[key]['count'] += 1
        ops[key]['cost'] += c.get('total_cost') or 0
        ops[key]['latency'] += c.get('latency_ms') or 0
        ops[key]['prompt_tokens'] += c.get('prompt_tokens') or 0
        ops[key]['agent'] = agent
        ops[key]['operation'] = op

    operation_metrics = {}
    for key, data in ops.items():
        count = data['count']
        operation_metrics[key] = {
            'agent': data['agent'],
            'operation': data['operation'],
            'count': count,
            'avg_latency': data['latency'] / count if count else 0,
            'avg_cost': data['cost'] / count if count else 0,
            'avg_prompt_tokens': data['prompt_tokens'] / count if count else 0,
        }

    return {
        'period': period_name,
        'total_calls': total_calls,
        'num_sessions': len(sessions),
        'num_days': num_days,

        # Cost metrics
        'total_cost': total_cost,
        'avg_cost_per_call': avg_cost_per_call,
        'cost_per_session': cost_per_session,
        'daily_cost': daily_cost,

        # Performance metrics
        'avg_latency_ms': avg_latency,
        'p95_latency_ms': p95_latency,
        'avg_ttft_ms': avg_ttft,
        'calls_per_second': calls_per_second,

        # Quality metrics
        'avg_quality': avg_quality,
        'quality_per_dollar': quality_per_dollar,
        'success_rate': success_rate,
        'error_rate': error_rate,

        # Cache metrics
        'cache_hits': cache_hits,
        'cache_hit_rate': cache_hit_rate,
        'cache_cost_savings': cache_cost_savings,
        'cache_latency_ms': cache_latency,

        # Token metrics
        'total_tokens': total_tokens,
        'avg_prompt_tokens': avg_prompt_tokens,
        'avg_completion_tokens': avg_completion_tokens,
        'prompt_completion_ratio': prompt_completion_ratio,
        'tokens_per_dollar': tokens_per_dollar,

        # Routing metrics
        'routing_decisions': routing_decisions,
        'routed_to_cheaper_pct': routed_to_cheaper_pct,
        'routing_cost_savings': routing_cost_savings,
        'routing_overhead_ms': routing_overhead,

        # Operation breakdown
        'by_operation': operation_metrics,
    }


def _build_comparison_rows(baseline: Dict, optimized: Dict) -> List[Dict]:
    """Build comparison table rows with impact indicators."""

    def calc_impact(b_val, o_val, lower_is_better=True, is_percentage=False):
        """Calculate impact percentage and direction."""
        if b_val is None or o_val is None:
            return {'pct': None, 'direction': 'neutral', 'indicator': '—'}
        if b_val == 0:
            if o_val == 0:
                return {'pct': 0, 'direction': 'neutral', 'indicator': '0%'}
            return {'pct': 100 if not lower_is_better else -100, 'direction': 'improved' if not lower_is_better else 'regressed', 'indicator': '+∞'}

        if is_percentage:
            # For percentage point change
            change = o_val - b_val
            indicator = f"{change:+.1f}pp"
            direction = 'improved' if (change > 0 and not lower_is_better) or (change < 0 and lower_is_better) else 'regressed' if change != 0 else 'neutral'
        else:
            pct = ((o_val - b_val) / b_val) * 100
            if lower_is_better:
                direction = 'improved' if pct < 0 else 'regressed' if pct > 0 else 'neutral'
            else:
                direction = 'improved' if pct > 0 else 'regressed' if pct < 0 else 'neutral'
            indicator = f"{pct:+.0f}%"
            change = pct

        return {
            'pct': change,
            'direction': direction,
            'indicator': indicator,
        }

    rows = []

    # Cost Metrics Section
    rows.append({'section': 'cost', 'label': 'COST METRICS', 'is_header': True})
    rows.append({
        'section': 'cost',
        'metric': 'Total Cost',
        'baseline': baseline.get('total_cost'),
        'baseline_fmt': f"${baseline.get('total_cost', 0):.2f}",
        'optimized': optimized.get('total_cost'),
        'optimized_fmt': f"${optimized.get('total_cost', 0):.2f}",
        **calc_impact(baseline.get('total_cost'), optimized.get('total_cost'), lower_is_better=True),
    })
    rows.append({
        'section': 'cost',
        'metric': 'Cost per Call',
        'baseline': baseline.get('avg_cost_per_call'),
        'baseline_fmt': f"${baseline.get('avg_cost_per_call', 0):.3f}",
        'optimized': optimized.get('avg_cost_per_call'),
        'optimized_fmt': f"${optimized.get('avg_cost_per_call', 0):.3f}",
        **calc_impact(baseline.get('avg_cost_per_call'), optimized.get('avg_cost_per_call'), lower_is_better=True),
    })
    rows.append({
        'section': 'cost',
        'metric': 'Cost per Session',
        'baseline': baseline.get('cost_per_session'),
        'baseline_fmt': f"${baseline.get('cost_per_session', 0):.3f}",
        'optimized': optimized.get('cost_per_session'),
        'optimized_fmt': f"${optimized.get('cost_per_session', 0):.3f}",
        **calc_impact(baseline.get('cost_per_session'), optimized.get('cost_per_session'), lower_is_better=True),
    })
    rows.append({
        'section': 'cost',
        'metric': 'Daily Cost (Avg)',
        'baseline': baseline.get('daily_cost'),
        'baseline_fmt': f"${baseline.get('daily_cost', 0):.2f}",
        'optimized': optimized.get('daily_cost'),
        'optimized_fmt': f"${optimized.get('daily_cost', 0):.2f}",
        **calc_impact(baseline.get('daily_cost'), optimized.get('daily_cost'), lower_is_better=True),
    })

    # Performance Metrics Section
    rows.append({'section': 'performance', 'label': 'PERFORMANCE METRICS', 'is_header': True})
    rows.append({
        'section': 'performance',
        'metric': 'Avg Latency',
        'baseline': baseline.get('avg_latency_ms'),
        'baseline_fmt': f"{baseline.get('avg_latency_ms', 0):,.0f} ms",
        'optimized': optimized.get('avg_latency_ms'),
        'optimized_fmt': f"{optimized.get('avg_latency_ms', 0):,.0f} ms",
        **calc_impact(baseline.get('avg_latency_ms'), optimized.get('avg_latency_ms'), lower_is_better=True),
    })
    rows.append({
        'section': 'performance',
        'metric': 'P95 Latency',
        'baseline': baseline.get('p95_latency_ms'),
        'baseline_fmt': f"{baseline.get('p95_latency_ms', 0):,.0f} ms",
        'optimized': optimized.get('p95_latency_ms'),
        'optimized_fmt': f"{optimized.get('p95_latency_ms', 0):,.0f} ms",
        **calc_impact(baseline.get('p95_latency_ms'), optimized.get('p95_latency_ms'), lower_is_better=True),
    })
    rows.append({
        'section': 'performance',
        'metric': 'Avg Time to First Token',
        'baseline': baseline.get('avg_ttft_ms'),
        'baseline_fmt': f"{baseline.get('avg_ttft_ms', 0):,.0f} ms",
        'optimized': optimized.get('avg_ttft_ms'),
        'optimized_fmt': f"{optimized.get('avg_ttft_ms', 0):,.0f} ms",
        **calc_impact(baseline.get('avg_ttft_ms'), optimized.get('avg_ttft_ms'), lower_is_better=True),
    })
    rows.append({
        'section': 'performance',
        'metric': 'Calls per Second (Max)',
        'baseline': baseline.get('calls_per_second'),
        'baseline_fmt': f"{baseline.get('calls_per_second', 0):.1f}",
        'optimized': optimized.get('calls_per_second'),
        'optimized_fmt': f"{optimized.get('calls_per_second', 0):.1f}",
        **calc_impact(baseline.get('calls_per_second'), optimized.get('calls_per_second'), lower_is_better=False),
    })

    # Quality Metrics Section
    rows.append({'section': 'quality', 'label': 'QUALITY METRICS', 'is_header': True})
    rows.append({
        'section': 'quality',
        'metric': 'Avg Quality Score',
        'baseline': baseline.get('avg_quality'),
        'baseline_fmt': f"{baseline.get('avg_quality', 0):.2f}" if baseline.get('avg_quality') else '—',
        'optimized': optimized.get('avg_quality'),
        'optimized_fmt': f"{optimized.get('avg_quality', 0):.2f}" if optimized.get('avg_quality') else '—',
        **calc_impact(baseline.get('avg_quality'), optimized.get('avg_quality'), lower_is_better=False),
    })
    rows.append({
        'section': 'quality',
        'metric': 'Quality per Dollar',
        'baseline': baseline.get('quality_per_dollar'),
        'baseline_fmt': f"{baseline.get('quality_per_dollar', 0):.2f}" if baseline.get('quality_per_dollar') else '—',
        'optimized': optimized.get('quality_per_dollar'),
        'optimized_fmt': f"{optimized.get('quality_per_dollar', 0):.2f}" if optimized.get('quality_per_dollar') else '—',
        **calc_impact(baseline.get('quality_per_dollar'), optimized.get('quality_per_dollar'), lower_is_better=False),
    })
    rows.append({
        'section': 'quality',
        'metric': 'Success Rate',
        'baseline': baseline.get('success_rate'),
        'baseline_fmt': f"{baseline.get('success_rate', 0):.0f}%",
        'optimized': optimized.get('success_rate'),
        'optimized_fmt': f"{optimized.get('success_rate', 0):.0f}%",
        **calc_impact(baseline.get('success_rate'), optimized.get('success_rate'), lower_is_better=False, is_percentage=True),
    })
    rows.append({
        'section': 'quality',
        'metric': 'Error Rate',
        'baseline': baseline.get('error_rate'),
        'baseline_fmt': f"{baseline.get('error_rate', 0):.0f}%",
        'optimized': optimized.get('error_rate'),
        'optimized_fmt': f"{optimized.get('error_rate', 0):.0f}%",
        **calc_impact(baseline.get('error_rate'), optimized.get('error_rate'), lower_is_better=True, is_percentage=True),
    })

    # Caching Metrics Section
    rows.append({'section': 'caching', 'label': 'CACHING METRICS', 'is_header': True})
    rows.append({
        'section': 'caching',
        'metric': 'Cache Hit Rate',
        'baseline': baseline.get('cache_hit_rate'),
        'baseline_fmt': f"{baseline.get('cache_hit_rate', 0):.1f}%",
        'optimized': optimized.get('cache_hit_rate'),
        'optimized_fmt': f"{optimized.get('cache_hit_rate', 0):.1f}%",
        **calc_impact(baseline.get('cache_hit_rate'), optimized.get('cache_hit_rate'), lower_is_better=False, is_percentage=True),
    })
    rows.append({
        'section': 'caching',
        'metric': 'Cache Hits',
        'baseline': baseline.get('cache_hits'),
        'baseline_fmt': f"{baseline.get('cache_hits', 0):,}",
        'optimized': optimized.get('cache_hits'),
        'optimized_fmt': f"{optimized.get('cache_hits', 0):,}",
        **calc_impact(baseline.get('cache_hits'), optimized.get('cache_hits'), lower_is_better=False),
    })
    rows.append({
        'section': 'caching',
        'metric': 'Cache Cost Savings',
        'baseline': baseline.get('cache_cost_savings'),
        'baseline_fmt': f"${baseline.get('cache_cost_savings', 0):.2f}",
        'optimized': optimized.get('cache_cost_savings'),
        'optimized_fmt': f"${optimized.get('cache_cost_savings', 0):.2f}",
        **calc_impact(baseline.get('cache_cost_savings'), optimized.get('cache_cost_savings'), lower_is_better=False),
    })
    rows.append({
        'section': 'caching',
        'metric': 'Avg Cache Latency',
        'baseline': baseline.get('cache_latency_ms'),
        'baseline_fmt': f"{baseline.get('cache_latency_ms', 0)} ms" if baseline.get('cache_latency_ms') else 'N/A',
        'optimized': optimized.get('cache_latency_ms'),
        'optimized_fmt': f"{optimized.get('cache_latency_ms', 0)} ms" if optimized.get('cache_latency_ms') else 'N/A',
        'pct': None,
        'direction': 'neutral',
        'indicator': 'N/A',
    })

    # Token Metrics Section
    rows.append({'section': 'tokens', 'label': 'TOKEN METRICS', 'is_header': True})
    rows.append({
        'section': 'tokens',
        'metric': 'Total Tokens',
        'baseline': baseline.get('total_tokens'),
        'baseline_fmt': f"{baseline.get('total_tokens', 0):,}",
        'optimized': optimized.get('total_tokens'),
        'optimized_fmt': f"{optimized.get('total_tokens', 0):,}",
        **calc_impact(baseline.get('total_tokens'), optimized.get('total_tokens'), lower_is_better=True),
    })
    rows.append({
        'section': 'tokens',
        'metric': 'Avg Prompt Tokens',
        'baseline': baseline.get('avg_prompt_tokens'),
        'baseline_fmt': f"{baseline.get('avg_prompt_tokens', 0):,.0f}",
        'optimized': optimized.get('avg_prompt_tokens'),
        'optimized_fmt': f"{optimized.get('avg_prompt_tokens', 0):,.0f}",
        **calc_impact(baseline.get('avg_prompt_tokens'), optimized.get('avg_prompt_tokens'), lower_is_better=True),
    })
    rows.append({
        'section': 'tokens',
        'metric': 'Avg Completion Tokens',
        'baseline': baseline.get('avg_completion_tokens'),
        'baseline_fmt': f"{baseline.get('avg_completion_tokens', 0):,.0f}",
        'optimized': optimized.get('avg_completion_tokens'),
        'optimized_fmt': f"{optimized.get('avg_completion_tokens', 0):,.0f}",
        **calc_impact(baseline.get('avg_completion_tokens'), optimized.get('avg_completion_tokens'), lower_is_better=False),
    })
    rows.append({
        'section': 'tokens',
        'metric': 'Prompt/Completion Ratio',
        'baseline': baseline.get('prompt_completion_ratio'),
        'baseline_fmt': f"{baseline.get('prompt_completion_ratio', 0):.1f}:1",
        'optimized': optimized.get('prompt_completion_ratio'),
        'optimized_fmt': f"{optimized.get('prompt_completion_ratio', 0):.1f}:1",
        **calc_impact(baseline.get('prompt_completion_ratio'), optimized.get('prompt_completion_ratio'), lower_is_better=True),
    })
    rows.append({
        'section': 'tokens',
        'metric': 'Tokens per Dollar',
        'baseline': baseline.get('tokens_per_dollar'),
        'baseline_fmt': f"{baseline.get('tokens_per_dollar', 0):,.0f}",
        'optimized': optimized.get('tokens_per_dollar'),
        'optimized_fmt': f"{optimized.get('tokens_per_dollar', 0):,.0f}",
        **calc_impact(baseline.get('tokens_per_dollar'), optimized.get('tokens_per_dollar'), lower_is_better=False),
    })

    # Routing Metrics Section
    rows.append({'section': 'routing', 'label': 'ROUTING METRICS', 'is_header': True})
    rows.append({
        'section': 'routing',
        'metric': 'Routing Decisions Made',
        'baseline': baseline.get('routing_decisions'),
        'baseline_fmt': f"{baseline.get('routing_decisions', 0):,}",
        'optimized': optimized.get('routing_decisions'),
        'optimized_fmt': f"{optimized.get('routing_decisions', 0):,}",
        **calc_impact(baseline.get('routing_decisions'), optimized.get('routing_decisions'), lower_is_better=False),
    })
    rows.append({
        'section': 'routing',
        'metric': 'Routed to Cheaper Model',
        'baseline': baseline.get('routed_to_cheaper_pct'),
        'baseline_fmt': f"{baseline.get('routed_to_cheaper_pct', 0):.0f}%",
        'optimized': optimized.get('routed_to_cheaper_pct'),
        'optimized_fmt': f"{optimized.get('routed_to_cheaper_pct', 0):.0f}%",
        **calc_impact(baseline.get('routed_to_cheaper_pct'), optimized.get('routed_to_cheaper_pct'), lower_is_better=False, is_percentage=True),
    })
    rows.append({
        'section': 'routing',
        'metric': 'Routing Cost Savings',
        'baseline': baseline.get('routing_cost_savings'),
        'baseline_fmt': f"${baseline.get('routing_cost_savings', 0):.2f}",
        'optimized': optimized.get('routing_cost_savings'),
        'optimized_fmt': f"${optimized.get('routing_cost_savings', 0):.2f}",
        **calc_impact(baseline.get('routing_cost_savings'), optimized.get('routing_cost_savings'), lower_is_better=False),
    })
    rows.append({
        'section': 'routing',
        'metric': 'Avg Routing Overhead',
        'baseline': baseline.get('routing_overhead_ms'),
        'baseline_fmt': f"{baseline.get('routing_overhead_ms', 0)} ms" if baseline.get('routing_overhead_ms') else 'N/A',
        'optimized': optimized.get('routing_overhead_ms'),
        'optimized_fmt': f"{optimized.get('routing_overhead_ms', 0)} ms" if optimized.get('routing_overhead_ms') else 'N/A',
        'pct': None,
        'direction': 'neutral',
        'indicator': 'N/A',
    })

    # Operation-Specific Metrics Section
    rows.append({'section': 'operations', 'label': 'OPERATION-SPECIFIC METRICS', 'is_header': True})

    # Get top operations by count
    baseline_ops = baseline.get('by_operation', {})
    optimized_ops = optimized.get('by_operation', {})
    all_ops = set(list(baseline_ops.keys()) + list(optimized_ops.keys()))

    for op_key in sorted(all_ops, key=lambda k: baseline_ops.get(k, {}).get('count', 0) + optimized_ops.get(k, {}).get('count', 0), reverse=True)[:5]:
        b_op = baseline_ops.get(op_key, {})
        o_op = optimized_ops.get(op_key, {})
        op_name = b_op.get('operation') or o_op.get('operation') or op_key
        agent = b_op.get('agent') or o_op.get('agent') or ''

        display_name = f"{agent} {op_name}".strip().replace('_', ' ').title()

        # Latency for this operation
        rows.append({
            'section': 'operations',
            'metric': f'{display_name} Avg Latency',
            'baseline': b_op.get('avg_latency'),
            'baseline_fmt': f"{b_op.get('avg_latency', 0):,.0f} ms",
            'optimized': o_op.get('avg_latency'),
            'optimized_fmt': f"{o_op.get('avg_latency', 0):,.0f} ms",
            **calc_impact(b_op.get('avg_latency'), o_op.get('avg_latency'), lower_is_better=True),
        })
        # Cost for this operation
        rows.append({
            'section': 'operations',
            'metric': f'{display_name} Avg Cost',
            'baseline': b_op.get('avg_cost'),
            'baseline_fmt': f"${b_op.get('avg_cost', 0):.3f}",
            'optimized': o_op.get('avg_cost'),
            'optimized_fmt': f"${o_op.get('avg_cost', 0):.3f}",
            **calc_impact(b_op.get('avg_cost'), o_op.get('avg_cost'), lower_is_better=True),
        })
        # Prompt tokens for this operation
        rows.append({
            'section': 'operations',
            'metric': f'{display_name} Avg Prompt Tokens',
            'baseline': b_op.get('avg_prompt_tokens'),
            'baseline_fmt': f"{b_op.get('avg_prompt_tokens', 0):,.0f}",
            'optimized': o_op.get('avg_prompt_tokens'),
            'optimized_fmt': f"{o_op.get('avg_prompt_tokens', 0):,.0f}",
            **calc_impact(b_op.get('avg_prompt_tokens'), o_op.get('avg_prompt_tokens'), lower_is_better=True),
        })

    return rows
