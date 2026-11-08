---
name: que-preferis
description: Test divertido «¿Qué preferís?» de 10 preguntas absurdas que calibra cómo trabaja Claude con el usuario (cuánto escribe, autonomía, tono, riesgo, si explica o va directo) y, con su OK, guarda las reglas en CLAUDE.md. Usar con /que-preferis, «hagamos el test», «test de preferencias» o «personalizá cómo me respondés».
---

# Test «¿Qué preferís?»

Un test de opción múltiple con preguntas absurdas. Se presenta como «un test rápido para personalizar la experiencia».
**No reveles qué mide cada pregunta hasta el final**: la revelación es el chiste.

El motor es `que_preferis.py`, en la misma carpeta que este archivo. Usalo para el sorteo, el puntaje y la escritura;
no sortees, no sumes ni edites CLAUDE.md a mano.

## Pasos

1. **Presentación (una o dos líneas).** Algo como: «Te hago 10 preguntas medio ridículas, respondé lo primero que te
   salga. Al final te cuento qué averigüé.» Hablá en el idioma del usuario; las preguntas están en español
   rioplatense: si el usuario habla otro idioma, traducilas manteniendo el humor.

2. **Sorteo.** Corré `python3 <carpeta-de-esta-skill>/que_preferis.py sortear`. Devuelve 10 preguntas con `id`,
   `texto` y 3 `opciones` ya mezcladas.

3. **Preguntas.** Hacelas con la herramienta AskUserQuestion: 4 + 4 + 2 (máximo 4 por llamada), una pregunta por
   ítem, las 3 opciones tal cual (el texto exacto, sin marcar ninguna como recomendada). En `header` poné algo corto
   y neutro («Pregunta 1», …): **nunca el eje ni el `id`**. Si la herramienta pide `description` por opción,
   poné un espacio (no expliques la opción: delataría el eje). Si no tenés AskUserQuestion, preguntá en texto, de a
   una, con las opciones numeradas.
   - Si el usuario elige «Otro» y escribe algo libre, interpretalo vos: -1 si se parece a la opción más «baja»
     (corta, cautelosa, formal, directa), 1 si se parece a la más «alta», 0 si queda en el medio o no se entiende.

4. **Puntaje.** Corré
   `python3 <carpeta>/que_preferis.py puntuar ID="texto exacto de la opción" ID=-1 ...`
   (una entrada por pregunta; comillas alrededor del texto). Devuelve el nivel de cada eje, la regla, el remate,
   el resultado `anterior` (si el test ya se hizo) y el `destino` por defecto.

5. **Revelación.** Una tabla con una fila por eje:
   | Eje | Lo que elegiste | Qué significa | La regla que voy a escribir |
   En «Lo que elegiste», citá cortito las 2 respuestas del eje. Después de la tabla, los 5 remates (uno por eje).
   Si hay `anterior` y algún eje cambió, agregá una línea «Antes / Ahora» por eje cambiado.
   Cerrá preguntando: «¿Corrijo algún eje? ¿Lo guardo en tu CLAUDE.md global (~/.claude/CLAUDE.md) o en el de este
   proyecto?»

6. **Correcciones.** Si el usuario cambia un eje («tono más serio»), ajustá ese nivel (bajo/medio/alto) y mostrá la
   regla nueva. No inventes reglas: solo las de los 3 niveles.

7. **Guardar (solo con un «sí» explícito).** Corré
   `python3 <carpeta>/que_preferis.py escribir largo=NIVEL autonomia=NIVEL tono=NIVEL riesgo=NIVEL explicacion=NIVEL [--destino RUTA]`
   (sin `--destino` = CLAUDE.md global; para el del proyecto, `--destino ./CLAUDE.md`). Reemplaza el bloque si ya
   existía y deja una copia `.bak`. Confirmá en una línea dónde quedó y que se puede repetir el test cuando quiera.
   Si el usuario no dice que sí, no escribas nada.
