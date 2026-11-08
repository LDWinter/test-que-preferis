# ¿Qué preferís? 🦝 — una skill para Claude Code

> *«Un mago te ofrece teletransportarte al laburo. Detalle: es la primera vez que lo intenta. ¿Te animás?»*

Un test de **10 preguntas absurdas** que, sin que te des cuenta, mide cómo querés que trabaje Claude con vos.
Al final te revela qué significó cada respuesta (ese es el chiste), te deja corregir lo que no te cierre y,
**solo si decís que sí**, guarda las reglas en tu `CLAUDE.md`.

*English: a silly 10-question quiz skill for Claude Code that secretly calibrates how Claude works with you (verbosity,
autonomy, tone, risk appetite, explain-vs-just-do-it) and, only with your OK, writes the result into `CLAUDE.md`.
Questions are in Rioplatense Spanish; Claude translates them on the fly if you talk to it in another language.*

## Qué mide

| Eje | Bajo | Medio | Alto |
|---|---|---|---|
| Cuánto escribe Claude | Corto, sin introducciones | Según la pregunta | Completo y detallado |
| Cuánta autonomía tiene | Propone y espera el OK | Solo lo chico y reversible | Hace, verifica y cuenta |
| Tono | Formal y sobrio | Cercano y profesional | Relajado, con humor |
| Riesgo | Lo probado, cambios mínimos | Lo estable + menciona la alternativa | Lo nuevo, avisando el riesgo |
| Explica o va directo | Directo al resultado | Resultado + una línea de por qué | Razonamiento completo |

## Así se ve el final

| Eje | Lo que elegiste | Qué significa | La regla que voy a escribir |
|---|---|---|---|
| Tono | «Leche: agotada.» · nota sin vueltas | Bajo | Tono formal y sobrio: sin chistes, sin emojis, sin exclamaciones. |
| Riesgo | Que el mago pruebe con una silla · la cucharita | Medio | Proponer lo estable por defecto y mencionar la alternativa… |

> *Tono: tus memes tienen bibliografía.*
> *Riesgo: probás el sabor nuevo, pero en el vasito de muestra.*

## Instalar

Requisitos: [Claude Code](https://claude.com/claude-code) y Python 3.8+ (sin dependencias).

```bash
git clone https://github.com/LDWinter/test-que-preferis.git ~/test-que-preferis
ln -s ~/test-que-preferis ~/.claude/skills/que-preferis
```

Abrí Claude Code y escribí `/que-preferis` (o «hagamos el test»).
Para desinstalar: `rm ~/.claude/skills/que-preferis`.

## Qué toca en tu máquina

- Solo escribe si confirmás, y solo un bloque marcado en el `CLAUDE.md` que elijas (global `~/.claude/CLAUDE.md`
  o el del proyecto):
  ```
  <!-- que-preferis:inicio largo=alto autonomia=medio ... -->
  ## Preferencias de trabajo (test «¿Qué preferís?»)
  - ...
  <!-- que-preferis:fin -->
  ```
- Si repetís el test, **reemplaza** ese bloque (y te muestra antes/después); el resto del archivo no se toca.
- Antes de escribir deja una copia `CLAUDE.md.bak`.
- No usa red ni guarda nada más.

## Cómo está hecho

| Archivo | Qué es |
|---|---|
| `SKILL.md` | Las instrucciones para Claude: presentar, preguntar sin revelar, revelar, corregir, guardar. |
| `banco.json` | 20 preguntas (4 por eje, 3 opciones con valor -1 / 0 / +1) y 15 reglas fijas con su remate. |
| `que_preferis.py` | El motor: sortea 2 preguntas por eje, puntúa y escribe el bloque. Lo exacto no queda librado a Claude. |
| `test_que_preferis.py` | Tests: `python3 -m unittest` |

Cada eje suma sus 2 respuestas: negativo = bajo, 0 = medio, positivo = alto.
Si respondés «Otro» con texto libre, Claude lo interpreta como -1, 0 o +1.

Uso del motor a mano:
```bash
python3 que_preferis.py sortear
python3 que_preferis.py puntuar largo-1="«Contame lo importante, quién y qué»" tono-2=-1 ...
python3 que_preferis.py escribir largo=medio autonomia=medio tono=alto riesgo=medio explicacion=bajo --destino ./CLAUDE.md
```

## Personalizar

Editá `banco.json`: podés cambiar preguntas, remates o reglas. Mantené 3 opciones por pregunta con valores
-1, 0 y 1, al menos 2 preguntas por eje y los 3 niveles de cada eje (los tests lo verifican).

## Licencia

MIT — ver [LICENSE](LICENSE). Hecho por LDev.
