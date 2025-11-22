from observatory.models import Session, QualityMetrics


class QualityAnalyzer:
    def analyze(self, session: Session) -> QualityMetrics:
        """Analyze quality metrics for a session."""
        if not session.llm_calls:
            return QualityMetrics(
                total_calls=0,
                successful_calls=0,
                failed_calls=0,
                success_rate=0.0,
                avg_tokens_per_call=0.0,
                cache_hit_rate=None,
            )
        
        total_calls = len(session.llm_calls)
        successful_calls = sum(1 for call in session.llm_calls if call.success)
        failed_calls = total_calls - successful_calls
        success_rate = successful_calls / total_calls if total_calls > 0 else 0.0
        
        avg_tokens_per_call = session.total_tokens / total_calls if total_calls > 0 else 0.0
        
        return QualityMetrics(
            total_calls=total_calls,
            successful_calls=successful_calls,
            failed_calls=failed_calls,
            success_rate=success_rate,
            avg_tokens_per_call=avg_tokens_per_call,
            cache_hit_rate=None,  # TODO: Implement cache tracking
        )