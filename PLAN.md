# PLAN — skill «¿Qué preferís?» (`/que-preferis`)

Diseño cerrado con grilling el 2026-11-07 (día de ocio). Alcance ~2 h.

## Diseño
- Test de 10 preguntas absurdas (aptas para todo público), 3 opciones c/u (+ «Otro» libre que Claude interpreta).
- Banco fijo de 20 preguntas (4 por eje); salen 2 por eje al azar.
- 5 ejes: `largo` (cuánto escribe), `autonomia`, `tono`, `riesgo`, `explicacion` (explica o va directo).
- Cada opción vale -1/0/+1; la suma de las 2 del eje da bajo (≤ -1) / medio (0) / alto (≥ 1).
- Revelación: tabla por eje (elegiste → significa → regla) + remate; se puede corregir cualquier eje;
  si ya había un resultado, muestra antes/después.
- Con el «sí»: bloque marcado `<!-- que-preferis:inicio -->…<!-- que-preferis:fin -->` en ~/.claude/CLAUDE.md
  (o el del proyecto); repetir el test lo reemplaza.
- 15 reglas fijas (5 ejes × 3 niveles) en `banco.json`.
- Motor: `que_preferis.py` (stdlib, con tests). Claude solo presenta y charla.
- Español rioplatense; si el usuario habla otro idioma, Claude traduce al vuelo.
- Publicable (MIT) si queda bien; primero repo privado.

## Etapas
1. **Contenido** — `banco.json` (20 preguntas + 15 reglas + remates). Hecho = LDev lo aprueba.
2. **Script** — `que_preferis.py` (sortear / puntuar / leer bloque / escribir bloque) + `test_que_preferis.py`.
   Hecho = `python3 -m unittest` pasa.
3. **Skill** — `SKILL.md` + enlace `~/.claude/skills/que-preferis`. Hecho = aparece en Claude Code.
4. **Prueba real** — LDev hace el test. Hecho = bloque escrito en su CLAUDE.md global.
5. **Cierre** — revisión final y publicación (repo público, MIT).
