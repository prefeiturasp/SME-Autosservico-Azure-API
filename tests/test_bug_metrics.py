# tests/test_bug_metrics.py
import pytest

from services.azure_devops import AzureDevOpsService
from utils.helpers import humanize_duration_hours, format_duration_label


def _bug(state, created=None, resolved=None, work_item_type="BugFix"):
    fields = {"System.WorkItemType": work_item_type, "System.State": state}
    if created:
        fields["System.CreatedDate"] = created
    if resolved:
        fields["Microsoft.VSTS.Common.ResolvedDate"] = resolved
    return {"fields": fields}


def _service():
    return AzureDevOpsService(organization="org", project_name="proj", pat="pat")


def test_bug_metrics_counts_by_state():
    """Agrupamento dos estados em abertos, em andamento e resolvidos."""
    items = (
        [_bug("New", "2024-05-01T00:00:00Z") for _ in range(3)]
        + [_bug("Approved", "2024-05-01T00:00:00Z") for _ in range(2)]
        + [_bug("Active", "2024-05-01T00:00:00Z") for _ in range(1)]
        + [_bug("Testing", "2024-05-01T00:00:00Z") for _ in range(1)]
        + [_bug("Blocked", "2024-05-01T00:00:00Z") for _ in range(1)]
        + [
            _bug("Resolved", "2024-05-01T00:00:00Z", "2024-05-03T00:00:00Z")
            for _ in range(4)
        ]
        + [
            _bug("Done", "2024-05-01T00:00:00Z", "2024-05-03T00:00:00Z")
            for _ in range(3)
        ]
    )

    metrics = _service()._compute_bug_metrics(items)

    assert metrics.total_cycle == 15
    assert metrics.open == 5          # New + Approved
    assert metrics.in_progress == 3   # Active + Testing + Blocked
    assert metrics.resolved == 7      # Resolved + Done
    assert metrics.average_resolution == "2d"


def test_bug_metrics_counts_all_types():
    """Todos os tipos retornados entram nas métricas (BugFix, HotFix, etc.)."""
    items = [
        _bug("New", work_item_type="BugFix"),
        _bug("Active", work_item_type="HotFix"),
        _bug("Resolved", "2024-05-01T00:00:00Z", "2024-05-02T00:00:00Z",
             work_item_type="Bug"),
    ]

    metrics = _service()._compute_bug_metrics(items)

    assert metrics.total_cycle == 3
    assert metrics.open == 1
    assert metrics.in_progress == 1
    assert metrics.resolved == 1


def test_bug_metrics_done_counts_as_resolved():
    """Itens em 'Done' contam como resolvidos."""
    items = [
        _bug("Done", "2024-05-01T00:00:00Z", "2024-05-05T00:00:00Z"),
    ]

    metrics = _service()._compute_bug_metrics(items)

    assert metrics.resolved == 1
    assert metrics.total_cycle == 1
    assert metrics.average_resolution == "4d"


def test_bug_metrics_empty():
    """Sem work items, métricas zeradas e tempo médio indefinido."""
    metrics = _service()._compute_bug_metrics([])

    assert metrics.total_cycle == 0
    assert metrics.open == 0
    assert metrics.in_progress == 0
    assert metrics.resolved == 0
    assert metrics.average_resolution is None


def test_bug_metrics_low_value_uses_hours():
    """Tempo baixo (5h) deve vir em horas, não em fração de dia."""
    items = [
        {
            "fields": {
                "System.WorkItemType": "Bug",
                "System.State": "Resolved",
                "System.CreatedDate": "2024-05-01T00:00:00Z",
                "Microsoft.VSTS.Common.ResolvedDate": "2024-05-01T05:00:00Z",
            }
        }
    ]

    metrics = _service()._compute_bug_metrics(items)

    assert metrics.average_resolution == "5h"


@pytest.mark.parametrize(
    "total_hours, expected",
    [
        (0.5, (30.0, "minutes")),   # 30 min
        (5, (5.0, "hours")),        # 5 horas
        (48, (2.0, "days")),        # 2 dias
        (24 * 45, (1.5, "months")), # 45 dias -> 1.5 meses
        (24 * 365 * 2, (2.0, "years")),  # 2 anos
    ],
)
def test_humanize_duration_hours(total_hours, expected):
    assert humanize_duration_hours(total_hours) == expected


@pytest.mark.parametrize(
    "value, unit, expected",
    [
        (30.0, "minutes", "30min"),
        (5.0, "hours", "5h"),
        (2.0, "days", "2d"),
        (1.5, "months", "1,5 meses"),
        (1.0, "months", "1 mês"),
        (2.0, "years", "2 anos"),
        (1.0, "years", "1 ano"),
    ],
)
def test_format_duration_label(value, unit, expected):
    assert format_duration_label(value, unit) == expected
