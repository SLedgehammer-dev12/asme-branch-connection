"""
UI cagri-imza kontrat testleri.

Regresyon amaci: app.py icindeki UI cagrilarinin gonderdigi keyword argumanlar,
ilgili UI fonksiyonunun imzasi ile uyusmali. Bu test, "render_step2_recommendations()
got an unexpected keyword argument 'hot_tap_flow_ms'" seklindeki TypeError sinifini
derleme/CI asamasinda yakalar.
"""

import ast
import inspect
import os

import ui.ui_analysis as ui_ana
import ui.ui_recommendations as ui_rec

_APP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"
)

_WATCHED = {
    "render_step1_recommendations": ui_rec.render_step1_recommendations,
    "render_step2_recommendations": ui_rec.render_step2_recommendations,
    "render_fitting_analysis": ui_ana.render_fitting_analysis,
    "render_analysis_results": ui_ana.render_analysis_results,
}


def _collect_call_kwargs():
    """app.py'yi import etmeden (Streamlit calistirmadan) AST ile cagri kwargs'larini toplar."""
    with open(_APP_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=_APP_PATH)

    calls = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _WATCHED
        ):
            names = {kw.arg for kw in node.keywords if kw.arg is not None}
            calls.setdefault(node.func.id, set()).update(names)
    return calls


def test_app_ui_calls_do_not_pass_unknown_kwargs():
    calls = _collect_call_kwargs()
    assert calls, "app.py icinde izlenen UI cagrilari bulunamadi"

    problems = []
    for func_name, kwarg_names in calls.items():
        sig = inspect.signature(_WATCHED[func_name])
        accepts_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if accepts_var_kw:
            continue
        unknown = kwarg_names - set(sig.parameters)
        if unknown:
            problems.append(f"{func_name} -> {sorted(unknown)}")

    assert not problems, (
        "app.py UI cagrilarinda gecersiz kwargs (imza uyusmazligi): "
        + "; ".join(problems)
    )


def test_render_step2_accepts_hot_tap_contract():
    sig = inspect.signature(ui_rec.render_step2_recommendations)
    for name in (
        "hot_tap_flow_ms",
        "hot_tap_fluid",
        "hot_tap_d_pen_mm",
        "sleeve_pressure_containing",
        "d_hole_type",
    ):
        assert name in sig.parameters, (
            f"render_step2_recommendations '{name}' parametresini kabul etmiyor"
        )


def test_render_step1_accepts_d_hole_type():
    sig = inspect.signature(ui_rec.render_step1_recommendations)
    assert "d_hole_type" in sig.parameters, (
        "render_step1_recommendations 'd_hole_type' parametresini kabul etmiyor"
    )
