/**
 * Quality Story - Layer 3 Configuration
 * 
 * UPDATED:
 * - Color fixed to #ef4444 (red)
 * - Lower thresholds for factor detection
 * - Fallback factors when criteria_scores not available
 * - More fix recommendations
 */

// ─────────────────────────────────────────────────────────────────────────────
// STORY METADATA
// ─────────────────────────────────────────────────────────────────────────────

export const QUALITY_STORY = {
  id: 'quality',
  label: 'Quality Analysis',
  icon: '⭐',
  color: '#ef4444', // Red - FIXED (was #eab308)
  entityType: 'call',
};

// ─────────────────────────────────────────────────────────────────────────────
// THRESHOLDS (lowered for better detection)
// ─────────────────────────────────────────────────────────────────────────────

const THRESHOLDS = {
  quality_critical: 5.0,
  quality_low: 7.0,
  quality_good: 8.0,
  criteria_low: 7.0,      // Criteria score below this triggers factor
  criteria_critical: 5.0, // Criteria score below this is critical
  short_response: 100,    // Completion tokens below this may indicate issue
};

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

function getScoreStatus(score) {
  if (score === null || score === undefined) {
    return { status: 'unknown', emoji: '⚪', label: 'Not Evaluated', color: 'text-slate-400' };
  }
  if (score < THRESHOLDS.quality_critical) {
    return { status: 'critical', emoji: '🔴', label: 'Critical', color: 'text-red-400' };
  }
  if (score < THRESHOLDS.quality_low) {
    return { status: 'low', emoji: '🟡', label: 'Low', color: 'text-yellow-400' };
  }
  if (score < THRESHOLDS.quality_good) {
    return { status: 'ok', emoji: '🟢', label: 'Acceptable', color: 'text-green-400' };
  }
  return { status: 'good', emoji: '🟢', label: 'Good', color: 'text-green-400' };
}

// Extract quality evaluation from various possible locations in call data
function extractQualityEvaluation(call) {
  // Try different possible locations
  if (call.quality_evaluation) return call.quality_evaluation;
  if (call.judge_evaluation) return call.judge_evaluation;
  if (call.evaluation) return call.evaluation;
  
  // Build from individual fields if available
  return {
    overall_score: call.judge_score,
    confidence: call.judge_confidence,
    reasoning: call.judge_reasoning,
    criteria_scores: call.criteria_scores,
    issues_found: call.quality_issues || call.issues_found,
    strengths: call.quality_strengths || call.strengths,
    suggestions: call.quality_suggestions || call.suggestions,
    hallucination_flag: call.hallucination_flag,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getQualityKPIs(call, operationStats = null) {
  const score = call.judge_score;
  const evaluation = extractQualityEvaluation(call);
  const confidence = evaluation.confidence;
  const hallucination = call.hallucination_flag || evaluation.hallucination_flag || false;
  const scoreStatus = getScoreStatus(score);

  // Calculate vs operation average
  let vsAvg = null;
  let vsAvgStatus = 'neutral';
  if (operationStats?.avg_score && score !== null) {
    vsAvg = score - operationStats.avg_score;
    vsAvgStatus = vsAvg >= 0 ? 'good' : 'warning';
  }

  return [
    {
      label: 'Quality Score',
      value: score !== null ? `${score.toFixed(1)}/10` : '—',
      subtext: scoreStatus.label,
      status: scoreStatus.status === 'critical' ? 'critical' :
              scoreStatus.status === 'low' ? 'warning' : 'good',
    },
    {
      label: 'Confidence',
      value: confidence ? `${(confidence * 100).toFixed(0)}%` : '—',
      subtext: 'Judge certainty',
      status: confidence && confidence < 0.7 ? 'warning' : 'neutral',
    },
    {
      label: 'Hallucination',
      value: hallucination ? '⚠️ Yes' : '✓ No',
      subtext: 'Factual accuracy',
      status: hallucination ? 'critical' : 'good',
    },
    {
      label: 'vs Op. Avg',
      value: vsAvg !== null ? `${vsAvg >= 0 ? '+' : ''}${vsAvg.toFixed(1)}` : '—',
      subtext: operationStats ? `Avg: ${operationStats.avg_score?.toFixed(1)}/10` : 'No data',
      status: vsAvgStatus,
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// CURRENT STATE (for comparison table)
// ─────────────────────────────────────────────────────────────────────────────

export function getQualityCurrentState(call) {
  const score = call.judge_score;
  const hallucination = call.hallucination_flag || false;
  
  return {
    quality: score !== null ? `${score.toFixed(1)}/10` : '—',
    hallucination: hallucination ? 'Yes' : 'No',
    tokens: call.completion_tokens?.toLocaleString() || '0',
    cost: `$${(call.total_cost || 0).toFixed(3)}`,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FACTOR DETECTION (improved with fallbacks)
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeQualityFactors(call) {
  const factors = [];
  const score = call.judge_score;
  const evaluation = extractQualityEvaluation(call);
  const hallucination = call.hallucination_flag || evaluation.hallucination_flag || false;
  const isError = call.success === false || call.status === 'error';
  
  // Extract criteria scores if available
  const criteria = evaluation.criteria_scores || evaluation.criteria || {};
  const hasCriteria = Object.keys(criteria).length > 0;
  
  // Factor: Low overall score
  if (score !== null && score < THRESHOLDS.quality_low) {
    const severity = score < THRESHOLDS.quality_critical ? 'critical' : 'warning';
    factors.push({
      id: 'low_quality_score',
      severity,
      label: `Low Quality Score: ${score.toFixed(1)}/10`,
      impact: severity === 'critical' ? 'Response may be unusable' : 'Response needs improvement',
      description: 'Overall quality score is below acceptable threshold.',
      hasFix: true,
    });
  }
  
  // Factor: Hallucination detected
  if (hallucination) {
    factors.push({
      id: 'hallucination_detected',
      severity: 'critical',
      label: 'Hallucination Detected',
      impact: 'Response contains unverified or false claims',
      description: 'The model made claims not supported by the input data.',
      hasFix: true,
    });
  }
  
  // Factor: Error in response
  if (isError) {
    factors.push({
      id: 'response_error',
      severity: 'critical',
      label: 'Response Error',
      impact: 'Call failed or returned error',
      description: call.error_message || 'The API call resulted in an error.',
      hasFix: true,
    });
  }
  
  // === CRITERIA-BASED FACTORS (when available) ===
  if (hasCriteria) {
    // Factor: Low accuracy
    if (criteria.accuracy !== undefined && criteria.accuracy < THRESHOLDS.criteria_low) {
      factors.push({
        id: 'low_accuracy',
        severity: criteria.accuracy < THRESHOLDS.criteria_critical ? 'critical' : 'warning',
        label: `Low Accuracy: ${criteria.accuracy.toFixed(1)}/10`,
        impact: 'Response contains factual errors',
        description: 'The response includes inaccurate information or unsupported claims.',
        hasFix: true,
      });
    }
    
    // Factor: Low helpfulness
    if (criteria.helpfulness !== undefined && criteria.helpfulness < THRESHOLDS.criteria_low) {
      factors.push({
        id: 'low_helpfulness',
        severity: criteria.helpfulness < THRESHOLDS.criteria_critical ? 'critical' : 'warning',
        label: `Low Helpfulness: ${criteria.helpfulness.toFixed(1)}/10`,
        impact: 'Response lacks actionable recommendations',
        description: 'The response doesn\'t adequately address user needs.',
        hasFix: true,
      });
    }
    
    // Factor: Low completeness
    if (criteria.completeness !== undefined && criteria.completeness < THRESHOLDS.criteria_low) {
      factors.push({
        id: 'incomplete_response',
        severity: criteria.completeness < THRESHOLDS.criteria_critical ? 'critical' : 'warning',
        label: `Incomplete Response: ${criteria.completeness.toFixed(1)}/10`,
        impact: 'Missing required sections or analysis',
        description: 'The response doesn\'t cover all requested topics.',
        hasFix: true,
      });
    }
    
    // Factor: Low coherence
    if (criteria.coherence !== undefined && criteria.coherence < THRESHOLDS.criteria_low) {
      factors.push({
        id: 'low_coherence',
        severity: 'warning',
        label: `Low Coherence: ${criteria.coherence.toFixed(1)}/10`,
        impact: 'Response structure could be improved',
        description: 'The response lacks clear organization or flow.',
        hasFix: true,
      });
    }
    
    // Factor: Low relevance
    if (criteria.relevance !== undefined && criteria.relevance < THRESHOLDS.criteria_low) {
      factors.push({
        id: 'low_relevance',
        severity: criteria.relevance < THRESHOLDS.criteria_critical ? 'critical' : 'warning',
        label: `Low Relevance: ${criteria.relevance.toFixed(1)}/10`,
        impact: 'Response doesn\'t address the query well',
        description: 'The response may be off-topic or miss the main question.',
        hasFix: true,
      });
    }
  }
  
  // === FALLBACK FACTORS (when criteria not available) ===
  if (!hasCriteria && score !== null && score < THRESHOLDS.quality_low) {
    // Infer potential issues from low score
    factors.push({
      id: 'potential_accuracy_issue',
      severity: 'warning',
      label: 'Potential Accuracy Issue',
      impact: 'Low score may indicate factual problems',
      description: 'Consider adding accuracy constraints to the prompt.',
      hasFix: true,
    });
    
    factors.push({
      id: 'potential_completeness_issue',
      severity: 'warning',
      label: 'Potential Completeness Issue',
      impact: 'Response may be missing required content',
      description: 'Consider enforcing required sections in the prompt.',
      hasFix: true,
    });
  }
  
  // Factor: Very short response
  if (call.completion_tokens && call.completion_tokens < THRESHOLDS.short_response && score !== null && score < THRESHOLDS.quality_good) {
    factors.push({
      id: 'very_short_response',
      severity: 'info',
      label: `Short Response: ${call.completion_tokens} tokens`,
      impact: 'May lack sufficient detail',
      description: 'The response may be too brief to be useful.',
      hasFix: true,
    });
  }
  
  // Factor: No max_tokens (may cause inconsistent output)
  if ((call.max_tokens === null || call.max_tokens === undefined) && score !== null && score < THRESHOLDS.quality_good) {
    factors.push({
      id: 'no_output_control',
      severity: 'info',
      label: 'No Output Length Control',
      impact: 'Response length is unbounded',
      description: 'Setting max_tokens can improve consistency.',
      hasFix: true,
    });
  }
  
  // Factor: High temperature with quality issues
  if (call.temperature && call.temperature > 0.7 && score !== null && score < THRESHOLDS.quality_low) {
    factors.push({
      id: 'high_temperature',
      severity: 'info',
      label: `High Temperature: ${call.temperature}`,
      impact: 'May cause less consistent outputs',
      description: 'Lower temperature can improve factual accuracy.',
      hasFix: true,
    });
  }
  
  // Sort by severity
  const severityOrder = { critical: 0, warning: 1, info: 2, ok: 3 };
  factors.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return factors;
}

// ─────────────────────────────────────────────────────────────────────────────
// CRITERIA BREAKDOWN
// ─────────────────────────────────────────────────────────────────────────────

export function getQualityCriteriaBreakdown(call) {
  const evaluation = extractQualityEvaluation(call);
  const criteria = evaluation.criteria_scores || evaluation.criteria || {};
  
  const breakdown = [];
  
  const criteriaConfig = [
    { key: 'relevance', label: 'Relevance', description: 'How well the response addresses the query' },
    { key: 'accuracy', label: 'Accuracy', description: 'Factual correctness of claims' },
    { key: 'completeness', label: 'Completeness', description: 'Coverage of required topics' },
    { key: 'coherence', label: 'Coherence', description: 'Organization and flow' },
    { key: 'helpfulness', label: 'Helpfulness', description: 'Actionable value provided' },
  ];
  
  criteriaConfig.forEach(({ key, label, description }) => {
    if (criteria[key] !== undefined) {
      breakdown.push({
        key,
        label,
        score: criteria[key],
        maxScore: 10,
        description,
        status: criteria[key] >= 7 ? 'good' : criteria[key] >= 5 ? 'warning' : 'critical',
      });
    }
  });
  
  return breakdown;
}

// ─────────────────────────────────────────────────────────────────────────────
// JUDGE EVALUATION DETAILS
// ─────────────────────────────────────────────────────────────────────────────

export function getJudgeEvaluation(call) {
  const evaluation = extractQualityEvaluation(call);
  
  return {
    reasoning: evaluation.reasoning || evaluation.judge_reasoning || null,
    issues_found: evaluation.issues_found || evaluation.issues || [],
    strengths: evaluation.strengths || [],
    suggestions: evaluation.suggestions || evaluation.recommendations || [],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX DEFINITIONS (more fixes, lower trigger thresholds)
// ─────────────────────────────────────────────────────────────────────────────

export function getQualityFixes(call, factors) {
  const fixes = [];
  const evaluation = extractQualityEvaluation(call);
  const criteria = evaluation.criteria_scores || evaluation.criteria || {};
  const score = call.judge_score;
  
  // Fix 1: Add Accuracy Constraints
  // Triggers on: hallucination, low accuracy, OR low overall score
  if (factors.some(f => ['hallucination_detected', 'low_accuracy', 'potential_accuracy_issue', 'low_quality_score'].includes(f.id))) {
    fixes.push({
      id: 'add_accuracy_constraints',
      title: 'Add Accuracy Constraints',
      subtitle: 'Prevent hallucinations with citation requirements',
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: factors.some(f => f.id === 'hallucination_detected'),
      
      metrics: [
        {
          label: 'Accuracy',
          before: criteria.accuracy ? `${criteria.accuracy.toFixed(1)}` : '—',
          after: '+2.0',
          changePercent: 40,
        },
        {
          label: 'Halluc.',
          before: call.hallucination_flag ? 'Yes' : '—',
          after: 'Reduced',
          changePercent: -80,
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: 'Same',
          changePercent: 0,
        },
        {
          label: 'Overall',
          before: score ? `${score.toFixed(1)}` : '—',
          after: '+1.5',
          changePercent: 20,
        },
      ],
      
      codeBefore: `system_prompt = """
You are an expert analyst. Provide a detailed 
assessment of the candidate based on their resume.
"""`,
      codeAfter: `system_prompt = """
You are an expert analyst. Provide a detailed 
assessment of the candidate based on their resume.

IMPORTANT ACCURACY RULES:
- Only state facts that appear explicitly in the resume
- Prefix uncertain claims with "The resume suggests..."
- If information is not provided, say "Not mentioned"
- Never invent or assume details not in the source
"""`,
      
      tradeoffs: [
        'May produce more hedged language',
        'Could result in more "not mentioned" responses',
        'Slightly longer prompts',
      ],
      benefits: [
        'Significantly reduces hallucinations',
        'Builds user trust in outputs',
        'Easier to verify claims',
        'No additional cost',
      ],
      bestFor: 'Any task requiring factual accuracy',
    });
  }
  
  // Fix 2: Enforce Required Sections
  // Triggers on: incomplete, low helpfulness, potential completeness issue, OR low score
  if (factors.some(f => ['incomplete_response', 'low_helpfulness', 'potential_completeness_issue', 'very_short_response', 'low_quality_score'].includes(f.id))) {
    fixes.push({
      id: 'enforce_sections',
      title: 'Enforce Required Sections',
      subtitle: 'Use structured output to guarantee completeness',
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      recommended: factors.some(f => f.id === 'incomplete_response'),
      
      metrics: [
        {
          label: 'Complete',
          before: criteria.completeness ? `${criteria.completeness.toFixed(1)}` : '—',
          after: '+2.0',
          changePercent: 40,
        },
        {
          label: 'Helpful',
          before: criteria.helpfulness ? `${criteria.helpfulness.toFixed(1)}` : '—',
          after: '+1.5',
          changePercent: 30,
        },
        {
          label: 'Tokens',
          before: `${call.completion_tokens || 0}`,
          after: '+20%',
          changePercent: 20,
        },
        {
          label: 'Overall',
          before: score ? `${score.toFixed(1)}` : '—',
          after: '+1.0',
          changePercent: 15,
        },
      ],
      
      codeBefore: `system_prompt = """
Analyze the candidate and provide your assessment.
"""`,
      codeAfter: `system_prompt = """
Analyze the candidate and provide your assessment.

YOU MUST INCLUDE ALL OF THESE SECTIONS:
1. **Skills Match** - Rate 1-10 with specific evidence
2. **Experience Analysis** - Years and relevance
3. **Concerns** - At least 2 potential issues
4. **Recommendation** - Clear hire/no-hire with reasoning

Do not skip any section.
"""`,
      
      tradeoffs: [
        'Slightly longer responses',
        'Less flexibility in output format',
        'May force content even when not applicable',
      ],
      benefits: [
        'Guarantees all required information',
        'Consistent output structure',
        'Easier to parse programmatically',
        'Reduces follow-up questions',
      ],
      bestFor: 'Structured analysis tasks with specific requirements',
    });
  }
  
  // Fix 3: Add Few-Shot Examples
  // Triggers on: low quality, low helpfulness, low coherence, OR moderate score
  if (factors.some(f => ['low_quality_score', 'low_helpfulness', 'low_coherence', 'low_relevance'].includes(f.id)) || (score !== null && score < THRESHOLDS.quality_good)) {
    fixes.push({
      id: 'add_examples',
      title: 'Add Few-Shot Examples',
      subtitle: 'Include good/bad examples to guide output quality',
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      
      metrics: [
        {
          label: 'Quality',
          before: score ? `${score.toFixed(1)}` : '—',
          after: '+1.5',
          changePercent: 20,
        },
        {
          label: 'Coherence',
          before: criteria.coherence ? `${criteria.coherence.toFixed(1)}` : '—',
          after: '+2.0',
          changePercent: 30,
        },
        {
          label: 'Tokens',
          before: `${call.prompt_tokens || 0}`,
          after: '+300',
          changePercent: 10,
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: '+5%',
          changePercent: 5,
        },
      ],
      
      codeBefore: `system_prompt = """
Analyze the candidate.
"""`,
      codeAfter: `system_prompt = """
Analyze the candidate.

EXAMPLE OF GOOD OUTPUT:
"The candidate shows strong Python expertise (7 years per resume). 
Their AWS experience aligns well with our cloud-first architecture.
Concern: No management experience for a senior role.
Recommendation: Proceed to technical interview."

EXAMPLE OF BAD OUTPUT (avoid this):
"Looks good. Has skills. Would hire."
"""`,
      
      tradeoffs: [
        'Increases prompt tokens (~300)',
        'Slightly higher cost per call',
        'Examples may bias toward specific style',
      ],
      benefits: [
        'Significantly improves output quality',
        'More consistent formatting',
        'Reduces need for iteration',
        'Clear expectations for model',
      ],
      bestFor: 'Complex tasks where quality is inconsistent',
    });
  }
  
  // Fix 4: Adjust Temperature
  // Triggers on: high temperature issue OR inconsistent quality
  if (factors.some(f => f.id === 'high_temperature') || (score !== null && score < 6)) {
    fixes.push({
      id: 'adjust_temperature',
      title: 'Lower Temperature',
      subtitle: 'Reduce randomness for more consistent outputs',
      effort: 'Low',
      effortColor: 'text-green-400',
      
      metrics: [
        {
          label: 'Consistency',
          before: 'Variable',
          after: 'Stable',
          changePercent: 50,
        },
        {
          label: 'Accuracy',
          before: criteria.accuracy ? `${criteria.accuracy.toFixed(1)}` : '—',
          after: '+1.0',
          changePercent: 15,
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: 'Same',
          changePercent: 0,
        },
        {
          label: 'Creativity',
          before: 'High',
          after: 'Lower',
          changePercent: -30,
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    temperature=${call.temperature || 0.7},
    messages=messages
)`,
      codeAfter: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    temperature=0.3,  # Lower for factual tasks
    messages=messages
)`,
      
      tradeoffs: [
        'Less creative/varied outputs',
        'May feel more repetitive',
        'Not ideal for creative writing',
      ],
      benefits: [
        'More deterministic outputs',
        'Better factual accuracy',
        'Easier to test and validate',
        'No additional cost',
      ],
      bestFor: 'Factual analysis and structured tasks',
    });
  }
  
  // Fix 5: Use Stronger Model (when score is very low)
  if (score !== null && score < THRESHOLDS.quality_critical) {
    fixes.push({
      id: 'upgrade_model',
      title: 'Upgrade to Stronger Model',
      subtitle: 'Use GPT-4o or Claude Opus for complex tasks',
      effort: 'Low',
      effortColor: 'text-green-400',
      
      metrics: [
        {
          label: 'Quality',
          before: `${score.toFixed(1)}`,
          after: '+2.0',
          changePercent: 40,
        },
        {
          label: 'Accuracy',
          before: '—',
          after: '+25%',
          changePercent: 25,
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: '3-5x',
          changePercent: 300,
        },
        {
          label: 'Latency',
          before: `${((call.latency_ms || 0) / 1000).toFixed(1)}s`,
          after: '+50%',
          changePercent: 50,
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o-mini'}",
    messages=messages
)`,
      codeAfter: `response = client.chat.completions.create(
    model="gpt-4o",  # or "claude-3-opus"
    messages=messages
)`,
      
      tradeoffs: [
        'Significantly higher cost',
        'Slower response times',
        'May be overkill for simple tasks',
      ],
      benefits: [
        'Best-in-class reasoning',
        'Better handling of complex prompts',
        'More nuanced analysis',
        'Fewer errors and hallucinations',
      ],
      bestFor: 'Complex analysis where quality is critical',
    });
  }

  return fixes.slice(0, 4); // Max 4 fixes
}

// ─────────────────────────────────────────────────────────────────────────────
// CONFIG HIGHLIGHTS
// ─────────────────────────────────────────────────────────────────────────────

export function getQualityConfigHighlights(call, factors) {
  const highlights = [];
  const score = call.judge_score;

  if (score !== null && score < THRESHOLDS.quality_critical) {
    highlights.push({
      key: 'score',
      message: `${score.toFixed(1)} CRITICAL`,
      severity: 'critical',
    });
  } else if (score !== null && score < THRESHOLDS.quality_low) {
    highlights.push({
      key: 'score',
      message: `${score.toFixed(1)} LOW`,
      severity: 'warning',
    });
  }

  if (call.hallucination_flag) {
    highlights.push({
      key: 'hallucination',
      message: 'HALLUCINATION',
      severity: 'critical',
    });
  }

  if (call.temperature && call.temperature > 0.7) {
    highlights.push({
      key: 'temperature',
      message: `TEMP ${call.temperature}`,
      severity: 'info',
    });
  }

  return highlights;
}

// ─────────────────────────────────────────────────────────────────────────────
// SIMILAR PANEL CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export const QUALITY_SIMILAR_CONFIG = {
  filterOptions: [
    { id: 'same_operation', label: 'Same Operation' },
    { id: 'low_quality', label: 'Low Quality (<7)' },
    { id: 'high_quality', label: 'High Quality (8+)' },
  ],
  defaultFilter: 'same_operation',
  
  columns: [
    { key: 'call_id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
    { key: 'judge_score', label: 'Score', format: (v) => v !== null ? `${v.toFixed(1)}/10` : '—' },
    { key: 'hallucination_flag', label: 'Halluc.', format: (v) => v ? '⚠️' : '✓' },
    { key: 'completion_tokens', label: 'Output', format: (v) => v?.toLocaleString() },
    { key: 'total_cost', label: 'Cost', format: (v) => `$${v?.toFixed(3)}` },
  ],
};

// ─────────────────────────────────────────────────────────────────────────────
// RAW PANEL CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export const QUALITY_RAW_CONFIG = {
  sections: [
    'systemPrompt',
    'userMessage', 
    'response',
    'qualityEvaluation',  // NEW: Judge evaluation JSON
    'modelConfig',
  ],
};