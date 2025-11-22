from typing import Dict, Tuple
from collections import defaultdict

from observatory.models import Session, CostBreakdown, ModelProvider


class CostAnalyzer:
    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        ModelProvider.OPENAI: {
            "gpt-4": {"prompt": 30.0, "completion": 60.0},
            "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
            "gpt-4o": {"prompt": 5.0, "completion": 15.0},
            "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
            "gpt-3.5-turbo": {"prompt": 0.50, "completion": 1.50},
            "text-embedding-3-small": {"prompt": 0.02, "completion": 0.0},
            "text-embedding-3-large": {"prompt": 0.13, "completion": 0.0},
        },
        ModelProvider.ANTHROPIC: {
            "claude-opus-4": {"prompt": 15.0, "completion": 75.0},
            "claude-sonnet-4": {"prompt": 3.0, "completion": 15.0},
            "claude-haiku-4": {"prompt": 0.80, "completion": 4.0},
            "claude-3-5-sonnet": {"prompt": 3.0, "completion": 15.0},
            "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
            "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},
            "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},
        },
        ModelProvider.AZURE: {
            # Same as OpenAI typically
            "gpt-4": {"prompt": 30.0, "completion": 60.0},
            "gpt-35-turbo": {"prompt": 0.50, "completion": 1.50},
        },
    }

    def calculate_cost(
        self,
        provider: ModelProvider,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Tuple[float, float]:
        """Calculate cost for a single LLM call."""
        provider_pricing = self.PRICING.get(provider, {})
        model_pricing = provider_pricing.get(model_name)
        
        if not model_pricing:
            # Default fallback pricing
            model_pricing = {"prompt": 1.0, "completion": 2.0}
        
        prompt_cost = (prompt_tokens / 1_000_000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * model_pricing["completion"]
        
        return prompt_cost, completion_cost

    def analyze(self, session: Session) -> CostBreakdown:
        """Analyze cost breakdown for a session."""
        by_model = defaultdict(float)
        by_provider = defaultdict(float)
        by_agent = defaultdict(float)
        by_operation = defaultdict(float)
        
        for call in session.llm_calls:
            by_model[call.model_name] += call.total_cost
            by_provider[call.provider.value] += call.total_cost
            
            if call.agent_name:
                by_agent[call.agent_name] += call.total_cost
            
            if call.operation:
                by_operation[call.operation] += call.total_cost
        
        return CostBreakdown(
            total_cost=session.total_cost,
            by_model=dict(by_model),
            by_provider=dict(by_provider),
            by_agent=dict(by_agent),
            by_operation=dict(by_operation),
        )