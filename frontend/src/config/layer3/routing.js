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

  const verdict = routing.verdict; // optimal, overprovisioned, underprovisioned
  const complexity = routing.complexity_score ?? call.complexity_score;
  const quality = call.judge_score;
  const model = call.model_name || '';

  // Use verdict for clearer logic - include `id` for fix system mapping
  if (verdict === 'overprovisioned') {
    factors.push({
      id: 'overprovisioned',  // Maps to FACTOR_FIX_MAP
      label: 'Model Overprovisioned',
      status: 'warning',
      severity: 'warning',
      detail: routing.reasoning || `Using ${model} for a task that could use a cheaper model`,
      hasFix: true,
    });

    const savings = routing.potential_savings_usd;
    if (savings > 0) {
      factors.push({
        id: 'cost_reduction_available',  // Maps to FACTOR_FIX_MAP
        label: 'Cost Reduction Available',
        status: 'info',
        severity: 'info',
        detail: `Potential savings of ${formatCurrency(savings)} per call (${routing.quality_impact})`,
        hasFix: true,
      });
    }
  }

  else if (verdict === 'underprovisioned') {
    factors.push({
      id: 'underprovisioned',  // Maps to FACTOR_FIX_MAP
      label: 'Model Underprovisioned',
      status: 'critical',
      severity: 'critical',
      detail: routing.reasoning || `Using ${model} for a task that needs more capable model`,
      hasFix: true,
    });

    if (quality !== null && quality < 8) {
      factors.push({
        id: 'low_quality_score',  // Maps to FACTOR_FIX_MAP
        label: 'Quality Below Target',
        status: 'critical',
        severity: 'critical',
        detail: `Quality score ${quality.toFixed(1)}/10 suggests need for stronger model`,
        hasFix: true,
      });
    }
  }

  else { // optimal
    factors.push({
      id: 'optimal_routing',
      label: 'Model Well-Matched',
      status: 'success',
      severity: 'ok',
      detail: routing.reasoning || `${model} is appropriate for this task`,
      hasFix: false,
    });
  }

  // Check for premium model that could be downgraded (even without routing analysis)
  if (!verdict) {
    const isPremium = model.includes('gpt-4o') && !model.includes('mini') ||
                      model.includes('claude-3-opus') ||
                      model.includes('claude-3-sonnet');
    if (isPremium && complexity < 0.5) {
      factors.push({
        id: 'premium_model',  // Maps to FACTOR_FIX_MAP
        label: 'Premium Model for Simple Task',
        status: 'warning',
        severity: 'warning',
        detail: `Using ${model} (premium) for a task with complexity ${(complexity * 100).toFixed(0)}%`,
        hasFix: true,
      });
    }
  }

  // Show complexity breakdown if available
  if (routing.complexity_breakdown) {
    const breakdown = routing.complexity_breakdown;
    const topFactors = Object.entries(breakdown)
      .sort((a, b) => b[1].value - a[1].value)
      .slice(0, 2); // Top 2 contributors

    topFactors.forEach(([key, data]) => {
      factors.push({
        id: `complexity_${key}`,
        label: `${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Factor`,
        status: 'info',
        severity: 'info',
        detail: `${data.label} contributes ${(data.value * 100).toFixed(0)}% to complexity`,
        hasFix: false,
      });
    });
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
  
  // Alternative Models Table Data
  if (routing.alternatives && routing.alternatives.length > 0) {
    sections.push({
      id: 'alternatives-table',
      title: '📊 Alternative Models Comparison',
      type: 'table',
      data: {
        headers: ['Model', 'Quality', 'Est. Cost', 'Latency', 'Verdict'],
        rows: routing.alternatives.map(alt => ({
          model: alt.model,
          quality: alt.estimated_quality,
          cost: alt.estimated_cost,
          latency: alt.latency_delta,
          verdict: alt.verdict,
        })),
      },
    });
  }
  
  // Complexity Breakdown Data
  if (routing.complexity_breakdown) {
    sections.push({
      id: 'complexity-breakdown',
      title: '🎯 Complexity Breakdown',
      type: 'breakdown',
      data: {
        items: Object.entries(routing.complexity_breakdown).map(([key, data]) => ({
          label: key.replace(/_/g, ' '),
          value: data.value,
          description: data.label,
        })),
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