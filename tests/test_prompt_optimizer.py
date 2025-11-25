from observatory.optimizers.prompt_optimizer import PromptOptimizer
import random


optimizer = PromptOptimizer(enabled=True, strategy="round_robin")

optimizer.add_variant(
    variant_id="verbose",
    template="You are an expert code reviewer. Please carefully analyze the following code and provide a comprehensive review covering bugs, style issues, and potential improvements. Code: {code}",
    description="Long, detailed instructions"
)

optimizer.add_variant(
    variant_id="concise",
    template="Review this code for bugs and style issues: {code}",
    description="Short and direct"
)

optimizer.add_variant(
    variant_id="structured",
    template="Review code: {code}\n\n1. Find bugs\n2. Check style\n3. Suggest improvements",
    description="Numbered instructions"
)

print("🧪 Prompt Optimizer Test\n")
print("Running 60 simulated tests (20 per variant)...\n")

for i in range(60):
    variant = optimizer.get_next_variant()
    
    cost = random.uniform(0.01, 0.05)
    tokens = random.randint(100, 500)
    latency = random.uniform(1000, 3000)
    
    if variant.id == "verbose":
        quality = random.uniform(7.0, 9.0)
        cost *= 1.5
        tokens = int(tokens * 1.5)
    elif variant.id == "concise":
        quality = random.uniform(6.0, 8.0)
        cost *= 0.7
        tokens = int(tokens * 0.7)
    else:
        quality = random.uniform(7.5, 8.5)
    
    optimizer.record_result(
        variant_id=variant.id,
        cost=cost,
        tokens=tokens,
        latency_ms=latency,
        quality_score=quality,
    )

print("="*60)
print("\n📊 Test Results:\n")

comparison = optimizer.get_comparison()

for variant_id, stats in comparison.items():
    print(f"{variant_id.upper()}:")
    print(f"  Description: {stats['description']}")
    print(f"  Times Used: {stats['times_used']}")
    print(f"  Avg Quality: {stats['avg_quality']:.2f}/10")
    print(f"  Avg Cost: ${stats['avg_cost']:.4f}")
    print(f"  Avg Tokens: {stats['avg_tokens']:.0f}")
    print(f"  Avg Latency: {stats['avg_latency']:.0f}ms")
    print(f"  Template Length: {stats['template_length']} chars")
    print()

print("="*60)
print("\n🏆 Winners by Metric:\n")

quality_winner = optimizer.get_winner("quality")
print(f"Best Quality: {quality_winner.id.upper()} ({quality_winner.avg_quality:.2f}/10)")

cost_winner = optimizer.get_winner("cost")
print(f"Lowest Cost: {cost_winner.id.upper()} (${cost_winner.avg_cost:.4f})")

latency_winner = optimizer.get_winner("latency")
print(f"Fastest: {latency_winner.id.upper()} ({latency_winner.avg_latency:.0f}ms)")

balanced_winner = optimizer.get_winner("balanced")
print(f"Best Balance: {balanced_winner.id.upper()}")

print("\n" + "="*60)
print("\n💡 Recommendation:\n")

recommendation = optimizer.get_recommendation()

print(f"Status: {'✅ Ready to decide' if recommendation['ready_to_decide'] else '⚠️ Need more tests'}")
print(f"\n{recommendation['message']}")

print(f"\nDetails:")
print(f"  Quality Winner: {recommendation['quality_winner']['id']} ({recommendation['quality_winner']['score']:.2f}/10)")
print(f"  Cost Winner: {recommendation['cost_winner']['id']} (${recommendation['cost_winner']['cost']:.4f})")
print(f"  Balanced Winner: {recommendation['balanced_winner']['id']}")

print("\n" + "="*60)
print("\n📈 Key Insights:\n")

verbose = comparison["verbose"]
concise = comparison["concise"]
structured = comparison["structured"]

print(f"💰 Cost Savings:")
print(f"  Using 'concise' vs 'verbose': ${(verbose['avg_cost'] - concise['avg_cost']):.4f} per call")
print(f"  Annual savings (1000 calls/day): ${(verbose['avg_cost'] - concise['avg_cost']) * 365000:.2f}")

print(f"\n📦 Token Efficiency:")
print(f"  'concise' uses {((verbose['avg_tokens'] - concise['avg_tokens']) / verbose['avg_tokens'] * 100):.0f}% fewer tokens")

print(f"\n⭐ Quality vs Cost:")
quality_diff = verbose['avg_quality'] - concise['avg_quality']
cost_diff = verbose['avg_cost'] - concise['avg_cost']
if quality_diff < 1.0 and cost_diff > 0.01:
    print(f"  💡 'concise' is nearly as good ({quality_diff:.1f} point difference) but ${cost_diff:.4f} cheaper!")
    print(f"     Recommendation: Switch to 'concise' variant")
else:
    print(f"  💡 'verbose' provides {quality_diff:.1f} higher quality for ${cost_diff:.4f} more")
    print(f"     Recommendation: Depends on your quality requirements")