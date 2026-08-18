"""Tests for pure utility functions across the codebase."""

import pytest
from ui.ui_utils import classify_comparison_line, parse_wt
from engine import (
    _normalize_selected_fitting_label,
    _selected_fitting_matches_recommendation,
    _evaluate_selected_fitting_against_recommendations,
)


class TestClassifyComparisonLine:
    def test_success_detection(self):
        assert classify_comparison_line("Mukavemet OK: Boru 360 MPa vs Fitting 415 MPa") == "success"
        assert classify_comparison_line("Some Uyumlu. text") == "success"

    def test_warning_detection(self):
        assert classify_comparison_line("Uyarısı: Fitting hafif alt-eşleşmiş. kontrol edin") == "warning"

    def test_error_detection(self):
        assert classify_comparison_line("Uyumsuz: Fitting akma değeri çok düşük") == "error"

    def test_divider_detection(self):
        assert classify_comparison_line("---") == "divider"

    def test_info_fallback(self):
        assert classify_comparison_line("Some random text") == "info"

    def test_empty_string(self):
        assert classify_comparison_line("") == "info"

    def test_emoji_success(self):
        assert classify_comparison_line("✅ Muazzam") == "success"

    def test_emoji_warning(self):
        assert classify_comparison_line("⚠️ Dikkat edin") == "warning"

    def test_emoji_error(self):
        assert classify_comparison_line("❌ Hatalı") == "error"

    def test_magnifying_glass_returns_title(self):
        assert classify_comparison_line("🔍 Büyüteç") == "title"


class TestParseWt:
    def test_standard_format(self):
        assert parse_wt("9.50 mm (STD/40)") == 9.5

    def test_mill_format(self):
        assert parse_wt("12.70 mm (Mill/Special)") == 12.7

    def test_plain_number(self):
        assert parse_wt("6.0") == 6.0

    def test_invalid_returns_zero(self):
        assert parse_wt("invalid") == 0.0

    def test_empty_returns_zero(self):
        assert parse_wt("") == 0.0

    def test_none_returns_zero(self):
        assert parse_wt(None) == 0.0


class TestNormalizeSelectedFittingLabel:
    def test_reinforcing_pad(self):
        assert "PAD" in _normalize_selected_fitting_label("REINFORCING PAD")

    def test_weldolet(self):
        tokens = _normalize_selected_fitting_label("WELDOLET / SOCKOLET / OLET")
        assert "WELDOLET" in tokens
        assert "SOCKOLET" in tokens
        assert "OLET" in tokens

    def test_welding_tee(self):
        tokens = _normalize_selected_fitting_label("WELDING TEE (FACTORY)")
        assert "WELDING TEE" in tokens

    def test_split_tee(self):
        tokens = _normalize_selected_fitting_label("SPLIT TEE")
        assert "SPLIT TEE" in tokens

    def test_sleeve(self):
        tokens = _normalize_selected_fitting_label("FULL ENCIRCLEMENT SLEEVE")
        assert "FULL ENCIRCLEMENT SLEEVE" in tokens

    def test_fabricated_branch(self):
        tokens = _normalize_selected_fitting_label("FABRICATED BRANCH (TAKVIYESIZ)")
        assert "FABRICATED BRANCH" in tokens

    def test_unknown_label_returns_uppercased(self):
        result = _normalize_selected_fitting_label("unknown type")
        assert result == ["UNKNOWN TYPE"]


class TestSelectedFittingMatchesRecommendation:
    def test_exact_match(self):
        assert _selected_fitting_matches_recommendation(
            "REINFORCING PAD", "WELDOLET / PAD / SADDLE"
        )

    def test_partial_match(self):
        assert _selected_fitting_matches_recommendation(
            "WELDING TEE (FACTORY)", "FACTORY WELDING TEE (B16.9)"
        )

    def test_no_match(self):
        assert not _selected_fitting_matches_recommendation(
            "REINFORCING PAD", "WELDING TEE (FACTORY)"
        )

    def test_empty_selected(self):
        assert not _selected_fitting_matches_recommendation(
            "", "WELDING TEE (FACTORY)"
        )

    def test_none_selected(self):
        assert not _selected_fitting_matches_recommendation(
            None, "WELDING TEE (FACTORY)"
        )

    def test_selected_matches_empty_recommendation(self):
        result = _evaluate_selected_fitting_against_recommendations("REINFORCING PAD", [])
        assert not result["matches_decision_matrix"]
        assert result["matching_types"] == []

    def test_selected_matches_none_recommendation(self):
        result = _evaluate_selected_fitting_against_recommendations("REINFORCING PAD", None)
        assert not result["matches_decision_matrix"]

    def test_none_selected_matches_any(self):
        result = _evaluate_selected_fitting_against_recommendations(None, [{"Type": "X"}])
        assert result["matches_decision_matrix"]
        assert result["matching_types"] == []

    def test_no_match(self):
        recs = [{"Type": "WELDING TEE (FACTORY)", "Priority": "Primary"}]
        result = _evaluate_selected_fitting_against_recommendations("REINFORCING PAD", recs)
        assert not result["matches_decision_matrix"]
        assert len(result["matching_types"]) == 0


class TestClauseTraceExtraction:
    def test_extract_from_dict_list(self):
        from ui.ui_decision_matrix import extract_clause_ids, format_clause_reference
        traces = [
            {"type": "clause", "ref": "Table 831.4.2-1", "note": "Decision bucket note"},
            {"type": "clause", "ref": "Para 831.4.2(h)", "note": "Full encirclement"},
            {"type": "heuristic", "ref": "Project Standard", "note": "Repo heuristic"}
        ]
        ids = extract_clause_ids(traces)
        assert "Table 831.4.2-1" in ids
        assert "831.4.2(h)" in ids

        ref_info = format_clause_reference("831.4.2(h)")
        assert isinstance(ref_info, dict)
        assert "title" in ref_info
        assert "description" in ref_info

    def test_extract_from_string_list(self):
        from ui.ui_decision_matrix import extract_clause_ids
        traces = ["831.4.1 - Title", "831.4.2(a)"]
        ids = extract_clause_ids(traces)
        assert "831.4.1" in ids
        assert "831.4.2(a)" in ids

