# Cómo escribir un guion (instrucciones para la rutina de Claude)

Cada guion es un archivo `guiones/<canal>/NNN_slug.py` que, al ejecutarse, genera el `.json` que lee el motor.
**Copia la estructura de `guiones/atlas/001_egipto_nilo.py`**: es la referencia de formato, tono y calidad.

## Proceso (una sola sesión por vídeo)

1. Lee `guiones/atlas/TEMAS.md` y coge el **primer tema sin marcar**. El número de vídeo es el siguiente al último que existe.
2. Investiga el tema con fuentes fiables (enciclopedias, organismos oficiales, universidades, prensa seria). Anota 4-6 fuentes en `sources`.
3. Escribe `guiones/atlas/NNN_slug.py` (slug en minúsculas, sin acentos, con guiones bajos).
4. Valida: `python scripts/validar_guion.py guiones/atlas/NNN_slug.py`. Corrige hasta que diga ✔.
5. Marca el tema en `TEMAS.md` como `- [x] NNN · Título`.
6. Commit y push a `main`. Al llegar a main, el flujo **Producir vídeo** de GitHub Actions genera el vídeo, las miniaturas y los Shorts y los sube a Google Drive solo.

## Reglas de contenido (retención y algoritmo)

- **Título** (≤ 65 caracteres): honesto pero con curiosidad, con un icono o lugar conocido y un número o contraste. Nada de "ALERTA", "ÚLTIMA HORA" ni exageraciones falsas.
- **Gancho (capítulo 0, < 30 s)**: la pregunta del título con el visual más potente. Sin saludos ni presentación.
- **Antes del minuto 2**: una promesa explícita de lo que se verá ("By the end of this video…").
- **4-6 capítulos** con título, cada uno con un bucle abierto (una pregunta que se responde más adelante).
- **Suscripción a mitad**, en una frase, justo después de un momento fuerte (escena `text` con kicker "Timeline Earth").
- **Capítulo final** `"card": False` con la respuesta completa a la pregunta del título.
- **Última escena**: `end_screen` (minDuration 12) **solo con suscripción**: `data: {"text": "Thanks for watching", "sub_label": "Subscribe"}`. **No** menciones ningún vídeo concreto ni pongas `next_title`: el dueño todavía no ha subido los vídeos anteriores. La narración cierra invitando a suscribirse (p. ej. "Every map hides a story like this one. If you want to discover the next one, subscribe to Timeline Earth.").
- **Duración**: 1.250-1.600 palabras de narración (8-10 min). Máximo ~45 palabras por escena: un cambio visual cada 5-15 s.
- **Datos**: solo cifras verificables. Si no es exacta, redondea y di "about"/"around". Nunca inventes citas.
- **Nada de**: consejos médicos o financieros, ni detalles morbosos de tragedias con víctimas.
- Narración escrita para leerse en voz alta: números en letras ("ninety-five percent"), sin símbolos.

## Tipos de escena disponibles (`src/yt/anim/scenes.py`)

| type | Para qué | data principal |
|---|---|---|
| `map_route` | mapas: países resaltados, ríos, rutas, puntos, etiquetas, zonas | `bbox [lon0,lat0,lon1,lat1]`, `highlight_countries [{name,color,strength}]`, `rivers [{names,width,band}]`, `routes [{points,label,color}]`, `points [{lon,lat,label,anchor,color}]`, `labels [{lon,lat,text,size,color}]`, `polygons [{points,color}]`, `title` |
| `big_number` | una cifra impactante que cuenta hacia arriba | `value`, `caption`, `kicker`, `color` |
| `text` | frase clave animada palabra a palabra | `text`, `highlight [palabras]`, `kicker` |
| `timeline` | línea del tiempo con un hito resaltado | `events [{year,label}]`, `focus`, `title` |
| `line_chart` | evolución (población, temperatura…) | `points [[x,y]]`, `xlabels`, `ymax`, `title`, `end_label` |
| `bars` | comparar cantidades | `bars [{label,value,display,color}]`, `title`, `highlight` |
| `versus` | A contra B | `left/right {name, lines[], title_color}` |
| `icon_grid` | proporciones (95 de 100…) | `icon (person/circle/store…)`, `icons`, `highlight`, `label`, `caption` |
| `diagram` | pasos o causas con flechas | `nodes [{id,label,x,y,color}]`, `edges [[a,b,label]]`, `pulse`, `title` |
| `list` | lista de puntos ✓/✗ | `title`, `items`, `marks` |
| `quote` | cita histórica real | `text`, `author` |
| `stamp` | sello sobre un documento (tratados, quiebras…) | `doc_title`, `text` |
| `scale` / `cross_section` / `multi_line` / `altitude` | comparaciones de tamaño, cortes, varias series, altitud | ver el código |
| `end_screen` | pantalla final: solo botón de suscribirse | `text`, `sub_label` (no usar `next_title` por ahora) |

Los nombres de países son los de Natural Earth (`NAME` en inglés: "Egypt", "Canada", "Russia"…). Los ríos, por su nombre en inglés ("Nile", "Danube", "Mississippi"…).

## Miniaturas (3 por vídeo)

Cada una con: `prompt` (foto **realista** en inglés, descriptiva, del lugar o escena real del vídeo, con luz cinematográfica, sin texto),
`tag` (1-2 palabras: el lugar o tema), `text` (2-5 palabras que complementen al título, no que lo repitan), `highlight` (la palabra clave),
`seed` distinta y un `fallback` de mapa (como en el 001). Las tres deben ser **variantes distintas** para la prueba A/B de YouTube.

## Shorts (3 por vídeo)

Lista `shorts`, cada uno con `title` (≤ 60 caracteres, termina en `#shorts`), `description` (1 línea + 3 hashtags) y 3-5 `scenes` (~45-60 palabras en total).
Cada Short cuenta **un dato sorprendente distinto** del vídeo y termina con "Full story on the channel."
