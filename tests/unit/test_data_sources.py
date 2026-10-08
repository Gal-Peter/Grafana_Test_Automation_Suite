import pytest

from utils.data_loader import load_rows

pytestmark = pytest.mark.unit


def test_csv_source_loads_all_rows_with_unique_ids():
    rows = load_rows("login_invalid")
    assert len(rows) == 4
    assert len({r["id"] for r in rows}) == 4


def test_csv_empty_cell_is_empty_string():
    row = next(r for r in load_rows("login_invalid") if r["id"] == "empty_password")
    assert row["password"] == ""


def test_sqlite_view_aggregates_panels_as_json():
    rows = {r["id"]: r for r in load_rows("dashboards_view", source="sqlite", json_columns=("panels",))}
    assert [p["title"] for p in rows["two_panels"]["panels"]] == ["First Panel", "Second Panel"]
    assert rows["mixed_panel_types"]["panels"][1]["type"] == "timeseries"


def test_sqlite_keeps_native_types():
    row = next(r for r in load_rows("api_negative_cases", source="sqlite", json_columns=("body",))
               if r["id"] == "unauthenticated_rejected")
    assert row["expected_status"] == 401 and row["authenticated"] == 0 and row["body"] is None


def test_sqlite_rejects_unsafe_table_names():
    with pytest.raises(ValueError):
        load_rows("api_negative_cases; DROP TABLE x", source="sqlite")


def test_unknown_source_is_rejected():
    with pytest.raises(ValueError):
        load_rows("login_invalid", source="excel")
