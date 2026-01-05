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

    # Step 7: Calculate health score
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
