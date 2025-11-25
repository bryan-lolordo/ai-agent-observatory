from typing import Dict, Any, Optional, List
from enum import Enum
import json
import re


class JudgeCriteria(str, Enum):
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    CONCISENESS = "conciseness"
    HELPFULNESS = "helpfulness"


class JudgmentResult:
    def __init__(
        self,
        overall_score: float,
        criteria_scores: Dict[str, float],
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.overall_score = overall_score
        self.criteria_scores = criteria_scores
        self.reasoning = reasoning
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "criteria_scores": self.criteria_scores,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }


class LLMJudge:
    def __init__(
        self,
        judge_model: str = "gpt-4",
        enabled: bool = True,
        criteria: Optional[List[JudgeCriteria]] = None,
    ):
        self.judge_model = judge_model
        self.enabled = enabled
        self.criteria = criteria or [
            JudgeCriteria.CORRECTNESS,
            JudgeCriteria.COMPLETENESS,
            JudgeCriteria.CLARITY,
        ]
        
        self.total_judgments = 0
        self.average_scores = []
        self.judgments_by_model = {}
    
    def judge(
        self,
        task: str,
        response: str,
        context: Optional[str] = None,
        ground_truth: Optional[str] = None,
    ) -> JudgmentResult:
        if not self.enabled:
            return JudgmentResult(
                overall_score=0.0,
                criteria_scores={},
                reasoning="Judge disabled",
            )
        
        self.total_judgments += 1
        
        judgment_prompt = self._build_judgment_prompt(
            task, response, context, ground_truth
        )
        
        judge_response = self._call_judge(judgment_prompt)
        
        result = self._parse_judgment(judge_response)
        
        self.average_scores.append(result.overall_score)
        
        return result
    
    def _build_judgment_prompt(
        self,
        task: str,
        response: str,
        context: Optional[str],
        ground_truth: Optional[str],
    ) -> str:
        criteria_descriptions = {
            JudgeCriteria.CORRECTNESS: "Is the response factually accurate and correct?",
            JudgeCriteria.COMPLETENESS: "Does it fully address all aspects of the task?",
            JudgeCriteria.CLARITY: "Is the explanation clear and easy to understand?",
            JudgeCriteria.CONCISENESS: "Is it concise without unnecessary information?",
            JudgeCriteria.HELPFULNESS: "Would this actually help the user accomplish their goal?",
        }
        
        criteria_section = "\n".join([
            f"- {criteria.value.title()}: {criteria_descriptions[criteria]}"
            for criteria in self.criteria
        ])
        
        prompt = f"""You are an expert judge evaluating AI responses. Rate the following response on a scale of 1-10.

Task: {task}

Response to evaluate:
{response}
"""
        
        if context:
            prompt += f"\nContext: {context}"
        
        if ground_truth:
            prompt += f"\nExpected answer: {ground_truth}"
        
        prompt += f"""

Evaluation criteria:
{criteria_section}

Provide your evaluation in the following JSON format:
{{
    "overall_score": <1-10>,
    "criteria_scores": {{
        "{self.criteria[0].value}": <1-10>,
        "{self.criteria[1].value}": <1-10>
    }},
    "reasoning": "Brief explanation of the score"
}}

Be strict but fair. A score of 7-8 is good, 9-10 is excellent."""
        
        return prompt
    
    def _call_judge(self, prompt: str) -> str:
        """
        Simulate judge LLM call.
        In production, replace with:
            response = openai.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content
        """
        import random
        score = random.uniform(6.0, 9.5)
        
        criteria_scores = {
            criteria.value: random.uniform(6.0, 9.5)
            for criteria in self.criteria
        }
        
        return json.dumps({
            "overall_score": round(score, 1),
            "criteria_scores": criteria_scores,
            "reasoning": f"Simulated judgment with score {score:.1f}"
        })
    
    def _parse_judgment(self, judge_response: str) -> JudgmentResult:
        try:
            match = re.search(r'\{[^}]+\}', judge_response, re.DOTALL)
            if match:
                judge_response = match.group()
            
            data = json.loads(judge_response)
            
            return JudgmentResult(
                overall_score=float(data.get("overall_score", 0)),
                criteria_scores={
                    k: float(v) for k, v in data.get("criteria_scores", {}).items()
                },
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, ValueError) as e:
            return JudgmentResult(
                overall_score=5.0,
                criteria_scores={},
                reasoning=f"Parse error: {str(e)}",
            )
    
    def compare_models(
        self,
        task: str,
        responses: Dict[str, str],
        context: Optional[str] = None,
    ) -> Dict[str, JudgmentResult]:
        results = {}
        
        for model_name, response in responses.items():
            judgment = self.judge(task, response, context)
            results[model_name] = judgment
            
            if model_name not in self.judgments_by_model:
                self.judgments_by_model[model_name] = []
            self.judgments_by_model[model_name].append(judgment.overall_score)
        
        return results
    
    def get_winner(self, comparison_results: Dict[str, JudgmentResult]) -> str:
        return max(
            comparison_results.items(),
            key=lambda x: x[1].overall_score
        )[0]
    
    def get_stats(self) -> Dict[str, Any]:
        avg_score = sum(self.average_scores) / len(self.average_scores) if self.average_scores else 0
        
        model_averages = {
            model: sum(scores) / len(scores)
            for model, scores in self.judgments_by_model.items()
            if scores
        }
        
        return {
            "enabled": self.enabled,
            "total_judgments": self.total_judgments,
            "average_score": avg_score,
            "model_averages": model_averages,
            "criteria_used": [c.value for c in self.criteria],
        }
    
    def batch_evaluate(
        self,
        evaluations: List[Dict[str, str]],
    ) -> List[JudgmentResult]:
        results = []
        
        for eval_data in evaluations:
            result = self.judge(
                task=eval_data["task"],
                response=eval_data["response"],
                context=eval_data.get("context"),
                ground_truth=eval_data.get("ground_truth"),
            )
            results.append(result)
        
        return results


class GroundTruthEvaluator:
    @staticmethod
    def exact_match(response: str, ground_truth: str) -> float:
        return 1.0 if response.strip() == ground_truth.strip() else 0.0
    
    @staticmethod
    def contains_keywords(response: str, required_keywords: List[str]) -> float:
        response_lower = response.lower()
        matches = sum(1 for keyword in required_keywords if keyword.lower() in response_lower)
        return matches / len(required_keywords) if required_keywords else 0.0
    
    @staticmethod
    def substring_match(response: str, ground_truth: str) -> float:
        response = response.lower().strip()
        ground_truth = ground_truth.lower().strip()
        
        if ground_truth in response:
            return 1.0
        
        words = set(ground_truth.split())
        response_words = set(response.split())
        overlap = len(words & response_words)
        
        return overlap / len(words) if words else 0.0