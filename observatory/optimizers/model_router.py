from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import re


class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class ModelRoute:
    def __init__(
        self,
        model_name: str,
        provider: str,
        cost_per_1k_tokens: float,
        complexity_range: List[TaskComplexity],
    ):
        self.model_name = model_name
        self.provider = provider
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.complexity_range = complexity_range


class ModelRouter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        
        self.routes = {
            TaskComplexity.SIMPLE: ModelRoute(
                model_name="gpt-3.5-turbo",
                provider="openai",
                cost_per_1k_tokens=0.002,
                complexity_range=[TaskComplexity.SIMPLE],
            ),
            TaskComplexity.MEDIUM: ModelRoute(
                model_name="gpt-4o-mini",
                provider="openai",
                cost_per_1k_tokens=0.015,
                complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM],
            ),
            TaskComplexity.COMPLEX: ModelRoute(
                model_name="gpt-4",
                provider="openai",
                cost_per_1k_tokens=0.06,
                complexity_range=[TaskComplexity.SIMPLE, TaskComplexity.MEDIUM, TaskComplexity.COMPLEX],
            ),
        }
        
        self.total_requests = 0
        self.routes_used = {
            TaskComplexity.SIMPLE: 0,
            TaskComplexity.MEDIUM: 0,
            TaskComplexity.COMPLEX: 0,
        }
        self.total_cost_saved = 0.0
        
        self.complexity_classifiers = [
            self._classify_by_keywords,
            self._classify_by_length,
            self._classify_by_instructions,
        ]
    
    def classify_task(self, messages: list, custom_classifier: Optional[Callable] = None) -> TaskComplexity:
        if not self.enabled:
            return TaskComplexity.COMPLEX
        
        if custom_classifier:
            return custom_classifier(messages)
        
        prompt = self._extract_prompt(messages)
        
        scores = {
            TaskComplexity.SIMPLE: 0,
            TaskComplexity.MEDIUM: 0,
            TaskComplexity.COMPLEX: 0,
        }
        
        for classifier in self.complexity_classifiers:
            complexity = classifier(prompt)
            scores[complexity] += 1
        
        return max(scores, key=scores.get)
    
    def _extract_prompt(self, messages: list) -> str:
        if not messages:
            return ""
        
        if isinstance(messages[-1], dict):
            return messages[-1].get("content", "")
        
        return str(messages[-1])
    
    def _classify_by_keywords(self, prompt: str) -> TaskComplexity:
        prompt_lower = prompt.lower()
        
        complex_keywords = [
            "analyze", "architecture", "design", "refactor", "optimize",
            "security audit", "performance", "scalability", "algorithm",
            "comprehensive", "detailed analysis", "deep dive"
        ]
        
        simple_keywords = [
            "fix typo", "add comment", "rename", "format", "simple",
            "quick", "basic", "summarize", "translate", "hello"
        ]
        
        complex_count = sum(1 for kw in complex_keywords if kw in prompt_lower)
        simple_count = sum(1 for kw in simple_keywords if kw in prompt_lower)
        
        if complex_count >= 2:
            return TaskComplexity.COMPLEX
        if simple_count >= 1 and complex_count == 0:
            return TaskComplexity.SIMPLE
        
        return TaskComplexity.MEDIUM
    
    def _classify_by_length(self, prompt: str) -> TaskComplexity:
        word_count = len(prompt.split())
        
        if word_count < 20:
            return TaskComplexity.SIMPLE
        elif word_count < 100:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.COMPLEX
    
    def _classify_by_instructions(self, prompt: str) -> TaskComplexity:
        instruction_markers = ["1.", "2.", "3.", "first", "second", "then", "next", "finally"]
        
        marker_count = sum(1 for marker in instruction_markers if marker in prompt.lower())
        
        if marker_count >= 3:
            return TaskComplexity.COMPLEX
        elif marker_count >= 1:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
    
    def route(
        self,
        messages: list,
        default_model: str = "gpt-4",
        custom_classifier: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "model": default_model,
                "complexity": TaskComplexity.COMPLEX,
                "reasoning": "Router disabled",
                "cost_saved": 0.0,
            }
        
        self.total_requests += 1
        
        complexity = self.classify_task(messages, custom_classifier)
        
        route = self.routes[complexity]
        
        self.routes_used[complexity] += 1
        
        default_route = self.routes[TaskComplexity.COMPLEX]
        cost_diff = default_route.cost_per_1k_tokens - route.cost_per_1k_tokens
        
        estimated_tokens = len(self._extract_prompt(messages).split()) * 2
        cost_saved = (cost_diff * estimated_tokens) / 1000
        
        if route.model_name != default_model:
            self.total_cost_saved += cost_saved
        
        return {
            "model": route.model_name,
            "provider": route.provider,
            "complexity": complexity,
            "reasoning": f"Task classified as {complexity.value}",
            "cost_saved": cost_saved,
            "estimated_tokens": estimated_tokens,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        total_routed = sum(self.routes_used.values())
        
        distribution = {
            complexity.value: (count / total_routed * 100 if total_routed > 0 else 0)
            for complexity, count in self.routes_used.items()
        }
        
        return {
            "enabled": self.enabled,
            "total_requests": self.total_requests,
            "routes_used": {k.value: v for k, v in self.routes_used.items()},
            "distribution": distribution,
            "total_cost_saved": self.total_cost_saved,
        }
    
    def add_custom_route(
        self,
        complexity: TaskComplexity,
        model_name: str,
        provider: str,
        cost_per_1k_tokens: float,
    ):
        self.routes[complexity] = ModelRoute(
            model_name=model_name,
            provider=provider,
            cost_per_1k_tokens=cost_per_1k_tokens,
            complexity_range=[complexity],
        )
    
    def clear_stats(self):
        self.total_requests = 0
        self.routes_used = {
            TaskComplexity.SIMPLE: 0,
            TaskComplexity.MEDIUM: 0,
            TaskComplexity.COMPLEX: 0,
        }
        self.total_cost_saved = 0.0