from observatory.analyzers.llm_judge import LLMJudge, JudgeCriteria, GroundTruthEvaluator


judge = LLMJudge(
    judge_model="gpt-4",
    enabled=True,
    criteria=[JudgeCriteria.CORRECTNESS, JudgeCriteria.CLARITY, JudgeCriteria.HELPFULNESS]
)

print("🧪 Test 1: Single Response Evaluation\n")

task = "Fix the bug in this code: def add(a, b): return a - b"
response = "The bug is using subtraction instead of addition. Change 'a - b' to 'a + b'."

result = judge.judge(task, response)

print(f"Task: {task}")
print(f"Response: {response}")
print(f"\n📊 Judgment:")
print(f"  Overall Score: {result.overall_score}/10")
print(f"  Criteria Scores:")
for criterion, score in result.criteria_scores.items():
    print(f"    {criterion}: {score}/10")
print(f"  Reasoning: {result.reasoning}")

print("\n" + "="*60 + "\n")

print("🧪 Test 2: Model Comparison\n")

task = "Explain what a linked list is"

responses = {
    "gpt-3.5-turbo": "A linked list is a data structure with nodes that point to the next node.",
    "gpt-4": "A linked list is a linear data structure where each element (node) contains data and a reference (link) to the next node in the sequence. Unlike arrays, linked lists don't require contiguous memory and allow efficient insertion/deletion.",
    "gpt-4o-mini": "Linked list: nodes with pointers. Good for insertions.",
}

print(f"Task: {task}\n")

comparison = judge.compare_models(task, responses)

for model, result in comparison.items():
    print(f"{model}:")
    print(f"  Score: {result.overall_score}/10")
    print(f"  Response: {responses[model][:60]}...")
    print()

winner = judge.get_winner(comparison)
print(f"🏆 Winner: {winner}\n")

print("="*60 + "\n")

print("🧪 Test 3: Ground Truth Evaluation\n")

ground_truth_tests = [
    {
        "response": "The capital of France is Paris",
        "ground_truth": "Paris",
        "description": "Exact answer present"
    },
    {
        "response": "The capital is London",
        "ground_truth": "Paris",
        "description": "Wrong answer"
    },
    {
        "response": "France's capital city is called Paris and it's very beautiful",
        "ground_truth": "Paris",
        "description": "Correct but verbose"
    },
]

evaluator = GroundTruthEvaluator()

for test in ground_truth_tests:
    score = evaluator.substring_match(test["response"], test["ground_truth"])
    print(f"{test['description']}:")
    print(f"  Response: {test['response']}")
    print(f"  Expected: {test['ground_truth']}")
    print(f"  Match Score: {score:.2f}")
    print()

print("="*60 + "\n")

print("🧪 Test 4: Batch Evaluation\n")

batch_tasks = [
    {"task": "What is 2+2?", "response": "4"},
    {"task": "What is 3+3?", "response": "6"},
    {"task": "What is 5+5?", "response": "10"},
]

batch_results = judge.batch_evaluate(batch_tasks)

for i, result in enumerate(batch_results, 1):
    print(f"Task {i}: {batch_tasks[i-1]['task']}")
    print(f"  Score: {result.overall_score}/10")

print("\n" + "="*60 + "\n")

print("📊 Overall Statistics:\n")
stats = judge.get_stats()

print(f"Total Judgments: {stats['total_judgments']}")
print(f"Average Score: {stats['average_score']:.2f}/10")
print(f"\nModel Performance:")
for model, avg in stats['model_averages'].items():
    print(f"  {model}: {avg:.2f}/10")