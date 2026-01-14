"""
Execution Optimization - Batching, Parallelism, and Streaming Detection
Location: observatory/execution.py

Detects and tracks opportunities for execution optimizations:
- BatchDetector: Identifies sequential calls that could be batched
- ParallelDetector: Identifies independent calls that could run in parallel
- StreamingDetector: Flags calls that would benefit from streaming

Each detector supports detection_only mode for baseline analysis.
"""

import logging
import time
from typing import Optional, Dict, List, Any, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

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
class StreamingCandidate:
    """Call that would benefit from streaming."""
    operation: str
    latency_ms: float
    completion_tokens: int
    reason: str  # "high_latency" or "large_output"
    call_id: Optional[str] = None


# =============================================================================
# BATCH DETECTOR
# =============================================================================

class BatchDetector:
    """
    Detects sequential calls that could be batched together.
    
    BASELINE MODE (detection_only=True):
        - Tracks rapid sequential calls to same operation
        - Logs batching opportunities
        - Calculates potential latency savings
        - Does NOT actually batch calls
    
    OPTIMIZED MODE (detection_only=False):
        - Same detection
        - Application code can use opportunities to batch calls
    
    Usage:
        detector = BatchDetector(
            observatory=obs,
            time_window_ms=100,  # Group calls within 100ms
            min_batch_size=2,    # At least 2 calls to be a batch
            detection_only=True, # Baseline mode
        )
        
        # Track each call
        detector.track_call(
            operation="quick_score_job",
            call_id="call_123",
            timestamp=time.time()
        )
        
        # Check for opportunities
        opportunities = detector.get_opportunities()
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
        """
        Initialize BatchDetector.
        
        Args:
            observatory: Observatory instance
            time_window_ms: Time window for grouping calls (milliseconds)
            min_batch_size: Minimum calls to qualify as batch
            operations: Set of operations to monitor (None = all)
            enabled: Whether detection is active
            detection_only: If True, only detect (don't apply batching)
        """
        self.observatory = observatory
        self.time_window_ms = time_window_ms
        self.min_batch_size = min_batch_size
        self.operations = operations
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Track recent calls: operation -> [(timestamp, call_id), ...]
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
    ):
        """
        Track a call for batch detection.
        
        Args:
            operation: Operation name
            call_id: Unique call identifier
            timestamp: Call timestamp (defaults to now)
            latency_ms: Call latency for savings calculation
        """
        if not self.is_monitored(operation):
            return
        
        timestamp = timestamp or time.time()
        
        # Add to recent calls
        self._recent_calls[operation].append((timestamp, call_id, latency_ms))
        
        # Clean old calls (outside time window)
        cutoff = timestamp - (self.time_window_ms / 1000)
        self._recent_calls[operation] = [
            (ts, cid, lat) for ts, cid, lat in self._recent_calls[operation]
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
        """Detect and log batch opportunity."""
        if len(calls) < self.min_batch_size:
            return
        
        call_ids = [cid for _, cid, _ in calls if cid]
        latencies = [lat for _, _, lat in calls if lat]
        
        # Calculate potential savings
        # Batching reduces N sequential calls to 1 batch call
        # Savings = (N - 1) * avg_latency
        avg_latency = sum(latencies) / len(latencies) if latencies else 500
        potential_saved = (len(calls) - 1) * avg_latency
        
        # Time window span
        timestamps = [ts for ts, _, _ in calls]
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
        - Identifies independent operations
        - Calculates potential parallel speedup
        - Does NOT actually parallelize calls
    
    OPTIMIZED MODE (detection_only=False):
        - Same detection
        - Application code can use opportunities to parallelize
    
    Usage:
        detector = ParallelDetector(
            observatory=obs,
            time_window_s=5,     # Look for parallelism within 5s
            min_parallel_count=2, # At least 2 calls to parallelize
            detection_only=True,
        )
        
        # Start tracking a sequence
        seq_id = detector.start_sequence()
        
        # Track each call
        detector.track_call(
            sequence_id=seq_id,
            operation="score_job",
            call_id="call_1",
            latency_ms=500,
            depends_on=None,  # No dependencies
        )
        
        detector.track_call(
            sequence_id=seq_id,
            operation="score_job",
            call_id="call_2",
            latency_ms=600,
            depends_on=None,  # Independent!
        )
        
        # End sequence and check opportunities
        opportunity = detector.end_sequence(seq_id)
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        time_window_s: float = 5.0,
        min_parallel_count: int = 2,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        """
        Initialize ParallelDetector.
        
        Args:
            observatory: Observatory instance
            time_window_s: Time window for detecting parallelism (seconds)
            min_parallel_count: Minimum calls to qualify as parallel opportunity
            enabled: Whether detection is active
            detection_only: If True, only detect (don't apply parallelism)
        """
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
    ):
        """
        Track a call in a sequence.
        
        Args:
            sequence_id: Sequence identifier
            operation: Operation name
            call_id: Call identifier
            latency_ms: Call latency
            depends_on: List of call_ids this call depends on
        """
        if not self.enabled or sequence_id not in self._sequences:
            return
        
        self._sequences[sequence_id].append({
            "operation": operation,
            "call_id": call_id,
            "latency_ms": latency_ms or 500,
            "depends_on": depends_on or [],
            "timestamp": time.time(),
        })
    
    def end_sequence(self, sequence_id: str) -> Optional[ParallelOpportunity]:
        """
        End sequence and analyze for parallelism.
        
        Returns:
            ParallelOpportunity if detected, None otherwise
        """
        if not self.enabled or sequence_id not in self._sequences:
            return None
        
        calls = self._sequences.pop(sequence_id)
        
        if len(calls) < self.min_parallel_count:
            return None
        
        # Find independent calls (no dependencies on each other)
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
        
        return opportunity
    
    def _find_independent_calls(self, calls: List[Dict]) -> List[Dict]:
        """Find calls with no dependencies on each other."""
        independent = []
        
        for call in calls:
            # Check if this call depends on any other call in the list
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
# STREAMING DETECTOR
# =============================================================================

class StreamingDetector:
    """
    Detects calls that would benefit from streaming.
    
    BASELINE MODE (detection_only=True):
        - Flags high-latency calls (>2s)
        - Flags large-output calls (>500 tokens)
        - Logs streaming candidates
        - Does NOT actually use streaming
    
    OPTIMIZED MODE (detection_only=False):
        - Same detection
        - Application code can use streaming API for flagged operations
    
    Criteria for streaming:
        - High latency: Response time > latency_threshold_ms
        - Large output: Completion tokens > token_threshold
    
    Usage:
        detector = StreamingDetector(
            observatory=obs,
            latency_threshold_ms=2000,
            token_threshold=500,
            detection_only=True,
        )
        
        # Check if call should use streaming
        candidate = detector.check_call(
            operation="deep_analyze_job",
            latency_ms=3500,
            completion_tokens=800,
        )
        
        if candidate:
            # This call would benefit from streaming!
            pass
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
        """
        Initialize StreamingDetector.
        
        Args:
            observatory: Observatory instance
            latency_threshold_ms: Latency threshold for streaming (milliseconds)
            token_threshold: Token count threshold for streaming
            operations: Set of operations to monitor (None = all)
            enabled: Whether detection is active
            detection_only: If True, only detect (don't apply streaming)
        """
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
    ) -> Optional[StreamingCandidate]:
        """
        Check if call is a streaming candidate.
        
        Args:
            operation: Operation name
            latency_ms: Call latency
            completion_tokens: Output token count
            call_id: Call identifier
        
        Returns:
            StreamingCandidate if criteria met, None otherwise
        """
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