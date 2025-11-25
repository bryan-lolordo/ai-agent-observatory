import time
from observatory import Observatory, ModelProvider
from observatory.optimizers.cache_layer import CacheLayer


def simulate_llm_call(prompt: str) -> dict:
    time.sleep(0.1)
    return {
        "response": f"Analysis: {prompt[:50]}",
        "prompt_tokens": len(prompt.split()) * 2,
        "completion_tokens": 100,
    }


cache = CacheLayer(enabled=True, ttl_seconds=3600)
obs = Observatory(project_name="Cache Test", enabled=True)

code_samples = [
    "def hello(): print('hello')",
    "def goodbye(): print('bye')",
    "def hello(): print('hello')",  # Duplicate
    "def hello(): print('hello')",  # Duplicate
]

session = obs.start_session("cache_test")

for i, code in enumerate(code_samples):
    print(f"\nCall {i+1}: {code}")
    
    messages = [{"role": "user", "content": f"Analyze: {code}"}]
    model = "gpt-4"
    
    cached = cache.get(model, messages)
    
    if cached:
        print("  ✅ CACHE HIT")
        prompt_tokens = cached.prompt_tokens
        completion_tokens = cached.completion_tokens
        latency_ms = 0
    else:
        print("  ⚪ Cache miss - API call")
        result = simulate_llm_call(code)
        prompt_tokens = result["prompt_tokens"]
        completion_tokens = result["completion_tokens"]
        latency_ms = 100
        
        cache.set(model, messages, result["response"], prompt_tokens, completion_tokens)
    
    obs.record_call(
        provider=ModelProvider.OPENAI,
        model_name=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        session=session,
    )

obs.end_session(session)

stats = cache.get_stats()
print(f"\n📊 Cache Stats:")
print(f"  Requests: {stats['total_requests']}")
print(f"  Hits: {stats['cache_hits']}")
print(f"  Misses: {stats['cache_misses']}")
print(f"  Hit Rate: {stats['hit_rate']:.1%}")
print(f"  Tokens Saved: {stats['total_tokens_saved']}")
print(f"  Cost Saved: ${cache.estimate_cost_savings():.4f}")

report = obs.get_report(session)
print(f"\n💰 Total Cost: ${report.cost_breakdown.total_cost:.4f}")