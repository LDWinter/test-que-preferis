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
git clone --branch v0.2.0 https://github.com/LDWinter/test-que-preferis.git ~/test-que-preferis
ln -s ~/test-que-preferis ~/.claude/skills/que-preferis
```

Clonás un **tag** (versión fija) a propósito: la skill es código que Claude ejecuta, así que antes de actualizar
(`git fetch --tags && git checkout vX.Y.Z`) mirá qué cambió (`git diff`, sobre todo `SKILL.md` y `banco.json`).

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
- La **primera vez** deja el original en `CLAUDE.md.bak` (con los mismos permisos) y **no lo pisa** en las siguientes:
  ahí queda siempre tu archivo de antes de la skill. Si guardás en el `CLAUDE.md` de un repo, agregá `*.bak` a su
  `.gitignore` para no subirlo. La escritura es atómica y no toca tus saltos de línea ni los enlaces simbólicos.
- Si el archivo tiene un bloque dañado o repetido, se niega a escribir y te lo dice (no adivina).
- Ojo con `autonomia=alto`: la regla le da permiso a Claude para actuar sin preguntar. La skill te lo avisa antes de guardar.
- No usa red ni guarda nada más.

## Cómo está hecho

| Archivo | Qué es |
|---|---|
| `SKILL.md` | Las instrucciones para Claude: presentar, preguntar sin revelar, revelar, corregir, guardar. |
| `banco.json` | 20 preguntas (4 por eje, ids opacos, 3 opciones con valor -1 / 0 / +1) y 15 reglas fijas con su remate. |
| `que_preferis.py` | El motor: sortea 2 preguntas por eje, puntúa y escribe el bloque. Lo exacto no queda librado a Claude. |
| `test_que_preferis.py` | Tests: `python3 -m unittest` |

Cada eje suma sus 2 respuestas (el motor exige las 10): negativo = bajo, 0 = medio, positivo = alto.
Si respondés «Otro» con texto libre, Claude lo interpreta como -1, 0 o +1.

Uso del motor a mano:
```bash
python3 que_preferis.py sortear
python3 que_preferis.py puntuar p18="«Contame lo importante, quién y qué»" p01=-1 ... --destino ./CLAUDE.md   # las 10, 2 por eje
python3 que_preferis.py escribir largo=medio autonomia=medio tono=alto riesgo=medio explicacion=bajo --destino ./CLAUDE.md
```

## Personalizar

Editá `banco.json`: podés cambiar preguntas, remates o reglas. Mantené 3 opciones por pregunta con valores
-1, 0 y 1 (textos distintos y que no sean `-1`/`0`/`1`), ids únicos que no nombren el eje, al menos 2 preguntas por eje
y los 3 niveles de cada eje. Cada regla va en **una línea**, sin `<!--` ni `-->`, de hasta 200 caracteres: el motor
se niega a volcar otra cosa a tu CLAUDE.md. Los tests lo verifican (`python3 -m unittest`).
La tabla de «Qué mide» de arriba es ilustrativa: la fuente de verdad es `banco.json`.

## Licencia

MIT — ver [LICENSE](LICENSE). Hecho por LDev.
