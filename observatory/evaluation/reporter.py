"""
Evaluation Reporters
====================

Generate human-readable reports from evaluation results.

Formats:
- Console: Rich terminal output with colors and formatting
- Markdown: GitHub-flavored markdown for documentation/PRs
- JSON: Structured data for programmatic consumption
- HTML: Web-ready reports (optional)

Usage:
    # Console output
    reporter = ConsoleReporter()
    reporter.print_run(evaluation_run)
    reporter.print_comparison(comparison)

    # Markdown file
    md_reporter = MarkdownReporter()
    content = md_reporter.generate_run_report(evaluation_run)
    md_reporter.save("reports/eval_report.md", content)

    # Quick summary
    summary = ReportBuilder.quick_summary(evaluation_run)
"""

import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
from io import StringIO

# Check if we're on Windows with limited encoding
_USE_ASCII = os.name == 'nt' and not os.environ.get('WT_SESSION')  # Windows but not Windows Terminal

from observatory.models import (
    EvaluationRun,
    EvaluationResultRecord,
    ComparisonRecord,
    Recommendation,
)


# =============================================================================
# CONSOLE COLORS (ANSI escape codes)
# =============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Foreground
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @classmethod
    def disable(cls):
        """Disable colors (for non-terminal output)"""
        for attr in dir(cls):
            if not attr.startswith('_') and attr.isupper():
                setattr(cls, attr, '')


# =============================================================================
# SYMBOLS
# =============================================================================

class Symbols:
    """Unicode symbols for terminal output (with ASCII fallbacks for Windows)"""
    # Use ASCII on Windows cmd.exe, Unicode elsewhere
    if _USE_ASCII:
        CHECK = "[OK]"
        CROSS = "[X]"
        WARNING = "[!]"
        INFO = "[i]"
        ARROW_RIGHT = "->"
        ARROW_UP = "^"
        ARROW_DOWN = "v"
        BULLET = "*"
        STAR = "*"
        CIRCLE = "o"
        FILLED_CIRCLE = "@"
        BAR_EMPTY = "."
        BAR_FILLED = "#"
        HORIZONTAL = "-"
        VERTICAL = "|"
        TOP_LEFT = "+"
        TOP_RIGHT = "+"
        BOTTOM_LEFT = "+"
        BOTTOM_RIGHT = "+"
        T_DOWN = "+"
        T_UP = "+"
        T_RIGHT = "+"
        T_LEFT = "+"
        CROSS_LINE = "+"
    else:
        CHECK = "✓"
        CROSS = "✗"
        WARNING = "⚠"
        INFO = "ℹ"
        ARROW_RIGHT = "→"
        ARROW_UP = "↑"
        ARROW_DOWN = "↓"
        BULLET = "•"
        STAR = "★"
        CIRCLE = "○"
        FILLED_CIRCLE = "●"
        BAR_EMPTY = "░"
        BAR_FILLED = "█"
        HORIZONTAL = "─"
        VERTICAL = "│"
        TOP_LEFT = "┌"
        TOP_RIGHT = "┐"
        BOTTOM_LEFT = "└"
        BOTTOM_RIGHT = "┘"
        T_DOWN = "┬"
        T_UP = "┴"
        T_RIGHT = "├"
        T_LEFT = "┤"
        CROSS_LINE = "┼"


# =============================================================================
# CONSOLE REPORTER
# =============================================================================

class ConsoleReporter:
    """
    Generate rich console output for evaluation results.

    Features:
    - Colorized pass/fail indicators
    - Progress bars for scores
    - Formatted tables
    - Summary statistics
    """

    def __init__(self, use_colors: bool = True, width: int = 80):
        """
        Initialize console reporter.

        Args:
            use_colors: If False, disable ANSI colors
            width: Terminal width for formatting
        """
        self.use_colors = use_colors
        self.width = width

        if not use_colors:
            Colors.disable()

    def print_run(self, run: EvaluationRun) -> None:
        """Print evaluation run summary to console"""
        output = self.format_run(run)
        try:
            print(output)
        except UnicodeEncodeError:
            # Fallback for Windows consoles with limited encoding
            print(output.encode('ascii', errors='replace').decode('ascii'))

    def format_run(self, run: EvaluationRun) -> str:
        """Format evaluation run as string"""
        lines = []

        # Header
        lines.append(self._header(f"Evaluation Run: {run.run_id}"))
        lines.append("")

        # Basic info
        lines.append(f"{Colors.BOLD}Test Suite:{Colors.RESET} {run.test_suite_name or run.test_suite_id}")
        lines.append(f"{Colors.BOLD}Version:{Colors.RESET}    {run.experiment_version}")
        lines.append(f"{Colors.BOLD}Phase:{Colors.RESET}      {run.phase}")
        lines.append(f"{Colors.BOLD}Status:{Colors.RESET}     {self._format_status(run.status)}")
        lines.append("")

        # Metrics summary
        m = run.metrics
        lines.append(self._section_header("Results"))
        lines.append(f"  Total Tests:    {m.total_tests}")
        lines.append(f"  Passed:         {Colors.GREEN}{m.passed_tests}{Colors.RESET}")
        lines.append(f"  Failed:         {Colors.RED if m.failed_tests > 0 else ''}{m.failed_tests}{Colors.RESET}")
        lines.append("")

        # Scores
        lines.append(self._section_header("Scores"))
        lines.append(f"  Pass Rate:      {self._format_percentage(m.pass_rate)}")
        lines.append(f"  Quality Score:  {self._format_score(m.avg_quality_score)}")
        if m.avg_tool_use_score is not None:
            lines.append(f"  Tool Use:       {self._format_score(m.avg_tool_use_score)}")
        if m.avg_model_judge_score is not None:
            lines.append(f"  Model Judge:    {self._format_score(m.avg_model_judge_score)}")
        lines.append("")

        # Performance
        lines.append(self._section_header("Performance"))
        lines.append(f"  Avg Latency:    {m.avg_agent_latency_ms:.0f}ms")
        lines.append(f"  Avg Cost:       ${m.avg_agent_cost:.6f}")
        lines.append(f"  Total Cost:     ${m.total_agent_cost:.4f}")
        lines.append("")

        # Evaluation overhead
        lines.append(self._section_header("Eval Overhead"))
        lines.append(f"  Eval Cost:      ${m.total_eval_cost:.6f}")
        lines.append(f"  Eval Latency:   {m.total_eval_latency_ms:.0f}ms")
        lines.append("")

        # Timing
        if run.started_at and run.completed_at:
            lines.append(self._section_header("Timing"))
            lines.append(f"  Started:        {run.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"  Completed:      {run.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if run.duration_seconds:
                lines.append(f"  Duration:       {run.duration_seconds:.1f}s")
            lines.append("")

        # Failed tests detail
        failed_results = [r for r in run.results if not r.passed]
        if failed_results:
            lines.append(self._section_header(f"Failed Tests ({len(failed_results)})"))
            for result in failed_results[:10]:  # Limit to 10
                lines.append(f"  {Colors.RED}{Symbols.CROSS}{Colors.RESET} {result.test_case_id}")
                if result.reasoning:
                    reason = result.reasoning[:60] + "..." if len(result.reasoning) > 60 else result.reasoning
                    lines.append(f"    {Colors.DIM}{reason}{Colors.RESET}")
            if len(failed_results) > 10:
                lines.append(f"    {Colors.DIM}... and {len(failed_results) - 10} more{Colors.RESET}")
            lines.append("")

        # Footer
        lines.append(self._divider())

        return "\n".join(lines)

    def print_comparison(self, comparison: Union[ComparisonRecord, Dict[str, Any]]) -> None:
        """Print comparison summary to console"""
        output = self.format_comparison(comparison)
        try:
            print(output)
        except UnicodeEncodeError:
            # Fallback for Windows consoles with limited encoding
            print(output.encode('ascii', errors='replace').decode('ascii'))

    def format_comparison(self, comparison: Union[ComparisonRecord, Dict[str, Any]]) -> str:
        """Format comparison as string"""
        lines = []

        # Handle both ComparisonRecord and dict
        if isinstance(comparison, ComparisonRecord):
            data = self._comparison_record_to_dict(comparison)
        else:
            data = comparison

        # Header
        lines.append(self._header(f"Comparison: {data.get('experiment_name', 'Unknown')}"))
        lines.append("")

        # Recommendation banner
        recommendation = data.get("recommendation", "NEUTRAL")
        lines.append(self._recommendation_banner(recommendation))
        lines.append("")

        # Side by side comparison
        baseline = data.get("baseline", {})
        optimized = data.get("optimized", {})
        deltas = data.get("deltas", {})

        lines.append(self._section_header("Comparison"))
        lines.append("")

        # Table header
        lines.append(f"  {'Metric':<20} {'Baseline':>15} {'Optimized':>15} {'Change':>15}")
        lines.append(f"  {self._divider(60)}")

        # Rows
        lines.append(self._comparison_row(
            "Quality Score",
            baseline.get("avg_quality_score", 0),
            optimized.get("avg_quality_score", 0),
            deltas.get("quality_change_abs", 0),
            format_type="score"
        ))
        lines.append(self._comparison_row(
            "Pass Rate",
            baseline.get("pass_rate", 0),
            optimized.get("pass_rate", 0),
            deltas.get("pass_rate_change_abs", 0),
            format_type="percent"
        ))
        lines.append(self._comparison_row(
            "Avg Cost",
            baseline.get("avg_cost", 0),
            optimized.get("avg_cost", 0),
            deltas.get("cost_change_pct", 0),
            format_type="cost"
        ))
        lines.append(self._comparison_row(
            "Avg Latency",
            baseline.get("avg_latency_ms", 0),
            optimized.get("avg_latency_ms", 0),
            deltas.get("latency_change_pct", 0),
            format_type="latency"
        ))
        lines.append("")

        # Summary
        if data.get("reason"):
            lines.append(self._section_header("Analysis"))
            lines.append(f"  {data['reason']}")
            lines.append("")

        if data.get("summary"):
            lines.append(f"  {Colors.DIM}{data['summary']}{Colors.RESET}")
            lines.append("")

        lines.append(self._divider())

        return "\n".join(lines)

    def print_test_result(
        self,
        test_case_id: str,
        passed: bool,
        score: float,
        details: Optional[str] = None
    ) -> None:
        """Print single test result"""
        status = f"{Colors.GREEN}{Symbols.CHECK}{Colors.RESET}" if passed else f"{Colors.RED}{Symbols.CROSS}{Colors.RESET}"
        score_str = self._format_score(score, inline=True)
        print(f"  {status} {test_case_id:<40} {score_str}")
        if details and not passed:
            print(f"    {Colors.DIM}{details}{Colors.RESET}")

    def print_progress(self, current: int, total: int, test_id: str = "") -> None:
        """Print progress indicator"""
        pct = current / total if total > 0 else 0
        bar_width = 30
        filled = int(bar_width * pct)
        bar = Symbols.BAR_FILLED * filled + Symbols.BAR_EMPTY * (bar_width - filled)

        print(f"\r  [{bar}] {current}/{total} {test_id:<30}", end="", flush=True)
        if current == total:
            print()  # New line when complete

    # =========================================================================
    # FORMATTING HELPERS
    # =========================================================================

    def _header(self, text: str) -> str:
        """Format main header"""
        line = Symbols.HORIZONTAL * (self.width - 2)
        return f"{Colors.BOLD}{Colors.CYAN}{Symbols.TOP_LEFT}{line}{Symbols.TOP_RIGHT}\n{Symbols.VERTICAL} {text:<{self.width-4}} {Symbols.VERTICAL}\n{Symbols.BOTTOM_LEFT}{line}{Symbols.BOTTOM_RIGHT}{Colors.RESET}"

    def _section_header(self, text: str) -> str:
        """Format section header"""
        return f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}"

    def _divider(self, width: Optional[int] = None) -> str:
        """Create divider line"""
        w = width or self.width
        return Symbols.HORIZONTAL * w

    def _format_status(self, status: str) -> str:
        """Format status with color"""
        colors = {
            "completed": Colors.GREEN,
            "running": Colors.YELLOW,
            "failed": Colors.RED,
            "pending": Colors.GRAY,
        }
        color = colors.get(status.lower(), Colors.RESET)
        return f"{color}{status.upper()}{Colors.RESET}"

    def _format_score(self, score: float, inline: bool = False) -> str:
        """Format score with color and optional bar"""
        if score >= 80:
            color = Colors.GREEN
        elif score >= 60:
            color = Colors.YELLOW
        else:
            color = Colors.RED

        if inline:
            return f"{color}{score:.1f}{Colors.RESET}"

        # Score with mini bar
        bar_width = 15
        filled = int(bar_width * score / 100)
        bar = Symbols.BAR_FILLED * filled + Symbols.BAR_EMPTY * (bar_width - filled)
        return f"{color}{score:.1f}{Colors.RESET} [{bar}]"

    def _format_percentage(self, value: float) -> str:
        """Format as percentage with color"""
        pct = value * 100 if value <= 1 else value
        if pct >= 80:
            color = Colors.GREEN
        elif pct >= 60:
            color = Colors.YELLOW
        else:
            color = Colors.RED
        return f"{color}{pct:.1f}%{Colors.RESET}"

    def _recommendation_banner(self, recommendation: str) -> str:
        """Format recommendation as banner"""
        colors = {
            "DEPLOY": (Colors.BG_GREEN, Colors.WHITE),
            "INVESTIGATE": (Colors.BG_YELLOW, Colors.WHITE),
            "REJECT": (Colors.BG_RED, Colors.WHITE),
            "NEUTRAL": (Colors.GRAY, Colors.WHITE),
        }
        bg, fg = colors.get(recommendation, (Colors.RESET, Colors.RESET))
        text = f" {Symbols.STAR} RECOMMENDATION: {recommendation} {Symbols.STAR} "
        padding = (self.width - len(text)) // 2
        return f"{bg}{fg}{' ' * padding}{text}{' ' * padding}{Colors.RESET}"

    def _comparison_row(
        self,
        label: str,
        baseline: float,
        optimized: float,
        change: float,
        format_type: str = "default"
    ) -> str:
        """Format comparison table row"""
        # Format values based on type
        if format_type == "score":
            b_str = f"{baseline:.1f}"
            o_str = f"{optimized:.1f}"
            c_str = f"{change:+.1f}"
        elif format_type == "percent":
            b_str = f"{baseline*100:.1f}%"
            o_str = f"{optimized*100:.1f}%"
            c_str = f"{change*100:+.1f}%"
        elif format_type == "cost":
            b_str = f"${baseline:.6f}"
            o_str = f"${optimized:.6f}"
            c_str = f"{change:+.1f}%"
        elif format_type == "latency":
            b_str = f"{baseline:.0f}ms"
            o_str = f"{optimized:.0f}ms"
            c_str = f"{change:+.1f}%"
        else:
            b_str = f"{baseline}"
            o_str = f"{optimized}"
            c_str = f"{change:+.2f}"

        # Color change indicator
        if change > 0.1:
            arrow = f"{Colors.GREEN}{Symbols.ARROW_UP}{Colors.RESET}"
        elif change < -0.1:
            arrow = f"{Colors.RED}{Symbols.ARROW_DOWN}{Colors.RESET}"
        else:
            arrow = f"{Colors.GRAY}{Symbols.ARROW_RIGHT}{Colors.RESET}"

        return f"  {label:<20} {b_str:>15} {o_str:>15} {arrow} {c_str:>12}"

    def _comparison_record_to_dict(self, record: ComparisonRecord) -> Dict[str, Any]:
        """Convert ComparisonRecord to dict format"""
        return {
            "experiment_name": record.experiment_name,
            "baseline": {
                "version": record.baseline.version,
                "avg_quality_score": record.baseline.avg_quality_score,
                "pass_rate": record.baseline.pass_rate,
                "avg_cost": record.baseline.avg_cost,
                "avg_latency_ms": record.baseline.avg_latency_ms,
            },
            "optimized": {
                "version": record.optimized.version,
                "avg_quality_score": record.optimized.avg_quality_score,
                "pass_rate": record.optimized.pass_rate,
                "avg_cost": record.optimized.avg_cost,
                "avg_latency_ms": record.optimized.avg_latency_ms,
            },
            "deltas": {
                "quality_change_abs": record.deltas.quality_change_abs,
                "quality_change_pct": record.deltas.quality_change_pct,
                "cost_change_pct": record.deltas.cost_change_pct,
                "latency_change_pct": record.deltas.latency_change_pct,
                "pass_rate_change_abs": record.deltas.pass_rate_change_abs,
            },
            "recommendation": record.recommendation,
            "reason": record.reason,
            "summary": record.summary,
        }


# =============================================================================
# MARKDOWN REPORTER
# =============================================================================

class MarkdownReporter:
    """
    Generate GitHub-flavored markdown reports.

    Features:
    - Formatted tables
    - Collapsible sections
    - Badges for status
    - Mermaid diagrams (optional)
    """

    def generate_run_report(
        self,
        run: EvaluationRun,
        include_details: bool = True,
        include_failed_tests: bool = True,
    ) -> str:
        """Generate markdown report for evaluation run"""
        lines = []

        # Header
        lines.append(f"# Evaluation Run: `{run.run_id}`")
        lines.append("")

        # Badges
        status_badge = self._status_badge(run.status)
        pass_rate_badge = self._pass_rate_badge(run.metrics.pass_rate)
        lines.append(f"{status_badge} {pass_rate_badge}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Test Suite:** {run.test_suite_name or run.test_suite_id}")
        lines.append(f"- **Version:** {run.experiment_version}")
        lines.append(f"- **Phase:** {run.phase}")
        lines.append(f"- **Status:** {run.status}")
        if run.started_at:
            lines.append(f"- **Started:** {run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if run.duration_seconds:
            lines.append(f"- **Duration:** {run.duration_seconds:.1f}s")
        lines.append("")

        # Results table
        lines.append("## Results")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Tests | {run.metrics.total_tests} |")
        lines.append(f"| Passed | {run.metrics.passed_tests} |")
        lines.append(f"| Failed | {run.metrics.failed_tests} |")
        lines.append(f"| Pass Rate | {run.metrics.pass_rate*100:.1f}% |")
        lines.append("")

        # Scores table
        lines.append("## Scores")
        lines.append("")
        lines.append("| Evaluator | Average Score |")
        lines.append("|-----------|---------------|")
        lines.append(f"| Overall Quality | {run.metrics.avg_quality_score:.1f} |")
        if run.metrics.avg_tool_use_score is not None:
            lines.append(f"| Tool Use | {run.metrics.avg_tool_use_score:.1f} |")
        if run.metrics.avg_model_judge_score is not None:
            lines.append(f"| Model Judge | {run.metrics.avg_model_judge_score:.1f} |")
        lines.append("")

        # Performance
        lines.append("## Performance")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Avg Agent Latency | {run.metrics.avg_agent_latency_ms:.0f}ms |")
        lines.append(f"| Avg Agent Cost | ${run.metrics.avg_agent_cost:.6f} |")
        lines.append(f"| Total Agent Cost | ${run.metrics.total_agent_cost:.4f} |")
        lines.append(f"| Total Eval Cost | ${run.metrics.total_eval_cost:.6f} |")
        lines.append("")

        # Failed tests
        if include_failed_tests:
            failed = [r for r in run.results if not r.passed]
            if failed:
                lines.append("## Failed Tests")
                lines.append("")
                lines.append("<details>")
                lines.append(f"<summary>Show {len(failed)} failed tests</summary>")
                lines.append("")
                lines.append("| Test Case | Evaluator | Score | Reason |")
                lines.append("|-----------|-----------|-------|--------|")
                for result in failed:
                    reason = result.reasoning[:50] + "..." if len(result.reasoning) > 50 else result.reasoning
                    reason = reason.replace("|", "\\|")  # Escape pipes
                    lines.append(f"| {result.test_case_id} | {result.evaluator} | {result.score:.1f} | {reason} |")
                lines.append("")
                lines.append("</details>")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*")

        return "\n".join(lines)

    def generate_comparison_report(
        self,
        comparison: Union[ComparisonRecord, Dict[str, Any]],
    ) -> str:
        """Generate markdown report for comparison"""
        lines = []

        # Handle both types
        if isinstance(comparison, ComparisonRecord):
            data = {
                "experiment_name": comparison.experiment_name,
                "baseline": {
                    "version": comparison.baseline.version,
                    "run_id": comparison.baseline.run_id,
                    "avg_quality_score": comparison.baseline.avg_quality_score,
                    "pass_rate": comparison.baseline.pass_rate,
                    "avg_cost": comparison.baseline.avg_cost,
                    "avg_latency_ms": comparison.baseline.avg_latency_ms,
                },
                "optimized": {
                    "version": comparison.optimized.version,
                    "run_id": comparison.optimized.run_id,
                    "avg_quality_score": comparison.optimized.avg_quality_score,
                    "pass_rate": comparison.optimized.pass_rate,
                    "avg_cost": comparison.optimized.avg_cost,
                    "avg_latency_ms": comparison.optimized.avg_latency_ms,
                },
                "deltas": {
                    "quality_change_abs": comparison.deltas.quality_change_abs,
                    "quality_change_pct": comparison.deltas.quality_change_pct,
                    "cost_change_pct": comparison.deltas.cost_change_pct,
                    "latency_change_pct": comparison.deltas.latency_change_pct,
                    "pass_rate_change_abs": comparison.deltas.pass_rate_change_abs,
                },
                "recommendation": comparison.recommendation,
                "reason": comparison.reason,
                "summary": comparison.summary,
            }
        else:
            data = comparison

        # Header
        lines.append(f"# Comparison: {data.get('experiment_name', 'Unknown')}")
        lines.append("")

        # Recommendation badge
        rec = data.get("recommendation", "NEUTRAL")
        badge = self._recommendation_badge(rec)
        lines.append(f"**Recommendation:** {badge}")
        lines.append("")

        # Summary
        if data.get("summary"):
            lines.append(f"> {data['summary']}")
            lines.append("")

        # Comparison table
        baseline = data.get("baseline", {})
        optimized = data.get("optimized", {})
        deltas = data.get("deltas", {})

        lines.append("## Comparison Table")
        lines.append("")
        lines.append("| Metric | Baseline | Optimized | Change |")
        lines.append("|--------|----------|-----------|--------|")
        lines.append(f"| Version | `{baseline.get('version', '-')}` | `{optimized.get('version', '-')}` | - |")
        lines.append(f"| Quality Score | {baseline.get('avg_quality_score', 0):.1f} | {optimized.get('avg_quality_score', 0):.1f} | {deltas.get('quality_change_abs', 0):+.1f} ({deltas.get('quality_change_pct', 0):+.1f}%) |")
        lines.append(f"| Pass Rate | {baseline.get('pass_rate', 0)*100:.1f}% | {optimized.get('pass_rate', 0)*100:.1f}% | {deltas.get('pass_rate_change_abs', 0)*100:+.1f}% |")
        lines.append(f"| Avg Cost | ${baseline.get('avg_cost', 0):.6f} | ${optimized.get('avg_cost', 0):.6f} | {deltas.get('cost_change_pct', 0):+.1f}% |")
        lines.append(f"| Avg Latency | {baseline.get('avg_latency_ms', 0):.0f}ms | {optimized.get('avg_latency_ms', 0):.0f}ms | {deltas.get('latency_change_pct', 0):+.1f}% |")
        lines.append("")

        # Analysis
        if data.get("reason"):
            lines.append("## Analysis")
            lines.append("")
            lines.append(data["reason"])
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*")

        return "\n".join(lines)

    def save(self, path: Union[str, Path], content: str) -> None:
        """Save markdown content to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # =========================================================================
    # BADGE HELPERS
    # =========================================================================

    def _status_badge(self, status: str) -> str:
        """Generate status badge"""
        colors = {
            "completed": "success",
            "running": "yellow",
            "failed": "critical",
            "pending": "inactive",
        }
        color = colors.get(status.lower(), "inactive")
        return f"![Status](https://img.shields.io/badge/status-{status}-{color})"

    def _pass_rate_badge(self, pass_rate: float) -> str:
        """Generate pass rate badge"""
        pct = pass_rate * 100
        if pct >= 90:
            color = "success"
        elif pct >= 70:
            color = "yellow"
        else:
            color = "critical"
        return f"![Pass Rate](https://img.shields.io/badge/pass_rate-{pct:.0f}%25-{color})"

    def _recommendation_badge(self, recommendation: str) -> str:
        """Generate recommendation badge"""
        colors = {
            "DEPLOY": "success",
            "INVESTIGATE": "yellow",
            "REJECT": "critical",
            "NEUTRAL": "inactive",
        }
        color = colors.get(recommendation, "inactive")
        return f"![{recommendation}](https://img.shields.io/badge/recommendation-{recommendation}-{color})"


# =============================================================================
# JSON REPORTER
# =============================================================================

class JSONReporter:
    """Generate JSON format reports for programmatic consumption"""

    def generate_run_report(self, run: EvaluationRun) -> str:
        """Generate JSON report for evaluation run"""
        data = {
            "run_id": run.run_id,
            "test_suite_id": run.test_suite_id,
            "test_suite_name": run.test_suite_name,
            "experiment_version": run.experiment_version,
            "phase": run.phase,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_seconds": run.duration_seconds,
            "metrics": {
                "total_tests": run.metrics.total_tests,
                "passed_tests": run.metrics.passed_tests,
                "failed_tests": run.metrics.failed_tests,
                "pass_rate": run.metrics.pass_rate,
                "avg_quality_score": run.metrics.avg_quality_score,
                "avg_tool_use_score": run.metrics.avg_tool_use_score,
                "avg_model_judge_score": run.metrics.avg_model_judge_score,
                "total_agent_cost": run.metrics.total_agent_cost,
                "total_eval_cost": run.metrics.total_eval_cost,
            },
            "results": [
                {
                    "test_case_id": r.test_case_id,
                    "evaluator": r.evaluator,
                    "score": r.score,
                    "passed": r.passed,
                    "reasoning": r.reasoning,
                }
                for r in run.results
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }
        return json.dumps(data, indent=2)

    def save(self, path: Union[str, Path], content: str) -> None:
        """Save JSON content to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# =============================================================================
# REPORT BUILDER (CONVENIENCE)
# =============================================================================

class ReportBuilder:
    """Convenience class for building reports"""

    @staticmethod
    def quick_summary(run: EvaluationRun) -> str:
        """Generate quick one-line summary"""
        m = run.metrics
        status = "PASS" if m.pass_rate >= 0.8 else "FAIL"
        return f"[{status}] {run.test_suite_id}: {m.passed_tests}/{m.total_tests} tests passed ({m.pass_rate*100:.0f}%), Quality: {m.avg_quality_score:.1f}, Cost: ${m.total_agent_cost:.4f}"

    @staticmethod
    def comparison_summary(comparison: Dict[str, Any]) -> str:
        """Generate quick comparison summary"""
        rec = comparison.get("recommendation", "NEUTRAL")
        deltas = comparison.get("deltas", {})
        quality = deltas.get("quality_change_abs", 0)
        cost = deltas.get("cost_change_pct", 0)
        return f"[{rec}] Quality: {quality:+.1f}, Cost: {cost:+.1f}%"

    @staticmethod
    def multi_format_report(
        run: EvaluationRun,
        base_path: Union[str, Path],
    ) -> Dict[str, Path]:
        """Generate reports in multiple formats"""
        base_path = Path(base_path)
        paths = {}

        # Markdown
        md_reporter = MarkdownReporter()
        md_content = md_reporter.generate_run_report(run)
        md_path = base_path.with_suffix(".md")
        md_reporter.save(md_path, md_content)
        paths["markdown"] = md_path

        # JSON
        json_reporter = JSONReporter()
        json_content = json_reporter.generate_run_report(run)
        json_path = base_path.with_suffix(".json")
        json_reporter.save(json_path, json_content)
        paths["json"] = json_path

        return paths
