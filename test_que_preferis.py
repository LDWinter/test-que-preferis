import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import que_preferis as q


class TestQuePreferis(unittest.TestCase):
    def setUp(self):
        self.banco = q.cargar()

    def test_banco_completo(self):
        por_eje = Counter(p["eje"] for p in self.banco["preguntas"])
        self.assertEqual(set(por_eje), set(self.banco["ejes"]))
        self.assertTrue(all(n >= q.POR_EJE for n in por_eje.values()), por_eje)
        for p in self.banco["preguntas"]:
            self.assertEqual(sorted(o["valor"] for o in p["opciones"]), [-1, 0, 1], p["id"])
        for e in self.banco["ejes"].values():
            for n in q.NIVELES:
                self.assertTrue(e[n]["regla"] and e[n]["remate"])

    def test_sortear_dos_por_eje_sin_valores(self):
        for semilla in range(20):
            s = q.sortear(self.banco, random.Random(semilla))
            self.assertEqual(len(s), 10)
            self.assertEqual(Counter(p["id"].rsplit("-", 1)[0] for p in s), {e: 2 for e in self.banco["ejes"]})
            self.assertTrue(all(isinstance(o, str) for p in s for o in p["opciones"]))

    def test_nivel(self):
        self.assertEqual([q.nivel(s) for s in (-2, -1, 0, 1, 2)], ["bajo", "bajo", "medio", "alto", "alto"])

    def test_puntuar_por_texto_y_por_valor_libre(self):
        p = next(x for x in self.banco["preguntas"] if x["id"] == "largo-1")
        alto = next(o["texto"] for o in p["opciones"] if o["valor"] == 1)
        r = q.puntuar(self.banco, {"largo-1": alto.upper(), "largo-2": "0", "tono-1": "-1"})
        self.assertEqual((r["largo"]["suma"], r["largo"]["nivel"]), (1, "alto"))
        self.assertEqual(r["tono"]["nivel"], "bajo")
        self.assertEqual(r["riesgo"]["nivel"], "medio")

    def test_puntuar_rechaza_basura(self):
        with self.assertRaises(ValueError):
            q.puntuar(self.banco, {"largo-1": "cualquier cosa"})
        with self.assertRaises(ValueError):
            q.puntuar(self.banco, {"no-existe": "0"})

    def test_bloque_valida_y_falta_eje(self):
        with self.assertRaises(ValueError):
            q.armar_bloque(self.banco, {"largo": "alto"})
        with self.assertRaises(ValueError):
            q.armar_bloque(self.banco, {e: "enorme" for e in self.banco["ejes"]})

    def test_escribir_agrega_reemplaza_y_lee_anterior(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "CLAUDE.md"
            ruta.write_text("# Mis reglas\nNo borrar esto.\n")
            todos = lambda n: {e: n for e in self.banco["ejes"]}
            q.escribir(ruta, q.armar_bloque(self.banco, todos("bajo")))
            q.escribir(ruta, q.armar_bloque(self.banco, todos("alto")))
            texto = ruta.read_text()
            self.assertEqual(texto.count(q.FIN), 1)            # reemplazó, no duplicó
            self.assertIn("No borrar esto.", texto)              # respetó lo demás
            self.assertEqual(q.leer_anterior(texto), todos("alto"))
            self.assertIn(q.INICIO, (Path(d) / "CLAUDE.md.bak").read_text())  # copia previa

    def test_escribir_en_archivo_nuevo(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "sub" / "CLAUDE.md"
            q.escribir(ruta, q.armar_bloque(self.banco, {e: "medio" for e in self.banco["ejes"]}))
            self.assertTrue(ruta.read_text().startswith(q.INICIO))
            self.assertEqual(q.leer_anterior("sin bloque"), {})


if __name__ == "__main__":
    unittest.main()
