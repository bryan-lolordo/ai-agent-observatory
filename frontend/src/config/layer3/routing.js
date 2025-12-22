/**
 * Layer 3 Configuration: Model Routing
 * 
 * Provides KPIs, diagnostic factors, fixes, and custom sections
 * for the Routing story's call detail view.
 * 
 * Location: src/config/layer3/routing.js
 */

import { formatCurrency } from '../../utils/formatters';

// =============================================================================
// KPIs - Top metrics bar
// =============================================================================

export function getKPIs(call) {
  const routing = call.routing_analysis || {};
  const kpis = [];
  
  // 1. Complexity Score
  const complexity = routing.complexity_score ?? call.complexity_score;
  if (complexity !== null && complexity !== undefined) {
    const complexityLabel = routing.complexity_label || 
      (complexity < 0.4 ? 'Low' : complexity < 0.7 ? 'Medium' : 'High');
    const complexityStatus = complexity < 0.4 ? 'success' : complexity < 0.7 ? 'warning' : 'critical';
    const complexityEmoji = complexity < 0.4 ? '🟢' : complexity < 0.7 ? '🟡' : '🔴';
    
    kpis.push({
      label: 'Complexity',
      value: `${complexityEmoji} ${complexity.toFixed(2)}`,
      subtext: complexityLabel,
      status: complexityStatus,
    });
  } else {
    kpis.push({
      label: 'Complexity',
      value: '—',
      subtext: 'Unknown',
      status: 'neutral',
    });
  }
  
  // 2. Quality Score
  const quality = call.judge_score;
  if (quality !== null && quality !== undefined) {
    const qualityStatus = quality >= 8 ? 'success' : quality >= 6 ? 'warning' : 'critical';
    kpis.push({
      label: 'Quality',
      value: `${quality.toFixed(1)}/10`,
      subtext: quality >= 8 ? 'Good' : quality >= 6 ? 'OK' : 'Poor',
      status: qualityStatus,
    });
  } else {
    kpis.push({
      label: 'Quality',
      value: '—',
      subtext: 'Not scored',
      status: 'neutral',
    });
  }
  
  // 3. Cost
  const cost = call.total_cost;
  if (cost !== null && cost !== undefined) {
    kpis.push({
      label: 'Cost',
      value: formatCurrency(cost),
      subtext: '',
      status: 'neutral',
    });
  }
  
  // 4. Current Model
  const model = call.model_name;
  if (model) {
    const isCheap = routing.is_cheap_model ?? false;
    kpis.push({
      label: 'Current Model',
      value: model,
      subtext: isCheap ? 'Budget tier' : 'Premium tier',
      status: 'neutral',
    });
  }
  
  // 5. Routing Opportunity
  const opportunity = routing.opportunity;
  if (opportunity) {
    const oppEmoji = routing.opportunity_emoji || (opportunity === 'downgrade' ? '↓' : opportunity === 'upgrade' ? '↑' : '✓');
    const oppLabel = routing.opportunity_label || opportunity.charAt(0).toUpperCase() + opportunity.slice(1);
    const oppStatus = opportunity === 'downgrade' ? 'info' : opportunity === 'upgrade' ? 'warning' : 'success';
    
    let oppSubtext = '';
    if (opportunity === 'downgrade') {
      oppSubtext = 'Save costs';
    } else if (opportunity === 'upgrade') {
      oppSubtext = 'Improve quality';
    } else {
      oppSubtext = 'Well matched';
    }
    
    kpis.push({
      label: 'Opportunity',
      value: `${oppEmoji} ${oppLabel}`,
      subtext: oppSubtext,
      status: oppStatus,
    });
  }
  
  return kpis;
}

// =============================================================================
// FACTORS - Diagnostic analysis
// =============================================================================

export function getFactors(call) {
  const routing = call.routing_analysis || {};
  const factors = [];
  
  const complexity = routing.complexity_score ?? call.complexity_score;
  const quality = call.judge_score;
  const opportunity = routing.opportunity;
  const isCheap = routing.is_cheap_model ?? false;
  const model = call.model_name || '';
  
  // Downgrade scenario factors
  if (opportunity === 'downgrade') {
    factors.push({
      label: 'Overpowered Model',
      status: 'info',
      detail: `Using ${model} for a low-complexity task (${complexity?.toFixed(2) || 'N/A'})`,
    });
    
    if (quality !== null && quality >= 8) {
      factors.push({
        label: 'High Quality Maintained',
        status: 'success',
        detail: `Quality score ${quality.toFixed(1)}/10 suggests simpler model would suffice`,
      });
    }
    
    const savings = routing.potential_savings;
    if (savings > 0) {
      factors.push({
        label: 'Cost Reduction Available',
        status: 'info',
        detail: `Potential savings of ${formatCurrency(savings)} per call (~${routing.potential_savings_pct}%)`,
      });
    }
  }
  
  // Upgrade scenario factors
  else if (opportunity === 'upgrade') {
    factors.push({
      label: 'Underpowered Model',
      status: 'warning',
      detail: `Using ${model} for a high-complexity task (${complexity?.toFixed(2) || 'N/A'})`,
    });
    
    if (quality !== null && quality < 8) {
      factors.push({
        label: 'Quality Below Threshold',
        status: 'critical',
        detail: `Quality score ${quality.toFixed(1)}/10 indicates need for stronger model`,
      });
    }
    
    factors.push({
      label: 'Complex Task Detected',
      status: 'warning',
      detail: 'Task complexity suggests need for advanced reasoning capabilities',
    });
  }
  
  // Keep scenario factors
  else {
    factors.push({
      label: 'Model Well-Matched',
      status: 'success',
      detail: `${model} is appropriate for this task complexity`,
    });
    
    if (complexity !== null && complexity !== undefined) {
      const complexityLabel = complexity < 0.4 ? 'low' : complexity < 0.7 ? 'medium' : 'high';
      factors.push({
        label: 'Complexity Aligned',
        status: 'success',
        detail: `Task complexity (${complexityLabel}) matches model capability`,
      });
    }
    
    if (quality !== null && quality >= 7) {
      factors.push({
        label: 'Quality Acceptable',
        status: 'success',
        detail: `Quality score ${quality.toFixed(1)}/10 meets expectations`,
      });
    }
  }
  
  // Add token-based complexity indicator
  if (call.prompt_tokens && call.completion_tokens) {
    const ratio = call.prompt_tokens / call.completion_tokens;
    if (ratio > 20) {
      factors.push({
        label: 'High Input/Output Ratio',
        status: 'info',
        detail: `${ratio.toFixed(0)}:1 ratio suggests extraction/classification task`,
      });
    } else if (ratio < 2) {
      factors.push({
        label: 'Low Input/Output Ratio',
        status: 'info',
        detail: `${ratio.toFixed(1)}:1 ratio suggests generation task`,
      });
    }
  }
  
  return factors;
}

// =============================================================================
// FIXES - Actionable recommendations
// =============================================================================

export function getFixes(call) {
  const routing = call.routing_analysis || {};
  const fixes = [];
  
  const opportunity = routing.opportunity;
  const suggestedModel = routing.suggested_model;
  const cost = call.total_cost || 0;
  const savingsPct = routing.potential_savings_pct || 0;
  const operationCount = call.operation_call_count || 1;
  
  // Downgrade fixes
  if (opportunity === 'downgrade') {
    fixes.push({
      title: 'Downgrade to GPT-3.5-Turbo',
      effort: 'Low',
      metrics: [
        { label: 'Cost Impact', value: '-73%', positive: true },
        { label: 'Latency Impact', value: '-40%', positive: true },
        { label: 'Quality Risk', value: 'Low', positive: true },
        { label: 'Est. Savings', value: formatCurrency(cost * 0.7 * operationCount) + '/period', positive: true },
      ],
      code: `# Simple model change
client.chat.completions.create(
    model="gpt-3.5-turbo",  # Changed from gpt-4o
    messages=messages,
    temperature=0.3
)`,
      bestFor: 'Simple classification, formatting, extraction, and summarization tasks',
    });
    
    fixes.push({
      title: 'Use Claude 3 Haiku',
      effort: 'Low',
      metrics: [
        { label: 'Cost Impact', value: '-85%', positive: true },
        { label: 'Latency Impact', value: '-60%', positive: true },
        { label: 'Quality Risk', value: 'Low-Medium', positive: true },
      ],
      code: `# Switch to Anthropic's fast model
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1024,
    messages=messages
)`,
      bestFor: 'High-volume, latency-sensitive operations',
    });
  }
  
  // Upgrade fixes
  else if (opportunity === 'upgrade') {
    fixes.push({
      title: 'Upgrade to GPT-4o',
      effort: 'Low',
      metrics: [
        { label: 'Cost Impact', value: '+200%', positive: false },
        { label: 'Latency Impact', value: '+50%', positive: false },
        { label: 'Quality Improvement', value: '+30%', positive: true },
      ],
      code: `# Upgrade to more capable model
client.chat.completions.create(
    model="gpt-4o",  # Changed from gpt-4o-mini
    messages=messages,
    temperature=0.7
)`,
      bestFor: 'Complex reasoning, analysis, multi-step tasks, and nuanced understanding',
    });
    
    fixes.push({
      title: 'Use Claude 3.5 Sonnet',
      effort: 'Low',
      metrics: [
        { label: 'Cost Impact', value: '+150%', positive: false },
        { label: 'Quality Improvement', value: '+25%', positive: true },
        { label: 'Context Window', value: '200K tokens', positive: true },
      ],
      code: `# Switch to Anthropic's balanced model
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=messages
)`,
      bestFor: 'Long-context tasks, coding, and detailed analysis',
    });
  }
  
  // Smart routing fix (always show)
  fixes.push({
    title: 'Implement Smart Router',
    effort: 'Medium',
    metrics: [
      { label: 'Cost Impact', value: '-40%', positive: true },
      { label: 'Quality Impact', value: 'Optimal', positive: true },
      { label: 'Implementation', value: '2-4 hours', positive: false },
    ],
    code: `# Complexity-based routing
def route_to_model(prompt: str, task_type: str) -> str:
    complexity = estimate_complexity(prompt, task_type)
    
    if complexity < 0.4:
        return "gpt-3.5-turbo"  # Simple tasks
    elif complexity < 0.7:
        return "gpt-4o-mini"    # Medium tasks
    else:
        return "gpt-4o"         # Complex tasks

def estimate_complexity(prompt: str, task_type: str) -> float:
    """Estimate task complexity 0-1 based on heuristics."""
    score = 0.0
    
    # Length-based complexity
    tokens = len(prompt.split())
    score += min(tokens / 2000, 0.3)
    
    # Task type complexity
    complex_tasks = ["analysis", "reasoning", "coding", "research"]
    if task_type in complex_tasks:
        score += 0.3
    
    # Keyword indicators
    complex_keywords = ["explain", "analyze", "compare", "evaluate"]
    if any(kw in prompt.lower() for kw in complex_keywords):
        score += 0.2
    
    return min(score, 1.0)`,
    bestFor: 'Mixed workloads with varying complexity levels',
  });
  
  // Caching fix for repeated patterns
  if (operationCount > 10) {
    fixes.push({
      title: 'Add Response Caching',
      effort: 'Medium',
      metrics: [
        { label: 'Cost Reduction', value: 'Up to 90%', positive: true },
        { label: 'Latency Reduction', value: 'Up to 95%', positive: true },
        { label: 'Cache Hit Requirement', value: 'Similar prompts', positive: false },
      ],
      code: `# Semantic caching for similar prompts
from functools import lru_cache
import hashlib

def get_cache_key(prompt: str, model: str) -> str:
    """Generate cache key from prompt signature."""
    # Normalize and hash the prompt
    normalized = prompt.lower().strip()
    return hashlib.sha256(f"{model}:{normalized}".encode()).hexdigest()[:16]

@lru_cache(maxsize=1000)
def cached_completion(cache_key: str, prompt: str, model: str):
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )`,
      bestFor: 'Operations with repeated or similar prompts',
    });
  }
  
  return fixes;
}

// =============================================================================
// CUSTOM SECTIONS - Additional analysis panels
// =============================================================================

export function getCustomSections(call) {
  const routing = call.routing_analysis || {};
  const sections = [];
  
  const complexity = routing.complexity_score ?? call.complexity_score;
  const operationAvgComplexity = call.comparison?.operation_avg_complexity;
  
  // Complexity Analysis Section
  if (complexity !== null && complexity !== undefined) {
    sections.push({
      id: 'complexity-analysis',
      title: 'Complexity Analysis',
      type: 'chart',
      data: {
        chartType: 'bar',
        items: [
          { 
            label: 'This Call', 
            value: complexity, 
            color: complexity < 0.4 ? '#22c55e' : complexity < 0.7 ? '#eab308' : '#ef4444',
            max: 1.0,
          },
          { 
            label: 'Low Threshold', 
            value: 0.4, 
            color: '#3b82f6',
            max: 1.0,
          },
          { 
            label: 'High Threshold', 
            value: 0.7, 
            color: '#8b5cf6',
            max: 1.0,
          },
        ],
      },
    });
  }
  
  // Routing Decision Section
  const opportunity = routing.opportunity;
  if (opportunity) {
    const model = call.model_name || 'Unknown';
    const suggestedModel = routing.suggested_model;
    
    sections.push({
      id: 'routing-decision',
      title: 'Routing Decision',
      type: 'cards',
      data: {
        cards: [
          {
            label: 'Current Model',
            value: model,
            icon: '🤖',
            color: routing.is_cheap_model ? 'blue' : 'purple',
          },
          {
            label: 'Task Type',
            value: complexity < 0.4 ? 'Simple' : complexity < 0.7 ? 'Medium' : 'Complex',
            icon: complexity < 0.4 ? '📝' : complexity < 0.7 ? '📊' : '🧠',
            color: complexity < 0.4 ? 'green' : complexity < 0.7 ? 'yellow' : 'red',
          },
          {
            label: 'Recommendation',
            value: opportunity === 'downgrade' 
              ? `Switch to ${suggestedModel || 'cheaper model'}`
              : opportunity === 'upgrade'
              ? `Switch to ${suggestedModel || 'stronger model'}`
              : 'Keep current model',
            icon: opportunity === 'downgrade' ? '↓' : opportunity === 'upgrade' ? '↑' : '✓',
            color: opportunity === 'downgrade' ? 'blue' : opportunity === 'upgrade' ? 'red' : 'green',
          },
        ],
      },
    });
  }
  
  // Model Comparison Section (if we have alternative models)
  if (call.alternative_models && call.alternative_models.length > 0) {
    sections.push({
      id: 'model-comparison',
      title: 'Alternative Models',
      type: 'table',
      data: {
        headers: ['Model', 'Est. Cost', 'Quality', 'Savings'],
        rows: call.alternative_models.map(alt => [
          alt.name,
          formatCurrency(alt.estimated_cost),
          alt.quality,
          formatCurrency((call.total_cost || 0) - alt.estimated_cost),
        ]),
      },
    });
  }
  
  return sections;
}

// =============================================================================
// EXPORT CONFIG OBJECT
// =============================================================================

export default {
  getKPIs,
  getFactors,
  getFixes,
  getCustomSections,
};