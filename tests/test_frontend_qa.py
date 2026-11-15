"""Pruebas reproducibles de QA para el frontend de Streamlit (Flame in Freefall).
Valida exclusivamente comportamiento lógico/visual de UI sin alterar ni duplicar el backend."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_scope_and_domain_labels_translate_to_spanish(self):
        """Las etiquetas de alcance, material y resultado se traducen al español en presentación."""
        self.assertEqual(ui.scope_label("todos"), "Todos")
        self.assertEqual(ui.scope_label("experiment"), "Experimento")
        self.assertEqual(ui.scope_label("comparison"), "Comparación")
        self.assertEqual(ui.mat_label("solid"), "Sólido")
        self.assertEqual(ui.mat_label("liquid"), "Líquido")
        self.assertEqual(ui.outcome_label("self_extinguished"), "Se autoextinguió")
        self.assertEqual(ui.outcome_label("flow_terminated"), "Flujo detenido")
        self.assertEqual(ui.fmt_gravity("microgravity"), "0g")

    def test_extract_and_norm_insights_both_formats(self):
        """Soporta tanto lista mock (claims/note) como dict InsightsDocument (schemas.py)."""
        legacy_list = [
            {"id": "I-1", "title": "T1", "confidence": "alta", "claims": [{"text": "Afirmación", "psi_id": "PSI-107", "doi": "10.1/a", "page": 3}]},
            {"id": "I-3", "title": "Sin evidencia", "confidence": "baja", "claims": [], "note": "No hay datos suficientes."},
        ]
        items_legacy, meta_legacy = ui.extract_insights(legacy_list)
        self.assertEqual(len(items_legacy), 2)
        self.assertEqual(meta_legacy, {})
        self.assertEqual(ui.norm_insight(items_legacy[1])["st"], "w")

        mock_path = ROOT / "data" / "mock" / "insights_mock.json"
        sample_path = ROOT / "data" / "processed" / "insights.sample.json"

        with open(mock_path, encoding="utf-8") as f:
            raw_mock = json.load(f)
        items_mock, meta_mock = ui.extract_insights(raw_mock)
        self.assertEqual(len(items_mock), 3)
        self.assertIsInstance(meta_mock, dict)
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

    def test_brand_logo_assets_and_safe_inline_svg(self):
        """Los assets del isotipo existen y el SVG inline conserva órbita sin colapsar contenedores."""
        assets_dir = APP_DIR / "assets"
        for filename in ("logo_animated.svg", "logo_static.svg", "logo.png"):
            self.assertTrue((assets_dir / filename).exists(), f"Falta {filename} en app/assets/")
        self.assertIn('width="44" height="44"', ui.LOGO_SVG)
        self.assertIn('width="56" height="56"', ui.LOGO_HERO_SVG)
        self.assertIn("<animateMotion", ui.LOGO_SVG)
        self.assertNotIn("<style>", ui.LOGO_SVG)
        self.assertNotIn("<metadata>", ui.LOGO_SVG)
        self.assertIn("@keyframes ff-k", ui.CSS)
        self.assertIn(":not(:has(svg))", ui.CSS)


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
        """Insights muestra alcances traducidos en español, formato fichas con <details> y avisa cuando no hay respuesta."""
        at = AppTest.from_file(str(APP_DIR / "pages" / "3_Insights.py"), default_timeout=15)
        at.run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.radio[1].options, ["Todos", "Comparación", "Experimento"])
        all_md = "\n".join(m.value for m in at.markdown)
        self.assertIn("Insight 1 · 3 ensayos citados", all_md)
        self.assertIn('<details class="cite-det">', all_md)
        self.assertIn("Ver cobertura", "\n".join([all_md] + [pl.label for pl in at.get("page_link")]))
        self.assertEqual(len(at.main.expander), 0)  # Addendum: eliminar st.expander en Insights

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

    def test_insights_schemas_format_two_citations_and_insufficient_data(self):
        """Insights soporta formato schemas.py con 2 citas (superíndices + notas al pie) e insufficient_data."""
        schemas_payload = {
            "generated_at": "2026-11-15T00:00:00Z",
            "model": "claude-sonnet-5-5",
            "prompt_version": "1.0",
            "insights": [
                {
                    "id": "ins-001",
                    "scope": "comparison",
                    "psi_ids": ["PSI-22", "PSI-23"],
                    "title": "Comparación de encendido en oxígeno elevado",
                    "description": "El umbral de propagación descendió al aumentar la fracción de oxígeno.",
                    "evidence_status": "supported",
                    "confidence": "high",
                    "citations": [
                        {
                            "psi_id": "PSI-22",
                            "doi": "10.0000/psi-22",
                            "page": "14",
                            "quote": "A 30% O2 la propagación fue sostenida en muestras delgadas.",
                        },
                        {
                            "psi_id": "PSI-23",
                            "doi": "",
                            "page": "8",
                            "quote": "A menor espesor se observó mayor velocidad de llama.",
                        },
                    ],
                },
                {
                    "id": "ins-002",
                    "scope": "experiment",
                    "psi_ids": ["PSI-99"],
                    "title": "Gravedad lunar con polímeros gruesos",
                    "description": "No se hallaron ensayos bajo 1/6 g real en los documentos analizados.",
                    "evidence_status": "insufficient_data",
                    "confidence": "low",
                    "citations": [],
                },
            ],
        }
        with patch("ui.load_insights_any", return_value=(schemas_payload, False)):
            at = AppTest.from_file(str(APP_DIR / "pages" / "3_Insights.py"), default_timeout=15)
            at.run()
            self.assertEqual(len(at.exception), 0)
            all_md = "\n".join(m.value for m in at.markdown)
            self.assertIn("<sup>1</sup><sup>2</sup>", all_md)
            self.assertIn("https://doi.org/10.0000/psi-22", all_md)
            self.assertIn("DOI pendiente", all_md)
            self.assertIn("A 30% O2 la propagación fue sostenida", all_md)
            self.assertIn("No hay ensayos que respondan esto. Revisa la cobertura.", all_md)
            self.assertNotIn("Este formato no incluye cita textual", all_md)

    def test_cobertura_gap_hero_and_fillpattern_and_scenario_spin(self):
        """Cobertura renderiza bloque de brecha 56 px + fillpattern, y Ranking alterna giro/conteo en los 3 escenarios."""
        at_cov = AppTest.from_file(str(APP_DIR / "pages" / "4_Cobertura.py"), default_timeout=15)
        at_cov.run()
        self.assertEqual(len(at_cov.exception), 0)
        cov_md = "\n".join(m.value for m in at_cov.markdown)
        self.assertIn("gap-num", cov_md)
        self.assertIn("ensayos en gravedad parcial real (1/6 g · 3/8 g)", cov_md)
        cov_spec = json.loads(at_cov.get("plotly_chart")[0].proto.spec)
        self.assertTrue(any(t.get("fillpattern", {}).get("shape") == "/" for t in cov_spec["data"]))

        at_rk = AppTest.from_file(str(APP_DIR / "pages" / "1_Ranking.py"), default_timeout=15)
        at_rk.run()
        init_md = "\n".join(m.value for m in at_rk.markdown)
        self.assertIn('<div class="strip">', init_md)
        self.assertIn('role="img"', init_md)
        self.assertIn('class="spec-dots"', init_md)
        for idx, scen_name in enumerate(("Base Lunar / Rover", "Traje Espacial", "ISS / Tierra"), 1):
            at_rk.sidebar.button(key="b_" + scen_name).click().run()
            self.assertEqual(len(at_rk.exception), 0)
            expected_spin = "spin-a" if idx % 2 == 1 else "spin-b"
            expected_cnt = "cnt-a" if idx % 2 == 1 else "cnt-b"
            sb_md = "\n".join(m.value for m in at_rk.sidebar.markdown)
            main_md = "\n".join(m.value for m in at_rk.markdown)
            self.assertIn(expected_spin, sb_md)
            self.assertIn(expected_cnt, main_md)


if __name__ == "__main__":
    unittest.main()
