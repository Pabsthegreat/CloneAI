from __future__ import annotations

from pathlib import Path

from agent.executor.workflow_builder import (
    BuildEnvironment,
    BuildStatus,
    LLMTier,
    PatchProposal,
    WorkflowAutoBuilder,
    WorkflowRecipe,
)


def test_workflow_recipe_tier_selection():
    small_recipe = WorkflowRecipe(
        namespace="demo",
        name="small",
        summary="small task",
        description="A simple workflow.",
        complexity="small",
    )
    assert small_recipe.preferred_tier() is LLMTier.LOCAL

    large_recipe = WorkflowRecipe(
        namespace="demo",
        name="large",
        summary="large task",
        description="A large workflow.",
        complexity="large",
    )
    assert large_recipe.preferred_tier() is LLMTier.CLOUD

    busy_recipe = WorkflowRecipe(
        namespace="demo",
        name="busy",
        summary="Many tests",
        description="Requires several tests.",
        complexity="small",
        acceptance_tests=["a", "b", "c", "d"],
    )
    assert busy_recipe.preferred_tier() is LLMTier.CLOUD


def test_auto_builder_rejects_dangerous_patch():
    recipe = WorkflowRecipe(
        namespace="demo",
        name="danger",
        summary="Dangerous patch",
        description="Should be rejected.",
    )

    builder = WorkflowAutoBuilder(environment_factory=BuildEnvironment)
    apply_called = False

    def request_patch(_recipe: WorkflowRecipe, _tier: LLMTier) -> PatchProposal:
        return PatchProposal(diff="rm -rf /", summary="delete everything")

    def apply_patch(_proposal: PatchProposal, _sandbox: Path) -> None:
        nonlocal apply_called
        apply_called = True

    def run_validations(_commands, _sandbox: Path):
        return []

    result = builder.build(
        recipe,
        request_patch=request_patch,
        apply_patch=apply_patch,
        run_validations=run_validations,
    )

    assert result.status is BuildStatus.REJECTED
    assert not result.applied
    assert not apply_called


def test_auto_builder_success_flow(tmp_path):
    recipe = WorkflowRecipe(
        namespace="demo",
        name="success",
        summary="Successful build",
        description="All checks should pass.",
        validation_commands=["pytest tests/test_sample.py"],
    )

    class LocalEnv(BuildEnvironment):
        def create(self) -> Path:
            # Use tmp_path to keep test deterministic.
            return tmp_path

        def cleanup(self) -> None:
            # Do not delete tmp_path; pytest will handle it.
            pass

    builder = WorkflowAutoBuilder(environment_factory=LocalEnv)
    applied_patches: list[PatchProposal] = []
    validations_ran: list[list[str]] = []

    def request_patch(_recipe: WorkflowRecipe, tier: LLMTier) -> PatchProposal:
        assert tier is LLMTier.LOCAL
        return PatchProposal(
            diff="*** Begin Patch\n*** End Patch",
            summary="No-op patch",
            tests_to_run=["pytest -k success"],
        )

    def apply_patch(proposal: PatchProposal, sandbox: Path) -> None:
        assert sandbox == tmp_path
        applied_patches.append(proposal)

    def run_validations(commands, sandbox: Path):
        assert sandbox == tmp_path
        validations_ran.append(list(commands))
        return []

    result = builder.build(
        recipe,
        request_patch=request_patch,
        apply_patch=apply_patch,
        run_validations=run_validations,
    )

    assert result.status is BuildStatus.SUCCESS
    assert result.applied
    assert applied_patches
    assert validations_ran
