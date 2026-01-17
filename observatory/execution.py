"""
Optimization Detectors - Execution and Prompt Patterns
Location: observatory/execution.py

Detects opportunities for optimization across execution and prompts:
- Execution Patterns:
  * BatchDetector: Rapid sequential calls → batch API
  * ParallelDetector: Independent calls → parallel execution
  * SequentialCallDetector: Sequential patterns → workflow restructure
  * StreamingDetector: High latency/large output → streaming
  
- Prompt Patterns:
  * ContextGrowthDetector: Chat history bloat → context limiting
  * TokenEfficiencyDetector: High prompt/completion ratio → prompt compression

Each detector supports detection_only mode for baseline analysis.
All detectors create optimization stories in the database.
"""

import logging
import time
from typing import Optional, Dict, List, Any, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

if TYPE_CHECKING:
    from observatory.collector import Observatory

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BatchOpportunity:
    """Detected batching opportunity."""
    operation: str
    call_count: int
    time_window_ms: float
    potential_latency_saved_ms: float
    call_ids: List[str] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ParallelOpportunity:
    """Detected parallelism opportunity."""
    operations: List[str]
    call_count: int
    sequential_latency_ms: float
    potential_parallel_latency_ms: float
    latency_saved_ms: float
    call_ids: List[str] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SequentialPattern:
    """Detected sequential call pattern."""
    operation: str
    call_count: int
    time_span_s: float
    avg_latency_ms: float
    call_ids: List[str] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class StreamingCandidate:
    """Call that would benefit from streaming."""
    operation: str
    latency_ms: float
    completion_tokens: int
    reason: str  # "high_latency" or "large_output"
    call_id: Optional[str] = None


@dataclass
class ContextGrowthAlert:
    """Detected context growth issue."""
    operation: str
    chat_history_tokens: int
    total_prompt_tokens: int
    history_percentage: float
    call_id: str = None
    recommendation: str = None


@dataclass
class TokenEfficiencyAlert:
    """Detected token inefficiency."""
    operation: str
    prompt_tokens: int
    completion_tokens: int
    efficiency_ratio: float  # prompt/completion
    call_id: str = None
    recommendation: str = None


@dataclass
class ExecutionMetrics:
    """Metrics from batch/parallel execution."""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_elapsed_ms: float
    estimated_sequential_ms: float
    time_saved_ms: float
    individual_latencies_ms: List[float] = field(default_factory=list)
    # Token tracking
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    # Per-task token breakdown
    task_token_usage: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# BATCH DETECTOR
# =============================================================================

class BatchDetector:
    """
    Detects sequential calls that could be batched together.
    
    BASELINE MODE (detection_only=True):
        - Tracks rapid sequential calls to same operation
        - Creates optimization stories in database
        - Logs batching opportunities
        - Does NOT actually batch calls
    
    OPTIMIZED MODE (detection_only=False):
        - Same detection + story creation
        - Application code can use opportunities to batch calls
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        time_window_ms: float = 100,
        min_batch_size: int = 2,
        operations: Optional[Set[str]] = None,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        self.observatory = observatory
        self.time_window_ms = time_window_ms
        self.min_batch_size = min_batch_size
        self.operations = operations
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Track recent calls: operation -> [(timestamp, call_id, latency, agent_name), ...]
        self._recent_calls: Dict[str, List[tuple]] = defaultdict(list)
        
        # Statistics
        self._stats = {
            "opportunities_detected": 0,
            "total_batchable_calls": 0,
            "potential_latency_saved_ms": 0.0,
            "by_operation": defaultdict(lambda: {"count": 0, "calls": 0}),
        }
    
    def is_monitored(self, operation: str) -> bool:
        """Check if operation is monitored for batching."""
        if not self.enabled:
            return False
        if self.operations is None:
            return True
        return operation in self.operations
    
    def track_call(
        self,
        operation: str,
        call_id: str = None,
        timestamp: float = None,
        latency_ms: float = None,
        agent_name: str = None,
    ):
        """
        Track a call for batch detection.
        
        Args:
            operation: Operation name
            call_id: Unique call identifier
            timestamp: Call timestamp (defaults to now)
            latency_ms: Call latency for savings calculation
            agent_name: Agent name for story creation
        """
        if not self.is_monitored(operation):
            return
        
        timestamp = timestamp or time.time()
        
        # Add to recent calls
        self._recent_calls[operation].append((timestamp, call_id, latency_ms, agent_name))
        
        # Clean old calls (outside time window)
        cutoff = timestamp - (self.time_window_ms / 1000)
        self._recent_calls[operation] = [
            (ts, cid, lat, agent) for ts, cid, lat, agent in self._recent_calls[operation]
            if ts >= cutoff
        ]
        
        # Check for batch opportunity
        recent = self._recent_calls[operation]
        if len(recent) >= self.min_batch_size:
            self._detect_opportunity(operation, recent)
    
    def _detect_opportunity(
        self,
        operation: str,
        calls: List[tuple],
    ):
        """Detect and log batch opportunity, create story."""
        if len(calls) < self.min_batch_size:
            return
        
        call_ids = [cid for _, cid, _, _ in calls if cid]
        latencies = [lat for _, _, lat, _ in calls if lat]
        agent_names = [agent for _, _, _, agent in calls if agent]
        agent_name = agent_names[0] if agent_names else None
        
        # Calculate potential savings
        avg_latency = sum(latencies) / len(latencies) if latencies else 500
        potential_saved = (len(calls) - 1) * avg_latency
        
        # Time window span
        timestamps = [ts for ts, _, _, _ in calls]
        time_span = (max(timestamps) - min(timestamps)) * 1000  # ms
        
        opportunity = BatchOpportunity(
            operation=operation,
            call_count=len(calls),
            time_window_ms=time_span,
            potential_latency_saved_ms=potential_saved,
            call_ids=call_ids,
        )
        
        # Update stats
        self._stats["opportunities_detected"] += 1
        self._stats["total_batchable_calls"] += len(calls)
        self._stats["potential_latency_saved_ms"] += potential_saved
        self._stats["by_operation"][operation]["count"] += 1
        self._stats["by_operation"][operation]["calls"] += len(calls)
        
        # Log
        logger.info(
            f"💡 BATCH OPPORTUNITY: {len(calls)} {operation} calls in {time_span:.0f}ms "
            f"(could save {potential_saved:.0f}ms latency)"
        )
        
        # Create optimization story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                self.observatory.storage.create_optimization_story(
                    opportunity_type="batch_opportunity",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=call_ids,
                    potential_savings_ms=potential_saved,
                    recommendation=f"Batch {len(calls)} {operation} calls in {time_span:.0f}ms window. Estimated {potential_saved:.0f}ms latency savings.",
                    metadata={
                        "call_count": len(calls),
                        "time_window_ms": time_span,
                        "avg_latency_ms": avg_latency,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create batch story: {e}")
        
        return opportunity
    
    def analyze_workflow(
        self,
        operation: str,
        call_count: int,
        total_duration_ms: float,
        metadata: Dict[str, Any] = None,
    ) -> Optional[BatchOpportunity]:
        """
        Analyze a completed workflow for batch opportunities.
        
        Used for workflow-level analysis (e.g., after matching 10 jobs).
        
        Args:
            operation: Operation name
            call_count: Number of calls made
            total_duration_ms: Total time for all calls
            metadata: Additional context
            
        Returns:
            BatchOpportunity if detected, None otherwise
        """
        if call_count < self.min_batch_size:
            return None
        
        avg_latency = total_duration_ms / call_count
        
        # Estimate batching savings (reduce N calls to ceil(N/3) batches)
        import math
        batch_count = math.ceil(call_count / 3)  # 3 items per batch
        potential_saved = (call_count - batch_count) * avg_latency
        
        opportunity = BatchOpportunity(
            operation=operation,
            call_count=call_count,
            time_window_ms=total_duration_ms,
            potential_latency_saved_ms=potential_saved,
            call_ids=[],
        )
        
        # Log
        logger.info(
            f"💡 WORKFLOW BATCH OPPORTUNITY: {call_count} {operation} calls "
            f"→ {batch_count} batches (saves {potential_saved:.0f}ms)"
        )
        
        # Create story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                agent_name = metadata.get('agent_name') if metadata else None
                self.observatory.storage.create_optimization_story(
                    opportunity_type="batch_opportunity",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=[],
                    potential_savings_ms=potential_saved,
                    recommendation=f"Batch {call_count} sequential {operation} calls into ~{batch_count} batch API calls. Estimated {potential_saved:.0f}ms latency savings.",
                    metadata={
                        "call_count": call_count,
                        "suggested_batch_count": batch_count,
                        "total_duration_ms": total_duration_ms,
                        **(metadata or {}),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create workflow batch story: {e}")
        
        return opportunity
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batching statistics."""
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "time_window_ms": self.time_window_ms,
            "min_batch_size": self.min_batch_size,
            "opportunities_detected": self._stats["opportunities_detected"],
            "total_batchable_calls": self._stats["total_batchable_calls"],
            "potential_latency_saved_ms": self._stats["potential_latency_saved_ms"],
            "by_operation": dict(self._stats["by_operation"]),
        }


# =============================================================================
# PARALLEL DETECTOR
# =============================================================================

class ParallelDetector:
    """
    Detects independent calls that could be executed in parallel.
    
    BASELINE MODE (detection_only=True):
        - Analyzes call dependencies
        - Creates optimization stories
        - Does NOT actually parallelize calls
    
    OPTIMIZED MODE (detection_only=False):
        - Same detection + story creation
        - Application code can parallelize
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        time_window_s: float = 5.0,
        min_parallel_count: int = 2,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        self.observatory = observatory
        self.time_window_s = time_window_s
        self.min_parallel_count = min_parallel_count
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Track sequences: sequence_id -> [calls]
        self._sequences: Dict[str, List[Dict]] = {}
        
        # Statistics
        self._stats = {
            "opportunities_detected": 0,
            "total_parallelizable_calls": 0,
            "potential_latency_saved_ms": 0.0,
        }
    
    def start_sequence(self, sequence_id: str = None) -> str:
        """Start tracking a new sequence of calls."""
        if not self.enabled:
            return None
        
        sequence_id = sequence_id or f"seq_{int(time.time() * 1000)}"
        self._sequences[sequence_id] = []
        return sequence_id
    
    def track_call(
        self,
        sequence_id: str,
        operation: str,
        call_id: str = None,
        latency_ms: float = None,
        depends_on: List[str] = None,
        agent_name: str = None,
    ):
        """Track a call in a sequence."""
        if not self.enabled or sequence_id not in self._sequences:
            return
        
        self._sequences[sequence_id].append({
            "operation": operation,
            "call_id": call_id,
            "latency_ms": latency_ms or 500,
            "depends_on": depends_on or [],
            "agent_name": agent_name,
            "timestamp": time.time(),
        })
    
    def end_sequence(self, sequence_id: str) -> Optional[ParallelOpportunity]:
        """End sequence and analyze for parallelism."""
        if not self.enabled or sequence_id not in self._sequences:
            return None
        
        calls = self._sequences.pop(sequence_id)
        
        if len(calls) < self.min_parallel_count:
            return None
        
        # Find independent calls
        independent = self._find_independent_calls(calls)
        
        if len(independent) < self.min_parallel_count:
            return None
        
        # Calculate sequential vs parallel latency
        sequential_latency = sum(c["latency_ms"] for c in independent)
        parallel_latency = max(c["latency_ms"] for c in independent)
        latency_saved = sequential_latency - parallel_latency
        
        opportunity = ParallelOpportunity(
            operations=[c["operation"] for c in independent],
            call_count=len(independent),
            sequential_latency_ms=sequential_latency,
            potential_parallel_latency_ms=parallel_latency,
            latency_saved_ms=latency_saved,
            call_ids=[c["call_id"] for c in independent if c["call_id"]],
        )
        
        # Update stats
        self._stats["opportunities_detected"] += 1
        self._stats["total_parallelizable_calls"] += len(independent)
        self._stats["potential_latency_saved_ms"] += latency_saved
        
        # Log
        logger.info(
            f"💡 PARALLEL OPPORTUNITY: {len(independent)} independent calls "
            f"({sequential_latency:.0f}ms sequential → {parallel_latency:.0f}ms parallel, "
            f"saves {latency_saved:.0f}ms)"
        )
        
        # Create story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                agent_name = independent[0].get("agent_name") if independent else None
                operation = independent[0]["operation"] if independent else "unknown"
                
                self.observatory.storage.create_optimization_story(
                    opportunity_type="parallel_opportunity",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=opportunity.call_ids,
                    potential_savings_ms=latency_saved,
                    recommendation=f"Parallelize {len(independent)} independent calls. Sequential: {sequential_latency:.0f}ms → Parallel: {parallel_latency:.0f}ms",
                    metadata={
                        "call_count": len(independent),
                        "sequential_latency_ms": sequential_latency,
                        "parallel_latency_ms": parallel_latency,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create parallel story: {e}")
        
        return opportunity
    
    def analyze_workflow(
        self,
        operation: str,
        call_count: int,
        total_duration_ms: float,
        are_independent: bool = True,
        metadata: Dict[str, Any] = None,
    ) -> Optional[ParallelOpportunity]:
        """
        Analyze a completed workflow for parallel opportunities.
        
        Args:
            operation: Operation name
            call_count: Number of calls made
            total_duration_ms: Total sequential time
            are_independent: Whether calls are independent
            metadata: Additional context
            
        Returns:
            ParallelOpportunity if detected, None otherwise
        """
        if not are_independent or call_count < self.min_parallel_count:
            return None
        
        # Estimate parallel execution time (assume 3 concurrent workers)
        parallel_duration = total_duration_ms / 3
        latency_saved = total_duration_ms - parallel_duration
        
        opportunity = ParallelOpportunity(
            operations=[operation] * call_count,
            call_count=call_count,
            sequential_latency_ms=total_duration_ms,
            potential_parallel_latency_ms=parallel_duration,
            latency_saved_ms=latency_saved,
            call_ids=[],
        )
        
        # Log
        logger.info(
            f"💡 WORKFLOW PARALLEL OPPORTUNITY: {call_count} independent {operation} calls "
            f"({total_duration_ms:.0f}ms sequential → ~{parallel_duration:.0f}ms with 3 workers)"
        )
        
        # Create story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                agent_name = metadata.get('agent_name') if metadata else None
                self.observatory.storage.create_optimization_story(
                    opportunity_type="parallel_opportunity",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=[],
                    potential_savings_ms=latency_saved,
                    recommendation=f"Run {call_count} independent {operation} calls in parallel with 3 concurrent workers. Saves ~{latency_saved:.0f}ms.",
                    metadata={
                        "call_count": call_count,
                        "sequential_duration_ms": total_duration_ms,
                        "estimated_parallel_duration_ms": parallel_duration,
                        "suggested_workers": 3,
                        **(metadata or {}),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create workflow parallel story: {e}")
        
        return opportunity
    
    def _find_independent_calls(self, calls: List[Dict]) -> List[Dict]:
        """Find calls with no dependencies on each other."""
        independent = []
        
        for call in calls:
            call_ids_in_list = {c["call_id"] for c in calls if c["call_id"]}
            depends_on_in_list = set(call["depends_on"]) & call_ids_in_list
            
            if not depends_on_in_list:
                independent.append(call)
        
        return independent
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parallelism statistics."""
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "time_window_s": self.time_window_s,
            "min_parallel_count": self.min_parallel_count,
            "opportunities_detected": self._stats["opportunities_detected"],
            "total_parallelizable_calls": self._stats["total_parallelizable_calls"],
            "potential_latency_saved_ms": self._stats["potential_latency_saved_ms"],
        }


# =============================================================================
# SEQUENTIAL CALL DETECTOR (NEW)
# =============================================================================

class SequentialCallDetector:
    """
    Detects sequential calls to same operation (even if not rapid).
    
    Different from BatchDetector:
    - BatchDetector: Rapid calls within 100ms → API batching
    - SequentialCallDetector: Sequential pattern over longer time → workflow optimization
    
    Example: 10 sequential quick_score_job calls over 30 seconds
    → Could be parallelized or batched at workflow level
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        sequence_window_s: float = 60.0,
        min_sequence_count: int = 5,
        operations: Optional[Set[str]] = None,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        self.observatory = observatory
        self.sequence_window_s = sequence_window_s
        self.min_sequence_count = min_sequence_count
        self.operations = operations
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Track recent calls: operation -> deque[(timestamp, call_id, latency, agent_name)]
        self._recent_calls: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Statistics
        self._stats = {
            "patterns_detected": 0,
            "total_sequential_calls": 0,
            "by_operation": defaultdict(lambda: {"count": 0, "calls": 0}),
        }
    
    def is_monitored(self, operation: str) -> bool:
        """Check if operation is monitored."""
        if not self.enabled:
            return False
        if self.operations is None:
            return True
        return operation in self.operations
    
    def track_call(
        self,
        operation: str,
        call_id: str = None,
        latency_ms: float = None,
        agent_name: str = None,
    ):
        """Track a call for sequential pattern detection."""
        if not self.is_monitored(operation):
            return
        
        timestamp = time.time()
        
        # Add to recent calls
        self._recent_calls[operation].append((timestamp, call_id, latency_ms or 500, agent_name))
        
        # Clean old calls (outside window)
        cutoff = timestamp - self.sequence_window_s
        while self._recent_calls[operation] and self._recent_calls[operation][0][0] < cutoff:
            self._recent_calls[operation].popleft()
        
        # Check for sequential pattern
        recent = list(self._recent_calls[operation])
        if len(recent) >= self.min_sequence_count:
            self._detect_pattern(operation, recent)
    
    def _detect_pattern(
        self,
        operation: str,
        calls: List[tuple],
    ):
        """Detect and log sequential pattern, create story."""
        if len(calls) < self.min_sequence_count:
            return
        
        timestamps = [ts for ts, _, _, _ in calls]
        call_ids = [cid for _, cid, _, _ in calls if cid]
        latencies = [lat for _, _, lat, _ in calls if lat]
        agent_names = [agent for _, _, _, agent in calls if agent]
        agent_name = agent_names[0] if agent_names else None
        
        time_span = timestamps[-1] - timestamps[0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 500
        
        pattern = SequentialPattern(
            operation=operation,
            call_count=len(calls),
            time_span_s=time_span,
            avg_latency_ms=avg_latency,
            call_ids=call_ids,
        )
        
        # Update stats
        self._stats["patterns_detected"] += 1
        self._stats["total_sequential_calls"] += len(calls)
        self._stats["by_operation"][operation]["count"] += 1
        self._stats["by_operation"][operation]["calls"] += len(calls)
        
        # Log
        logger.info(
            f"💡 SEQUENTIAL PATTERN: {len(calls)} {operation} calls over {time_span:.1f}s "
            f"(avg {avg_latency:.0f}ms each)"
        )
        
        # Create story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                # Calculate potential savings (parallel execution)
                total_sequential_time = sum(latencies)
                potential_parallel_time = max(latencies)
                potential_savings_ms = total_sequential_time - potential_parallel_time
                
                self.observatory.storage.create_optimization_story(
                    opportunity_type="sequential_calls",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=call_ids,
                    potential_savings_ms=potential_savings_ms,
                    recommendation=f"Parallelize or batch {len(calls)} sequential {operation} calls. Sequential: {total_sequential_time:.0f}ms → Parallel: {potential_parallel_time:.0f}ms",
                    metadata={
                        "time_span_s": time_span,
                        "avg_latency_ms": avg_latency,
                        "call_count": len(calls),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create sequential story: {e}")
        
        return pattern
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sequential pattern statistics."""
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "sequence_window_s": self.sequence_window_s,
            "min_sequence_count": self.min_sequence_count,
            "patterns_detected": self._stats["patterns_detected"],
            "total_sequential_calls": self._stats["total_sequential_calls"],
            "by_operation": dict(self._stats["by_operation"]),
        }


# =============================================================================
# STREAMING DETECTOR
# =============================================================================

class StreamingDetector:
    """
    Detects calls that would benefit from streaming.
    
    BASELINE MODE: Flags candidates, creates stories
    OPTIMIZED MODE: Application can use streaming API
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        latency_threshold_ms: float = 2000,
        token_threshold: int = 500,
        operations: Optional[Set[str]] = None,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        self.observatory = observatory
        self.latency_threshold_ms = latency_threshold_ms
        self.token_threshold = token_threshold
        self.operations = operations
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Statistics
        self._stats = {
            "candidates_detected": 0,
            "high_latency_count": 0,
            "large_output_count": 0,
            "by_operation": defaultdict(lambda: {"count": 0}),
        }
    
    def is_monitored(self, operation: str) -> bool:
        """Check if operation is monitored for streaming."""
        if not self.enabled:
            return False
        if self.operations is None:
            return True
        return operation in self.operations
    
    def check_call(
        self,
        operation: str,
        latency_ms: float = None,
        completion_tokens: int = None,
        call_id: str = None,
        agent_name: str = None,
    ) -> Optional[StreamingCandidate]:
        """Check if call is a streaming candidate."""
        if not self.is_monitored(operation):
            return None
        
        reason = None
        
        # Check latency threshold
        if latency_ms and latency_ms > self.latency_threshold_ms:
            reason = "high_latency"
            self._stats["high_latency_count"] += 1
        
        # Check token threshold
        elif completion_tokens and completion_tokens > self.token_threshold:
            reason = "large_output"
            self._stats["large_output_count"] += 1
        
        if not reason:
            return None
        
        # Create candidate
        candidate = StreamingCandidate(
            operation=operation,
            latency_ms=latency_ms or 0,
            completion_tokens=completion_tokens or 0,
            reason=reason,
            call_id=call_id,
        )
        
        # Update stats
        self._stats["candidates_detected"] += 1
        self._stats["by_operation"][operation]["count"] += 1
        
        # Log
        logger.info(
            f"💡 STREAMING CANDIDATE: {operation} "
            f"({reason}: {latency_ms:.0f}ms, {completion_tokens} tokens)"
        )
        
        # Create story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                self.observatory.storage.create_optimization_story(
                    opportunity_type="streaming_candidate",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=[call_id] if call_id else [],
                    potential_savings_ms=None,  # Streaming improves UX, not latency
                    recommendation=f"Use streaming for {operation}. Reason: {reason} ({latency_ms:.0f}ms, {completion_tokens} tokens)",
                    metadata={
                        "reason": reason,
                        "latency_ms": latency_ms,
                        "completion_tokens": completion_tokens,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create streaming story: {e}")
        
        return candidate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming detection statistics."""
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "latency_threshold_ms": self.latency_threshold_ms,
            "token_threshold": self.token_threshold,
            "candidates_detected": self._stats["candidates_detected"],
            "high_latency_count": self._stats["high_latency_count"],
            "large_output_count": self._stats["large_output_count"],
            "by_operation": dict(self._stats["by_operation"]),
        }


# =============================================================================
# CONTEXT GROWTH DETECTOR (NEW)
# =============================================================================

class ContextGrowthDetector:
    """
    Detects when chat history grows too large relative to total prompt.
    
    Alerts when chat_history_tokens > threshold% of total prompt tokens.
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        threshold_percentage: float = 50.0,
        operations: Optional[Set[str]] = None,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        self.observatory = observatory
        self.threshold_percentage = threshold_percentage
        self.operations = operations
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Statistics
        self._stats = {
            "alerts_detected": 0,
            "by_operation": defaultdict(lambda: {"count": 0, "max_pct": 0}),
        }
    
    def is_monitored(self, operation: str) -> bool:
        """Check if operation is monitored."""
        if not self.enabled:
            return False
        if self.operations is None:
            return True
        return operation in self.operations
    
    def check_call(
        self,
        operation: str,
        chat_history_tokens: int,
        total_prompt_tokens: int,
        call_id: str = None,
        agent_name: str = None,
    ) -> Optional[ContextGrowthAlert]:
        """Check if call has context growth issue."""
        if not self.is_monitored(operation):
            return None
        
        if not chat_history_tokens or not total_prompt_tokens or total_prompt_tokens == 0:
            return None
        
        history_pct = (chat_history_tokens / total_prompt_tokens) * 100
        
        if history_pct <= self.threshold_percentage:
            return None
        
        # Create alert
        alert = ContextGrowthAlert(
            operation=operation,
            chat_history_tokens=chat_history_tokens,
            total_prompt_tokens=total_prompt_tokens,
            history_percentage=history_pct,
            call_id=call_id,
            recommendation=f"Limit chat history to ~10 messages. Current: {chat_history_tokens} tokens ({history_pct:.0f}% of prompt)",
        )
        
        # Update stats
        self._stats["alerts_detected"] += 1
        self._stats["by_operation"][operation]["count"] += 1
        if history_pct > self._stats["by_operation"][operation]["max_pct"]:
            self._stats["by_operation"][operation]["max_pct"] = history_pct
        
        # Log
        logger.info(
            f"💡 CONTEXT GROWTH: {operation} has {chat_history_tokens} history tokens "
            f"({history_pct:.0f}% of {total_prompt_tokens} total)"
        )
        
        # Create story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                # Estimate savings (reduce to ~20% of prompt)
                target_tokens = int(total_prompt_tokens * 0.2)
                potential_savings_tokens = chat_history_tokens - target_tokens
                
                self.observatory.storage.create_optimization_story(
                    opportunity_type="context_growth",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=[call_id] if call_id else [],
                    potential_savings_tokens=potential_savings_tokens,
                    recommendation=alert.recommendation,
                    metadata={
                        "chat_history_tokens": chat_history_tokens,
                        "total_prompt_tokens": total_prompt_tokens,
                        "history_percentage": history_pct,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create context growth story: {e}")
        
        return alert
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context growth statistics."""
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "threshold_percentage": self.threshold_percentage,
            "alerts_detected": self._stats["alerts_detected"],
            "by_operation": dict(self._stats["by_operation"]),
        }


# =============================================================================
# TOKEN EFFICIENCY DETECTOR 
# =============================================================================

class TokenEfficiencyDetector:
    """
    Detects inefficient token usage (high prompt/completion ratio).
    
    Alerts when prompt_tokens / completion_tokens > threshold.
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        threshold_ratio: float = 50.0,
        operations: Optional[Set[str]] = None,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        self.observatory = observatory
        self.threshold_ratio = threshold_ratio
        self.operations = operations
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Statistics
        self._stats = {
            "alerts_detected": 0,
            "by_operation": defaultdict(lambda: {"count": 0, "max_ratio": 0}),
        }
    
    def is_monitored(self, operation: str) -> bool:
        """Check if operation is monitored."""
        if not self.enabled:
            return False
        if self.operations is None:
            return True
        return operation in self.operations
    
    def check_call(
        self,
        operation: str,
        prompt_tokens: int,
        completion_tokens: int,
        call_id: str = None,
        agent_name: str = None,
    ) -> Optional[TokenEfficiencyAlert]:
        """Check if call has token efficiency issue."""
        if not self.is_monitored(operation):
            return None
        
        if not completion_tokens or completion_tokens == 0:
            return None
        
        ratio = prompt_tokens / completion_tokens
        
        if ratio <= self.threshold_ratio:
            return None
        
        # Create alert
        alert = TokenEfficiencyAlert(
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            efficiency_ratio=ratio,
            call_id=call_id,
            recommendation=f"Compress prompt. Current ratio: {ratio:.1f}:1 ({prompt_tokens} prompt / {completion_tokens} completion)",
        )
        
        # Update stats
        self._stats["alerts_detected"] += 1
        self._stats["by_operation"][operation]["count"] += 1
        if ratio > self._stats["by_operation"][operation]["max_ratio"]:
            self._stats["by_operation"][operation]["max_ratio"] = ratio
        
        # Log
        logger.info(
            f"💡 TOKEN INEFFICIENCY: {operation} has {ratio:.1f}:1 ratio "
            f"({prompt_tokens} prompt / {completion_tokens} completion)"
        )
        
        # Create story
        if self.observatory and hasattr(self.observatory, 'storage'):
            try:
                # Estimate savings (reduce prompt by 50%)
                potential_savings_tokens = int(prompt_tokens * 0.5)
                
                self.observatory.storage.create_optimization_story(
                    opportunity_type="token_efficiency",
                    operation=operation,
                    agent_name=agent_name,
                    call_ids=[call_id] if call_id else [],
                    potential_savings_tokens=potential_savings_tokens,
                    recommendation=alert.recommendation,
                    metadata={
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "efficiency_ratio": ratio,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to create token efficiency story: {e}")
        
        return alert
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token efficiency statistics."""
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "threshold_ratio": self.threshold_ratio,
            "alerts_detected": self._stats["alerts_detected"],
            "by_operation": dict(self._stats["by_operation"]),
        }

# =============================================================================
# BATCH PROCESSOR - UNIVERSAL BATCHING EXECUTION
# =============================================================================

class BatchProcessor:
    """
    Universal batch execution for any list of items.

    Unlike BatchDetector (which only detects opportunities),
    this actually creates batches and tracks execution.

    Usage:
        batches = batch_processor.create_batches(jobs, batch_size=3)
        # Each batch can be processed by your custom function

        # Or use execute_batches for end-to-end processing with metrics:
        results, metrics = await batch_processor.execute_batches(
            items=jobs,
            process_func=score_job,
            batch_size=3,
            max_concurrent=3,
            return_metrics=True
        )
    """

    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        default_batch_size: int = 3,
        track_batching: bool = True,
        enabled: bool = True,
    ):
        self.observatory = observatory
        self.default_batch_size = default_batch_size
        self.track_batching = track_batching
        self.enabled = enabled

        # Statistics
        self._stats = {
            "batches_created": 0,
            "total_items_batched": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost": 0.0,
            "total_time_saved_ms": 0.0,
            "by_operation": defaultdict(lambda: {"batches": 0, "items": 0, "time_saved_ms": 0.0}),
        }
    
    def create_batches(
        self,
        items: List[Any],
        batch_size: int = None,
        operation: str = None,
    ) -> List[List[Any]]:
        """
        Create batches from items list.
        
        Args:
            items: List of items to batch
            batch_size: Items per batch (defaults to default_batch_size)
            operation: Operation name for tracking
            
        Returns:
            List of batches (each batch is a list of items)
            
        Example:
            jobs = [job1, job2, job3, job4, job5]
            batches = processor.create_batches(jobs, batch_size=3)
            # Returns: [[job1, job2, job3], [job4, job5]]
        """
        if not self.enabled or not items:
            return [items] if items else []
        
        batch_size = batch_size or self.default_batch_size
        
        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            batches.append(batch)
        
        # Track creation
        if self.track_batching:
            self._stats["batches_created"] += len(batches)
            self._stats["total_items_batched"] += len(items)
            
            if operation:
                self._stats["by_operation"][operation]["batches"] += len(batches)
                self._stats["by_operation"][operation]["items"] += len(items)
            
            logger.info(
                f"📦 Created {len(batches)} batches from {len(items)} items "
                f"(batch_size={batch_size}, operation={operation})"
            )
        
        return batches
    
    async def execute_batches(
        self,
        items: List[Any],
        process_func: callable,
        batch_size: int = None,
        max_concurrent: int = 3,
        operation: str = None,
        return_metrics: bool = False,
        timeout: float = 60.0,
        fallback_to_sequential: bool = True,
    ) -> Any:
        """
        Create batches and execute them in parallel with full metrics tracking.

        This is a convenience method that combines create_batches() with parallel execution.

        Args:
            items: List of items to batch and process
            process_func: Async function to process each batch
                         Should accept (batch, batch_index) and return result
                         Can optionally return (result, token_usage_dict) tuple
            batch_size: Items per batch (defaults to default_batch_size)
            max_concurrent: Max concurrent batch executions
            operation: Operation name for tracking
            return_metrics: If True, returns (results, ExecutionMetrics) tuple
            timeout: Timeout in seconds for the entire parallel execution (default: 60.0)
            fallback_to_sequential: If True, falls back to sequential execution on timeout (default: True)

        Returns:
            List of results (one per batch), or (results, ExecutionMetrics) if return_metrics=True

        Example:
            async def score_batch(batch, batch_num):
                results = []
                total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}
                for item in batch:
                    result = await score_item(item)
                    results.append(result)
                    total_tokens["prompt_tokens"] += result.prompt_tokens
                    total_tokens["completion_tokens"] += result.completion_tokens
                    total_tokens["cost"] += result.cost
                return results, total_tokens

            all_results, metrics = await batch_processor.execute_batches(
                items=jobs,
                process_func=score_batch,
                batch_size=3,
                max_concurrent=3,
                operation="quick_score_job",
                return_metrics=True,
                timeout=60.0,  # 60 second timeout
                fallback_to_sequential=True
            )
            print(f"Processed {len(jobs)} items in {metrics.total_elapsed_ms:.0f}ms")
            print(f"Time saved: {metrics.time_saved_ms:.0f}ms ({metrics.time_saved_ms/metrics.estimated_sequential_ms*100:.1f}%)")
            print(f"Total cost: ${metrics.total_cost:.4f}")
        """
        import asyncio

        if not self.enabled or not items:
            empty_metrics = ExecutionMetrics(
                total_tasks=0,
                successful_tasks=0,
                failed_tasks=0,
                total_elapsed_ms=0.0,
                estimated_sequential_ms=0.0,
                time_saved_ms=0.0,
            )
            return ([], empty_metrics) if return_metrics else []

        batch_size = batch_size or self.default_batch_size
        start_time = time.time()

        # Create batches
        batches = self.create_batches(items, batch_size=batch_size, operation=operation)

        # Track individual latencies and token usage
        individual_latencies = []
        task_token_usage = []
        successful_count = 0
        failed_count = 0

        # Create semaphore
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(batch, batch_num):
            """Execute with semaphore control and latency tracking."""
            nonlocal successful_count, failed_count

            async with semaphore:
                batch_start = time.time()

                try:
                    raw_result = await process_func(batch, batch_num)
                    duration_ms = (time.time() - batch_start) * 1000
                    individual_latencies.append(duration_ms)

                    # Check if result includes token usage info
                    result = raw_result
                    token_info = None

                    if isinstance(raw_result, tuple) and len(raw_result) == 2:
                        result, token_info = raw_result
                        if isinstance(token_info, dict):
                            task_token_usage.append({
                                "batch_num": batch_num,
                                "batch_size": len(batch),
                                "latency_ms": duration_ms,
                                **token_info,
                            })

                    successful_count += 1

                    logger.debug(
                        f"✅ Batch {batch_num + 1}/{len(batches)} complete: {duration_ms:.0f}ms "
                        f"({len(batch)} items)"
                    )

                    return result

                except Exception as e:
                    duration_ms = (time.time() - batch_start) * 1000
                    individual_latencies.append(duration_ms)
                    failed_count += 1
                    logger.error(f"❌ Batch {batch_num + 1} failed: {e}")
                    return None

        # Log start
        if self.track_batching:
            logger.info(
                f"📦⚡ Executing {len(batches)} batches ({len(items)} items, batch_size={batch_size}) "
                f"with max {max_concurrent} concurrent (operation={operation}, timeout={timeout}s)"
            )

        # Execute all batches in parallel with timeout
        tasks = [execute_with_semaphore(batch, i) for i, batch in enumerate(batches)]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"⏱️ Batch execution timed out after {timeout}s for {operation or 'unknown'}"
            )

            if fallback_to_sequential:
                logger.info(f"🔄 Falling back to sequential execution for {operation or 'unknown'}")
                results = await self._sequential_fallback(
                    batches, process_func, operation,
                    individual_latencies, task_token_usage
                )
                # Update counts from sequential execution
                successful_count = sum(1 for r in results if r is not None)
                failed_count = len(results) - successful_count
            else:
                # Return partial results (Nones for incomplete tasks)
                results = [None] * len(batches)
                failed_count = len(batches)

        total_elapsed_ms = (time.time() - start_time) * 1000

        # Calculate time savings correctly using individual latencies
        estimated_sequential_ms = sum(individual_latencies)
        time_saved_ms = estimated_sequential_ms - total_elapsed_ms

        # Aggregate token usage
        total_prompt_tokens = sum(t.get("prompt_tokens", 0) for t in task_token_usage)
        total_completion_tokens = sum(t.get("completion_tokens", 0) for t in task_token_usage)
        total_cost = sum(t.get("cost", 0.0) for t in task_token_usage)

        # Create execution metrics
        metrics = ExecutionMetrics(
            total_tasks=len(batches),
            successful_tasks=successful_count,
            failed_tasks=failed_count,
            total_elapsed_ms=total_elapsed_ms,
            estimated_sequential_ms=estimated_sequential_ms,
            time_saved_ms=time_saved_ms,
            individual_latencies_ms=individual_latencies,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_cost=total_cost,
            task_token_usage=task_token_usage,
        )

        # Update stats
        if self.track_batching:
            self._stats["total_time_saved_ms"] += time_saved_ms
            self._stats["total_prompt_tokens"] += total_prompt_tokens
            self._stats["total_completion_tokens"] += total_completion_tokens
            self._stats["total_cost"] += total_cost

            if operation:
                self._stats["by_operation"][operation]["time_saved_ms"] += time_saved_ms

            # Log completion with accurate metrics
            token_info_str = ""
            if total_prompt_tokens > 0 or total_completion_tokens > 0:
                token_info_str = f", tokens: {total_prompt_tokens}+{total_completion_tokens}"
            if total_cost > 0:
                token_info_str += f", cost: ${total_cost:.4f}"

            speedup_pct = (time_saved_ms / estimated_sequential_ms * 100) if estimated_sequential_ms > 0 else 0

            logger.info(
                f"📦⚡ Batch execution complete: {total_elapsed_ms:.0f}ms actual, "
                f"{estimated_sequential_ms:.0f}ms sequential estimate, "
                f"{time_saved_ms:.0f}ms saved ({speedup_pct:.1f}% faster)"
                f"{token_info_str}"
            )

        return (results, metrics) if return_metrics else results

    async def _sequential_fallback(
        self,
        batches: List[List[Any]],
        process_func: callable,
        operation: str,
        individual_latencies: List[float],
        task_token_usage: List[Dict],
    ) -> List[Any]:
        """
        Execute batches sequentially as a fallback when parallel execution times out.

        Args:
            batches: List of batches to process
            process_func: Async function to process each batch
            operation: Operation name for logging
            individual_latencies: List to append latencies to (shared with caller)
            task_token_usage: List to append token usage to (shared with caller)

        Returns:
            List of results (one per batch)
        """
        results = []

        for i, batch in enumerate(batches):
            batch_start = time.time()

            try:
                raw_result = await process_func(batch, i)
                duration_ms = (time.time() - batch_start) * 1000
                individual_latencies.append(duration_ms)

                # Check if result includes token usage info
                result = raw_result
                if isinstance(raw_result, tuple) and len(raw_result) == 2:
                    result, token_info = raw_result
                    if isinstance(token_info, dict):
                        task_token_usage.append({
                            "batch_num": i,
                            "batch_size": len(batch),
                            "latency_ms": duration_ms,
                            **token_info,
                        })

                results.append(result)
                logger.debug(
                    f"✅ Sequential batch {i + 1}/{len(batches)} complete: {duration_ms:.0f}ms "
                    f"({len(batch)} items)"
                )

            except Exception as e:
                duration_ms = (time.time() - batch_start) * 1000
                individual_latencies.append(duration_ms)
                results.append(None)
                logger.error(f"❌ Sequential batch {i + 1} failed: {e}")

        return results

    def track_batch_opportunity(
        self,
        operation: str,
        item_count: int,
        batch_size: int,
        estimated_savings: Dict[str, Any] = None,
    ):
        """
        Track that batching was applied.

        Creates optimization story showing batching was used.
        """
        if not self.observatory or not hasattr(self.observatory, 'storage'):
            return

        import math
        batch_count = math.ceil(item_count / batch_size)

        try:
            self.observatory.storage.create_optimization_story(
                opportunity_type="batch_applied",
                operation=operation,
                agent_name=None,
                call_ids=[],
                potential_savings_ms=None,
                recommendation=f"Batching applied: {item_count} items → {batch_count} batches (size={batch_size})",
                metadata={
                    "item_count": item_count,
                    "batch_count": batch_count,
                    "batch_size": batch_size,
                    "estimated_savings": estimated_savings or {},
                },
            )
        except Exception as e:
            logger.warning(f"Failed to create batch application story: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batching statistics."""
        return {
            "enabled": self.enabled,
            "default_batch_size": self.default_batch_size,
            "batches_created": self._stats["batches_created"],
            "total_items_batched": self._stats["total_items_batched"],
            "total_time_saved_ms": self._stats["total_time_saved_ms"],
            "total_prompt_tokens": self._stats["total_prompt_tokens"],
            "total_completion_tokens": self._stats["total_completion_tokens"],
            "total_cost": self._stats["total_cost"],
            "by_operation": dict(self._stats["by_operation"]),
        }


# =============================================================================
# PARALLEL EXECUTOR - UNIVERSAL PARALLEL EXECUTION
# =============================================================================

class ParallelExecutor:
    """
    Universal parallel execution with concurrency control.
    
    Unlike ParallelDetector (which only detects opportunities),
    this actually executes tasks in parallel with semaphores.
    
    Usage:
        results = await executor.execute(
            batches=batches,
            process_func=your_async_function,
            max_concurrent=3
        )
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        default_max_concurrent: int = 3,
        semaphore_type: str = 'count',
        track_parallelism: bool = True,
        enabled: bool = True,
    ):
        self.observatory = observatory
        self.default_max_concurrent = default_max_concurrent
        self.semaphore_type = semaphore_type
        self.track_parallelism = track_parallelism
        self.enabled = enabled
        
        # Statistics
        self._stats = {
            "executions": 0,
            "total_tasks": 0,
            "total_time_saved_ms": 0.0,
            "by_operation": defaultdict(lambda: {"executions": 0, "tasks": 0}),
        }
    
    async def execute(
        self,
        batches: List[Any],
        process_func: callable,
        max_concurrent: int = None,
        operation: str = None,
        return_metrics: bool = False,
        timeout: float = 60.0,
        fallback_to_sequential: bool = True,
    ) -> Any:
        """
        Execute batches in parallel with concurrency control.

        Args:
            batches: List of batches to process
            process_func: Async function to process each batch
                         Should accept (batch, batch_index) and return result
                         Can optionally return (result, token_usage_dict) tuple
                         where token_usage_dict = {"prompt_tokens": int, "completion_tokens": int, "cost": float}
            max_concurrent: Max concurrent tasks (defaults to default_max_concurrent)
            operation: Operation name for tracking
            return_metrics: If True, returns (results, ExecutionMetrics) tuple
            timeout: Timeout in seconds for the entire parallel execution (default: 60.0)
            fallback_to_sequential: If True, falls back to sequential execution on timeout (default: True)

        Returns:
            List of results (one per batch), or (results, ExecutionMetrics) if return_metrics=True

        Example:
            async def score_batch(batch, batch_num):
                result = await score_jobs(batch)
                # Optionally return token usage for tracking
                return result, {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.001}

            results, metrics = await executor.execute(
                batches=job_batches,
                process_func=score_batch,
                max_concurrent=3,
                operation="quick_score_job",
                return_metrics=True,
                timeout=60.0,  # 60 second timeout
                fallback_to_sequential=True
            )
            print(f"Time saved: {metrics.time_saved_ms}ms")
            print(f"Total cost: ${metrics.total_cost:.4f}")
        """
        if not self.enabled or not batches:
            empty_metrics = ExecutionMetrics(
                total_tasks=0,
                successful_tasks=0,
                failed_tasks=0,
                total_elapsed_ms=0.0,
                estimated_sequential_ms=0.0,
                time_saved_ms=0.0,
            )
            return ([], empty_metrics) if return_metrics else []

        import asyncio

        max_concurrent = max_concurrent or self.default_max_concurrent
        start_time = time.time()

        # Track individual task latencies for accurate time savings calculation
        individual_latencies = []
        task_token_usage = []
        successful_count = 0
        failed_count = 0

        # Create semaphore
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(batch, batch_num):
            """Execute with semaphore control and latency tracking."""
            nonlocal successful_count, failed_count

            async with semaphore:
                batch_start = time.time()

                try:
                    raw_result = await process_func(batch, batch_num)
                    duration_ms = (time.time() - batch_start) * 1000
                    individual_latencies.append(duration_ms)

                    # Check if result includes token usage info
                    result = raw_result
                    token_info = None

                    if isinstance(raw_result, tuple) and len(raw_result) == 2:
                        result, token_info = raw_result
                        if isinstance(token_info, dict):
                            task_token_usage.append({
                                "batch_num": batch_num,
                                "latency_ms": duration_ms,
                                **token_info,
                            })

                    successful_count += 1

                    logger.debug(
                        f"✅ Batch {batch_num + 1}/{len(batches)} complete: {duration_ms:.0f}ms"
                    )

                    return result

                except Exception as e:
                    duration_ms = (time.time() - batch_start) * 1000
                    individual_latencies.append(duration_ms)
                    failed_count += 1
                    logger.error(f"❌ Batch {batch_num + 1} failed: {e}")
                    return None

        # Execute all batches in parallel with timeout
        if self.track_parallelism:
            logger.info(
                f"⚡ Executing {len(batches)} batches with max {max_concurrent} concurrent "
                f"(operation={operation}, timeout={timeout}s)"
            )

        tasks = [execute_with_semaphore(batch, i) for i, batch in enumerate(batches)]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"⏱️ Parallel execution timed out after {timeout}s for {operation or 'unknown'}"
            )

            if fallback_to_sequential:
                logger.info(f"🔄 Falling back to sequential execution for {operation or 'unknown'}")
                results = await self._sequential_fallback(
                    batches, process_func, operation,
                    individual_latencies, task_token_usage
                )
                # Update counts from sequential execution
                successful_count = sum(1 for r in results if r is not None)
                failed_count = len(results) - successful_count
            else:
                # Return partial results (Nones for incomplete tasks)
                results = [None] * len(batches)
                failed_count = len(batches)

        total_elapsed_ms = (time.time() - start_time) * 1000

        # Calculate time savings correctly using individual latencies
        # Sequential time = sum of all individual task durations
        # Parallel time = actual wall-clock time
        estimated_sequential_ms = sum(individual_latencies)
        time_saved_ms = estimated_sequential_ms - total_elapsed_ms

        # Aggregate token usage
        total_prompt_tokens = sum(t.get("prompt_tokens", 0) for t in task_token_usage)
        total_completion_tokens = sum(t.get("completion_tokens", 0) for t in task_token_usage)
        total_cost = sum(t.get("cost", 0.0) for t in task_token_usage)

        # Create execution metrics
        metrics = ExecutionMetrics(
            total_tasks=len(batches),
            successful_tasks=successful_count,
            failed_tasks=failed_count,
            total_elapsed_ms=total_elapsed_ms,
            estimated_sequential_ms=estimated_sequential_ms,
            time_saved_ms=time_saved_ms,
            individual_latencies_ms=individual_latencies,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_cost=total_cost,
            task_token_usage=task_token_usage,
        )

        # Track execution
        if self.track_parallelism:
            self._stats["executions"] += 1
            self._stats["total_tasks"] += len(batches)
            self._stats["total_time_saved_ms"] += time_saved_ms

            if operation:
                self._stats["by_operation"][operation]["executions"] += 1
                self._stats["by_operation"][operation]["tasks"] += len(batches)

            # Log with accurate time savings
            token_info_str = ""
            if total_prompt_tokens > 0 or total_completion_tokens > 0:
                token_info_str = f", tokens: {total_prompt_tokens}+{total_completion_tokens}"
            if total_cost > 0:
                token_info_str += f", cost: ${total_cost:.4f}"

            logger.info(
                f"⚡ Parallel execution complete: {total_elapsed_ms:.0f}ms actual, "
                f"{estimated_sequential_ms:.0f}ms sequential estimate, "
                f"{time_saved_ms:.0f}ms saved ({time_saved_ms/estimated_sequential_ms*100:.1f}% faster)"
                f"{token_info_str}"
            )

        return (results, metrics) if return_metrics else results
    
    async def _sequential_fallback(
        self,
        batches: List[Any],
        process_func: callable,
        operation: str,
        individual_latencies: List[float],
        task_token_usage: List[Dict],
    ) -> List[Any]:
        """
        Execute batches sequentially as a fallback when parallel execution times out.

        Args:
            batches: List of batches to process
            process_func: Async function to process each batch
            operation: Operation name for logging
            individual_latencies: List to append latencies to (shared with caller)
            task_token_usage: List to append token usage to (shared with caller)

        Returns:
            List of results (one per batch)
        """
        results = []

        for i, batch in enumerate(batches):
            batch_start = time.time()

            try:
                raw_result = await process_func(batch, i)
                duration_ms = (time.time() - batch_start) * 1000
                individual_latencies.append(duration_ms)

                # Check if result includes token usage info
                result = raw_result
                if isinstance(raw_result, tuple) and len(raw_result) == 2:
                    result, token_info = raw_result
                    if isinstance(token_info, dict):
                        task_token_usage.append({
                            "batch_num": i,
                            "latency_ms": duration_ms,
                            **token_info,
                        })

                results.append(result)
                logger.debug(
                    f"✅ Sequential batch {i + 1}/{len(batches)} complete: {duration_ms:.0f}ms"
                )

            except Exception as e:
                duration_ms = (time.time() - batch_start) * 1000
                individual_latencies.append(duration_ms)
                results.append(None)
                logger.error(f"❌ Sequential batch {i + 1} failed: {e}")

        return results

    def track_parallel_opportunity(
        self,
        operation: str,
        batch_count: int,
        concurrency: int,
        time_saved: float,
    ):
        """
        Track that parallel execution was applied.
        
        Creates optimization story showing parallelism was used.
        """
        if not self.observatory or not hasattr(self.observatory, 'storage'):
            return
        
        try:
            self.observatory.storage.create_optimization_story(
                opportunity_type="parallel_applied",
                operation=operation,
                agent_name=None,
                call_ids=[],
                potential_savings_ms=time_saved,
                recommendation=f"Parallelism applied: {batch_count} batches with {concurrency} concurrent workers (saved {time_saved:.0f}ms)",
                metadata={
                    "batch_count": batch_count,
                    "concurrency": concurrency,
                    "time_saved_ms": time_saved,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to create parallel application story: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parallel execution statistics."""
        return {
            "enabled": self.enabled,
            "default_max_concurrent": self.default_max_concurrent,
            "semaphore_type": self.semaphore_type,
            "executions": self._stats["executions"],
            "total_tasks": self._stats["total_tasks"],
            "total_time_saved_ms": self._stats["total_time_saved_ms"],
            "by_operation": dict(self._stats["by_operation"]),
        }