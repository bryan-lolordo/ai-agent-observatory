from collections import defaultdict

from observatory.models import Session, TokenBreakdown


class TokenAnalyzer:
    def analyze(self, session: Session) -> TokenBreakdown:
        """Analyze token usage breakdown for a session."""
        prompt_tokens = 0
        completion_tokens = 0
        by_model = defaultdict(int)
        by_agent = defaultdict(int)
        
        for call in session.llm_calls:
            prompt_tokens += call.prompt_tokens
            completion_tokens += call.completion_tokens
            by_model[call.model_name] += call.total_tokens
            
            if call.agent_name:
                by_agent[call.agent_name] += call.total_tokens
        
        return TokenBreakdown(
            total_tokens=session.total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            by_model=dict(by_model),
            by_agent=dict(by_agent),
        )