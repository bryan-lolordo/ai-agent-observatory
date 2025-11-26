"""
Optimizer State Manager
Location: dashboard/optimizer_state.py

Manages shared optimizer instances across all dashboard pages.
Ensures consistent state and prevents re-initialization.
"""

import sys
from pathlib import Path
from typing import Optional

# Add parent directory for observatory imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from observatory.optimizers.cache_layer import CacheLayer
from observatory.optimizers.model_router import ModelRouter
from observatory.optimizers.prompt_optimizer import PromptOptimizer
from observatory.analyzers.llm_judge import LLMJudge
from observatory.analyzers.cost_estimator import CostEstimator


class OptimizerState:
    """
    Singleton state manager for all optimizers.
    Ensures consistent state across dashboard pages.
    """
    
    _instance: Optional['OptimizerState'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize all optimizers (only once)."""
        if self._initialized:
            return
        
        # Initialize Cache Layer
        self.cache = CacheLayer(
            enabled=True,
            ttl_seconds=3600,  # 1 hour TTL
            max_entries=1000
        )
        
        # Initialize Model Router
        self.router = ModelRouter(enabled=True)
        
        # Initialize Prompt Optimizer
        self.prompt_optimizer = PromptOptimizer(
            enabled=True,
            strategy="epsilon_greedy",
            epsilon=0.1
        )
        
        # Initialize LLM Judge
        self.llm_judge = LLMJudge(
            judge_model="gpt-4",
            enabled=True
        )
        
        # Initialize Cost Estimator
        self.cost_estimator = CostEstimator()
        
        self._initialized = True
    
    def get_cache(self) -> CacheLayer:
        """Get the cache layer instance."""
        return self.cache
    
    def get_router(self) -> ModelRouter:
        """Get the model router instance."""
        return self.router
    
    def get_prompt_optimizer(self) -> PromptOptimizer:
        """Get the prompt optimizer instance."""
        return self.prompt_optimizer
    
    def get_llm_judge(self) -> LLMJudge:
        """Get the LLM judge instance."""
        return self.llm_judge
    
    def get_cost_estimator(self) -> CostEstimator:
        """Get the cost estimator instance."""
        return self.cost_estimator
    
    def reset_cache(self):
        """Reset cache statistics."""
        self.cache.clear()
    
    def reset_router(self):
        """Reset router statistics."""
        self.router.clear_stats()
    
    def reset_all(self):
        """Reset all optimizer statistics."""
        self.reset_cache()
        self.reset_router()
        # Reinitialize prompt optimizer and judge
        self.prompt_optimizer = PromptOptimizer(enabled=True)
        self.llm_judge = LLMJudge(enabled=True)


# Global singleton getter
def get_optimizer_state() -> OptimizerState:
    """Get the global optimizer state instance."""
    return OptimizerState()