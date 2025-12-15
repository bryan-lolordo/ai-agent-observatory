"""
Code Location Models
Location: api/models/code_location.py

Models for code guidance and optimization recommendations.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CodeLocation(BaseModel):
    """Source code location."""
    file: str
    class_name: Optional[str] = None
    method: Optional[str] = None
    line: Optional[int] = None
    
    def format(self) -> str:
        """Format as human-readable string."""
        if self.class_name and self.method:
            return f"{self.file}:{self.line} ({self.class_name}.{self.method})"
        elif self.method:
            return f"{self.file}:{self.line} ({self.method})"
        else:
            return f"{self.file}:{self.line}"


class CodeExample(BaseModel):
    """Before/after code example."""
    before: str
    after: str
    language: str = "python"
    savings: Optional[str] = None
    explanation: Optional[str] = None


class OptimizationTemplate(BaseModel):
    """Optimization template/hint."""
    category: str  # "cache", "prompt", "output", "routing"
    title: str
    description: str
    impact: str  # "High", "Medium", "Low"


class OptimizationGuidance(BaseModel):
    """Complete optimization guidance."""
    operation: str
    agent: str
    
    # Where to fix
    location: Optional[CodeLocation] = None
    
    # How to fix
    templates: List[OptimizationTemplate] = Field(default_factory=list)
    examples: List[CodeExample] = Field(default_factory=list)
    
    # Expected impact
    estimated_impact: Dict[str, float] = Field(default_factory=dict)
    
    # Metadata
    can_cache: bool = False
    recommended_model: Optional[str] = None
    expected_latency_ms: Optional[float] = None
    expected_cost: Optional[float] = None


class CodeLocationResponse(BaseModel):
    """Response with code location info."""
    operation: str
    agent: str
    location: Optional[CodeLocation] = None
    guidance: Optional[OptimizationGuidance] = None