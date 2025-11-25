from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import statistics


@dataclass
class PromptVariant:
    id: str
    template: str
    description: str = ""
    times_used: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    quality_scores: List[float] = field(default_factory=list)
    
    @property
    def avg_cost(self) -> float:
        return self.total_cost / self.times_used if self.times_used > 0 else 0.0
    
    @property
    def avg_tokens(self) -> float:
        return self.total_tokens / self.times_used if self.times_used > 0 else 0.0
    
    @property
    def avg_latency(self) -> float:
        return self.total_latency_ms / self.times_used if self.times_used > 0 else 0.0
    
    @property
    def avg_quality(self) -> float:
        return statistics.mean(self.quality_scores) if self.quality_scores else 0.0
    
    @property
    def quality_std(self) -> float:
        return statistics.stdev(self.quality_scores) if len(self.quality_scores) > 1 else 0.0


@dataclass
class TestResult:
    variant_id: str
    cost: float
    tokens: int
    latency_ms: float
    quality_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PromptOptimizer:
    def __init__(
        self,
        enabled: bool = True,
        strategy: str = "round_robin",  # or "epsilon_greedy", "ucb"
        epsilon: float = 0.1,
    ):
        self.enabled = enabled
        self.strategy = strategy
        self.epsilon = epsilon
        
        self.variants: Dict[str, PromptVariant] = {}
        self.current_index = 0
        self.total_tests = 0
        self.test_history: List[TestResult] = []
    
    def add_variant(
        self,
        variant_id: str,
        template: str,
        description: str = "",
    ) -> PromptVariant:
        variant = PromptVariant(
            id=variant_id,
            template=template,
            description=description,
        )
        self.variants[variant_id] = variant
        return variant
    
    def get_next_variant(self) -> PromptVariant:
        if not self.enabled or not self.variants:
            return None
        
        if self.strategy == "round_robin":
            return self._round_robin()
        elif self.strategy == "epsilon_greedy":
            return self._epsilon_greedy()
        elif self.strategy == "ucb":
            return self._ucb()
        else:
            return self._round_robin()
    
    def _round_robin(self) -> PromptVariant:
        variant_list = list(self.variants.values())
        variant = variant_list[self.current_index % len(variant_list)]
        self.current_index += 1
        return variant
    
    def _epsilon_greedy(self) -> PromptVariant:
        import random
        
        if random.random() < self.epsilon:
            return random.choice(list(self.variants.values()))
        else:
            return self._get_best_variant()
    
    def _ucb(self) -> PromptVariant:
        import math
        
        if self.total_tests < len(self.variants):
            return self._round_robin()
        
        best_variant = None
        best_score = float('-inf')
        
        for variant in self.variants.values():
            if variant.times_used == 0:
                return variant
            
            exploitation = variant.avg_quality
            exploration = math.sqrt(2 * math.log(self.total_tests) / variant.times_used)
            ucb_score = exploitation + exploration
            
            if ucb_score > best_score:
                best_score = ucb_score
                best_variant = variant
        
        return best_variant
    
    def _get_best_variant(self) -> PromptVariant:
        if not self.variants:
            return None
        
        return max(
            self.variants.values(),
            key=lambda v: v.avg_quality if v.quality_scores else 0.0
        )
    
    def record_result(
        self,
        variant_id: str,
        cost: float,
        tokens: int,
        latency_ms: float,
        quality_score: Optional[float] = None,
    ):
        if variant_id not in self.variants:
            return
        
        variant = self.variants[variant_id]
        
        variant.times_used += 1
        variant.total_cost += cost
        variant.total_tokens += tokens
        variant.total_latency_ms += latency_ms
        
        if quality_score is not None:
            variant.quality_scores.append(quality_score)
        
        result = TestResult(
            variant_id=variant_id,
            cost=cost,
            tokens=tokens,
            latency_ms=latency_ms,
            quality_score=quality_score,
        )
        
        self.test_history.append(result)
        self.total_tests += 1
    
    def get_winner(self, metric: str = "quality") -> Optional[PromptVariant]:
        if not self.variants:
            return None
        
        if metric == "quality":
            return max(
                self.variants.values(),
                key=lambda v: v.avg_quality if v.quality_scores else 0.0
            )
        elif metric == "cost":
            return min(
                self.variants.values(),
                key=lambda v: v.avg_cost if v.times_used > 0 else float('inf')
            )
        elif metric == "latency":
            return min(
                self.variants.values(),
                key=lambda v: v.avg_latency if v.times_used > 0 else float('inf')
            )
        elif metric == "balanced":
            return max(
                self.variants.values(),
                key=lambda v: self._calculate_balanced_score(v)
            )
        else:
            return self._get_best_variant()
    
    def _calculate_balanced_score(self, variant: PromptVariant) -> float:
        if variant.times_used == 0:
            return 0.0
        
        quality_score = variant.avg_quality / 10.0
        cost_score = 1.0 - min(variant.avg_cost / 0.1, 1.0)
        latency_score = 1.0 - min(variant.avg_latency / 5000, 1.0)
        
        return (quality_score * 0.5) + (cost_score * 0.3) + (latency_score * 0.2)
    
    def is_significant(
        self,
        variant_a_id: str,
        variant_b_id: str,
        confidence: float = 0.95,
    ) -> Tuple[bool, float]:
        if variant_a_id not in self.variants or variant_b_id not in self.variants:
            return False, 0.0
        
        variant_a = self.variants[variant_a_id]
        variant_b = self.variants[variant_b_id]
        
        if len(variant_a.quality_scores) < 2 or len(variant_b.quality_scores) < 2:
            return False, 0.0
        
        from scipy import stats
        
        t_stat, p_value = stats.ttest_ind(
            variant_a.quality_scores,
            variant_b.quality_scores
        )
        
        is_sig = p_value < (1 - confidence)
        
        return is_sig, p_value
    
    def get_comparison(self) -> Dict[str, Any]:
        comparison = {}
        
        for variant_id, variant in self.variants.items():
            comparison[variant_id] = {
                "description": variant.description,
                "times_used": variant.times_used,
                "avg_cost": variant.avg_cost,
                "avg_tokens": variant.avg_tokens,
                "avg_latency": variant.avg_latency,
                "avg_quality": variant.avg_quality,
                "quality_std": variant.quality_std,
                "template_length": len(variant.template),
            }
        
        return comparison
    
    def get_recommendation(self) -> Dict[str, Any]:
        if not self.variants:
            return {"recommendation": "No variants to compare"}
        
        quality_winner = self.get_winner("quality")
        cost_winner = self.get_winner("cost")
        latency_winner = self.get_winner("latency")
        balanced_winner = self.get_winner("balanced")
        
        min_tests_needed = 30
        all_tested = all(v.times_used >= min_tests_needed for v in self.variants.values())
        
        recommendation = {
            "ready_to_decide": all_tested,
            "min_tests_needed": min_tests_needed,
            "quality_winner": {
                "id": quality_winner.id,
                "score": quality_winner.avg_quality,
                "description": quality_winner.description,
            },
            "cost_winner": {
                "id": cost_winner.id,
                "cost": cost_winner.avg_cost,
                "description": cost_winner.description,
            },
            "latency_winner": {
                "id": latency_winner.id,
                "latency": latency_winner.avg_latency,
                "description": latency_winner.description,
            },
            "balanced_winner": {
                "id": balanced_winner.id,
                "description": balanced_winner.description,
            },
        }
        
        if quality_winner.id == cost_winner.id == latency_winner.id:
            recommendation["message"] = f"Clear winner: {quality_winner.id} - best on all metrics!"
        elif balanced_winner.id == quality_winner.id:
            recommendation["message"] = f"Recommended: {balanced_winner.id} - best quality"
        else:
            recommendation["message"] = f"Recommended: {balanced_winner.id} - best balance of quality/cost/speed"
        
        return recommendation
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "strategy": self.strategy,
            "total_tests": self.total_tests,
            "total_variants": len(self.variants),
            "variants": self.get_comparison(),
        }