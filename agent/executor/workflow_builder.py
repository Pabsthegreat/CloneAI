"""
Automated workflow generation scaffolding.

This module orchestrates planning, LLM selection, guarded patch generation,
and validation before applying code changes suggested by models.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence


class BuildStatus(Enum):
    """Possible outcomes for the workflow build pipeline."""

    SUCCESS = "success"
    REJECTED = "rejected"
    FAILED = "failed"


class BuildError(Exception):
    """Base exception for build pipeline failures."""


class PatchValidationError(BuildError):
    """Raised when a generated patch fails guard checks."""


class LLMExecutionError(BuildError):
    """Raised when the LLM client fails to complete a request."""


class LLMTier(str, Enum):
    """LLM tier preference for a workflow."""

    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class WorkflowRecipe:
    """
    Developer-authored recipe describing a new or updated workflow.

    This is the primary artifact passed to the builder agent before asking an LLM
    to write code.
    """

    namespace: str
    name: str
    summary: str
    description: str
    complexity: str = "small"  # small | medium | large
    acceptance_tests: List[str] = field(default_factory=list)
    validation_commands: List[str] = field(default_factory=list)
    safety_constraints: List[str] = field(default_factory=list)
    context_files: List[str] = field(default_factory=list)
    notes: Dict[str, str] = field(default_factory=dict)

    def command_key(self) -> str:
        return f"{self.namespace}:{self.name}"

    def preferred_tier(self) -> LLMTier:
        """
        Decide whether a recipe should use a local or cloud model.

        Heuristics:
            - medium/large complexity defaults to cloud
            - explicit note `force_tier` overrides
        """
        force_tier = self.notes.get("force_tier")
        if force_tier == LLMTier.LOCAL.value:
            return LLMTier.LOCAL
        if force_tier == LLMTier.CLOUD.value:
            return LLMTier.CLOUD

        if self.complexity.lower() in {"medium", "large"}:
            return LLMTier.CLOUD

        if len(self.context_files) > 6 or len(self.acceptance_tests) > 3:
            return LLMTier.CLOUD

        return LLMTier.LOCAL


@dataclass
class PatchProposal:
    """Structured container for diff proposals produced by an LLM."""

    diff: str
    summary: str
    tests_to_run: Sequence[str] = field(default_factory=tuple)
    touched_files: Sequence[str] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return not self.diff.strip()


@dataclass
class BuildResult:
    """Result of executing the workflow builder pipeline."""

    status: BuildStatus
    tier: LLMTier
    applied: bool
    errors: List[str] = field(default_factory=list)
    patches: List[PatchProposal] = field(default_factory=list)
    working_dir: Optional[Path] = None

    @property
    def succeeded(self) -> bool:
        return self.status is BuildStatus.SUCCESS and self.applied


class PatchGuard:
    """
    Performs lightweight checks on generated patches before applying them.

    The guard errs on the side of caution—any suspicious content triggers rejection.
    """

    _DANGEROUS_PATTERNS: Sequence[str] = (
        "rm -rf",
        "os.remove(",
        "shutil.rmtree(",
        "DROP TABLE",
        "ALTER TABLE",
        "subprocess.call(['rm'",
    )

    def validate(self, proposal: PatchProposal) -> None:
        if proposal.is_empty():
            raise PatchValidationError("Proposed patch is empty.")

        lowered = proposal.diff.lower()
        for pattern in self._DANGEROUS_PATTERNS:
            if pattern.lower() in lowered:
                raise PatchValidationError(
                    f"Patch contains dangerous pattern: '{pattern}'"
                )


class LLMSelector:
    """Selects an LLM tier for a recipe."""

    def choose(self, recipe: WorkflowRecipe) -> LLMTier:
        return recipe.preferred_tier()


class BuildEnvironment:
    """
    Manages a temporary sandbox where patches are applied and validated.
    Ensures the main workspace remains untouched until validation completes.
    """

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()
        self._tempdir: Optional[tempfile.TemporaryDirectory[str]] = None

    def create(self) -> Path:
        if self._tempdir is not None:
            return Path(self._tempdir.name)
        self._tempdir = tempfile.TemporaryDirectory(prefix="clai-build-")
        temp_path = Path(self._tempdir.name)
        return temp_path

    def cleanup(self) -> None:
        if self._tempdir is not None:
            self._tempdir.cleanup()
            self._tempdir = None


class WorkflowAutoBuilder:
    """
    High-level coordinator that turns recipes into code patches using LLMs.
    This class does not talk to an LLM directly; instead, it relies on injectable
    callables for model interaction so it is easy to test.
    """

    def __init__(
        self,
        *,
        selector: Optional[LLMSelector] = None,
        guard: Optional[PatchGuard] = None,
        environment_factory: Callable[[], BuildEnvironment] = BuildEnvironment,
    ):
        self.selector = selector or LLMSelector()
        self.guard = guard or PatchGuard()
        self.environment_factory = environment_factory

    def build(
        self,
        recipe: WorkflowRecipe,
        *,
        request_patch: Callable[[WorkflowRecipe, LLMTier], PatchProposal],
        apply_patch: Callable[[PatchProposal, Path], None],
        run_validations: Callable[[Iterable[str], Path], Sequence[str]],
    ) -> BuildResult:
        """
        Execute the workflow building pipeline.

        Args:
            recipe: recipe describing the workflow extension.
            request_patch: callable that interacts with an LLM to obtain a patch.
            apply_patch: callable that applies the patch inside the sandbox directory.
            run_validations: callable that runs validations/tests and returns failures.
        """
        tier = self.selector.choose(recipe)
        environment = self.environment_factory()
        sandbox = environment.create()
        patches: List[PatchProposal] = []
        errors: List[str] = []

        try:
            proposal = request_patch(recipe, tier)
            patches.append(proposal)
            self.guard.validate(proposal)

            apply_patch(proposal, sandbox)

            commands = list(recipe.validation_commands) or list(proposal.tests_to_run)
            failures = run_validations(commands, sandbox)

            if failures:
                errors.extend(failures)
                return BuildResult(
                    status=BuildStatus.FAILED,
                    tier=tier,
                    applied=False,
                    errors=errors,
                    patches=patches,
                    working_dir=sandbox,
                )

            return BuildResult(
                status=BuildStatus.SUCCESS,
                tier=tier,
                applied=True,
                patches=patches,
                working_dir=sandbox,
            )
        except PatchValidationError as exc:
            errors.append(str(exc))
            return BuildResult(
                status=BuildStatus.REJECTED,
                tier=tier,
                applied=False,
                errors=errors,
                patches=patches,
                working_dir=sandbox,
            )
        except LLMExecutionError as exc:
            errors.append(str(exc))
            return BuildResult(
                status=BuildStatus.FAILED,
                tier=tier,
                applied=False,
                errors=errors,
                patches=patches,
                working_dir=sandbox,
            )
        except Exception as exc:  # pragma: no cover - defensive default
            errors.append(f"Unexpected error: {exc}")
            return BuildResult(
                status=BuildStatus.FAILED,
                tier=tier,
                applied=False,
                errors=errors,
                patches=patches,
                working_dir=sandbox,
            )
        finally:
            # We intentionally keep the sandbox intact for inspection on failure.
            if not errors:
                environment.cleanup()


__all__ = [
    "BuildEnvironment",
    "BuildError",
    "BuildResult",
    "BuildStatus",
    "LLMExecutionError",
    "LLMSelector",
    "LLMTier",
    "PatchGuard",
    "PatchProposal",
    "PatchValidationError",
    "WorkflowAutoBuilder",
    "WorkflowRecipe",
]
