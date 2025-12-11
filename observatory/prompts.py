"""
Prompt Manager - Template Versioning and A/B Testing
Location: observatory/prompts.py

Manages prompt templates with version tracking and A/B testing capabilities.
Integrates with Observatory for variant performance tracking.
"""

import hashlib
import random
from typing import Optional, Dict, List, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

from observatory.models import PromptMetadata, PromptBreakdown

if TYPE_CHECKING:
    from observatory.collector import Observatory


# =============================================================================
# PROMPT TEMPLATE
# =============================================================================

@dataclass
class PromptTemplate:
    """A versioned prompt template with optional variants."""
    template_id: str
    version: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # A/B testing
    variants: Dict[str, str] = field(default_factory=dict)
    active_variant_weights: Dict[str, float] = field(default_factory=dict)
    experiment_id: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    compressible_sections: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    @property
    def content_hash(self) -> str:
        """Generate hash from content prefix."""
        return hashlib.md5(self.content[:500].encode()).hexdigest()[:8]


# =============================================================================
# PROMPT MANAGER
# =============================================================================

class PromptManager:
    """
    Manages prompt templates with versioning and A/B testing.
    
    Usage:
        prompts = PromptManager(observatory=obs)
        
        # Register a template with variants
        prompts.register(
            template_id="system_prompt",
            version="2.0.0",
            content=SYSTEM_PROMPT,
            variants={
                "control": SYSTEM_PROMPT,
                "concise": CONCISE_PROMPT,
                "detailed": DETAILED_PROMPT,
            },
            experiment_id="system_prompt_test_dec_2024",
            weights={"control": 0.5, "concise": 0.25, "detailed": 0.25}
        )
        
        # At runtime - select a variant
        content, variant_id, metadata = prompts.select_variant("system_prompt")
        
        # Use content in LLM call, track variant_id
        track_llm_call(
            ...,
            prompt_variant_id=variant_id,
            prompt_metadata=metadata
        )
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
    ):
        """
        Initialize Prompt Manager.
        
        Args:
            observatory: Observatory instance for tracking
        """
        self.observatory = observatory
        
        # Template storage
        self._templates: Dict[str, PromptTemplate] = {}
        
        # Version history
        self._version_history: Dict[str, List[str]] = {}
        
        # Usage tracking
        self._variant_usage: Dict[str, Dict[str, int]] = {}
        
        # Sticky assignments (user_id → template_id → variant)
        self._sticky_assignments: Dict[str, Dict[str, str]] = {}
    
    # =========================================================================
    # TEMPLATE REGISTRATION
    # =========================================================================
    
    def register(
        self,
        template_id: str,
        version: str,
        content: str,
        variants: Optional[Dict[str, str]] = None,
        weights: Optional[Dict[str, float]] = None,
        experiment_id: Optional[str] = None,
        description: Optional[str] = None,
        compressible_sections: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> 'PromptManager':
        """
        Register a prompt template.
        
        Args:
            template_id: Unique identifier for the template
            version: Semantic version (e.g., "1.0.0")
            content: Base template content
            variants: Dict of variant_name → content for A/B testing
            weights: Dict of variant_name → selection weight (must sum to 1.0)
            experiment_id: A/B test experiment identifier
            description: Human-readable description
            compressible_sections: List of sections that can be compressed
            tags: List of tags for categorization
        
        Returns:
            Self for chaining
        """
        # Create base variants dict with "base" if no variants provided
        if variants is None:
            variants = {"base": content}
        elif "base" not in variants:
            variants["base"] = content
        
        # Normalize weights
        if weights is None:
            # Equal weights for all variants
            num_variants = len(variants)
            weights = {k: 1.0 / num_variants for k in variants.keys()}
        
        template = PromptTemplate(
            template_id=template_id,
            version=version,
            content=content,
            variants=variants,
            active_variant_weights=weights,
            experiment_id=experiment_id,
            description=description,
            compressible_sections=compressible_sections or [],
            tags=tags or [],
        )
        
        # Track version history
        if template_id not in self._version_history:
            self._version_history[template_id] = []
        self._version_history[template_id].append(version)
        
        # Initialize usage tracking
        if template_id not in self._variant_usage:
            self._variant_usage[template_id] = {}
        for variant_name in variants.keys():
            if variant_name not in self._variant_usage[template_id]:
                self._variant_usage[template_id][variant_name] = 0
        
        self._templates[template_id] = template
        return self
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(self) -> List[str]:
        """List all registered template IDs."""
        return list(self._templates.keys())
    
    # =========================================================================
    # VARIANT SELECTION
    # =========================================================================
    
    def select_variant(
        self,
        template_id: str,
        strategy: str = "weighted",
        user_id: Optional[str] = None,
        variant_override: Optional[str] = None,
    ) -> Tuple[str, str, PromptMetadata]:
        """
        Select a variant for a template.
        
        Args:
            template_id: Template to select from
            strategy: Selection strategy:
                - "weighted": Random selection based on weights
                - "sticky": Consistent per user_id
                - "round_robin": Cycle through variants
            user_id: User identifier (required for "sticky" strategy)
            variant_override: Force a specific variant
        
        Returns:
            Tuple of (content, variant_id, PromptMetadata)
        
        Raises:
            ValueError: If template not found
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        
        # Determine variant
        if variant_override and variant_override in template.variants:
            variant_name = variant_override
        elif strategy == "sticky" and user_id:
            variant_name = self._get_sticky_variant(template, user_id)
        elif strategy == "round_robin":
            variant_name = self._get_round_robin_variant(template)
        else:
            variant_name = self._get_weighted_variant(template)
        
        # Get content
        content = template.variants[variant_name]
        
        # Build variant ID
        variant_id = f"{template_id}:{variant_name}"
        if template.experiment_id:
            variant_id = f"{template.experiment_id}:{variant_name}"
        
        # Track usage
        self._variant_usage[template_id][variant_name] += 1
        
        # Create metadata
        metadata = PromptMetadata(
            prompt_template_id=template_id,
            prompt_version=template.version,
            prompt_hash=template.content_hash,
            experiment_id=template.experiment_id,
            compressible_sections=template.compressible_sections,
        )
        
        return content, variant_id, metadata
    
    def _get_weighted_variant(self, template: PromptTemplate) -> str:
        """Select variant based on weights."""
        variants = list(template.active_variant_weights.keys())
        weights = list(template.active_variant_weights.values())
        
        # Normalize weights
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]
        
        return random.choices(variants, weights=weights, k=1)[0]
    
    def _get_sticky_variant(self, template: PromptTemplate, user_id: str) -> str:
        """Get consistent variant for a user."""
        if user_id not in self._sticky_assignments:
            self._sticky_assignments[user_id] = {}
        
        if template.template_id not in self._sticky_assignments[user_id]:
            # Assign a variant based on user_id hash
            variants = list(template.variants.keys())
            hash_val = int(hashlib.md5(f"{user_id}:{template.template_id}".encode()).hexdigest(), 16)
            variant_idx = hash_val % len(variants)
            self._sticky_assignments[user_id][template.template_id] = variants[variant_idx]
        
        return self._sticky_assignments[user_id][template.template_id]
    
    def _get_round_robin_variant(self, template: PromptTemplate) -> str:
        """Cycle through variants."""
        variants = list(template.variants.keys())
        usage = self._variant_usage.get(template.template_id, {})
        
        # Find least used variant
        min_usage = float('inf')
        selected = variants[0]
        for v in variants:
            if usage.get(v, 0) < min_usage:
                min_usage = usage.get(v, 0)
                selected = v
        
        return selected
    
    # =========================================================================
    # A/B TEST MANAGEMENT
    # =========================================================================
    
    def update_weights(
        self,
        template_id: str,
        weights: Dict[str, float],
    ) -> 'PromptManager':
        """
        Update variant weights for a template.
        
        Args:
            template_id: Template to update
            weights: New weights dict
        
        Returns:
            Self for chaining
        """
        template = self._templates.get(template_id)
        if template:
            template.active_variant_weights = weights
        return self
    
    def pause_variant(
        self,
        template_id: str,
        variant_name: str,
    ) -> 'PromptManager':
        """
        Pause a variant (set weight to 0).
        
        Args:
            template_id: Template ID
            variant_name: Variant to pause
        
        Returns:
            Self for chaining
        """
        template = self._templates.get(template_id)
        if template and variant_name in template.active_variant_weights:
            template.active_variant_weights[variant_name] = 0
        return self
    
    def promote_variant(
        self,
        template_id: str,
        variant_name: str,
    ) -> 'PromptManager':
        """
        Promote a variant to 100% traffic.
        
        Args:
            template_id: Template ID
            variant_name: Variant to promote
        
        Returns:
            Self for chaining
        """
        template = self._templates.get(template_id)
        if template and variant_name in template.variants:
            # Set all weights to 0
            for v in template.active_variant_weights:
                template.active_variant_weights[v] = 0
            # Set winner to 100%
            template.active_variant_weights[variant_name] = 1.0
        return self
    
    # =========================================================================
    # METADATA HELPERS
    # =========================================================================
    
    def get_metadata(self, template_id: str) -> Optional[PromptMetadata]:
        """Get metadata for a template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        return PromptMetadata(
            prompt_template_id=template_id,
            prompt_version=template.version,
            prompt_hash=template.content_hash,
            experiment_id=template.experiment_id,
            compressible_sections=template.compressible_sections,
        )
    
    def create_breakdown(
        self,
        system_prompt: Optional[str] = None,
        system_prompt_tokens: Optional[int] = None,
        chat_history: Optional[List[Dict]] = None,
        chat_history_tokens: Optional[int] = None,
        user_message: Optional[str] = None,
        user_message_tokens: Optional[int] = None,
        response_text: Optional[str] = None,
    ) -> PromptBreakdown:
        """
        Create a PromptBreakdown for tracking.
        
        Args:
            system_prompt: System prompt text (truncated)
            system_prompt_tokens: Token count
            chat_history: List of message dicts
            chat_history_tokens: Token count
            user_message: User message text (truncated)
            user_message_tokens: Token count
            response_text: Response text (truncated)
        
        Returns:
            PromptBreakdown object
        """
        return PromptBreakdown(
            system_prompt=system_prompt[:2000] if system_prompt else None,
            system_prompt_tokens=system_prompt_tokens,
            chat_history=chat_history,
            chat_history_tokens=chat_history_tokens,
            chat_history_count=len(chat_history) if chat_history else 0,
            user_message=user_message[:1000] if user_message else None,
            user_message_tokens=user_message_tokens,
            response_text=response_text[:2000] if response_text else None,
        )
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prompt manager statistics."""
        stats = {
            "total_templates": len(self._templates),
            "templates": {},
        }
        
        for template_id, template in self._templates.items():
            usage = self._variant_usage.get(template_id, {})
            total_usage = sum(usage.values())
            
            stats["templates"][template_id] = {
                "version": template.version,
                "num_variants": len(template.variants),
                "variants": list(template.variants.keys()),
                "weights": template.active_variant_weights,
                "experiment_id": template.experiment_id,
                "total_selections": total_usage,
                "usage_by_variant": dict(usage),
            }
        
        return stats
    
    def get_version_history(self, template_id: str) -> List[str]:
        """Get version history for a template."""
        return self._version_history.get(template_id, [])
    
    def reset_stats(self):
        """Reset usage statistics."""
        for template_id in self._variant_usage:
            for variant in self._variant_usage[template_id]:
                self._variant_usage[template_id][variant] = 0


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_prompt_metadata(
    template_id: Optional[str] = None,
    version: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    experiment_id: Optional[str] = None,
    compressible_sections: Optional[List[str]] = None,
    optimization_flags: Optional[Dict[str, bool]] = None,
    config_version: Optional[str] = None,
) -> PromptMetadata:
    """
    Convenience function to create PromptMetadata.
    
    Args:
        template_id: Identifier for the prompt template
        version: Version string (e.g., "1.0.0")
        prompt_hash: Hash of prompt content
        experiment_id: A/B test grouping
        compressible_sections: Sections that can be compressed
        optimization_flags: Feature flags
        config_version: Config file version
    
    Returns:
        PromptMetadata object
    """
    return PromptMetadata(
        prompt_template_id=template_id,
        prompt_version=version,
        prompt_hash=prompt_hash,
        experiment_id=experiment_id,
        compressible_sections=compressible_sections,
        optimization_flags=optimization_flags,
        config_version=config_version,
    )


def create_prompt_breakdown(
    system_prompt: Optional[str] = None,
    system_prompt_tokens: Optional[int] = None,
    chat_history: Optional[List[Dict]] = None,
    chat_history_tokens: Optional[int] = None,
    user_message: Optional[str] = None,
    user_message_tokens: Optional[int] = None,
    response_text: Optional[str] = None,
) -> PromptBreakdown:
    """
    Convenience function to create PromptBreakdown.
    
    Args:
        system_prompt: System prompt text
        system_prompt_tokens: Token count
        chat_history: List of message dicts
        chat_history_tokens: Token count
        user_message: User message text
        user_message_tokens: Token count
        response_text: Response text
    
    Returns:
        PromptBreakdown object
    """
    return PromptBreakdown(
        system_prompt=system_prompt[:2000] if system_prompt else None,
        system_prompt_tokens=system_prompt_tokens,
        chat_history=chat_history,
        chat_history_tokens=chat_history_tokens,
        chat_history_count=len(chat_history) if chat_history else 0,
        user_message=user_message[:1000] if user_message else None,
        user_message_tokens=user_message_tokens,
        response_text=response_text[:2000] if response_text else None,
    )


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough: 4 chars ≈ 1 token)."""
    if not text:
        return 0
    return len(text) // 4