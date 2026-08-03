"""Tests for the palette ranker (fuzzy match, recency, persistence)."""

from __future__ import annotations

import json
from pathlib import Path

from tekla_nest.services.palette_ranker import (
    _HISTORY_CAP,
    fuzzy_score,
    load_history,
    rank_commands,
    record_invocation,
    save_history,
)


class TestFuzzyScore:
    def test_empty_query_returns_zero(self) -> None:
        assert fuzzy_score("", "Calculate") == 0

    def test_exact_prefix_scores_highest(self) -> None:
        prefix = fuzzy_score("calc", "Calculate")
        middle = fuzzy_score("ate", "Calculate")
        assert prefix is not None
        assert middle is not None
        assert prefix > middle

    def test_no_match_returns_none(self) -> None:
        assert fuzzy_score("xyz", "Calculate") is None

    def test_word_start_bonus_after_separators(self) -> None:
        with_break = fuzzy_score("ls", "Load Stock")
        without = fuzzy_score("ls", "blossom")
        assert with_break is not None
        assert without is not None
        assert with_break > without

    def test_case_insensitive(self) -> None:
        assert fuzzy_score("CALC", "calculate") == fuzzy_score("calc", "Calculate")


class TestRankCommands:
    def test_filters_non_matches(self) -> None:
        ranked = rank_commands(
            "calc",
            [("calculate", "Calculate"), ("load", "Load Parts")],
        )
        assert [r.command_id for r in ranked] == ["calculate"]

    def test_empty_query_uses_recency(self) -> None:
        history = [("load", 100.0), ("calc", 200.0)]
        ranked = rank_commands(
            "",
            [("calc", "Calculate"), ("load", "Load Parts"), ("other", "Other")],
            history,
            now=200.0,
        )
        # calc most recent → highest score, other has no history → lowest
        assert ranked[0].command_id == "calc"
        assert ranked[-1].command_id == "other"

    def test_recency_breaks_ties(self) -> None:
        # 'a' is 4 weeks old (4 half-lives → ~1/16 weight), 'b' is fresh.
        history = [("a", 0.0), ("b", 4 * 7 * 24 * 3600.0)]
        ranked = rank_commands(
            "",
            [("a", "Same"), ("b", "Same")],
            history,
            now=4 * 7 * 24 * 3600.0,
        )
        assert ranked[0].command_id == "b"


class TestHistoryPersistence:
    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert load_history(tmp_path / "missing.json") == []

    def test_load_malformed_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "prefs.json"
        p.write_text("not json", encoding="utf-8")
        assert load_history(p) == []

    def test_round_trip(self, tmp_path: Path) -> None:
        p = tmp_path / "prefs.json"
        history = [("calc", 100.0), ("load", 200.0)]
        save_history(history, p)
        assert load_history(p) == history

    def test_save_preserves_other_keys(self, tmp_path: Path) -> None:
        p = tmp_path / "prefs.json"
        p.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
        save_history([("calc", 1.0)], p)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["theme"] == "dark"
        assert data["palette_history"] == [["calc", 1.0]]

    def test_record_caps_at_history_limit(self) -> None:
        history = [("c", float(i)) for i in range(_HISTORY_CAP)]
        new_history = record_invocation("new", history, now=999999.0)
        assert len(new_history) == _HISTORY_CAP
        assert new_history[-1] == ("new", 999999.0)
