"""
Chat Router - GPT-4 Powered Feedback for Operations
Location: api/routers/chat.py

Provides intelligent feedback about LLM operations using GPT-4.
Reuses the existing Azure OpenAI setup from fix_analysis_service.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Lazy-loaded OpenAI client (reuse same pattern as fix_analysis_service)
_openai_client = None

def _get_openai_client():
    """Get or create Azure OpenAI client."""
    global _openai_client
    if _openai_client is None:
        from openai import AzureOpenAI
        _openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        )
    return _openai_client


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ConversationMessage(BaseModel):
    role: str
    content: str


class FeedbackRequest(BaseModel):
    operation: str
    systemPrompt: Optional[str] = None
    issues: Optional[List[Dict[str, Any]]] = None
    metrics: Optional[Dict[str, Any]] = None
    conversation: Optional[List[ConversationMessage]] = None
    userQuery: str


class FeedbackResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None


# =============================================================================
# SYSTEM PROMPT FOR THE FEEDBACK BOT
# =============================================================================

FEEDBACK_SYSTEM_PROMPT = """You are an expert AI/LLM optimization consultant embedded in an AI Agent Observatory tool. Your role is to help developers optimize their LLM operations.

You have access to:
1. The operation name being analyzed
2. The system prompt used by that operation (if available)
3. Detected issues (latency, cost, caching opportunities, etc.)
4. Metrics (call count, total cost, average latency, token counts)

Your expertise includes:
- Prompt engineering and optimization
- LLM cost reduction strategies
- Latency optimization techniques
- Caching strategies (prompt caching, semantic caching, response caching)
- Model selection and routing
- Token optimization
- Batching and parallelization

Guidelines:
- Be concise and actionable
- Provide specific recommendations with expected impact
- Reference the actual metrics when giving advice
- If reviewing a system prompt, give concrete suggestions for improvement
- Use markdown formatting for clarity (bold for emphasis, lists for recommendations)
- When estimating savings, be realistic (e.g., "~30-50% reduction" rather than exact numbers)
- Consider trade-offs (cost vs quality, latency vs accuracy)

Always be helpful and specific to the operation being discussed."""


# =============================================================================
# FEEDBACK ENDPOINT
# =============================================================================

@router.post("/feedback", response_model=FeedbackResponse)
async def get_feedback(request: FeedbackRequest):
    """
    Get GPT-4 powered feedback about an LLM operation.

    Analyzes the operation's metrics, issues, and system prompt
    to provide optimization recommendations.
    """
    try:
        # Build context message with operation details
        context_parts = [f"**Operation:** `{request.operation}`\n"]

        # Add metrics if available
        if request.metrics:
            context_parts.append("**Current Metrics:**")
            if request.metrics.get("call_count"):
                context_parts.append(f"- Calls: {request.metrics['call_count']}")
            if request.metrics.get("total_cost"):
                context_parts.append(f"- Total Cost: ${request.metrics['total_cost']:.2f}")
            if request.metrics.get("avg_latency_ms"):
                context_parts.append(f"- Avg Latency: {request.metrics['avg_latency_ms'] / 1000:.1f}s")
            if request.metrics.get("system_prompt_tokens"):
                context_parts.append(f"- System Prompt Tokens: {request.metrics['system_prompt_tokens']}")
            context_parts.append("")

        # Add issues if available
        if request.issues and len(request.issues) > 0:
            context_parts.append("**Detected Issues:**")
            for issue in request.issues[:5]:  # Limit to 5 issues
                title = issue.get("title", "Unknown issue")
                desc = issue.get("description", "")
                context_parts.append(f"- {title}: {desc}")
            context_parts.append("")

        # Add system prompt if available (truncated)
        if request.systemPrompt:
            prompt_preview = request.systemPrompt[:1500]
            if len(request.systemPrompt) > 1500:
                prompt_preview += "\n... (truncated)"
            context_parts.append("**System Prompt:**")
            context_parts.append(f"```\n{prompt_preview}\n```")
            context_parts.append("")

        context_message = "\n".join(context_parts)

        # Build messages for GPT-4
        messages = [
            {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
            {"role": "user", "content": f"Here's the context about the operation I'm analyzing:\n\n{context_message}"}
        ]

        # Add conversation history if available
        if request.conversation:
            for msg in request.conversation[-6:]:  # Last 6 messages for context
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Add the current user query
        messages.append({
            "role": "user",
            "content": request.userQuery
        })

        # Call Azure OpenAI (GPT-4)
        client = _get_openai_client()
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )

        assistant_message = response.choices[0].message.content

        return FeedbackResponse(
            response=assistant_message,
            suggestions=None  # Could parse suggestions from response if needed
        )

    except Exception as e:
        # Log the error but return a helpful fallback
        print(f"Error calling GPT-4: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedback: {str(e)}"
        )


# =============================================================================
# QUICK ANALYSIS ENDPOINT
# =============================================================================

@router.post("/quick-analysis")
async def quick_analysis(request: FeedbackRequest):
    """
    Get a quick one-shot analysis of an operation.
    Returns structured recommendations.
    """
    try:
        # Build a focused prompt for quick analysis
        analysis_prompt = f"""Analyze this LLM operation and provide 3-5 specific optimization recommendations:

Operation: {request.operation}
"""
        if request.metrics:
            analysis_prompt += f"""
Metrics:
- Calls: {request.metrics.get('call_count', 'N/A')}
- Total Cost: ${request.metrics.get('total_cost', 0):.2f}
- Avg Latency: {(request.metrics.get('avg_latency_ms', 0) / 1000):.1f}s
- System Prompt Tokens: {request.metrics.get('system_prompt_tokens', 'N/A')}
"""

        if request.issues:
            analysis_prompt += "\nDetected Issues:\n"
            for issue in request.issues[:3]:
                analysis_prompt += f"- {issue.get('title', 'Unknown')}\n"

        analysis_prompt += """
Provide your response as a JSON object with this structure:
{
    "priority": "high|medium|low",
    "estimated_savings": "XX%",
    "recommendations": [
        {"title": "...", "description": "...", "impact": "high|medium|low"},
        ...
    ],
    "quick_wins": ["...", "..."]
}"""

        client = _get_openai_client()
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are an LLM optimization expert. Respond only with valid JSON."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.5,
            max_tokens=500,
        )

        # Try to parse as JSON, fall back to raw text
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError:
            return {"response": response.choices[0].message.content}

    except Exception as e:
        print(f"Error in quick analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze: {str(e)}"
        )
