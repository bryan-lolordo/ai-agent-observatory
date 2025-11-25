from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ModelType(str, Enum):
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_35_TURBO = "gpt-3.5-turbo"
    CLAUDE_OPUS_4 = "claude-opus-4"
    CLAUDE_SONNET_4 = "claude-sonnet-4"
    CLAUDE_HAIKU_4 = "claude-haiku-4"


@dataclass
class LLMCallPattern:
    model: ModelType
    prompt_tokens: int
    completion_tokens: int
    description: str = ""
    
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ProjectTemplate:
    name: str
    description: str
    calls_per_operation: List[LLMCallPattern]
    operations_per_day: int
    
    @property
    def total_calls_per_operation(self) -> int:
        return len(self.calls_per_operation)


class CostEstimator:
    
    PRICING = {
        ModelType.GPT_4: {"prompt": 30.0, "completion": 60.0},
        ModelType.GPT_4_TURBO: {"prompt": 10.0, "completion": 30.0},
        ModelType.GPT_4O: {"prompt": 5.0, "completion": 15.0},
        ModelType.GPT_4O_MINI: {"prompt": 0.15, "completion": 0.60},
        ModelType.GPT_35_TURBO: {"prompt": 0.50, "completion": 1.50},
        ModelType.CLAUDE_OPUS_4: {"prompt": 15.0, "completion": 75.0},
        ModelType.CLAUDE_SONNET_4: {"prompt": 3.0, "completion": 15.0},
        ModelType.CLAUDE_HAIKU_4: {"prompt": 0.80, "completion": 4.0},
    }
    
    TEMPLATES = {
        "code_review_crew": ProjectTemplate(
            name="Code Review Crew",
            description="Multi-agent code review system with analysis, security check, and fixing",
            calls_per_operation=[
                LLMCallPattern(ModelType.GPT_4, 800, 400, "Deep code analysis"),
                LLMCallPattern(ModelType.GPT_35_TURBO, 400, 200, "Security scan"),
                LLMCallPattern(ModelType.GPT_4, 600, 300, "Code fixing"),
            ],
            operations_per_day=100,
        ),
        "career_copilot": ProjectTemplate(
            name="Career Copilot",
            description="AI career assistant with job matching and resume optimization",
            calls_per_operation=[
                LLMCallPattern(ModelType.GPT_4O, 1200, 600, "Job analysis & matching"),
                LLMCallPattern(ModelType.GPT_35_TURBO, 500, 0, "Embedding generation"),
            ],
            operations_per_day=50,
        ),
        "customer_chatbot": ProjectTemplate(
            name="Customer Support Chatbot",
            description="24/7 customer support with context-aware responses",
            calls_per_operation=[
                LLMCallPattern(ModelType.GPT_4O_MINI, 300, 150, "Simple query response"),
            ],
            operations_per_day=1000,
        ),
        "content_generator": ProjectTemplate(
            name="Content Generator",
            description="Blog posts, social media, and marketing content creation",
            calls_per_operation=[
                LLMCallPattern(ModelType.GPT_4, 500, 800, "Long-form content"),
            ],
            operations_per_day=20,
        ),
        "data_analyst": ProjectTemplate(
            name="Data Analysis Assistant",
            description="SQL generation, data visualization, and insights",
            calls_per_operation=[
                LLMCallPattern(ModelType.GPT_4, 600, 400, "Complex analysis"),
                LLMCallPattern(ModelType.GPT_35_TURBO, 300, 200, "Simple queries"),
            ],
            operations_per_day=200,
        ),
    }
    
    def __init__(self):
        self.custom_templates: Dict[str, ProjectTemplate] = {}
    
    def calculate_call_cost(self, call_pattern: LLMCallPattern) -> float:
        pricing = self.PRICING.get(call_pattern.model)
        if not pricing:
            return 0.0
        
        prompt_cost = (call_pattern.prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (call_pattern.completion_tokens / 1_000_000) * pricing["completion"]
        
        return prompt_cost + completion_cost
    
    def estimate(
        self,
        template_name: str,
        operations_per_day: Optional[int] = None,
        days_per_month: int = 30,
        custom_template: Optional[ProjectTemplate] = None,
    ) -> Dict[str, Any]:
        if custom_template:
            template = custom_template
        elif template_name in self.TEMPLATES:
            template = self.TEMPLATES[template_name]
        elif template_name in self.custom_templates:
            template = self.custom_templates[template_name]
        else:
            raise ValueError(f"Template '{template_name}' not found")
        
        ops_per_day = operations_per_day or template.operations_per_day
        
        cost_per_operation = sum(
            self.calculate_call_cost(call) for call in template.calls_per_operation
        )
        
        tokens_per_operation = sum(
            call.total_tokens for call in template.calls_per_operation
        )
        
        daily_cost = cost_per_operation * ops_per_day
        monthly_cost = daily_cost * days_per_month
        yearly_cost = monthly_cost * 12
        
        call_breakdown = [
            {
                "model": call.model.value,
                "description": call.description,
                "tokens": call.total_tokens,
                "cost": self.calculate_call_cost(call),
            }
            for call in template.calls_per_operation
        ]
        
        return {
            "template_name": template.name,
            "description": template.description,
            "operations_per_day": ops_per_day,
            "calls_per_operation": template.total_calls_per_operation,
            "tokens_per_operation": tokens_per_operation,
            "cost_per_operation": cost_per_operation,
            "daily_cost": daily_cost,
            "monthly_cost": monthly_cost,
            "yearly_cost": yearly_cost,
            "call_breakdown": call_breakdown,
        }
    
    def estimate_with_optimizations(
        self,
        template_name: str,
        operations_per_day: Optional[int] = None,
        enable_caching: bool = False,
        cache_hit_rate: float = 0.30,
        use_cheaper_models: bool = False,
        compress_prompts: bool = False,
        prompt_compression_rate: float = 0.20,
    ) -> Dict[str, Any]:
        base_estimate = self.estimate(template_name, operations_per_day)
        
        optimized_cost = base_estimate["monthly_cost"]
        optimizations_applied = []
        
        if enable_caching:
            cache_savings = optimized_cost * cache_hit_rate
            optimized_cost -= cache_savings
            optimizations_applied.append({
                "name": "Caching",
                "savings": cache_savings,
                "description": f"{cache_hit_rate:.0%} cache hit rate",
            })
        
        if use_cheaper_models:
            model_savings = optimized_cost * 0.40
            optimized_cost -= model_savings
            optimizations_applied.append({
                "name": "Model Routing",
                "savings": model_savings,
                "description": "Use GPT-3.5 for simple tasks",
            })
        
        if compress_prompts:
            compression_savings = optimized_cost * prompt_compression_rate
            optimized_cost -= compression_savings
            optimizations_applied.append({
                "name": "Prompt Compression",
                "savings": compression_savings,
                "description": f"Reduce tokens by {prompt_compression_rate:.0%}",
            })
        
        total_savings = base_estimate["monthly_cost"] - optimized_cost
        savings_percentage = (total_savings / base_estimate["monthly_cost"]) * 100
        
        return {
            **base_estimate,
            "optimized_monthly_cost": optimized_cost,
            "optimized_yearly_cost": optimized_cost * 12,
            "total_monthly_savings": total_savings,
            "savings_percentage": savings_percentage,
            "optimizations": optimizations_applied,
        }
    
    def compare_templates(
        self,
        template_names: List[str],
        operations_per_day: Optional[int] = None,
    ) -> Dict[str, Any]:
        comparisons = {}
        
        for template_name in template_names:
            try:
                estimate = self.estimate(template_name, operations_per_day)
                comparisons[template_name] = estimate
            except ValueError:
                continue
        
        if not comparisons:
            return {}
        
        cheapest = min(comparisons.items(), key=lambda x: x[1]["monthly_cost"])
        most_expensive = max(comparisons.items(), key=lambda x: x[1]["monthly_cost"])
        
        return {
            "comparisons": comparisons,
            "cheapest": {
                "name": cheapest[0],
                "monthly_cost": cheapest[1]["monthly_cost"],
            },
            "most_expensive": {
                "name": most_expensive[0],
                "monthly_cost": most_expensive[1]["monthly_cost"],
            },
            "cost_range": most_expensive[1]["monthly_cost"] - cheapest[1]["monthly_cost"],
        }
    
    def add_custom_template(
        self,
        template_name: str,
        template: ProjectTemplate,
    ):
        self.custom_templates[template_name] = template
    
    def get_available_templates(self) -> List[str]:
        return list(self.TEMPLATES.keys()) + list(self.custom_templates.keys())
    
    def calculate_roi(
        self,
        template_name: str,
        operations_per_day: int,
        integration_cost: float,
        monthly_savings_from_optimization: float,
    ) -> Dict[str, Any]:
        base_estimate = self.estimate(template_name, operations_per_day)
        
        monthly_base_cost = base_estimate["monthly_cost"]
        monthly_optimized_cost = monthly_base_cost - monthly_savings_from_optimization
        
        months_to_break_even = integration_cost / monthly_savings_from_optimization if monthly_savings_from_optimization > 0 else float('inf')
        
        year_1_savings = (monthly_savings_from_optimization * 12) - integration_cost
        year_2_savings = monthly_savings_from_optimization * 12
        
        return {
            "integration_cost": integration_cost,
            "monthly_base_cost": monthly_base_cost,
            "monthly_optimized_cost": monthly_optimized_cost,
            "monthly_savings": monthly_savings_from_optimization,
            "months_to_break_even": months_to_break_even,
            "year_1_net_savings": year_1_savings,
            "year_2_net_savings": year_2_savings,
            "roi_year_1": (year_1_savings / integration_cost * 100) if integration_cost > 0 else 0,
            "roi_year_2": (year_2_savings / integration_cost * 100) if integration_cost > 0 else 0,
        }