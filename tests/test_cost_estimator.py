from observatory.analyzers.cost_estimator import CostEstimator


estimator = CostEstimator()

print("💰 Cost Estimator - Project Cost Predictions\n")
print("="*60)

print("\n🧪 Test 1: Code Review Crew Estimate\n")

estimate = estimator.estimate("code_review_crew")

print(f"Project: {estimate['template_name']}")
print(f"Description: {estimate['description']}")
print(f"\n📊 Usage Pattern:")
print(f"  Operations per day: {estimate['operations_per_day']}")
print(f"  LLM calls per operation: {estimate['calls_per_operation']}")
print(f"  Tokens per operation: {estimate['tokens_per_operation']:,}")

print(f"\n💵 Cost Breakdown per Operation:")
for call in estimate['call_breakdown']:
    print(f"  • {call['model']}: ${call['cost']:.4f} ({call['tokens']} tokens)")
    print(f"    {call['description']}")

print(f"\n💰 Total Costs:")
print(f"  Per operation: ${estimate['cost_per_operation']:.4f}")
print(f"  Per day: ${estimate['daily_cost']:.2f}")
print(f"  Per month: ${estimate['monthly_cost']:.2f}")
print(f"  Per year: ${estimate['yearly_cost']:.2f}")

print("\n" + "="*60)

print("\n🧪 Test 2: With Optimizations\n")

optimized = estimator.estimate_with_optimizations(
    "code_review_crew",
    enable_caching=True,
    cache_hit_rate=0.30,
    use_cheaper_models=True,
    compress_prompts=True,
    prompt_compression_rate=0.20,
)

print(f"📉 Cost Reduction:\n")
print(f"Base Cost: ${optimized['monthly_cost']:.2f}/month")
print(f"Optimized Cost: ${optimized['optimized_monthly_cost']:.2f}/month")
print(f"Savings: ${optimized['total_monthly_savings']:.2f}/month ({optimized['savings_percentage']:.1f}%)")

print(f"\n🎯 Applied Optimizations:")
for opt in optimized['optimizations']:
    print(f"  ✅ {opt['name']}: -${opt['savings']:.2f}/month")
    print(f"     {opt['description']}")

print("\n" + "="*60)

print("\n🧪 Test 3: Compare Multiple Projects\n")

comparison = estimator.compare_templates([
    "code_review_crew",
    "career_copilot",
    "customer_chatbot",
    "content_generator",
    "data_analyst",
])

print("Project Comparison:\n")
for name, est in comparison['comparisons'].items():
    print(f"{est['template_name']}:")
    print(f"  Monthly: ${est['monthly_cost']:.2f}")
    print(f"  Operations/day: {est['operations_per_day']}")
    print()

print(f"💵 Cheapest: {comparison['cheapest']['name']} (${comparison['cheapest']['monthly_cost']:.2f}/month)")
print(f"💰 Most Expensive: {comparison['most_expensive']['name']} (${comparison['most_expensive']['monthly_cost']:.2f}/month)")
print(f"📊 Cost Range: ${comparison['cost_range']:.2f}/month")

print("\n" + "="*60)

print("\n🧪 Test 4: ROI Calculation (Client Pitch)\n")

roi = estimator.calculate_roi(
    template_name="code_review_crew",
    operations_per_day=100,
    integration_cost=8000,
    monthly_savings_from_optimization=97.50,
)

print("Client Scenario:")
print(f"  Integration Service Cost: ${roi['integration_cost']:,.2f}")
print(f"  Current Monthly Cost: ${roi['monthly_base_cost']:.2f}")
print(f"  Optimized Monthly Cost: ${roi['monthly_optimized_cost']:.2f}")
print(f"  Monthly Savings: ${roi['monthly_savings']:.2f}")

print(f"\n📈 ROI Analysis:")
print(f"  Break-even: {roi['months_to_break_even']:.1f} months")
print(f"  Year 1 Net Savings: ${roi['year_1_net_savings']:,.2f}")
print(f"  Year 1 ROI: {roi['roi_year_1']:.0f}%")
print(f"  Year 2 Net Savings: ${roi['year_2_net_savings']:,.2f}")
print(f"  Year 2 ROI: {roi['roi_year_2']:.0f}%")

print(f"\n💡 Pitch:")
print(f"  'My integration service is ${roi['integration_cost']:,.0f} one-time.'")
print(f"  'You save ${roi['monthly_savings']:.2f}/month, so ROI in {roi['months_to_break_even']:.0f} months.'")
print(f"  'Year 1 net savings: ${roi['year_1_net_savings']:,.2f}'")
print(f"  'Plus you get quality improvements and monitoring.'")

print("\n" + "="*60)

print("\n🧪 Test 5: Custom Volume Scenario\n")

scenarios = [
    {"name": "Startup", "ops_per_day": 50},
    {"name": "Mid-size", "ops_per_day": 200},
    {"name": "Enterprise", "ops_per_day": 1000},
]

print("Code Review Crew - Scaling Costs:\n")

for scenario in scenarios:
    est = estimator.estimate("code_review_crew", operations_per_day=scenario['ops_per_day'])
    print(f"{scenario['name']} ({scenario['ops_per_day']} reviews/day):")
    print(f"  Monthly: ${est['monthly_cost']:.2f}")
    print(f"  Yearly: ${est['yearly_cost']:,.2f}")
    print()