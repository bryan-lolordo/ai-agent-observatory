# MCP Server Demo Questions

Use these questions during your Claude Desktop screen recording to showcase
the AI Agent Observatory MCP server capabilities.

---

## Setup Before Recording

Configure Claude Desktop to use your existing Observatory database:

```json
// Add to claude_desktop_config.json:
{
  "mcpServers": {
    "observatory": {
      "command": "python",
      "args": ["-m", "observatory.mcp.server"],
      "env": {
        "OBSERVATORY_DB_URL": "sqlite:///observatory.db"
      }
    }
  }
}
```

Then restart Claude Desktop.

---

## Demo Flow (Recommended Order)

### 1. Introduction - Overview Questions (2-3 min)

Start with high-level questions to introduce what the Observatory does:

> "What LLM usage data do you have access to?"

> "Give me a quick summary of my LLM costs for the last 7 days"

> "How many LLM calls have been made this week?"

---

### 2. Cost Analysis Deep Dive (3-4 min)

Show the cost tracking capabilities:

> "Break down my LLM costs by model"

> "Which operations are costing me the most?"

> "Show me cost trends - am I spending more or less than before?"

> "What's my average cost per LLM call?"

---

### 3. Optimization Opportunities (3-4 min)

This is the "wow" moment - show AI-powered optimization suggestions:

> "What optimization opportunities do you see in my LLM usage?"

> "How much money could I save with better model routing?"

> "Are there any calls that could be cached?"

> "Which expensive model calls could use a cheaper model instead?"

---

### 4. Routing Analysis (2-3 min)

Show the intelligent routing features:

> "Analyze my routing decisions - how much have I saved?"

> "Which routing rules are triggering most often?"

> "Show me recent routing decisions and their impact"

---

### 5. Cache Effectiveness (2-3 min)

Demonstrate caching insights:

> "What's my cache hit rate?"

> "How much am I saving from caching?"

> "What patterns could benefit from caching?"

---

### 6. Quality Monitoring (2-3 min)

Show the quality evaluation features:

> "How's the quality of my LLM responses?"

> "Have there been any hallucinations detected?"

> "Which agents have the highest quality scores?"

> "Show me any low-quality calls that need attention"

---

### 7. Session Analysis (2 min)

Demonstrate session tracking:

> "List my recent sessions"

> "Tell me about the most recent session - what happened?"

> "Which session had the highest cost?"

---

### 8. Before/After Comparison (2-3 min)

Show the A/B testing capabilities:

> "Compare my baseline period to the optimized period"

> "Has my optimization work actually saved money?"

> "Show me the improvement in cache hit rate after optimization"

---

### 9. Report Generation (2 min)

End with report generation for stakeholders:

> "Generate a weekly report of my LLM usage"

> "Create a daily summary"

> "I need to present to my team - give me key metrics and recommendations"

---

## Quick One-Liner Questions

If you need quick impressive queries:

| Question | Showcases |
|----------|-----------|
| "How much have I spent on LLMs this week?" | Cost tracking |
| "What's wasting the most money?" | Optimization |
| "Am I getting better over time?" | Comparison |
| "Any problems I should know about?" | Monitoring |
| "Summarize my LLM health" | Overview |

---

## Advanced Questions (Optional)

For technical audiences:

> "Show me token usage patterns - any bloat in system prompts?"

> "Calculate my cost per 1000 tokens by model"

> "What's the latency distribution across my operations?"

> "Identify calls with high token counts but low quality scores"

> "Which agents are most cost-efficient?"

---

## Narrative Demo Script

For a polished presentation, follow this narrative:

### Opening (30 sec)
"I'm going to show you how Claude can help monitor and optimize AI agent costs using the Observatory MCP server."

### Discovery (1 min)
> "What do you know about my LLM usage?"

Let Claude explain the data it has access to.

### The Problem (1 min)
> "How much am I spending on LLMs, and is it too much?"

Show cost breakdown and trends.

### The Solution (2 min)
> "What can I do to reduce costs without sacrificing quality?"

Let Claude identify optimization opportunities.

### Proof It Works (1 min)
> "Compare before and after my optimizations"

Show measurable improvements.

### Wrap-up (30 sec)
> "Give me three action items for next week"

End with actionable recommendations.

---

## Tips for Recording

1. **Pause after asking** - Give Claude time to call tools and show the process
2. **React naturally** - Comment on interesting findings
3. **Ask follow-ups** - "Tell me more about that" or "Why is that?"
4. **Show the tool calls** - Viewers want to see MCP in action
5. **Keep it conversational** - Don't read from a script verbatim

---

## Expected Tool Calls

During the demo, you should see these MCP tools being invoked:

- `get_cost_summary` - Cost breakdowns
- `find_optimization_opportunities` - Savings suggestions
- `analyze_routing` - Routing decisions
- `analyze_cache_effectiveness` - Cache stats
- `analyze_quality` - Quality metrics
- `list_sessions` / `get_session` - Session data
- `compare_phases` - Before/after comparison

This demonstrates the full power of MCP tool integration!
