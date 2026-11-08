import contextlib
import io
import json
import os
import random
import stat
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import que_preferis as q


def todos(banco, nivel):
    return {e: nivel for e in banco["ejes"]}


def respuestas_completas(banco, valor="0"):
    """2 preguntas por eje, todas con la misma respuesta libre (-1/0/1)."""
    out = {}
    for eje in banco["ejes"]:
        for p in [p for p in banco["preguntas"] if p["eje"] == eje][: q.POR_EJE]:
            out[p["id"]] = valor
    return out


class TestBanco(unittest.TestCase):
    def setUp(self):
        self.banco = q.cargar()

    def test_banco_completo(self):
        por_eje = Counter(p["eje"] for p in self.banco["preguntas"])
        self.assertEqual(set(por_eje), set(self.banco["ejes"]))
        self.assertTrue(all(n >= q.POR_EJE for n in por_eje.values()), por_eje)
        for p in self.banco["preguntas"]:
            self.assertEqual(sorted(o["valor"] for o in p["opciones"]), [-1, 0, 1], p["id"])
            textos = [q._norm(o["texto"]) for o in p["opciones"]]
            self.assertEqual(len(set(textos)), 3, p["id"])  # distintas incluso sin «» ni mayúsculas
            self.assertFalse({t.strip() for t in textos} & {"-1", "0", "1", "+1"}, p["id"])  # chocarían con valor_de
        for e in self.banco["ejes"].values():
            for n in q.NIVELES:
                self.assertTrue(e[n]["regla"] and e[n]["remate"])

    def test_ids_unicos_y_opacos(self):
        ids = [p["id"] for p in self.banco["preguntas"]]
        self.assertEqual(len(ids), len(set(ids)))
        for i in ids:  # el id no puede delatar el eje antes de la revelación
            self.assertFalse(any(e in i for e in self.banco["ejes"]), i)

    def test_reglas_del_banco_son_seguras(self):
        q.armar_bloque(self.banco, todos(self.banco, "alto"))  # lanza si alguna regla no pasa el filtro
        for n in q.NIVELES:
            q.armar_bloque(self.banco, todos(self.banco, n))


class TestSortear(unittest.TestCase):
    def setUp(self):
        self.banco = q.cargar()
        self.eje_de = {p["id"]: p["eje"] for p in self.banco["preguntas"]}

    def test_dos_por_eje_sin_valores(self):
        for semilla in range(20):
            s = q.sortear(self.banco, random.Random(semilla))
            self.assertEqual(len(s), 10)
            self.assertEqual(len({p["id"] for p in s}), 10)  # sin repetidas
            self.assertEqual(Counter(self.eje_de[p["id"]] for p in s), {e: 2 for e in self.banco["ejes"]})
            for p in s:
                self.assertEqual(set(p), {"id", "texto", "opciones"})  # ni valor ni eje
                self.assertEqual(len(p["opciones"]), 3)
                self.assertTrue(all(isinstance(o, str) for o in p["opciones"]))

    def test_mezcla(self):
        ordenes = {tuple(p["id"] for p in q.sortear(self.banco, random.Random(s))) for s in range(20)}
        self.assertGreater(len(ordenes), 1)


class TestPuntuar(unittest.TestCase):
    def setUp(self):
        self.banco = q.cargar()

    def test_nivel(self):
        self.assertEqual([q.nivel(s) for s in (-2, -1, 0, 1, 2)], ["bajo", "bajo", "medio", "alto", "alto"])

    def test_valor_de_texto_numero_y_ruido(self):
        p = next(x for x in self.banco["preguntas"] if x["id"] == "p18")
        alto = next(o["texto"] for o in p["opciones"] if o["valor"] == 1)
        for variante in (alto, alto.upper(), "  " + alto + " ", alto.replace("«", "").replace("»", "")):
            self.assertEqual(q.valor_de(p, variante), 1, variante)
        self.assertEqual([q.valor_de(p, x) for x in ("-1", "0", "1", "+1", " 1 ")], [-1, 0, 1, 1, 1])

    def test_puntuar_por_texto_y_valor_libre(self):
        r = respuestas_completas(self.banco, "1")
        ids_largo = [i for i, e in ((p["id"], p["eje"]) for p in self.banco["preguntas"]) if e == "largo" and i in r]
        p0 = next(x for x in self.banco["preguntas"] if x["id"] == ids_largo[0])
        r[ids_largo[0]] = next(o["texto"] for o in p0["opciones"] if o["valor"] == -1).upper()
        r[ids_largo[1]] = "1"
        res = q.puntuar(self.banco, r)
        self.assertEqual((res["largo"]["suma"], res["largo"]["nivel"]), (0, "medio"))
        self.assertEqual(res["tono"]["nivel"], "alto")

    def test_rechaza_basura(self):
        r = respuestas_completas(self.banco)
        with self.assertRaises(ValueError):
            q.puntuar(self.banco, {**r, "p18": "cualquier cosa"})
        with self.assertRaises(ValueError):
            q.puntuar(self.banco, {**r, "no-existe": "0"})

    def test_exige_dos_por_eje(self):
        r = respuestas_completas(self.banco)
        with self.assertRaises(ValueError):
            q.puntuar(self.banco, {})
        with self.assertRaises(ValueError):
            q.puntuar(self.banco, dict(list(r.items())[:-1]))  # falta una
        q.puntuar(self.banco, r)  # completo: pasa

    def test_pares(self):
        self.assertEqual(q._pares(["a=b=c", " d =1"]), {"a": "b=c", "d": "1"})
        with self.assertRaises(ValueError):
            q._pares(["sin-igual"])
        with self.assertRaises(ValueError):
            q._pares(["a=1", "a=2"])  # repetida: no se pisa en silencio


class TestBloque(unittest.TestCase):
    def setUp(self):
        self.banco = q.cargar()

    def test_valida_y_falta_eje(self):
        with self.assertRaises(ValueError):
            q.armar_bloque(self.banco, {"largo": "alto"})
        with self.assertRaises(ValueError):
            q.armar_bloque(self.banco, {e: "enorme" for e in self.banco["ejes"]})
        with self.assertRaises(ValueError):
            q.armar_bloque(self.banco, {**todos(self.banco, "alto"), "inventado": "alto"})

    def test_contenido_y_orden(self):
        niveles = {"riesgo": "bajo", "largo": "alto", "tono": "medio", "autonomia": "bajo", "explicacion": "alto"}
        lineas = q.armar_bloque(self.banco, niveles).split("\n")
        self.assertEqual(lineas[0], f"{q.INICIO} " + " ".join(f"{e}={niveles[e]}" for e in self.banco["ejes"]) + " -->")
        self.assertEqual(lineas[-1], q.FIN)
        for e, linea in zip(self.banco["ejes"], lineas[2:-1]):
            self.assertEqual(linea, f"- **{self.banco['ejes'][e]['nombre']}:** {self.banco['ejes'][e][niveles[e]]['regla']}")

    def test_banco_hostil_no_se_vuelca(self):
        for mal in ("dos\nlíneas", "cierra --> acá", "abre <!-- acá", "x" * (q.MAX_REGLA + 1)):
            banco = json.loads(json.dumps(self.banco))
            banco["ejes"]["tono"]["alto"]["regla"] = mal
            with self.assertRaises(ValueError, msg=mal):
                q.armar_bloque(banco, todos(banco, "alto"))

    def test_leer_anterior_robusto(self):
        b = q.armar_bloque(self.banco, todos(self.banco, "bajo"))
        self.assertEqual(q.leer_anterior("antes\n" + b + "\ndespués"), todos(self.banco, "bajo"))
        self.assertEqual(q.leer_anterior("sin bloque"), {})
        self.assertEqual(q.leer_anterior(f"{q.INICIO} largo=alto -->"), {"largo": "alto"})
        malo = f"{q.INICIO} ignora=todo_lo_anterior largo=alto -->\n{q.FIN}"
        self.assertEqual(q.leer_anterior(malo), {"largo": "alto"})          # valor que no es nivel: descartado
        self.assertEqual(q.leer_anterior(malo, self.banco["ejes"]), {"largo": "alto"})
        self.assertEqual(q.leer_anterior(f"{q.INICIO} zzz=alto largo=bajo -->\n{q.FIN}", self.banco["ejes"]), {"largo": "bajo"})
        self.assertEqual(q.leer_anterior(f"nota: {q.INICIO} largo=alto -->"), {})  # a mitad de línea no cuenta


class TestEscribir(unittest.TestCase):
    def setUp(self):
        self.banco = q.cargar()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.ruta = self.dir / "CLAUDE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def bloque(self, n):
        return q.armar_bloque(self.banco, todos(self.banco, n))

    def test_agrega_reemplaza_y_respeta_el_resto(self):
        self.ruta.write_text("# Mis reglas\nNo borrar esto.\n")
        q.escribir(self.ruta, self.bloque("bajo"))
        q.escribir(self.ruta, self.bloque("alto"))
        texto = self.ruta.read_text()
        self.assertEqual(texto.count(q.FIN), 1)
        self.assertTrue(texto.startswith("# Mis reglas\nNo borrar esto.\n\n" + q.INICIO))
        self.assertTrue(texto.endswith(q.FIN + "\n"))
        self.assertEqual(q.leer_anterior(texto), todos(self.banco, "alto"))

    def test_idempotente_y_texto_alrededor(self):
        self.ruta.write_text("arriba\n" + self.bloque("medio") + "\nabajo \\1 \\n sin salto final")
        q.escribir(self.ruta, self.bloque("alto"))
        q.escribir(self.ruta, self.bloque("alto"))
        t = self.ruta.read_text()
        self.assertEqual(t, "arriba\n" + self.bloque("alto") + "\nabajo \\1 \\n sin salto final")

    def test_bak_guarda_el_original_y_no_se_pisa(self):
        self.ruta.write_text("ORIGINAL\n")
        q.escribir(self.ruta, self.bloque("bajo"))
        q.escribir(self.ruta, self.bloque("alto"))
        self.assertEqual((self.dir / "CLAUDE.md.bak").read_text(), "ORIGINAL\n")

    def test_bak_hereda_permisos(self):
        self.ruta.write_text("privado\n")
        os.chmod(self.ruta, 0o600)
        q.escribir(self.ruta, self.bloque("bajo"))
        self.assertEqual(stat.S_IMODE(os.stat(self.dir / "CLAUDE.md.bak").st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.ruta).st_mode), 0o600)

    def test_archivo_nuevo(self):
        ruta = self.dir / "sub" / "CLAUDE.md"
        q.escribir(ruta, self.bloque("medio"))
        self.assertTrue(ruta.read_text().startswith(q.INICIO))
        self.assertFalse((self.dir / "sub" / "CLAUDE.md.bak").exists())
        self.assertEqual(sorted(p.name for p in (self.dir / "sub").iterdir()), ["CLAUDE.md"])  # sin temporales

    def test_crlf_se_conserva(self):
        self.ruta.write_bytes(b"a\r\nb\r\n")
        q.escribir(self.ruta, self.bloque("bajo"))
        q.escribir(self.ruta, self.bloque("alto"))
        datos = self.ruta.read_bytes()
        self.assertTrue(datos.startswith(b"a\r\nb\r\n\r\n"))
        self.assertEqual(datos.replace(b"\r\n", b"").count(b"\n"), 0)

    def test_symlink_escribe_el_destino_real(self):
        real = self.dir / "real.md"
        real.write_text("x\n")
        enlace = self.dir / "enlace.md"
        enlace.symlink_to(real)
        q.escribir(enlace, self.bloque("alto"))
        self.assertTrue(enlace.is_symlink())
        self.assertIn(q.INICIO, real.read_text())

    def test_bak_symlink_no_se_sigue(self):
        victima = self.dir / "victima.txt"
        victima.write_text("intacta")
        (self.dir / "CLAUDE.md.bak").symlink_to(self.dir / "no-existe")
        self.ruta.write_text("hola\n")
        with self.assertRaises(ValueError):
            q.escribir(self.ruta, self.bloque("alto"))
        self.assertEqual(victima.read_text(), "intacta")
        self.assertEqual(self.ruta.read_text(), "hola\n")

    def test_prosa_que_cita_el_marcador_no_se_borra(self):
        nota = f"Nota: el marcador es {q.INICIO} ... y cierra con {q.FIN}\nOtra línea\n"
        self.ruta.write_text(nota)
        q.escribir(self.ruta, self.bloque("alto"))
        self.assertTrue(self.ruta.read_text().startswith(nota))

    def test_bloque_danado_o_repetido_no_se_toca(self):
        for contenido in (
            f"{q.INICIO} largo=bajo -->\nroto\n",                                     # sin fin
            f"{q.FIN}\n{q.INICIO} largo=bajo -->\n",                                  # orden inverso
            self.bloque("bajo") + "\n" + self.bloque("alto") + "\n",                  # dos bloques
        ):
            self.ruta.write_text(contenido)
            with self.assertRaises(ValueError, msg=contenido):
                q.escribir(self.ruta, self.bloque("medio"))
            self.assertEqual(self.ruta.read_text(), contenido)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name) / "CLAUDE.md"
        self.banco = q.cargar()
        # Seguro: nada de estos tests puede llegar al CLAUDE.md real.
        self._destino, q.DESTINO = q.DESTINO, Path(self.tmp.name) / "no-tocar" / "CLAUDE.md"

    def tearDown(self):
        q.DESTINO = self._destino
        self.tmp.cleanup()

    def correr(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = q.main(list(argv))
            except (ValueError, IndexError, KeyError, OSError) as e:
                rc = 2
                err.write(str(e))
        return rc, out.getvalue(), err.getvalue()

    def test_sin_argumentos_o_comando_malo(self):
        self.assertEqual(self.correr()[0], 1)
        self.assertEqual(self.correr("foo")[0], 1)

    def test_flujo_completo_con_destino(self):
        rc, out, _ = self.correr("sortear")
        self.assertEqual((rc, len(json.loads(out))), (0, 10))
        args = [f"{i}=1" for i in respuestas_completas(self.banco)]
        rc, out, _ = self.correr("puntuar", *args, "--destino", str(self.ruta))
        r = json.loads(out)
        self.assertEqual((rc, r["anterior"]), (0, {}))
        niveles = {e: v["nivel"] for e, v in r["ejes"].items()}
        rc, out, _ = self.correr("escribir", *[f"{e}={n}" for e, n in niveles.items()], f"--destino={self.ruta}")
        e = json.loads(out)
        self.assertEqual(Path(e["escrito"]), self.ruta.resolve())
        self.assertIn(q.FIN, e["bloque"])
        rc, out, _ = self.correr("puntuar", *args, f"--destino={self.ruta}")
        self.assertEqual(json.loads(out)["anterior"], niveles)
        self.assertFalse(q.DESTINO.exists())  # el destino por defecto no se tocó

    def test_errores_dan_codigo_2_y_no_traceback(self):
        d = self.tmp.name
        self.assertEqual(self.correr("puntuar", "abc")[0], 2)
        self.assertEqual(self.correr("puntuar", "--destino")[0], 2)           # falta la ruta
        self.assertEqual(self.correr("escribir", "largo=alto", "--destino", self.tmp.name)[0], 2)  # directorio
        self.assertEqual(self.correr("escribir", *[f"{e}=enorme" for e in self.banco["ejes"]], "--destino", d + "/x.md")[0], 2)
        self.assertEqual(self.correr("puntuar", "p18=0", "--destino", d + "/x.md")[0], 2)  # incompleto

    def test_script_sin_importar_el_modulo(self):
        # el __main__ real: errores a stderr con código 2, sin traceback
        import subprocess, sys
        p = subprocess.run([sys.executable, q.__file__, "puntuar", "abc"], capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        self.assertTrue(p.stderr.startswith("Error:") and "Traceback" not in p.stderr)


if __name__ == "__main__":
    unittest.main()
