"""The local CI check rejects action drift."""

from scripts.check_ci import ALLOWED_ACTIONS, validate_workflow


def test_unpinned_action_is_rejected() -> None:
    workflow = "- uses: actions/checkout@v4\n"

    assert "Unapproved action or pin" in " ".join(validate_workflow(workflow))


def test_known_full_pins_are_accepted() -> None:
    workflow = "\n".join(
        f"- uses: {name}@{revision}" for name, revision in ALLOWED_ACTIONS.items()
    )
    workflow += (
        "\npermissions:\n  contents: read\n"
        "cancel-in-progress: true\n"
        "persist-credentials: false\n"
        "timeout-minutes: 15\n"
        "uv sync --locked --all-packages --all-groups\n"
        "scripts/check-quality.sh all\n"
        "bash scripts/check-migrations.sh\n"
    )

    assert validate_workflow(workflow) == []
