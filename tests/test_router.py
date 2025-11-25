from observatory.optimizers.model_router import ModelRouter, TaskComplexity


router = ModelRouter(enabled=True)

test_prompts = [
    {"role": "user", "content": "Fix the typo in line 5"},
    {"role": "user", "content": "Hello, how are you?"},
    {"role": "user", "content": "Analyze the architecture of this microservices system and identify scalability bottlenecks"},
    {"role": "user", "content": "Refactor this code for better performance and add comprehensive error handling"},
    {"role": "user", "content": "Add a comment to this function"},
    {"role": "user", "content": "Perform a detailed security audit of this authentication system, checking for SQL injection, XSS, CSRF, and other vulnerabilities"},
    {"role": "user", "content": "What does this function do?"},
    {"role": "user", "content": "Design a scalable distributed system architecture"},
]

print("🎯 Model Router Test\n")

for i, prompt in enumerate(test_prompts, 1):
    messages = [prompt]
    
    result = router.route(messages)
    
    print(f"Call {i}: {prompt['content'][:60]}...")
    print(f"  → Model: {result['model']}")
    print(f"  → Complexity: {result['complexity'].value}")
    print(f"  → Cost saved: ${result['cost_saved']:.4f}")
    print()

print("=" * 60)
print("\n📊 Router Statistics:")
stats = router.get_stats()

print(f"\nTotal Requests: {stats['total_requests']}")
print(f"\nTask Distribution:")
for complexity, count in stats['routes_used'].items():
    percentage = stats['distribution'][complexity]
    print(f"  {complexity}: {count} ({percentage:.1f}%)")

print(f"\n💰 Total Cost Saved: ${stats['total_cost_saved']:.4f}")
print(f"\nIf all tasks used GPT-4: ${stats['total_cost_saved']:.4f} more expensive")