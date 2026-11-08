#!/usr/bin/env python3
"""Motor del test «¿Qué preferís?»: sortea preguntas, puntúa y escribe el bloque de reglas en un CLAUDE.md.

Claude solo presenta y conversa; todo lo que tiene que ser exacto (azar, sumas, escritura) pasa por acá.

  que_preferis.py sortear                         -> JSON con 10 preguntas (2 por eje), opciones mezcladas, sin valores
  que_preferis.py puntuar ID=RESPUESTA ... [--destino RUTA]
        -> JSON con el nivel de cada eje + resultado anterior (leído de RUTA, si hay). Exige las 10 respuestas.
        RESPUESTA = texto exacto de la opción elegida, o -1/0/1 si fue «Otro» y Claude lo interpretó
  que_preferis.py escribir EJE=NIVEL ... [--destino RUTA]
        -> escribe/reemplaza el bloque en RUTA (por defecto ~/.claude/CLAUDE.md). La primera vez guarda el
           original en RUTA.bak (nunca lo pisa después). --destino también se acepta como --destino=RUTA.
"""
import json
import os
import random
import re
import shutil
import sys
import tempfile
from pathlib import Path

BANCO = Path(__file__).with_name("banco.json")
DESTINO = Path.home() / ".claude" / "CLAUDE.md"
INICIO, FIN = "<!-- que-preferis:inicio", "<!-- que-preferis:fin -->"
NIVELES = ("bajo", "medio", "alto")
POR_EJE = 2
MAX_REGLA = 200
# Marcadores solo cuentan si ocupan su propia línea: una nota que los cite a mitad de línea no se toca.
RE_INICIO = re.compile(r"^" + re.escape(INICIO) + r"((?: \w+=\w+)+) -->[ \t]*\r?$", re.M)
RE_FIN = re.compile(r"^" + re.escape(FIN) + r"[ \t]*\r?$", re.M)


def cargar():
    return json.loads(BANCO.read_text(encoding="utf-8"))


def sortear(banco, rng=None):
    """2 preguntas por eje, orden y opciones mezclados. Sin valores: Claude no tiene que verlos."""
    rng = rng or random
    elegidas = []
    for eje in banco["ejes"]:
        del_eje = [p for p in banco["preguntas"] if p["eje"] == eje]
        elegidas += rng.sample(del_eje, POR_EJE)
    rng.shuffle(elegidas)
    salida = []
    for p in elegidas:
        textos = [o["texto"] for o in p["opciones"]]
        rng.shuffle(textos)
        salida.append({"id": p["id"], "texto": p["texto"], "opciones": textos})
    return salida


def nivel(suma):
    return "bajo" if suma < 0 else "alto" if suma > 0 else "medio"


def _norm(texto):
    """Para comparar opciones: sin «», espacios sobrantes ni mayúsculas."""
    return " ".join(texto.replace("«", " ").replace("»", " ").split()).lower()


def valor_de(pregunta, respuesta):
    """Texto de una opción -> su valor; '-1'/'0'/'1'/'+1' (respuesta libre ya interpretada) -> ese valor."""
    respuesta = respuesta.strip()
    if respuesta in ("-1", "0", "1", "+1"):
        return int(respuesta)
    for o in pregunta["opciones"]:
        if _norm(o["texto"]) == _norm(respuesta):
            return o["valor"]
    raise ValueError(f"'{respuesta}' no es una opción de {pregunta['id']}")


def puntuar(banco, respuestas):
    """respuestas: {id_pregunta: texto o '-1'/'0'/'1'} -> {eje: {suma, nivel, nombre, regla, remate}}
    Exige POR_EJE respuestas por eje: un test a medias no se puntúa."""
    por_id = {p["id"]: p for p in banco["preguntas"]}
    sumas = {eje: 0 for eje in banco["ejes"]}
    cuenta = {eje: 0 for eje in banco["ejes"]}
    for pid, resp in respuestas.items():
        if pid not in por_id:
            raise ValueError(f"Pregunta desconocida: {pid}")
        eje = por_id[pid]["eje"]
        sumas[eje] += valor_de(por_id[pid], resp)
        cuenta[eje] += 1
    mal = [e for e, n in cuenta.items() if n != POR_EJE]
    if mal:
        raise ValueError(f"Hacen falta exactamente {POR_EJE} respuestas por eje; no cumplen: {', '.join(mal)}")
    resultado = {}
    for eje, suma in sumas.items():
        n = nivel(suma)
        resultado[eje] = {"suma": suma, "nivel": n, "nombre": banco["ejes"][eje]["nombre"], **banco["ejes"][eje][n]}
    return resultado


def _linea_segura(texto, campo):
    """El banco se vuelca tal cual a un CLAUDE.md: una línea, sin cerrar el comentario, de largo acotado."""
    if "\n" in texto or "\r" in texto or "<!--" in texto or "-->" in texto or len(texto) > MAX_REGLA:
        raise ValueError(f"banco.json: '{campo}' no puede tener saltos de línea, <!-- / --> ni más de {MAX_REGLA} caracteres")
    return texto


def armar_bloque(banco, niveles):
    """niveles: {eje: 'bajo'|'medio'|'alto'} -> bloque marcado listo para pegar en CLAUDE.md."""
    for eje, n in niveles.items():
        if eje not in banco["ejes"] or n not in NIVELES:
            raise ValueError(f"Eje o nivel inválido: {eje}={n}")
    faltan = set(banco["ejes"]) - set(niveles)
    if faltan:
        raise ValueError(f"Faltan ejes: {', '.join(sorted(faltan))}")
    marca = " ".join(f"{e}={niveles[e]}" for e in banco["ejes"])
    lineas = [f"{INICIO} {marca} -->", "## Preferencias de trabajo (test «¿Qué preferís?»)"]
    for e in banco["ejes"]:
        nombre = _linea_segura(banco["ejes"][e]["nombre"], f"{e}.nombre")
        regla = _linea_segura(banco["ejes"][e][niveles[e]]["regla"], f"{e}.{niveles[e]}.regla")
        lineas.append(f"- **{nombre}:** {regla}")
    lineas.append(FIN)
    return "\n".join(lineas)


def leer_anterior(texto, ejes=None):
    """Niveles del bloque ya escrito (si hay) -> {eje: nivel}, o {} si no hay bloque.
    Solo devuelve niveles válidos (y ejes de `ejes`, si se pasa): el archivo no es de fiar."""
    m = RE_INICIO.search(texto)
    pares = re.findall(r"(\w+)=(\w+)", m.group(1)) if m else []
    return {e: n for e, n in pares if n in NIVELES and (ejes is None or e in ejes)}


def _leer(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:  # newline="": no tocar los CRLF del usuario
        return f.read()


def escribir(ruta, bloque):
    """Reemplaza el bloque si ya existe; si no, lo agrega al final.
    El original se guarda UNA vez en .bak (con sus permisos) y no se pisa. La escritura es atómica."""
    real = Path(ruta).resolve()  # si es un symlink (dotfiles), se escribe el archivo de verdad
    texto = _leer(real) if real.exists() else ""
    if "\r\n" in texto:
        bloque = bloque.replace("\n", "\r\n")
    inicios, fines = RE_INICIO.findall(texto), RE_FIN.findall(texto)
    if len(inicios) > 1 or len(fines) > 1 or len(inicios) != len(fines):
        raise ValueError(f"{real}: bloque de que-preferis dañado o repetido (marcadores desparejos); revisalo a mano")
    bak = real.with_name(real.name + ".bak")
    if texto and not bak.exists():
        if bak.is_symlink():
            raise ValueError(f"{bak} es un enlace simbólico; no lo piso")
        shutil.copy2(real, bak)
    if inicios:
        patron = re.compile(RE_INICIO.pattern + r".*?" + RE_FIN.pattern, re.M | re.S)
        if not patron.search(texto):  # fin antes que inicio
            raise ValueError(f"{real}: los marcadores de que-preferis están en orden inverso; revisalo a mano")
        # el match se come el \r final de la línea FIN (si lo hay): devolverlo para no dejar un \n suelto
        nuevo = patron.sub(lambda m: bloque + ("\r" if m.group(0).endswith("\r") else ""), texto, count=1)
    else:
        sep = "\r\n" if "\r\n" in texto else "\n"
        nuevo = texto.rstrip("\r\n") + (sep * 2 if texto else "") + bloque + sep
    real.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=real.parent, prefix=real.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(nuevo)
        if real.exists():
            shutil.copymode(real, tmp)
        else:
            os.chmod(tmp, 0o644)
        os.replace(tmp, real)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return real


def _pares(args):
    pares = {}
    for a in args:
        if "=" not in a:
            raise ValueError(f"Se esperaba CLAVE=VALOR, llegó: {a}")
        k, v = a.split("=", 1)
        k = k.strip()
        if k in pares:
            raise ValueError(f"Repetido: {k}")
        pares[k] = v
    return pares


def _sacar_destino(args):
    """(args con --destino RUTA o --destino=RUTA) -> (ruta, args sin eso)."""
    for i, a in enumerate(args):
        if a == "--destino":
            if i + 1 >= len(args):
                raise ValueError("--destino necesita una ruta")
            return Path(args[i + 1]).expanduser(), args[:i] + args[i + 2:]
        if a.startswith("--destino="):
            return Path(a.split("=", 1)[1]).expanduser(), args[:i] + args[i + 1:]
    return DESTINO, args


def main(argv):
    if not argv or argv[0] not in ("sortear", "puntuar", "escribir"):
        print(__doc__)
        return 1
    banco = cargar()
    cmd = argv[0]
    destino, args = _sacar_destino(argv[1:])
    if cmd == "sortear":
        out = sortear(banco)
    elif cmd == "puntuar":
        anterior = leer_anterior(_leer(destino), banco["ejes"]) if destino.exists() else {}
        out = {"ejes": puntuar(banco, _pares(args)), "anterior": anterior, "destino": str(destino)}
    else:
        bloque = armar_bloque(banco, _pares(args))
        out = {"escrito": str(escribir(destino, bloque)), "bloque": bloque}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ValueError, IndexError, KeyError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
