"""
Test Suite Management
=====================

Provides loading, validation, and management of test suites for evaluation.

Features:
- Load test suites from YAML/JSON files
- Programmatic test suite creation
- Schema validation with detailed error reporting
- Test case filtering and organization
- Version management

Usage:
    # Load from file
    loader = TestSuiteLoader()
    suite = loader.load("tests/job_matcher_tests.yaml")

    # Load from directory
    suites = loader.load_all("tests/")

    # Create programmatically
    builder = TestSuiteBuilder("job_matcher_v1")
    suite = (builder
        .set_name("Job Matcher Tests")
        .add_test_case(...)
        .build())

    # Validate
    validator = TestSuiteValidator()
    is_valid, errors = validator.validate(suite)
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

import yaml

from observatory.models import (
    TestCase,
    TestCaseExpected,
    TestCaseGroundTruth,
    TestSuite,
    TestSuiteConfig,
    TestCaseCategory,
    TestDifficulty,
)


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

@dataclass
class ValidationError:
    """Details about a validation error"""
    path: str                    # Where in the structure (e.g., "test_cases[0].expected.tool_called")
    message: str                 # Human-readable error
    severity: str = "error"      # "error" or "warning"
    value: Any = None            # The invalid value

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Result of test suite validation"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [str(e) for e in self.errors],
            "warnings": [str(w) for w in self.warnings],
            "stats": self.stats,
        }


# =============================================================================
# TEST SUITE VALIDATOR
# =============================================================================

class TestSuiteValidator:
    """
    Validates test suites for correctness and completeness.

    Checks:
    - Required fields present
    - Valid data types
    - Valid enum values
    - Logical consistency
    - Best practices (warnings)
    """

    # Valid values for enums
    VALID_CATEGORIES = [c.value for c in TestCaseCategory]
    VALID_DIFFICULTIES = [d.value for d in TestDifficulty]
    VALID_EVALUATORS = ["tool_use", "model_judge", "llm_judge", "schema", "range", "custom"]

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict

    def validate(self, suite: Union[TestSuite, Dict[str, Any]]) -> ValidationResult:
        """
        Validate a test suite.

        Args:
            suite: TestSuite object or dictionary

        Returns:
            ValidationResult with errors and warnings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Convert dict to object if needed
        if isinstance(suite, dict):
            try:
                suite = self._dict_to_suite(suite)
            except Exception as e:
                errors.append(ValidationError(
                    path="root",
                    message=f"Failed to parse test suite: {str(e)}",
                    severity="error"
                ))
                return ValidationResult(valid=False, errors=errors)

        # Validate suite-level fields
        self._validate_suite_fields(suite, errors, warnings)

        # Validate config
        self._validate_config(suite.config, errors, warnings)

        # Validate test cases
        self._validate_test_cases(suite.test_cases, errors, warnings)

        # Check for best practices
        self._check_best_practices(suite, warnings)

        # Compile stats
        stats = self._compile_stats(suite)

        # Determine validity
        valid = len(errors) == 0
        if self.strict and len(warnings) > 0:
            valid = False

        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            stats=stats
        )

    def _validate_suite_fields(
        self,
        suite: TestSuite,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Validate suite-level required fields"""
        if not suite.id:
            errors.append(ValidationError(
                path="id",
                message="Test suite ID is required",
                severity="error"
            ))

        if not suite.name:
            errors.append(ValidationError(
                path="name",
                message="Test suite name is required",
                severity="error"
            ))

        if not suite.version:
            warnings.append(ValidationError(
                path="version",
                message="Test suite version not specified (defaulting to 1.0)",
                severity="warning"
            ))

        if not suite.test_cases:
            errors.append(ValidationError(
                path="test_cases",
                message="Test suite must have at least one test case",
                severity="error"
            ))

    def _validate_config(
        self,
        config: TestSuiteConfig,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Validate test suite configuration"""
        # Validate pass threshold
        if config.pass_threshold < 0 or config.pass_threshold > 100:
            errors.append(ValidationError(
                path="config.pass_threshold",
                message=f"Pass threshold must be 0-100, got {config.pass_threshold}",
                severity="error",
                value=config.pass_threshold
            ))

        # Validate evaluators
        for evaluator in config.evaluators:
            if evaluator not in self.VALID_EVALUATORS:
                warnings.append(ValidationError(
                    path="config.evaluators",
                    message=f"Unknown evaluator type: {evaluator}",
                    severity="warning",
                    value=evaluator
                ))

        # Validate timeout
        if config.timeout_seconds <= 0:
            errors.append(ValidationError(
                path="config.timeout_seconds",
                message="Timeout must be positive",
                severity="error",
                value=config.timeout_seconds
            ))

        # Validate max_concurrent
        if config.max_concurrent <= 0:
            errors.append(ValidationError(
                path="config.max_concurrent",
                message="max_concurrent must be positive",
                severity="error",
                value=config.max_concurrent
            ))

        # Validate evaluator weights
        weight_sum = sum(config.evaluator_weights.values())
        if abs(weight_sum - 1.0) > 0.01 and weight_sum > 0:
            warnings.append(ValidationError(
                path="config.evaluator_weights",
                message=f"Evaluator weights sum to {weight_sum}, consider normalizing to 1.0",
                severity="warning",
                value=config.evaluator_weights
            ))

    def _validate_test_cases(
        self,
        test_cases: List[TestCase],
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Validate individual test cases"""
        seen_ids: set = set()

        for i, tc in enumerate(test_cases):
            prefix = f"test_cases[{i}]"

            # Check required fields
            if not tc.id:
                errors.append(ValidationError(
                    path=f"{prefix}.id",
                    message="Test case ID is required",
                    severity="error"
                ))
            elif tc.id in seen_ids:
                errors.append(ValidationError(
                    path=f"{prefix}.id",
                    message=f"Duplicate test case ID: {tc.id}",
                    severity="error",
                    value=tc.id
                ))
            else:
                seen_ids.add(tc.id)

            # Validate category
            if tc.category and tc.category not in self.VALID_CATEGORIES:
                warnings.append(ValidationError(
                    path=f"{prefix}.category",
                    message=f"Non-standard category: {tc.category}",
                    severity="warning",
                    value=tc.category
                ))

            # Validate difficulty
            if tc.difficulty and tc.difficulty not in self.VALID_DIFFICULTIES:
                warnings.append(ValidationError(
                    path=f"{prefix}.difficulty",
                    message=f"Unknown difficulty: {tc.difficulty}",
                    severity="warning",
                    value=tc.difficulty
                ))

            # Validate input
            if not tc.input:
                errors.append(ValidationError(
                    path=f"{prefix}.input",
                    message="Test case input is required",
                    severity="error"
                ))

            # Validate expected
            self._validate_expected(tc.expected, f"{prefix}.expected", errors, warnings)

            # Validate ground truth if present
            if tc.ground_truth:
                self._validate_ground_truth(tc.ground_truth, f"{prefix}.ground_truth", errors, warnings)

            # Validate timeout
            if tc.timeout_seconds is not None and tc.timeout_seconds <= 0:
                errors.append(ValidationError(
                    path=f"{prefix}.timeout_seconds",
                    message="Timeout must be positive",
                    severity="error",
                    value=tc.timeout_seconds
                ))

    def _validate_expected(
        self,
        expected: TestCaseExpected,
        path: str,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Validate expected behavior specification"""
        # At least one expectation type should be specified
        has_expectations = (
            expected.tool_called or
            expected.required_args or
            expected.evaluation_criteria or
            expected.score_range
        )

        if not has_expectations:
            warnings.append(ValidationError(
                path=path,
                message="No expectations defined (tool_called, required_args, evaluation_criteria, or score_range)",
                severity="warning"
            ))

        # Validate score range format
        if expected.score_range:
            if len(expected.score_range) != 2:
                errors.append(ValidationError(
                    path=f"{path}.score_range",
                    message="score_range must have exactly 2 values [min, max]",
                    severity="error",
                    value=expected.score_range
                ))
            elif expected.score_range[0] > expected.score_range[1]:
                errors.append(ValidationError(
                    path=f"{path}.score_range",
                    message="score_range min must be <= max",
                    severity="error",
                    value=expected.score_range
                ))

        # Validate arg_types
        for arg_name, arg_type in expected.arg_types.items():
            valid_types = ["str", "int", "float", "bool", "list", "dict", "any"]
            if arg_type.lower() not in valid_types:
                warnings.append(ValidationError(
                    path=f"{path}.arg_types.{arg_name}",
                    message=f"Unknown argument type: {arg_type}",
                    severity="warning",
                    value=arg_type
                ))

    def _validate_ground_truth(
        self,
        ground_truth: TestCaseGroundTruth,
        path: str,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Validate ground truth specification"""
        # Validate ideal score range
        if ground_truth.ideal_score_range:
            if len(ground_truth.ideal_score_range) != 2:
                errors.append(ValidationError(
                    path=f"{path}.ideal_score_range",
                    message="ideal_score_range must have exactly 2 values [min, max]",
                    severity="error",
                    value=ground_truth.ideal_score_range
                ))
            elif ground_truth.ideal_score_range[0] > ground_truth.ideal_score_range[1]:
                errors.append(ValidationError(
                    path=f"{path}.ideal_score_range",
                    message="ideal_score_range min must be <= max",
                    severity="error",
                    value=ground_truth.ideal_score_range
                ))

        # Validate ideal score
        if ground_truth.ideal_score is not None:
            if ground_truth.ideal_score < 0 or ground_truth.ideal_score > 100:
                errors.append(ValidationError(
                    path=f"{path}.ideal_score",
                    message="ideal_score must be 0-100",
                    severity="error",
                    value=ground_truth.ideal_score
                ))

    def _check_best_practices(
        self,
        suite: TestSuite,
        warnings: List[ValidationError]
    ) -> None:
        """Check for best practices and provide suggestions"""
        # Check for description
        if not suite.description:
            warnings.append(ValidationError(
                path="description",
                message="Consider adding a description for the test suite",
                severity="warning"
            ))

        # Check for balanced categories
        categories = {}
        for tc in suite.test_cases:
            cat = tc.category
            categories[cat] = categories.get(cat, 0) + 1

        # Suggest adding edge cases if missing
        if TestCaseCategory.EDGE_CASE.value not in categories:
            warnings.append(ValidationError(
                path="test_cases",
                message="Consider adding edge case tests",
                severity="warning"
            ))

        # Suggest adding error handling tests if missing
        if TestCaseCategory.ERROR_HANDLING.value not in categories:
            warnings.append(ValidationError(
                path="test_cases",
                message="Consider adding error handling tests",
                severity="warning"
            ))

        # Check test case count
        if len(suite.test_cases) < 5:
            warnings.append(ValidationError(
                path="test_cases",
                message=f"Only {len(suite.test_cases)} test cases. Consider adding more for comprehensive coverage",
                severity="warning"
            ))

    def _compile_stats(self, suite: TestSuite) -> Dict[str, Any]:
        """Compile statistics about the test suite"""
        categories: Dict[str, int] = {}
        difficulties: Dict[str, int] = {}
        tags: Dict[str, int] = {}

        for tc in suite.test_cases:
            # Categories
            cat = tc.category
            categories[cat] = categories.get(cat, 0) + 1

            # Difficulties
            diff = tc.difficulty
            difficulties[diff] = difficulties.get(diff, 0) + 1

            # Tags
            for tag in tc.tags:
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "total_test_cases": len(suite.test_cases),
            "enabled_test_cases": len([tc for tc in suite.test_cases if tc.enabled]),
            "disabled_test_cases": len([tc for tc in suite.test_cases if not tc.enabled]),
            "categories": categories,
            "difficulties": difficulties,
            "tags": tags,
            "evaluators": suite.config.evaluators,
            "pass_threshold": suite.config.pass_threshold,
        }

    def _dict_to_suite(self, data: Dict[str, Any]) -> TestSuite:
        """Convert dictionary to TestSuite model"""
        # Parse config
        config_data = data.get("config", {})
        config = TestSuiteConfig(**config_data)

        # Parse test cases
        test_cases = []
        for tc_data in data.get("test_cases", []):
            # Parse expected
            expected_data = tc_data.get("expected", {})
            expected = TestCaseExpected(**expected_data)

            # Parse ground truth
            ground_truth = None
            if "ground_truth" in tc_data:
                ground_truth = TestCaseGroundTruth(**tc_data["ground_truth"])

            test_case = TestCase(
                id=tc_data.get("id", ""),
                category=tc_data.get("category", TestCaseCategory.CUSTOM.value),
                description=tc_data.get("description", ""),
                difficulty=tc_data.get("difficulty", TestDifficulty.NORMAL.value),
                tags=tc_data.get("tags", []),
                input=tc_data.get("input", {}),
                expected=expected,
                ground_truth=ground_truth,
                timeout_seconds=tc_data.get("timeout_seconds"),
                enabled=tc_data.get("enabled", True),
            )
            test_cases.append(test_case)

        return TestSuite(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            agent_name=data.get("agent_name", ""),
            config=config,
            test_cases=test_cases,
            author=data.get("author"),
            tags=data.get("tags", []),
        )


# =============================================================================
# TEST SUITE LOADER
# =============================================================================

class TestSuiteLoader:
    """
    Loads test suites from YAML/JSON files.

    Supports:
    - Single file loading
    - Directory scanning
    - Glob patterns
    - Validation on load
    """

    def __init__(
        self,
        validate: bool = True,
        strict_validation: bool = False,
    ):
        """
        Initialize loader.

        Args:
            validate: If True, validate suites after loading
            strict_validation: If True, treat warnings as errors
        """
        self.validate = validate
        self.validator = TestSuiteValidator(strict=strict_validation)
        self._loaded_suites: Dict[str, TestSuite] = {}

    def load(self, path: Union[str, Path]) -> TestSuite:
        """
        Load a test suite from a file.

        Args:
            path: Path to YAML or JSON file

        Returns:
            TestSuite object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid or validation fails
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Test suite file not found: {path}")

        # Load based on extension
        suffix = path.suffix.lower()
        if suffix in [".yaml", ".yml"]:
            data = self._load_yaml(path)
        elif suffix == ".json":
            data = self._load_json(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use .yaml, .yml, or .json")

        # Convert to TestSuite
        suite = self._parse_suite(data, str(path))

        # Validate if enabled
        if self.validate:
            result = self.validator.validate(suite)
            if not result.valid:
                error_msgs = "\n".join([str(e) for e in result.errors])
                raise ValueError(f"Test suite validation failed:\n{error_msgs}")

        # Cache
        self._loaded_suites[suite.id] = suite

        return suite

    def load_all(
        self,
        directory: Union[str, Path],
        pattern: str = "*.yaml",
        recursive: bool = True
    ) -> List[TestSuite]:
        """
        Load all test suites from a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for files (default: *.yaml)
            recursive: If True, search recursively

        Returns:
            List of TestSuite objects
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Find files
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))

        # Also include JSON files
        json_pattern = pattern.replace(".yaml", ".json").replace(".yml", ".json")
        if recursive:
            files.extend(directory.rglob(json_pattern))
        else:
            files.extend(directory.glob(json_pattern))

        # Load each
        suites = []
        errors = []

        for file_path in sorted(set(files)):
            try:
                suite = self.load(file_path)
                suites.append(suite)
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")

        if errors and not suites:
            raise ValueError(f"Failed to load any test suites:\n" + "\n".join(errors))

        return suites

    def load_from_dict(self, data: Dict[str, Any]) -> TestSuite:
        """
        Load a test suite from a dictionary.

        Args:
            data: Test suite data as dictionary

        Returns:
            TestSuite object
        """
        suite = self._parse_suite(data, "dict")

        if self.validate:
            result = self.validator.validate(suite)
            if not result.valid:
                error_msgs = "\n".join([str(e) for e in result.errors])
                raise ValueError(f"Test suite validation failed:\n{error_msgs}")

        self._loaded_suites[suite.id] = suite
        return suite

    def get_cached(self, suite_id: str) -> Optional[TestSuite]:
        """Get a previously loaded suite by ID"""
        return self._loaded_suites.get(suite_id)

    def clear_cache(self) -> None:
        """Clear loaded suites cache"""
        self._loaded_suites.clear()

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _parse_suite(self, data: Dict[str, Any], source: str) -> TestSuite:
        """Parse dictionary into TestSuite model"""
        try:
            return self.validator._dict_to_suite(data)
        except Exception as e:
            raise ValueError(f"Failed to parse test suite from {source}: {str(e)}")


# =============================================================================
# TEST SUITE BUILDER
# =============================================================================

class TestSuiteBuilder:
    """
    Fluent builder for creating test suites programmatically.

    Usage:
        suite = (TestSuiteBuilder("my_suite_id")
            .set_name("My Test Suite")
            .set_description("Tests for my agent")
            .configure(pass_threshold=80)
            .add_test_case(
                id="test_1",
                category="strong_match",
                description="Test strong match scenario",
                input={"resume": "...", "job_description": "..."},
                expected={"tool_called": "score_job_match"},
            )
            .build())
    """

    def __init__(self, suite_id: str):
        """
        Initialize builder with suite ID.

        Args:
            suite_id: Unique identifier for the test suite
        """
        self._id = suite_id
        self._name = suite_id
        self._version = "1.0"
        self._description = ""
        self._agent_name = ""
        self._author: Optional[str] = None
        self._tags: List[str] = []
        self._config = TestSuiteConfig()
        self._test_cases: List[TestCase] = []

    def set_name(self, name: str) -> 'TestSuiteBuilder':
        """Set suite name"""
        self._name = name
        return self

    def set_version(self, version: str) -> 'TestSuiteBuilder':
        """Set suite version"""
        self._version = version
        return self

    def set_description(self, description: str) -> 'TestSuiteBuilder':
        """Set suite description"""
        self._description = description
        return self

    def set_agent_name(self, agent_name: str) -> 'TestSuiteBuilder':
        """Set the agent being tested"""
        self._agent_name = agent_name
        return self

    def set_author(self, author: str) -> 'TestSuiteBuilder':
        """Set suite author"""
        self._author = author
        return self

    def add_tag(self, tag: str) -> 'TestSuiteBuilder':
        """Add a tag"""
        self._tags.append(tag)
        return self

    def add_tags(self, tags: List[str]) -> 'TestSuiteBuilder':
        """Add multiple tags"""
        self._tags.extend(tags)
        return self

    def configure(
        self,
        pass_threshold: Optional[float] = None,
        evaluators: Optional[List[str]] = None,
        timeout_seconds: Optional[int] = None,
        parallel: Optional[bool] = None,
        max_concurrent: Optional[int] = None,
        retry_failed: Optional[bool] = None,
        retry_count: Optional[int] = None,
        evaluator_weights: Optional[Dict[str, float]] = None,
    ) -> 'TestSuiteBuilder':
        """
        Configure test suite settings.

        Only provided values are updated; others keep defaults.
        """
        if pass_threshold is not None:
            self._config.pass_threshold = pass_threshold
        if evaluators is not None:
            self._config.evaluators = evaluators
        if timeout_seconds is not None:
            self._config.timeout_seconds = timeout_seconds
        if parallel is not None:
            self._config.parallel = parallel
        if max_concurrent is not None:
            self._config.max_concurrent = max_concurrent
        if retry_failed is not None:
            self._config.retry_failed = retry_failed
        if retry_count is not None:
            self._config.retry_count = retry_count
        if evaluator_weights is not None:
            self._config.evaluator_weights = evaluator_weights
        return self

    def add_test_case(
        self,
        id: str,
        input: Dict[str, Any],
        expected: Optional[Dict[str, Any]] = None,
        category: str = "custom",
        description: str = "",
        difficulty: str = "normal",
        tags: Optional[List[str]] = None,
        ground_truth: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        enabled: bool = True,
    ) -> 'TestSuiteBuilder':
        """
        Add a test case to the suite.

        Args:
            id: Unique test case ID
            input: Input data for the agent
            expected: Expected behavior dict (converted to TestCaseExpected)
            category: Test category
            description: Human-readable description
            difficulty: easy/normal/hard
            tags: Test case tags
            ground_truth: Ground truth for validation
            timeout_seconds: Per-test timeout override
            enabled: Whether test is active
        """
        # Build expected
        expected_obj = TestCaseExpected()
        if expected:
            expected_obj = TestCaseExpected(
                tool_called=expected.get("tool_called"),
                required_args=expected.get("required_args", []),
                optional_args=expected.get("optional_args", []),
                arg_types=expected.get("arg_types", {}),
                evaluation_criteria=expected.get("evaluation_criteria"),
                score_range=expected.get("score_range"),
            )

        # Build ground truth
        gt_obj = None
        if ground_truth:
            gt_obj = TestCaseGroundTruth(
                ideal_score_range=ground_truth.get("ideal_score_range"),
                ideal_score=ground_truth.get("ideal_score"),
                key_matches=ground_truth.get("key_matches", []),
                key_mismatches=ground_truth.get("key_mismatches", []),
                required_content=ground_truth.get("required_content", []),
                forbidden_content=ground_truth.get("forbidden_content", []),
                custom=ground_truth.get("custom", {}),
            )

        test_case = TestCase(
            id=id,
            category=category,
            description=description,
            difficulty=difficulty,
            tags=tags or [],
            input=input,
            expected=expected_obj,
            ground_truth=gt_obj,
            timeout_seconds=timeout_seconds,
            enabled=enabled,
        )

        self._test_cases.append(test_case)
        return self

    def add_test_case_object(self, test_case: TestCase) -> 'TestSuiteBuilder':
        """Add a pre-built TestCase object"""
        self._test_cases.append(test_case)
        return self

    def build(self, validate: bool = True) -> TestSuite:
        """
        Build the test suite.

        Args:
            validate: If True, validate before returning

        Returns:
            TestSuite object

        Raises:
            ValueError: If validation fails
        """
        suite = TestSuite(
            id=self._id,
            name=self._name,
            version=self._version,
            description=self._description,
            agent_name=self._agent_name,
            config=self._config,
            test_cases=self._test_cases,
            created_at=datetime.utcnow(),
            author=self._author,
            tags=self._tags,
        )

        if validate:
            validator = TestSuiteValidator()
            result = validator.validate(suite)
            if not result.valid:
                error_msgs = "\n".join([str(e) for e in result.errors])
                raise ValueError(f"Test suite validation failed:\n{error_msgs}")

        return suite


# =============================================================================
# TEST SUITE WRITER
# =============================================================================

class TestSuiteWriter:
    """
    Writes test suites to YAML/JSON files.

    Usage:
        writer = TestSuiteWriter()
        writer.write(suite, "tests/my_suite.yaml")
    """

    def write(
        self,
        suite: TestSuite,
        path: Union[str, Path],
        format: Optional[str] = None,
    ) -> None:
        """
        Write a test suite to file.

        Args:
            suite: TestSuite to write
            path: Output file path
            format: "yaml" or "json" (auto-detected from extension if not specified)
        """
        path = Path(path)

        # Determine format
        if format is None:
            suffix = path.suffix.lower()
            if suffix in [".yaml", ".yml"]:
                format = "yaml"
            elif suffix == ".json":
                format = "json"
            else:
                format = "yaml"  # Default

        # Convert to dict
        data = self._suite_to_dict(suite)

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write
        if format == "yaml":
            self._write_yaml(data, path)
        else:
            self._write_json(data, path)

    def _suite_to_dict(self, suite: TestSuite) -> Dict[str, Any]:
        """Convert TestSuite to serializable dictionary"""
        return {
            "id": suite.id,
            "name": suite.name,
            "version": suite.version,
            "description": suite.description,
            "agent_name": suite.agent_name,
            "author": suite.author,
            "tags": suite.tags,
            "config": {
                "pass_threshold": suite.config.pass_threshold,
                "evaluators": suite.config.evaluators,
                "timeout_seconds": suite.config.timeout_seconds,
                "parallel": suite.config.parallel,
                "max_concurrent": suite.config.max_concurrent,
                "retry_failed": suite.config.retry_failed,
                "retry_count": suite.config.retry_count,
                "evaluator_weights": suite.config.evaluator_weights,
            },
            "test_cases": [
                self._test_case_to_dict(tc)
                for tc in suite.test_cases
            ],
        }

    def _test_case_to_dict(self, tc: TestCase) -> Dict[str, Any]:
        """Convert TestCase to dictionary"""
        result = {
            "id": tc.id,
            "category": tc.category,
            "description": tc.description,
            "difficulty": tc.difficulty,
            "tags": tc.tags,
            "input": tc.input,
            "expected": {
                "tool_called": tc.expected.tool_called,
                "required_args": tc.expected.required_args,
                "optional_args": tc.expected.optional_args,
                "arg_types": tc.expected.arg_types,
                "evaluation_criteria": tc.expected.evaluation_criteria,
                "score_range": tc.expected.score_range,
            },
            "enabled": tc.enabled,
        }

        if tc.timeout_seconds is not None:
            result["timeout_seconds"] = tc.timeout_seconds

        if tc.ground_truth:
            result["ground_truth"] = {
                "ideal_score_range": tc.ground_truth.ideal_score_range,
                "ideal_score": tc.ground_truth.ideal_score,
                "key_matches": tc.ground_truth.key_matches,
                "key_mismatches": tc.ground_truth.key_mismatches,
                "required_content": tc.ground_truth.required_content,
                "forbidden_content": tc.ground_truth.forbidden_content,
                "custom": tc.ground_truth.custom,
            }

        # Clean up None values in expected
        result["expected"] = {k: v for k, v in result["expected"].items() if v}

        return result

    def _write_yaml(self, data: Dict[str, Any], path: Path) -> None:
        """Write as YAML"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def _write_json(self, data: Dict[str, Any], path: Path) -> None:
        """Write as JSON"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_suite_id(name: str, version: str = "1.0") -> str:
    """
    Generate a unique suite ID from name and version.

    Args:
        name: Human-readable name
        version: Version string

    Returns:
        Unique ID string
    """
    base = f"{name}_{version}".lower().replace(" ", "_")
    hash_suffix = hashlib.md5(f"{name}_{version}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]
    return f"{base}_{hash_suffix}"


def merge_test_suites(
    suites: List[TestSuite],
    new_id: str,
    new_name: str,
) -> TestSuite:
    """
    Merge multiple test suites into one.

    Args:
        suites: List of suites to merge
        new_id: ID for merged suite
        new_name: Name for merged suite

    Returns:
        Merged TestSuite
    """
    if not suites:
        raise ValueError("No suites to merge")

    # Collect all test cases with prefixed IDs
    all_test_cases: List[TestCase] = []
    all_tags: set = set()

    for suite in suites:
        all_tags.update(suite.tags)
        for tc in suite.test_cases:
            # Prefix test case ID with suite ID to avoid collisions
            prefixed_tc = TestCase(
                id=f"{suite.id}__{tc.id}",
                category=tc.category,
                description=f"[{suite.name}] {tc.description}",
                difficulty=tc.difficulty,
                tags=tc.tags + [suite.id],  # Add source suite as tag
                input=tc.input,
                expected=tc.expected,
                ground_truth=tc.ground_truth,
                timeout_seconds=tc.timeout_seconds,
                enabled=tc.enabled,
            )
            all_test_cases.append(prefixed_tc)

    # Use config from first suite as base
    config = suites[0].config

    return TestSuite(
        id=new_id,
        name=new_name,
        version="1.0",
        description=f"Merged from: {', '.join(s.name for s in suites)}",
        config=config,
        test_cases=all_test_cases,
        tags=list(all_tags),
    )


def filter_test_cases(
    suite: TestSuite,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    difficulties: Optional[List[str]] = None,
    enabled_only: bool = True,
) -> List[TestCase]:
    """
    Filter test cases from a suite.

    Args:
        suite: Test suite to filter
        categories: Include only these categories (None = all)
        tags: Include only tests with any of these tags (None = all)
        difficulties: Include only these difficulties (None = all)
        enabled_only: If True, exclude disabled tests

    Returns:
        Filtered list of TestCase objects
    """
    result = []

    for tc in suite.test_cases:
        # Check enabled
        if enabled_only and not tc.enabled:
            continue

        # Check category
        if categories and tc.category not in categories:
            continue

        # Check difficulty
        if difficulties and tc.difficulty not in difficulties:
            continue

        # Check tags (any match)
        if tags:
            if not any(tag in tc.tags for tag in tags):
                continue

        result.append(tc)

    return result


def create_subset_suite(
    suite: TestSuite,
    test_case_ids: List[str],
    new_id: Optional[str] = None,
) -> TestSuite:
    """
    Create a new suite with only specified test cases.

    Args:
        suite: Source suite
        test_case_ids: IDs of test cases to include
        new_id: ID for new suite (default: original_id__subset)

    Returns:
        New TestSuite with selected test cases
    """
    id_set = set(test_case_ids)
    selected = [tc for tc in suite.test_cases if tc.id in id_set]

    return TestSuite(
        id=new_id or f"{suite.id}__subset",
        name=f"{suite.name} (Subset)",
        version=suite.version,
        description=f"Subset of {suite.name} with {len(selected)} test cases",
        agent_name=suite.agent_name,
        config=suite.config,
        test_cases=selected,
        tags=suite.tags + ["subset"],
    )
