from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import time

from observatory.collector import MetricsCollector
from observatory.models import ModelProvider, AgentRole


class BaseIntegration(ABC):
    """Base class for framework integrations."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    @abstractmethod
    def wrap_llm_call(self, *args, **kwargs):
        """Wrap an LLM call to capture metrics."""
        pass


class OpenAIIntegration(BaseIntegration):
    """Integration for OpenAI API calls."""
    
    def wrap_completion(
        self,
        client,
        model: str,
        messages: list,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Wrap OpenAI chat completion call."""
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.collector.record_llm_call(
                provider=ModelProvider.OPENAI,
                model_name=model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                latency_ms=latency_ms,
                agent_name=agent_name,
                operation=operation,
                success=True,
            )
            
            return response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            self.collector.record_llm_call(
                provider=ModelProvider.OPENAI,
                model_name=model,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                agent_name=agent_name,
                operation=operation,
                success=False,
                error=str(e),
            )
            
            raise
    
    def wrap_llm_call(self, *args, **kwargs):
        return self.wrap_completion(*args, **kwargs)


class AnthropicIntegration(BaseIntegration):
    """Integration for Anthropic API calls."""
    
    def wrap_message(
        self,
        client,
        model: str,
        messages: list,
        max_tokens: int,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Wrap Anthropic message call."""
        start_time = time.time()
        
        try:
            response = client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                **kwargs
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.collector.record_llm_call(
                provider=ModelProvider.ANTHROPIC,
                model_name=model,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                latency_ms=latency_ms,
                agent_name=agent_name,
                operation=operation,
                success=True,
            )
            
            return response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            self.collector.record_llm_call(
                provider=ModelProvider.ANTHROPIC,
                model_name=model,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                agent_name=agent_name,
                operation=operation,
                success=False,
                error=str(e),
            )
            
            raise
    
    def wrap_llm_call(self, *args, **kwargs):
        return self.wrap_message(*args, **kwargs)