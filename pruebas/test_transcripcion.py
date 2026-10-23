# -*- coding: utf-8 -*-
"""Pruebas de legibles.py y auditar_idioma.py, sin modelo ni red."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "transcripcion"))

import auditar_idioma  # noqa: E402
import legibles  # noqa: E402
import transcribir  # noqa: E402

LINEAS = ["Hola a todos.", "Hoy vemos agentes.", "Primero, qué es un agente.", "Después, cómo se evalúa.",
          "Y para terminar, preguntas."]


class TestLegibles(unittest.TestCase):
    def test_monta_bloques_con_titulo_y_conserva_las_palabras(self):
        cuerpo, igual = legibles.montar(LINEAS, [{"s": 1, "e": 2, "t": "Intro"}, {"s": 3, "e": 5, "t": "## Agentes"}])
        self.assertTrue(igual)
        self.assertEqual(cuerpo, "### Intro\n\nHola a todos. Hoy vemos agentes.\n\n### Agentes\n\n"
                                 "Primero, qué es un agente. Después, cómo se evalúa. Y para terminar, preguntas.\n")

    def test_un_hueco_entre_bloques_no_pierde_texto(self):
        cuerpo, igual = legibles.montar(LINEAS, [{"s": 1, "e": 1, "t": "A"}, {"s": 4, "e": 5, "t": "B"}])
        self.assertTrue(igual)
        self.assertIn("Hoy vemos agentes. Primero, qué es un agente.", cuerpo)

    def test_bloques_solapados_o_fuera_de_rango_no_duplican(self):
        cuerpo, igual = legibles.montar(LINEAS, [{"s": 1, "e": 3}, {"s": 2, "e": 4, "t": "X"}, {"s": 4, "e": 99}])
        self.assertTrue(igual)
        self.assertEqual(cuerpo.count("Hoy vemos agentes."), 1)

    def test_entradas_rotas_se_ignoran(self):
        _, igual = legibles.montar(LINEAS, ["texto", {"s": "a", "e": 2}, {"e": 3}])
        self.assertTrue(igual)   # sin bloques válidos, todo sale como un párrafo


class TestAuditarIdioma(unittest.TestCase):
    def test_reconoce_espanol_e_ingles(self):
        self.assertEqual(auditar_idioma.idioma_dominante("Hoy vamos a ver que es un agente y como se usa en la empresa")[0], "es")
        self.assertEqual(auditar_idioma.idioma_dominante("Today we are going to see what an agent is and how it works in the company")[0], "en")

    def test_detecta_el_gales_que_saca_whisper(self):
        texto = "Mae'r ymgyrch wedi dechrau ac yn bod yr hwn gan chi roedd ydych yn mae wedi"
        self.assertEqual(auditar_idioma.idioma_dominante(texto)[0], "cy")


class TestTranscribir(unittest.TestCase):
    def test_marca_de_tiempo_srt(self):
        self.assertEqual(transcribir.fmt_ts(3725.5), "01:02:05,500")

    def test_recoge_y_filtra_por_nombre(self):
        datos = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
        self.assertEqual(transcribir.recoger([datos]), [])   # ahí no hay audio
        rutas = ["clase_P1.mp4", "clase_P2 (inglés).mp4", "sesion.mp3"]
        self.assertEqual(transcribir.recoger(rutas, excluir="inglés"), ["clase_P1.mp4", "sesion.mp3"])
        self.assertEqual(transcribir.recoger(rutas, solo=r"re:P\d"), ["clase_P1.mp4", "clase_P2 (inglés).mp4"])


if __name__ == "__main__":
    unittest.main()
