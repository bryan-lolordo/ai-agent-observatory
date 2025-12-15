"""
Experiment Models
Location: api/models/experiment.py

Models for A/B testing and experimentation.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ExperimentConfig(BaseModel):
    """Experiment configuration."""
    id: str
    name: str
    description: Optional[str] = None
    hypothesis: str
    
    # Groups
    control_group: str
    treatment_groups: List[str]
    traffic_split: Dict[str, float]  # group_name -> percentage
    
    # Metrics to track
    metrics: List[str] = Field(default_factory=lambda: ["cost", "latency", "quality"])
    
    # Duration
    start_date: datetime
    end_date: Optional[datetime] = None
    min_sample_size: int = Field(default=100)
    
    # Status
    status: Literal["draft", "running", "paused", "completed"] = "draft"
    
    # Results
    winner: Optional[str] = None
    confidence_level: Optional[float] = None


class ExperimentResults(BaseModel):
    """Experiment results."""
    experiment_id: str
    experiment_name: str
    
    # Group metrics
    control_metrics: Dict[str, float]
    treatment_metrics: Dict[str, Dict[str, float]]  # group -> metrics
    
    # Statistical significance
    statistical_significance: Dict[str, float]  # metric -> p_value
    confidence_intervals: Dict[str, Dict[str, tuple]]  # metric -> {group: (low, high)}
    
    # Sample sizes
    sample_sizes: Dict[str, int]  # group -> count
    
    # Winner
    winner: Optional[str] = None
    recommendation: str


class ExperimentListResponse(BaseModel):
    """List of experiments."""
    experiments: List[ExperimentConfig]
    total: int
    active_count: int
    completed_count: int