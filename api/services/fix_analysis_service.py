"""
LLM-Powered Fix Analysis Service
Location: api/services/fix_analysis_service.py

Uses LLM to analyze a call and generate tailored fix recommendations.
This replaces static rule-based recommendations with context-aware analysis.
"""

import json
import hashlib
import os  
from typing import Dict, Any, Optional, List
from datetime import datetime

from observatory.storage import ObservatoryStorage


# Cache for analysis results (avoid re-analyzing same calls)
_analysis_cache: Dict[str, Dict] = {}

# Lazy-loaded OpenAI client
_openai_client = None

def _get_openai_client():
    """Get or create Azure OpenAI client."""
    global _openai_client
    if _openai_client is None:
        import os
        from openai import AzureOpenAI
        _openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        )
    return _openai_client


# =============================================================================
# ANALYSIS PROMPT TEMPLATE
# =============================================================================

ANALYSIS_PROMPT = """You are an expert at optimizing LLM applications. Analyze this LLM call and provide exactly 3 specific, actionable recommendations to reduce cost and latency while preserving essential functionality.

## CURRENT CALL DATA

**Operation:** {operation}
**Agent:** {agent_name}
**Model:** {model_name}
**Latency:** {latency_ms}ms ({latency_seconds}s)
**Tokens:** {prompt_tokens} input → {completion_tokens} output ({total_tokens} total)
**Cost:** ${total_cost:.4f}
**max_tokens setting:** {max_tokens}
**temperature:** {temperature}

---

**SYSTEM PROMPT:**
```
{system_prompt}
```

---

**USER MESSAGE:**
```
{user_message}
```

---

**RESPONSE:**
```
{response_text}
```

---

## YOUR TASK

Analyze this call deeply and answer:
1. What is this call trying to accomplish?
2. What parts of the response are ESSENTIAL vs REDUNDANT/VERBOSE?
3. Is the prompt efficient or bloated? Are there unnecessary instructions?
4. Is the output format optimal? Would JSON be better than prose? Vice versa?
5. Is this the right model for this task? Could a cheaper model work?
6. Are there obvious caching opportunities (repeated identical calls)?

Then provide exactly 3 recommendations, ranked by impact (highest first).

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown, no code blocks):

{{
  "analysis": {{
    "purpose": "One sentence describing what this call does",
    "essential_output": ["list", "of", "essential", "fields/data"],
    "redundant_output": ["list", "of", "unnecessary", "content"],
    "prompt_issues": ["list", "of", "prompt", "problems"],
    "output_format_assessment": "Is the current format optimal? Suggest better format if not."
  }},
  "recommendations": [
    {{
      "id": "rec_1",
      "title": "Short actionable title (e.g., 'Switch to Structured JSON Output')",
      "priority": "high",
      "problem": "What's wrong - be specific (1-2 sentences)",
      "solution": "What to change - be specific (1-2 sentences)",
      "implementation": {{
        "code_before": "Show the CURRENT code pattern being used (e.g., 'messages = conversation_history' or 'response_format=None')",
        "code_after": "Show the NEW code implementation needed. Include actual Python code snippets, function definitions, or configuration changes. Be specific and copy-paste ready."
      }},
      "new_prompt": "The actual rewritten system prompt - FULL TEXT ready to copy. If the fix doesn't involve changing the prompt, write 'N/A'",
      "expected_output_example": "Show what the optimized output would look like (abbreviated if long)",
      "estimated_impact": {{
        "tokens_before": {completion_tokens},
        "tokens_after": <your estimate>,
        "token_reduction_pct": <percentage reduction>,
        "latency_reduction_pct": <percentage reduction>,
        "cost_reduction_pct": <percentage reduction>
      }},
      "preserves": ["what essential functionality is kept"],
      "tradeoffs": ["what is lost or requires code changes"],
      "effort": "Low|Medium|High",
      "confidence": <0.0 to 1.0 - how confident are you this will help?>
    }},
    {{
      "id": "rec_2",
      ...second recommendation...
    }},
    {{
      "id": "rec_3", 
      ...third recommendation...
    }}
  ]
}}

IMPORTANT:
- Be specific and actionable - vague advice like "simplify the prompt" is not helpful
- The new_prompt field should be copy-paste ready when applicable
- Estimate realistic impacts based on the actual content
- If the call is already well-optimized, say so and suggest minor improvements
- Consider: max_tokens limits, structured output (JSON), caching, model routing, prompt compression
"""


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_call_for_fixes(call_id: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Analyze a call using LLM and return tailored fix recommendations.
    
    Args:
        call_id: The LLM call ID to analyze
        use_cache: Whether to use cached results (default True)
        
    Returns:
        Dict with analysis and 3 recommendations
    """
    # Check cache first
    if use_cache and call_id in _analysis_cache:
        cached = _analysis_cache[call_id]
        cached['from_cache'] = True
        return cached
    
    # 1. Fetch call from database
    call = ObservatoryStorage.get_llm_call_by_id(call_id)
    if not call:
        return {"error": f"Call not found: {call_id}"}
    
    # 2. Extract fields (handle missing data gracefully)
    system_prompt = _get_system_prompt(call)
    user_message = _get_user_message(call)
    response_text = _get_response_text(call)
    
    # Check if we have enough data
    if not system_prompt and not user_message:
        return {
            "error": "Insufficient data for analysis",
            "details": "Neither system_prompt nor user_message is available for this call.",
            "call_id": call_id,
        }
    
    # Truncate if too long (to fit in context window)
    system_prompt = _truncate(system_prompt, 4000)
    user_message = _truncate(user_message, 3000)
    response_text = _truncate(response_text, 4000)
    
    # 3. Build prompt - safely access all call attributes
    latency_ms = getattr(call, 'latency_ms', 0) or 0
    prompt = ANALYSIS_PROMPT.format(
        operation=getattr(call, 'operation', 'unknown') or "unknown",
        agent_name=getattr(call, 'agent_name', 'unknown') or "unknown",
        model_name=getattr(call, 'model_name', 'unknown') or "unknown",
        latency_ms=latency_ms,
        latency_seconds=latency_ms / 1000 if latency_ms else 0,
        prompt_tokens=getattr(call, 'prompt_tokens', 0) or 0,
        completion_tokens=getattr(call, 'completion_tokens', 0) or 0,
        total_tokens=(getattr(call, 'prompt_tokens', 0) or 0) + (getattr(call, 'completion_tokens', 0) or 0),
        total_cost=getattr(call, 'total_cost', 0) or 0,
        max_tokens=getattr(call, 'max_tokens', None) or "NOT SET",
        temperature=getattr(call, 'temperature', None) if getattr(call, 'temperature', None) is not None else "default",
        system_prompt=system_prompt or "[Not captured]",
        user_message=user_message or "[Not captured]",
        response_text=response_text or "[Not captured]",
    )
    
    # 4. Call LLM for analysis
    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert LLM optimization consultant. Analyze the given LLM call and provide specific, actionable recommendations. Return ONLY valid JSON - no markdown, no code blocks, no explanation outside the JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temp for consistent analysis
            max_tokens=3000,
        )
        
        result_text = response.choices[0].message.content
        
        # 5. Parse JSON response
        result = _parse_llm_response(result_text)
        
        if "error" in result:
            return result
        
        # Add metadata
        result["call_id"] = call_id
        result["analysis_model"] = "gpt-4o"
        result["analysis_timestamp"] = datetime.utcnow().isoformat()
        result["analysis_cost"] = _estimate_analysis_cost(response.usage)
        result["from_cache"] = False
        
        # Cache the result
        _analysis_cache[call_id] = result
        
        return result
        
    except Exception as e:
        return {
            "error": "Analysis failed",
            "details": str(e),
            "call_id": call_id,
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_system_prompt(call) -> str:
    """Extract system prompt from call."""
    # Try direct attribute first (with safe access)
    system_prompt = getattr(call, 'system_prompt', None)
    if system_prompt:
        return system_prompt
    
    # Try prompt_metadata
    prompt_metadata = getattr(call, 'prompt_metadata', None)
    if prompt_metadata:
        if isinstance(prompt_metadata, dict) and prompt_metadata.get('system_prompt'):
            return prompt_metadata['system_prompt']
        if hasattr(prompt_metadata, 'system_prompt') and prompt_metadata.system_prompt:
            return prompt_metadata.system_prompt
    
    # Try prompt_breakdown
    prompt_breakdown = getattr(call, 'prompt_breakdown', None)
    if prompt_breakdown:
        if isinstance(prompt_breakdown, dict) and prompt_breakdown.get('system_prompt'):
            return prompt_breakdown['system_prompt']
        if hasattr(prompt_breakdown, 'system_prompt') and prompt_breakdown.system_prompt:
            return prompt_breakdown.system_prompt
    
    # Try metadata
    meta_data = getattr(call, 'meta_data', None)
    if meta_data and isinstance(meta_data, dict):
        if meta_data.get('system_prompt'):
            return meta_data['system_prompt']
    
    # Try parsing from full prompt
    prompt = getattr(call, 'prompt', None)
    if prompt:
        if '[SYSTEM]' in prompt:
            parts = prompt.split('[USER]')
            if parts:
                return parts[0].replace('[SYSTEM]', '').strip()
        return prompt[:2000]  # Return first part as fallback
    
    return ""


def _get_user_message(call) -> str:
    """Extract user message from call."""
    # Try direct attribute first (with safe access)
    user_message = getattr(call, 'user_message', None)
    if user_message:
        return user_message
    
    # Try prompt_metadata
    prompt_metadata = getattr(call, 'prompt_metadata', None)
    if prompt_metadata:
        if isinstance(prompt_metadata, dict) and prompt_metadata.get('user_message'):
            return prompt_metadata['user_message']
        if hasattr(prompt_metadata, 'user_message') and prompt_metadata.user_message:
            return prompt_metadata.user_message
    
    # Try prompt_breakdown
    prompt_breakdown = getattr(call, 'prompt_breakdown', None)
    if prompt_breakdown:
        if isinstance(prompt_breakdown, dict):
            return prompt_breakdown.get('user_content') or prompt_breakdown.get('user_message') or ''
        if hasattr(prompt_breakdown, 'user_content') and prompt_breakdown.user_content:
            return prompt_breakdown.user_content
        if hasattr(prompt_breakdown, 'user_message') and prompt_breakdown.user_message:
            return prompt_breakdown.user_message
    
    # Try metadata
    meta_data = getattr(call, 'meta_data', None)
    if meta_data and isinstance(meta_data, dict):
        if meta_data.get('user_message'):
            return meta_data['user_message']
    
    # Try parsing from full prompt
    prompt = getattr(call, 'prompt', None)
    if prompt and '[USER]' in prompt:
        parts = prompt.split('[USER]')
        if len(parts) > 1:
            return parts[1].strip()
    
    return ""


def _get_response_text(call) -> str:
    """Extract response text from call."""
    response_text = getattr(call, 'response_text', None)
    if response_text:
        return response_text
    
    # Try response field
    response = getattr(call, 'response', None)
    if response:
        return str(response)
    
    return ""


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text with indicator."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... truncated, {len(text) - max_chars} more chars ...]"


def _parse_llm_response(result_text: str) -> Dict[str, Any]:
    """Parse and validate LLM JSON response."""
    # Clean up common issues
    result_text = result_text.strip()
    
    # Remove markdown code blocks if present
    if result_text.startswith("```"):
        lines = result_text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        result_text = "\n".join(lines)
    
    try:
        result = json.loads(result_text)
        
        # Validate structure
        if "recommendations" not in result:
            return {
                "error": "Invalid response structure",
                "details": "Missing 'recommendations' field",
                "raw_response": result_text[:500],
            }
        
        # Ensure we have exactly 3 recommendations
        recs = result.get("recommendations", [])
        if len(recs) < 3:
            # Pad with empty recommendations if needed
            while len(recs) < 3:
                recs.append({
                    "id": f"rec_{len(recs) + 1}",
                    "title": "No additional recommendation",
                    "priority": "low",
                    "problem": "Call appears well-optimized",
                    "solution": "No changes needed",
                    "new_prompt": "N/A",
                    "estimated_impact": {
                        "tokens_before": 0,
                        "tokens_after": 0,
                        "token_reduction_pct": 0,
                        "latency_reduction_pct": 0,
                        "cost_reduction_pct": 0,
                    },
                    "preserves": [],
                    "tradeoffs": [],
                    "effort": "Low",
                    "confidence": 0.5,
                })
        
        result["recommendations"] = recs[:3]  # Max 3
        return result
        
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse LLM response as JSON",
            "details": str(e),
            "raw_response": result_text[:1000],
        }


def _estimate_analysis_cost(usage) -> float:
    """Estimate cost of the analysis call."""
    if not usage:
        return 0.0
    # GPT-4o pricing (approximate)
    input_cost = (usage.prompt_tokens / 1000) * 0.005
    output_cost = (usage.completion_tokens / 1000) * 0.015
    return round(input_cost + output_cost, 4)


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

def clear_analysis_cache(call_id: Optional[str] = None):
    """Clear analysis cache."""
    global _analysis_cache
    if call_id:
        _analysis_cache.pop(call_id, None)
    else:
        _analysis_cache = {}


def get_cached_analysis(call_id: str) -> Optional[Dict]:
    """Get cached analysis if available."""
    return _analysis_cache.get(call_id)