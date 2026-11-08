#!/usr/bin/env python3
"""Motor del test «¿Qué preferís?»: sortea preguntas, puntúa y escribe el bloque de reglas en un CLAUDE.md.

Claude solo presenta y conversa; todo lo que tiene que ser exacto (azar, sumas, escritura) pasa por acá.

  que_preferis.py sortear                         -> JSON con 10 preguntas (2 por eje), opciones mezcladas, sin valores
  que_preferis.py puntuar ID=RESPUESTA ...        -> JSON con el nivel de cada eje + resultado anterior (si hay)
        RESPUESTA = texto exacto de la opción elegida, o -1/0/1 si fue «Otro» y Claude lo interpretó
  que_preferis.py escribir EJE=NIVEL ... [--destino RUTA]
        -> escribe/reemplaza el bloque en RUTA (por defecto ~/.claude/CLAUDE.md), con copia .bak
"""
import json
import random
import re
import sys
from pathlib import Path

BANCO = Path(__file__).with_name("banco.json")
DESTINO = Path.home() / ".claude" / "CLAUDE.md"
INICIO, FIN = "<!-- que-preferis:inicio", "<!-- que-preferis:fin -->"
NIVELES = ("bajo", "medio", "alto")
POR_EJE = 2


def cargar(ruta=BANCO):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def sortear(banco, rng=random):
    """2 preguntas por eje, orden y opciones mezclados. Sin valores: Claude no tiene que verlos."""
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


def valor_de(pregunta, respuesta):
    """Texto de una opción -> su valor; '-1'/'0'/'1' (respuesta libre ya interpretada) -> ese valor."""
    respuesta = respuesta.strip()
    if respuesta in ("-1", "0", "1"):
        return int(respuesta)
    for o in pregunta["opciones"]:
        if o["texto"].strip().lower() == respuesta.lower():
            return o["valor"]
    raise ValueError(f"'{respuesta}' no es una opción de {pregunta['id']}")


def puntuar(banco, respuestas):
    """respuestas: {id_pregunta: texto o '-1'/'0'/'1'} -> {eje: {suma, nivel, nombre, regla, remate}}"""
    por_id = {p["id"]: p for p in banco["preguntas"]}
    sumas = {eje: 0 for eje in banco["ejes"]}
    for pid, resp in respuestas.items():
        if pid not in por_id:
            raise ValueError(f"Pregunta desconocida: {pid}")
        sumas[por_id[pid]["eje"]] += valor_de(por_id[pid], resp)
    resultado = {}
    for eje, suma in sumas.items():
        n = nivel(suma)
        resultado[eje] = {"suma": suma, "nivel": n, "nombre": banco["ejes"][eje]["nombre"], **banco["ejes"][eje][n]}
    return resultado


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
    lineas += [f"- **{banco['ejes'][e]['nombre']}:** {banco['ejes'][e][niveles[e]]['regla']}" for e in banco["ejes"]]
    lineas.append(FIN)
    return "\n".join(lineas)


def leer_anterior(texto):
    """Niveles del bloque ya escrito (si hay) -> {eje: nivel}, o {} si no hay bloque."""
    m = re.search(re.escape(INICIO) + r"(.*?)-->", texto)
    return dict(re.findall(r"(\w+)=(\w+)", m.group(1))) if m else {}


def escribir(ruta, bloque):
    """Reemplaza el bloque si ya existe; si no, lo agrega al final. Deja copia .bak del original."""
    ruta = Path(ruta)
    texto = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
    if texto:
        ruta.with_name(ruta.name + ".bak").write_text(texto, encoding="utf-8")
    patron = re.compile(re.escape(INICIO) + r".*?" + re.escape(FIN), re.S)
    if patron.search(texto):
        nuevo = patron.sub(lambda _: bloque, texto, count=1)
    else:
        nuevo = texto.rstrip("\n") + ("\n\n" if texto else "") + bloque + "\n"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(nuevo, encoding="utf-8")
    return ruta


def _pares(args):
    pares = {}
    for a in args:
        if "=" not in a:
            raise ValueError(f"Se esperaba CLAVE=VALOR, llegó: {a}")
        k, v = a.split("=", 1)
        pares[k.strip()] = v
    return pares


def main(argv):
    if not argv or argv[0] not in ("sortear", "puntuar", "escribir"):
        print(__doc__)
        return 1
    banco = cargar()
    cmd, args = argv[0], argv[1:]
    destino = DESTINO
    if "--destino" in args:
        i = args.index("--destino")
        destino = Path(args[i + 1]).expanduser()
        args = args[:i] + args[i + 2:]
    if cmd == "sortear":
        out = sortear(banco)
    elif cmd == "puntuar":
        anterior = leer_anterior(destino.read_text(encoding="utf-8")) if destino.exists() else {}
        out = {"ejes": puntuar(banco, _pares(args)), "anterior": anterior, "destino": str(destino)}
    else:
        ruta = escribir(destino, armar_bloque(banco, _pares(args)))
        out = {"escrito": str(ruta)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ValueError, IndexError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
