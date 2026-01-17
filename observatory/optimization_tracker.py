# observatory/optimization_tracker.py
"""
Optimization Tracker - Measure Optimization Impact by Phase
Location: observatory/optimization_tracker.py

Tracks optimization impact by comparing baseline vs optimized phases.
Aggregates all LLM calls tagged with phase='baseline' vs phase='optimized'.

Usage:
    from observatory import Observatory, OptimizationTracker
    
    obs = Observatory(project_name="My App")
    tracker = OptimizationTracker(observatory=obs)
    
    # Run app in baseline mode (data auto-tagged with phase='baseline')
    # OBSERVATORY_PHASE=baseline python app.py
    
    # Run app in optimized mode (data auto-tagged with phase='optimized')
    # OBSERVATORY_PHASE=optimized python app.py
    
    # Compare phases automatically
    comparison = tracker.compare_phases()
    print(comparison['comparison']['improvement_summary'])
    
    # Generate comparison table
    table = tracker.generate_comparison_table(comparison)
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OptimizationTracker:
    """
    Tracks optimization impact by comparing baseline vs optimized phases.
    
    Automatically aggregates metrics based on phase tag in metadata,
    eliminating need for manual snapshot capture.
    """
    
    def __init__(
        self,
        observatory=None,
        db_path: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize OptimizationTracker.
        
        Args:
            observatory: Observatory instance (preferred)
            db_path: Direct database path (fallback)
            enabled: Enable/disable optimization tracking
        """
        self.enabled = enabled
        
        if not self.enabled:
            logger.info("OptimizationTracker disabled")
            return
        
        # Get database path from Observatory or direct
        if observatory:
            self.storage = observatory.collector.storage
            self.db_path = self.storage.engine.url.database
        elif db_path:
            from observatory.storage import Storage
            self.storage = Storage(f"sqlite:///{db_path}")
            self.db_path = db_path
        else:
            raise ValueError("Must provide either observatory instance or db_path")
        
        # In-memory baseline storage (for manual snapshots if needed)
        self.baselines: Dict[str, Dict] = {}
        
        logger.info(f"✅ OptimizationTracker initialized (db: {self.db_path})")
    
    # =========================================================================
    # PHASE-AWARE METHODS (NEW)
    # =========================================================================
    
    def get_phase_aggregate(
        self,
        phase: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregate metrics for all calls in a specific phase.
        
        Queries all LLM calls with metadata['phase'] == phase and aggregates.
        
        Args:
            phase: 'baseline' or 'optimized'
            start_date: Optional start (YYYY-MM-DD)
            end_date: Optional end (YYYY-MM-DD)
        
        Returns:
            Aggregated metrics dict
        """
        # Parse dates if provided
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        
        # Query all calls in date range
        calls = self.storage.get_llm_calls(
            start_time=start_dt,
            end_time=end_dt,
            limit=100000,
        )
        
        # Filter by phase in metadata
        phase_calls = [
            c for c in calls 
            if c.metadata.get('phase') == phase
        ]
        
        if not phase_calls:
            logger.warning(f"⚠️ No calls found for phase '{phase}'")
            return {
                'phase': phase,
                'total_calls': 0,
                'start_date': start_date,
                'end_date': end_date,
            }
        
        logger.info(f"📊 Found {len(phase_calls)} calls for phase '{phase}'")
        
        # Aggregate metrics
        metrics = self._aggregate_metrics(phase_calls)
        metrics['phase'] = phase
        metrics['start_date'] = start_date
        metrics['end_date'] = end_date
        
        return metrics
    
    def compare_phases(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare baseline phase vs optimized phase automatically.
        
        Aggregates ALL calls with phase='baseline' vs phase='optimized'
        in the specified date range (or all time if no dates provided).
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
        
        Returns:
            Comparison dict with baseline vs optimized
        """
        logger.info("📊 Comparing phases: baseline vs optimized")
        
        # Get baseline aggregate
        baseline = self.get_phase_aggregate('baseline', start_date, end_date)
        
        # Get optimized aggregate
        optimized = self.get_phase_aggregate('optimized', start_date, end_date)
        
        if baseline['total_calls'] == 0:
            return {
                'error': 'No baseline data found. Run with OBSERVATORY_PHASE=baseline first.',
                'baseline': baseline,
                'optimized': optimized,
            }
        
        if optimized['total_calls'] == 0:
            return {
                'error': 'No optimized data found. Run with OBSERVATORY_PHASE=optimized first.',
                'baseline': baseline,
                'optimized': optimized,
            }
        
        # Calculate comparison
        comparison = self._calculate_comparison(baseline, optimized)
        
        result = {
            'baseline': baseline,
            'optimized': optimized,
            'comparison': comparison,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
        logger.info(f"✅ Comparison complete: {comparison['improvement_summary']}")
        
        return result
    
    # =========================================================================
    # MANUAL SNAPSHOT METHODS (OPTIONAL - for date-based comparison)
    # =========================================================================
    
    def capture_baseline(
        self,
        baseline_id: str,
        start_date: str,
        end_date: str,
        description: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Capture a manual baseline snapshot for a date range.
        
        Optional method for date-based comparisons (vs phase-based).
        
        Args:
            baseline_id: Unique identifier (e.g., 'pre_optimization_v1')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            description: Human-readable description
            filters: Optional filters (project_name, operation, agent_name, etc.)
        
        Returns:
            Dict with baseline metrics
        """
        if not self.enabled:
            return {}
        
        logger.info(f"📸 Capturing baseline '{baseline_id}' ({start_date} to {end_date})")
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include end date
        
        # Query calls in date range
        calls = self.storage.get_llm_calls(
            start_time=start_dt,
            end_time=end_dt,
            limit=100000,  # High limit to get all calls
            **(filters or {})
        )
        
        if not calls:
            logger.warning(f"⚠️ No calls found for baseline '{baseline_id}'")
            return {
                'baseline_id': baseline_id,
                'start_date': start_date,
                'end_date': end_date,
                'description': description,
                'captured_at': datetime.utcnow().isoformat(),
                'total_calls': 0,
                'error': 'No calls found in date range'
            }
        
        # Aggregate metrics
        baseline = self._aggregate_metrics(calls)
        
        # Add metadata
        baseline.update({
            'baseline_id': baseline_id,
            'start_date': start_date,
            'end_date': end_date,
            'description': description,
            'captured_at': datetime.utcnow().isoformat(),
            'filters': filters or {},
        })
        
        # Store in memory
        self.baselines[baseline_id] = baseline
        
        logger.info(f"✅ Baseline captured: {baseline['total_calls']} calls, ${baseline['total_cost']:.4f}")
        
        return baseline
    
    def compare(
        self,
        baseline_id: str,
        current_start: str,
        current_end: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compare current period to a manual baseline snapshot.
        
        Optional method for date-based comparisons (vs phase-based).
        
        Args:
            baseline_id: Baseline to compare against
            current_start: Current period start (YYYY-MM-DD)
            current_end: Current period end (YYYY-MM-DD)
            filters: Optional filters (must match baseline filters)
        
        Returns:
            Dict with comparison metrics
        """
        if not self.enabled:
            return {}
        
        # Load baseline
        baseline = self.baselines.get(baseline_id)
        if not baseline:
            raise ValueError(f"Baseline '{baseline_id}' not found. Call capture_baseline() first.")
        
        logger.info(f"📊 Comparing to baseline '{baseline_id}' ({current_start} to {current_end})")
        
        # Parse dates
        start_dt = datetime.strptime(current_start, '%Y-%m-%d')
        end_dt = datetime.strptime(current_end, '%Y-%m-%d') + timedelta(days=1)
        
        # Query current calls
        calls = self.storage.get_llm_calls(
            start_time=start_dt,
            end_time=end_dt,
            limit=100000,
            **(filters or {})
        )
        
        if not calls:
            logger.warning(f"⚠️ No calls found for current period")
            return {
                'baseline': baseline,
                'current': {'total_calls': 0},
                'comparison': {},
                'error': 'No calls in current period'
            }
        
        # Aggregate current metrics
        current = self._aggregate_metrics(calls)
        current.update({
            'start_date': current_start,
            'end_date': current_end,
            'captured_at': datetime.utcnow().isoformat(),
        })
        
        # Calculate comparison
        comparison = self._calculate_comparison(baseline, current)
        
        result = {
            'baseline_id': baseline_id,
            'baseline': baseline,
            'current': current,
            'comparison': comparison,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
        logger.info(f"✅ Comparison complete: {comparison['improvement_summary']}")
        
        return result
    
    # =========================================================================
    # HELPER: AGGREGATE METRICS
    # =========================================================================
    
    def _aggregate_metrics(self, calls: List[Any]) -> Dict[str, Any]:
        """
        Aggregate metrics from a list of LLM calls.
        
        Returns comprehensive metrics dict.
        """
        if not calls:
            return {}
        
        # Basic aggregates
        total_calls = len(calls)
        total_cost = sum(c.total_cost for c in calls)
        total_tokens = sum(c.total_tokens for c in calls)
        total_latency = sum(c.latency_ms for c in calls)
        
        # Token breakdown
        system_prompt_tokens = sum(c.system_prompt_tokens or 0 for c in calls)
        user_message_tokens = sum(c.user_message_tokens or 0 for c in calls)
        chat_history_tokens = sum(c.chat_history_tokens or 0 for c in calls)
        
        # Cache metrics
        cache_hits = sum(1 for c in calls if c.cache_metadata and c.cache_metadata.cache_hit)
        cache_misses = total_calls - cache_hits
        cache_hit_rate = cache_hits / total_calls if total_calls > 0 else 0.0
        
        # Quality metrics
        quality_scores = [
            c.quality_evaluation.judge_score
            for c in calls
            if c.quality_evaluation and c.quality_evaluation.judge_score is not None
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        # Routing metrics
        routing_decisions = sum(1 for c in calls if c.routing_decision)
        
        # Error metrics
        errors = sum(1 for c in calls if not c.success)
        error_rate = errors / total_calls if total_calls > 0 else 0.0
        
        # Per-operation breakdown
        operations = {}
        for call in calls:
            op = call.operation or 'unknown'
            if op not in operations:
                operations[op] = {
                    'count': 0,
                    'cost': 0.0,
                    'tokens': 0,
                    'latency': 0.0,
                    'cache_hits': 0,
                }
            
            operations[op]['count'] += 1
            operations[op]['cost'] += call.total_cost
            operations[op]['tokens'] += call.total_tokens
            operations[op]['latency'] += call.latency_ms
            
            if call.cache_metadata and call.cache_metadata.cache_hit:
                operations[op]['cache_hits'] += 1
        
        # Calculate averages per operation
        for op, metrics in operations.items():
            count = metrics['count']
            metrics['avg_cost'] = metrics['cost'] / count
            metrics['avg_tokens'] = metrics['tokens'] / count
            metrics['avg_latency'] = metrics['latency'] / count
            metrics['cache_hit_rate'] = metrics['cache_hits'] / count if count > 0 else 0.0
        
        # Per-agent breakdown
        agents = {}
        for call in calls:
            agent = call.agent_name or 'unknown'
            if agent not in agents:
                agents[agent] = {
                    'count': 0,
                    'cost': 0.0,
                    'tokens': 0,
                    'latency': 0.0,
                }
            
            agents[agent]['count'] += 1
            agents[agent]['cost'] += call.total_cost
            agents[agent]['tokens'] += call.total_tokens
            agents[agent]['latency'] += call.latency_ms
        
        return {
            # Totals
            'total_calls': total_calls,
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'total_latency_ms': total_latency,
            
            # Averages
            'avg_cost_per_call': total_cost / total_calls,
            'avg_tokens_per_call': total_tokens / total_calls,
            'avg_latency_ms': total_latency / total_calls,
            
            # Token breakdown
            'system_prompt_tokens': system_prompt_tokens,
            'user_message_tokens': user_message_tokens,
            'chat_history_tokens': chat_history_tokens,
            'system_prompt_pct': system_prompt_tokens / total_tokens if total_tokens > 0 else 0,
            'user_message_pct': user_message_tokens / total_tokens if total_tokens > 0 else 0,
            'chat_history_pct': chat_history_tokens / total_tokens if total_tokens > 0 else 0,
            
            # Cache metrics
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': cache_hit_rate,
            
            # Quality metrics
            'avg_quality_score': avg_quality,
            'quality_evaluated_calls': len(quality_scores),
            
            # Routing metrics
            'routing_decisions': routing_decisions,
            
            # Error metrics
            'errors': errors,
            'error_rate': error_rate,
            
            # Breakdowns
            'by_operation': operations,
            'by_agent': agents,
        }
    
    # =========================================================================
    # HELPER: CALCULATE COMPARISON
    # =========================================================================
    
    def _calculate_comparison(
        self,
        baseline: Dict[str, Any],
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate improvement metrics between baseline and current.
        
        Returns comparison dict with improvements/regressions.
        """
        def calc_improvement(baseline_val, current_val, lower_is_better=True) -> Tuple[float, float, str]:
            """Calculate improvement (handles direction)"""
            if baseline_val == 0:
                return (0.0, 0.0, 'neutral')
            
            absolute_change = baseline_val - current_val  # Reversed for improvement
            pct_change = (absolute_change / baseline_val) * 100
            
            if not lower_is_better:
                absolute_change = -absolute_change
                pct_change = -pct_change
            
            if pct_change > 0:
                direction = 'improved'
            elif pct_change < 0:
                direction = 'regressed'
            else:
                direction = 'neutral'
            
            return (absolute_change, pct_change, direction)
        
        # Cost comparison (lower is better)
        cost_change, cost_pct, cost_direction = calc_improvement(
            baseline.get('total_cost', 0),
            current.get('total_cost', 0),
            lower_is_better=True
        )
        
        # Latency comparison (lower is better)
        latency_change, latency_pct, latency_direction = calc_improvement(
            baseline.get('avg_latency_ms', 0),
            current.get('avg_latency_ms', 0),
            lower_is_better=True
        )
        
        # Token comparison (lower is better)
        token_change, token_pct, token_direction = calc_improvement(
            baseline.get('avg_tokens_per_call', 0),
            current.get('avg_tokens_per_call', 0),
            lower_is_better=True
        )
        
        # Cache hit rate comparison (higher is better)
        cache_change, cache_pct, cache_direction = calc_improvement(
            baseline.get('cache_hit_rate', 0),
            current.get('cache_hit_rate', 0),
            lower_is_better=False
        )
        
        # Quality comparison (higher is better)
        quality_change, quality_pct, quality_direction = calc_improvement(
            baseline.get('avg_quality_score') or 0,
            current.get('avg_quality_score') or 0,
            lower_is_better=False
        )
        
        # Overall improvement score (weighted)
        improvements = []
        regressions = []
        
        if cost_direction == 'improved':
            improvements.append(f"Cost: {abs(cost_pct):.1f}%")
        elif cost_direction == 'regressed':
            regressions.append(f"Cost: +{abs(cost_pct):.1f}%")
        
        if latency_direction == 'improved':
            improvements.append(f"Latency: {abs(latency_pct):.1f}%")
        elif latency_direction == 'regressed':
            regressions.append(f"Latency: +{abs(latency_pct):.1f}%")
        
        if token_direction == 'improved':
            improvements.append(f"Tokens: {abs(token_pct):.1f}%")
        elif token_direction == 'regressed':
            regressions.append(f"Tokens: +{abs(token_pct):.1f}%")
        
        if cache_direction == 'improved':
            improvements.append(f"Cache: +{abs(cache_pct):.1f}%")
        elif cache_direction == 'regressed':
            regressions.append(f"Cache: {abs(cache_pct):.1f}%")
        
        # Summary
        if improvements and not regressions:
            improvement_summary = f"✅ Improved: {', '.join(improvements)}"
        elif regressions and not improvements:
            improvement_summary = f"⚠️ Regressed: {', '.join(regressions)}"
        elif improvements and regressions:
            improvement_summary = f"📊 Mixed: {', '.join(improvements)} | {', '.join(regressions)}"
        else:
            improvement_summary = "➡️ No significant change"
        
        return {
            'cost': {
                'baseline': baseline.get('total_cost', 0),
                'current': current.get('total_cost', 0),
                'absolute_change': cost_change,
                'pct_change': cost_pct,
                'direction': cost_direction,
            },
            'latency': {
                'baseline': baseline.get('avg_latency_ms', 0),
                'current': current.get('avg_latency_ms', 0),
                'absolute_change': latency_change,
                'pct_change': latency_pct,
                'direction': latency_direction,
            },
            'tokens': {
                'baseline': baseline.get('avg_tokens_per_call', 0),
                'current': current.get('avg_tokens_per_call', 0),
                'absolute_change': token_change,
                'pct_change': token_pct,
                'direction': token_direction,
            },
            'cache_hit_rate': {
                'baseline': baseline.get('cache_hit_rate', 0),
                'current': current.get('cache_hit_rate', 0),
                'absolute_change': cache_change,
                'pct_change': cache_pct,
                'direction': cache_direction,
            },
            'quality': {
                'baseline': baseline.get('avg_quality_score'),
                'current': current.get('avg_quality_score'),
                'absolute_change': quality_change,
                'pct_change': quality_pct,
                'direction': quality_direction,
            },
            'call_count': {
                'baseline': baseline.get('total_calls', 0),
                'current': current.get('total_calls', 0),
            },
            'improvement_summary': improvement_summary,
        }
    
    # =========================================================================
    # UTILITIES: SAVE/LOAD BASELINES
    # =========================================================================
    
    def save_baseline(
        self,
        baseline_id: str,
        filepath: Optional[str] = None,
    ) -> str:
        """
        Save a baseline to disk as JSON.
        
        Args:
            baseline_id: Baseline to save
            filepath: Path to save to (default: baselines/{baseline_id}.json)
        
        Returns:
            Path where baseline was saved
        """
        if not self.enabled:
            return ""
        
        baseline = self.baselines.get(baseline_id)
        if not baseline:
            raise ValueError(f"Baseline '{baseline_id}' not found")
        
        # Default path
        if not filepath:
            baselines_dir = Path('baselines')
            baselines_dir.mkdir(exist_ok=True)
            filepath = baselines_dir / f"{baseline_id}.json"
        
        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(baseline, f, indent=2, default=str)
        
        logger.info(f"💾 Baseline saved: {filepath}")
        
        return str(filepath)
    
    def load_baseline(
        self,
        baseline_id: str,
        filepath: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load a baseline from disk.
        
        Args:
            baseline_id: Baseline ID
            filepath: Path to load from (default: baselines/{baseline_id}.json)
        
        Returns:
            Baseline dict
        """
        if not self.enabled:
            return {}
        
        # Default path
        if not filepath:
            filepath = Path('baselines') / f"{baseline_id}.json"
        
        if not Path(filepath).exists():
            raise FileNotFoundError(f"Baseline file not found: {filepath}")
        
        # Load from JSON
        with open(filepath, 'r') as f:
            baseline = json.load(f)
        
        # Store in memory
        self.baselines[baseline_id] = baseline
        
        logger.info(f"📂 Baseline loaded: {filepath}")
        
        return baseline
    
    def list_baselines(self) -> List[str]:
        """List all loaded baseline IDs."""
        return list(self.baselines.keys())
    
    def delete_baseline(self, baseline_id: str) -> bool:
        """Delete a baseline from memory."""
        if baseline_id in self.baselines:
            del self.baselines[baseline_id]
            return True
        return False
    
    # =========================================================================
    # UTILITIES: GENERATE COMPARISON TABLE
    # =========================================================================
    
    def generate_comparison_table(
        self,
        comparison: Dict[str, Any],
        format: str = 'dict',
    ) -> Any:
        """
        Generate a comparison table for display.
        
        Args:
            comparison: Comparison dict from compare() or compare_phases()
            format: 'dict' or 'dataframe'
        
        Returns:
            Dict or pandas DataFrame
        """
        # Handle both compare() and compare_phases() output formats
        if 'baseline' in comparison and 'optimized' in comparison:
            # compare_phases() format
            baseline = comparison['baseline']
            current = comparison['optimized']
        elif 'baseline' in comparison and 'current' in comparison:
            # compare() format
            baseline = comparison['baseline']
            current = comparison['current']
        else:
            raise ValueError("Invalid comparison format")
        
        comp = comparison['comparison']
        
        # Build table rows
        rows = []
        
        # Cost row
        rows.append({
            'metric': 'Total Cost',
            'baseline': f"${baseline.get('total_cost', 0):.4f}",
            'current': f"${current.get('total_cost', 0):.4f}",
            'change': f"{comp['cost']['pct_change']:+.1f}%",
            'direction': comp['cost']['direction'],
        })
        
        # Latency row
        rows.append({
            'metric': 'Avg Latency',
            'baseline': f"{baseline.get('avg_latency_ms', 0):.0f}ms",
            'current': f"{current.get('avg_latency_ms', 0):.0f}ms",
            'change': f"{comp['latency']['pct_change']:+.1f}%",
            'direction': comp['latency']['direction'],
        })
        
        # Tokens row
        rows.append({
            'metric': 'Avg Tokens/Call',
            'baseline': f"{baseline.get('avg_tokens_per_call', 0):.0f}",
            'current': f"{current.get('avg_tokens_per_call', 0):.0f}",
            'change': f"{comp['tokens']['pct_change']:+.1f}%",
            'direction': comp['tokens']['direction'],
        })
        
        # Cache hit rate row
        rows.append({
            'metric': 'Cache Hit Rate',
            'baseline': f"{baseline.get('cache_hit_rate', 0)*100:.1f}%",
            'current': f"{current.get('cache_hit_rate', 0)*100:.1f}%",
            'change': f"{comp['cache_hit_rate']['pct_change']:+.1f}%",
            'direction': comp['cache_hit_rate']['direction'],
        })
        
        # Quality row (if available)
        if baseline.get('avg_quality_score') and current.get('avg_quality_score'):
            rows.append({
                'metric': 'Avg Quality Score',
                'baseline': f"{baseline.get('avg_quality_score', 0):.2f}",
                'current': f"{current.get('avg_quality_score', 0):.2f}",
                'change': f"{comp['quality']['pct_change']:+.1f}%",
                'direction': comp['quality']['direction'],
            })
        
        # Call count row
        rows.append({
            'metric': 'Call Count',
            'baseline': str(baseline.get('total_calls', 0)),
            'current': str(current.get('total_calls', 0)),
            'change': str(current.get('total_calls', 0) - baseline.get('total_calls', 0)),
            'direction': 'neutral',
        })
        
        if format == 'dataframe':
            try:
                import pandas as pd
                return pd.DataFrame(rows)
            except ImportError:
                logger.warning("pandas not installed, returning dict")
                return rows
        
        return rows