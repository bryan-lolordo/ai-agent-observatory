"""
Model Router - Intelligent Model Selection with Tracking
Location: observatory/router.py

Routes LLM requests to appropriate models based on configurable rules.
Tracks routing decisions for Observatory analysis.
"""

import re
from typing import Optional, Dict, List, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass

from observatory.models import RoutingDecision

if TYPE_CHECKING:
    from observatory.collector import Observatory


# =============================================================================
# ROUTING RULE
# =============================================================================

@dataclass
class RoutingRule:
    """Individual routing rule."""
    name: str
    model: str
    reason: str
    priority: int = 0
    
    # Match conditions (any can be set)
    operations: Optional[List[str]] = None
    agents: Optional[List[str]] = None
    min_complexity: Optional[float] = None
    max_complexity: Optional[float] = None
    max_tokens: Optional[int] = None
    min_tokens: Optional[int] = None
    
    def matches(
        self,
        operation: Optional[str] = None,
        agent: Optional[str] = None,
        complexity: Optional[float] = None,
        estimated_tokens: Optional[int] = None,
    ) -> bool:
        """Check if this rule matches the given context."""
        
        # Check operations
        if self.operations and operation:
            if operation not in self.operations:
                return False
        
        # Check agents
        if self.agents and agent:
            if agent not in self.agents:
                return False
        
        # Check complexity range
        if complexity is not None:
            if self.min_complexity is not None and complexity < self.min_complexity:
                return False
            if self.max_complexity is not None and complexity > self.max_complexity:
                return False
        
        # Check token range
        if estimated_tokens is not None:
            if self.min_tokens is not None and estimated_tokens < self.min_tokens:
                return False
            if self.max_tokens is not None and estimated_tokens > self.max_tokens:
                return False
        
        return True


# =============================================================================
# MODEL ROUTER
# =============================================================================

class ModelRouter:
    """
    Intelligent model selection with Observatory tracking.
    
    Usage:
        router = ModelRouter(
            observatory=obs,
            default_model="gpt-4o-mini",
            rules=[
                {"operations": ["find_jobs", "list_resumes"], 
                 "model": "gpt-4o-mini", "reason": "Simple retrieval"},
                {"operations": ["deep_analyze_job"], 
                 "model": "gpt-4o", "reason": "Complex analysis"},
                {"min_complexity": 0.7, 
                 "model": "gpt-4o", "reason": "High complexity task"},
            ]
        )
        
        # Select model
        model, decision = router.select(
            operation="find_jobs",
            prompt="Find Python jobs",
            estimated_tokens=500
        )
        
        # Make LLM call with selected model...
        
        # Track with routing decision
        track_llm_call(..., routing_decision=decision)
    """
    
    # Model pricing (cost per 1K tokens: input, output)
    MODEL_PRICING = {
        "gpt-4o": (0.0025, 0.01),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4": (0.03, 0.06),
        "gpt-3.5-turbo": (0.0005, 0.0015),
        "claude-sonnet-4": (0.003, 0.015),
        "claude-opus-4": (0.015, 0.075),
    }
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        default_model: str = "gpt-4o-mini",
        fallback_model: Optional[str] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        complexity_calculator: Optional[Callable[[str], float]] = None,
    ):
        """
        Initialize Model Router.
        
        Args:
            observatory: Observatory instance
            default_model: Default model when no rules match
            fallback_model: Fallback if selected model fails
            rules: List of routing rule dicts
            complexity_calculator: Custom function to calculate complexity
        """
        self.observatory = observatory
        self.default_model = default_model
        self.fallback_model = fallback_model or default_model
        self.complexity_calculator = complexity_calculator or self._default_complexity
        
        # Convert rule dicts to RoutingRule objects
        self._rules: List[RoutingRule] = []
        if rules:
            for i, rule_dict in enumerate(rules):
                self._rules.append(self._create_rule(rule_dict, i))
        
        # Statistics
        self._total_decisions = 0
        self._decisions_by_model: Dict[str, int] = {}
        self._total_estimated_savings = 0.0
        
        # Last decision for easy retrieval
        self._last_decision: Optional[RoutingDecision] = None
    
    # =========================================================================
    # RULE MANAGEMENT
    # =========================================================================
    
    def _create_rule(self, rule_dict: Dict[str, Any], index: int) -> RoutingRule:
        """Create RoutingRule from dict."""
        return RoutingRule(
            name=rule_dict.get('name', f"rule_{index}"),
            model=rule_dict['model'],
            reason=rule_dict.get('reason', ''),
            priority=rule_dict.get('priority', index),
            operations=rule_dict.get('operations'),
            agents=rule_dict.get('agents'),
            min_complexity=rule_dict.get('min_complexity'),
            max_complexity=rule_dict.get('max_complexity'),
            max_tokens=rule_dict.get('max_tokens'),
            min_tokens=rule_dict.get('min_tokens'),
        )
    
    def add_rule(
        self,
        model: str,
        reason: str = "",
        operations: Optional[List[str]] = None,
        agents: Optional[List[str]] = None,
        min_complexity: Optional[float] = None,
        max_complexity: Optional[float] = None,
        max_tokens: Optional[int] = None,
        min_tokens: Optional[int] = None,
        priority: Optional[int] = None,
        name: Optional[str] = None,
    ) -> 'ModelRouter':
        """
        Add a routing rule.
        
        Args:
            model: Model to route to
            reason: Explanation for this rule
            operations: List of operations this rule applies to
            agents: List of agents this rule applies to
            min_complexity: Minimum complexity score to match
            max_complexity: Maximum complexity score to match
            max_tokens: Maximum token count to match
            min_tokens: Minimum token count to match
            priority: Rule priority (lower = higher priority)
            name: Rule name
        
        Returns:
            Self for chaining
        """
        rule = RoutingRule(
            name=name or f"rule_{len(self._rules)}",
            model=model,
            reason=reason,
            priority=priority if priority is not None else len(self._rules),
            operations=operations,
            agents=agents,
            min_complexity=min_complexity,
            max_complexity=max_complexity,
            max_tokens=max_tokens,
            min_tokens=min_tokens,
        )
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)
        return self
    
    def clear_rules(self) -> 'ModelRouter':
        """Clear all routing rules."""
        self._rules.clear()
        return self
    
    # =========================================================================
    # MODEL SELECTION
    # =========================================================================
    
    def select(
        self,
        operation: Optional[str] = None,
        agent: Optional[str] = None,
        prompt: Optional[str] = None,
        estimated_tokens: Optional[int] = None,
        complexity: Optional[float] = None,
    ) -> tuple[str, RoutingDecision]:
        """
        Select the best model based on rules.
        
        Args:
            operation: Operation name
            agent: Agent name
            prompt: Prompt text (for complexity calculation)
            estimated_tokens: Estimated token count
            complexity: Pre-calculated complexity (0-1)
        
        Returns:
            Tuple of (model_name, RoutingDecision)
        """
        # Calculate complexity if not provided
        if complexity is None and prompt:
            complexity = self.complexity_calculator(prompt)
        
        # Estimate tokens if not provided
        if estimated_tokens is None and prompt:
            estimated_tokens = self._estimate_tokens(prompt)
        
        # Find matching rule
        matched_rule = None
        for rule in self._rules:
            if rule.matches(operation, agent, complexity, estimated_tokens):
                matched_rule = rule
                break
        
        # Determine selected model
        if matched_rule:
            selected_model = matched_rule.model
            reasoning = matched_rule.reason
            rule_triggered = matched_rule.name
        else:
            selected_model = self.default_model
            reasoning = "No matching rule - using default model"
            rule_triggered = None
        
        # Calculate alternative models and potential savings
        alternatives = self._get_alternative_models(selected_model)
        estimated_savings = self._estimate_savings(
            selected_model, 
            alternatives[0] if alternatives else None,
            estimated_tokens or 500
        )
        
        # Create routing decision
        decision = RoutingDecision(
            chosen_model=selected_model,
            alternative_models=alternatives,
            reasoning=reasoning,
            rule_triggered=rule_triggered,
            complexity_score=complexity,
            estimated_cost_savings=estimated_savings if estimated_savings > 0 else None,
            routing_strategy=self._determine_strategy(matched_rule),
        )
        
        # Update statistics
        self._total_decisions += 1
        self._decisions_by_model[selected_model] = self._decisions_by_model.get(selected_model, 0) + 1
        if estimated_savings > 0:
            self._total_estimated_savings += estimated_savings
        
        self._last_decision = decision
        
        return selected_model, decision
    
    def _determine_strategy(self, rule: Optional[RoutingRule]) -> str:
        """Determine routing strategy name."""
        if rule is None:
            return "default"
        
        if rule.min_complexity is not None or rule.max_complexity is not None:
            return "complexity_based"
        elif rule.operations:
            return "operation_based"
        elif rule.agents:
            return "agent_based"
        elif rule.max_tokens is not None or rule.min_tokens is not None:
            return "token_based"
        else:
            return "rule_based"
    
    def _get_alternative_models(self, selected: str) -> List[str]:
        """Get list of alternative models."""
        all_models = ["gpt-4o", "gpt-4o-mini", "gpt-4", "claude-sonnet-4"]
        return [m for m in all_models if m != selected][:3]
    
    def _estimate_savings(
        self, 
        selected: str, 
        expensive_alternative: Optional[str],
        tokens: int
    ) -> float:
        """Estimate cost savings vs expensive alternative."""
        if not expensive_alternative:
            return 0.0
        
        selected_price = self.MODEL_PRICING.get(selected, (0.001, 0.002))
        alt_price = self.MODEL_PRICING.get(expensive_alternative, (0.001, 0.002))
        
        # Assume 70% input, 30% output tokens
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        selected_cost = (input_tokens * selected_price[0] / 1000) + (output_tokens * selected_price[1] / 1000)
        alt_cost = (input_tokens * alt_price[0] / 1000) + (output_tokens * alt_price[1] / 1000)
        
        return max(0, alt_cost - selected_cost)
    
    # =========================================================================
    # COMPLEXITY CALCULATION
    # =========================================================================
    
    def _default_complexity(self, prompt: str) -> float:
        """
        Default complexity calculator.
        
        Factors:
        - Length
        - Question complexity indicators
        - Technical terms
        - Multi-step indicators
        """
        if not prompt:
            return 0.3
        
        score = 0.3  # Base score
        
        # Length factor
        word_count = len(prompt.split())
        if word_count > 200:
            score += 0.2
        elif word_count > 100:
            score += 0.1
        elif word_count < 20:
            score -= 0.1
        
        # Complexity indicators
        complex_patterns = [
            r'\banalyze\b',
            r'\bcompare\b',
            r'\bevaluate\b',
            r'\bexplain why\b',
            r'\bhow does\b',
            r'\bwhat are the implications\b',
            r'\bpros and cons\b',
            r'\bstep by step\b',
            r'\bdetailed\b',
            r'\bcomprehensive\b',
        ]
        
        prompt_lower = prompt.lower()
        for pattern in complex_patterns:
            if re.search(pattern, prompt_lower):
                score += 0.05
        
        # Simple task indicators
        simple_patterns = [
            r'^(list|show|find|get|search)\b',
            r'\bhow many\b',
            r'\bwhat is\b',
            r'^(yes|no)\b',
        ]
        
        for pattern in simple_patterns:
            if re.search(pattern, prompt_lower):
                score -= 0.05
        
        return max(0.0, min(1.0, score))
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4
    
    def set_complexity_calculator(
        self, 
        calculator: Callable[[str], float]
    ) -> 'ModelRouter':
        """Set custom complexity calculator."""
        self.complexity_calculator = calculator
        return self
    
    # =========================================================================
    # PROPERTIES
    # =========================================================================
    
    @property
    def last_decision(self) -> Optional[RoutingDecision]:
        """Get the last routing decision."""
        return self._last_decision
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            "total_decisions": self._total_decisions,
            "decisions_by_model": dict(self._decisions_by_model),
            "total_estimated_savings": round(self._total_estimated_savings, 4),
            "default_model": self.default_model,
            "num_rules": len(self._rules),
            "rules": [
                {
                    "name": r.name,
                    "model": r.model,
                    "reason": r.reason,
                    "operations": r.operations,
                    "complexity_range": (r.min_complexity, r.max_complexity),
                }
                for r in self._rules
            ],
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self._total_decisions = 0
        self._decisions_by_model.clear()
        self._total_estimated_savings = 0.0


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def create_routing_decision(
    chosen_model: str,
    alternative_models: Optional[List[str]] = None,
    model_scores: Optional[Dict[str, float]] = None,
    reasoning: str = "",
    rule_triggered: Optional[str] = None,
    complexity_score: Optional[float] = None,
    estimated_cost_savings: Optional[float] = None,
    routing_strategy: Optional[str] = None,
) -> RoutingDecision:
    """
    Convenience function to create RoutingDecision.
    
    Args:
        chosen_model: The model that was selected
        alternative_models: Other models that were considered
        model_scores: Scores for each model considered
        reasoning: Why this model was chosen
        rule_triggered: Which routing rule triggered this selection
        complexity_score: Calculated complexity (0-1)
        estimated_cost_savings: Estimated $ saved vs default
        routing_strategy: Strategy used (complexity_based, operation_based, etc.)
    
    Returns:
        RoutingDecision object
    """
    return RoutingDecision(
        chosen_model=chosen_model,
        alternative_models=alternative_models or [],
        model_scores=model_scores or {},
        reasoning=reasoning,
        rule_triggered=rule_triggered,
        complexity_score=complexity_score,
        estimated_cost_savings=estimated_cost_savings,
        routing_strategy=routing_strategy,
    )