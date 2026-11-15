"""Pruebas reproducibles de QA para el frontend de Streamlit (Flame in Freefall).
Valida exclusivamente comportamiento lógico/visual de UI sin alterar ni duplicar el backend."""
import json
import sys
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import ui  # noqa: E402


class TestFrontendHelpers(unittest.TestCase):
    def test_outcome_counts_negation_and_bilingual(self):
        """'no propagó' no debe contarse como propagación; soporta ES y EN."""
        s = pd.Series(["propagó", "no propagó", "se extinguió", "flame spread", "self-extinguished", None])
        p, x, pp = ui.outcome_counts(s)
        self.assertEqual(p, 2)  # "propagó", "flame spread"
        self.assertEqual(x, 3)  # "no propagó", "se extinguió", "self-extinguished"
        self.assertEqual(pp, 40)

    def test_num_and_clean_str_never_render_nan_or_orphan_unit(self):
        """Valores NaN deben devolver '—' sin unidad huérfana ni texto 'nan'."""
        self.assertEqual(ui.num(float("nan"), 2, " mm/s"), "—")
        self.assertEqual(ui.num(1.25, 2, " mm/s"), "1.25 mm/s")
        self.assertEqual(ui.clean_str(float("nan")), "—")
        self.assertIn("sin DOI", ui.doi_pill(float("nan")))

    def test_scope_label_translates_to_spanish(self):
        """Las etiquetas de alcance se traducen al español solo en presentación."""
        self.assertEqual(ui.scope_label("todos"), "Todos")
        self.assertEqual(ui.scope_label("experiment"), "Experimento")
        self.assertEqual(ui.scope_label("comparison"), "Comparación")

    def test_extract_and_norm_insights_both_formats(self):
        """Soporta tanto lista mock (claims/note) como dict InsightsDocument (schemas.py)."""
        mock_path = ROOT / "data" / "mock" / "insights_mock.json"
        sample_path = ROOT / "data" / "processed" / "insights.sample.json"

        with open(mock_path, encoding="utf-8") as f:
            raw_mock = json.load(f)
        items_mock, meta_mock = ui.extract_insights(raw_mock)
        self.assertEqual(len(items_mock), 3)
        self.assertEqual(meta_mock, {})
        norm_empty = ui.norm_insight(items_mock[2])
        self.assertEqual(norm_empty["st"], "w")
        self.assertIn("no hay datos suficientes", norm_empty["text"].lower())

        with open(sample_path, encoding="utf-8") as f:
            raw_sample = json.load(f)
        items_sample, meta_sample = ui.extract_insights(raw_sample)
        self.assertEqual(len(items_sample), 2)
        self.assertEqual(meta_sample["model"], "claude-sonnet-5-5")
        norm_sup = ui.norm_insight(items_sample[0])
        self.assertEqual(norm_sup["st"], "b")
        self.assertEqual(len(norm_sup["cites"]), 1)
        norm_insuf = ui.norm_insight(items_sample[1])
        self.assertEqual(norm_insuf["st"], "w")


class TestStreamlitRoutes(unittest.TestCase):
    def test_all_five_routes_render_without_exception(self):
        """Las 5 rutas deben ejecutarse sin excepciones con los datos actuales."""
        routes = [
            APP_DIR / "app.py",
            APP_DIR / "pages" / "1_Ranking.py",
            APP_DIR / "pages" / "2_Comparacion.py",
            APP_DIR / "pages" / "3_Insights.py",
            APP_DIR / "pages" / "4_Cobertura.py",
        ]
        for route in routes:
            with self.subTest(route=route.name):
                at = AppTest.from_file(str(route), default_timeout=15)
                at.run()
                self.assertEqual(len(at.exception), 0, f"Excepción en {route.name}: {at.exception}")

    def test_ranking_scenario_fallback_and_toggle(self):
        """En Ranking, 'Traje Espacial' muestra 0 exactos + alerta, y un segundo clic desactiva el escenario."""
        at = AppTest.from_file(str(APP_DIR / "pages" / "1_Ranking.py"), default_timeout=15)
        at.run()
        self.assertEqual(len(at.exception), 0)

        for cap in at.caption:
            self.assertNotIn("<span", cap.value)

        at.sidebar.button(key="b_Traje Espacial").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.session_state["scen"], "Traje Espacial")
        self.assertTrue(any("Traje Espacial" in w.value for w in at.warning))
        self.assertTrue(any("0 exactos" in m.value for m in at.markdown))
        # En el segundo rerun de la misma página, las animaciones de entrada se desactivan para no parpadear
        self.assertTrue(any("animation:none!important" in m.value for m in at.markdown))

        at.sidebar.button(key="b_Traje Espacial").click().run()
        self.assertIsNone(at.session_state["scen"])

    def test_insights_unanswered_question_and_translated_scopes(self):
        """Insights muestra alcances traducidos en español e informa que no consulta un LLM en vivo cuando no hay respuesta."""
        at = AppTest.from_file(str(APP_DIR / "pages" / "3_Insights.py"), default_timeout=15)
        at.run()
        self.assertEqual(len(at.exception), 0)
        # El radio 'Mostrar' debe presentar opciones traducidas al español
        self.assertEqual(at.radio[1].options, ["Todos", "Comparación", "Experimento"])
        self.assertTrue(any("Experimento · PSI-MOCK-A" in m.value for m in at.markdown))

        at.radio[0].set_value("¿Qué sabemos de gravedad parcial?").run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("no consulta un LLM en vivo" in info.value for info in at.info))

    def test_comparacion_handles_nan_spread_and_renders_charts_without_zero_fallback(self):
        """En Comparación, existen las gráficas comparativas y los NaN se anotan como 'sin dato' (nunca como 0)."""
        at = AppTest.from_file(str(APP_DIR / "pages" / "2_Comparacion.py"), default_timeout=15)
        at.run()
        at.multiselect[0].set_value(["M-001", "M-004"]).run()
        self.assertEqual(len(at.exception), 0)
        for m in at.markdown:
            self.assertNotIn("— mm/s", m.value)

        charts = at.get("plotly_chart")
        self.assertEqual(len(charts), 4)  # 3 small multiples (O2, presión, flujo) + 1 comportamiento de llama
        spread_spec = json.loads(charts[3].proto.spec)
        y_vals = spread_spec["data"][0]["y"]
        self.assertEqual(y_vals[0], 1.2)
        self.assertIsNone(y_vals[1])  # M-004 es NaN -> None, nunca 0
        annotations = spread_spec["layout"].get("annotations", [])
        self.assertTrue(any("sin dato" in a.get("text", "") for a in annotations))

    def test_multipage_navigation_preserves_sidebar_state(self):
        """El estado de escenario y filtros persiste al navegar entre páginas desde app.py."""
        at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=15)
        at.run()
        self.assertEqual(len(at.exception), 0)
        at.sidebar.button(key="b_Base Lunar / Rover").click().run()
        self.assertEqual(at.session_state["scen"], "Base Lunar / Rover")

        for subpage in (
            "pages/1_Ranking.py",
            "pages/2_Comparacion.py",
            "pages/3_Insights.py",
            "pages/4_Cobertura.py",
            "app.py",
        ):
            at.switch_page(subpage).run()
            self.assertEqual(len(at.exception), 0, f"Excepción al cambiar a {subpage}: {at.exception}")
            self.assertEqual(at.session_state["scen"], "Base Lunar / Rover")


if __name__ == "__main__":
    unittest.main()
