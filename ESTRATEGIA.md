# Estrategia de los canales

## Tema elegido: historias de dinero y negocios

Los dos canales cubren el mismo nicho: **historias de empresas, millonarios, estafas y psicología del dinero**
(por ejemplo: "Cómo Blockbuster perdió contra Netflix", "El negocio oculto de IKEA", "La mayor estafa de la historia").

Por qué este tema:

| Criterio | Motivo |
|---|---|
| **RPM alto** (lo que cobras por cada 1.000 visitas) | Finanzas y negocios tienen de los anunciantes más caros. En inglés (EE. UU./R. U.) suele estar entre 6 y 15 $ o más, frente a 1-3 $ de nichos de entretenimiento. En español es menor, pero sigue estando entre los más altos del idioma. |
| **Sin cara** | Se cuenta con voz en off e imágenes de archivo. Es el formato de canales como *Company Man*, *Modern MBA* o *Dinero en Imagen*. |
| **Temas infinitos y "evergreen"** | Hay miles de empresas y fortunas; un vídeo sigue sumando visitas años después. |
| **Búsqueda + recomendación** | La gente ya busca "qué pasó con X", así que el vídeo entra por el buscador y por las sugerencias. |
| **Reutilizable** | El mismo sistema sirve para abrir más canales (en alemán, francés, portugués o con otro nicho) cambiando solo `config/canales.yaml`. |

**Nichos para tus siguientes canales** (del más rentable al menos rentable, y todos se pueden automatizar):
1. Tecnología / IA explicada (RPM alto, audiencia joven).
2. Historia oscura y misterios sin resolver (RPM medio, retención muy alta).
3. "Qué pasaría si…" / ciencia curiosa (volumen enorme de visitas, RPM medio-bajo).
4. Psicología y hábitos (RPM medio-alto).
5. Un canal de habla alemana o francesa del mismo nicho de dinero (RPM alto y menos competencia).

## Nombres

| Canal | Nombre recomendado | Alternativas | Por qué |
|---|---|---|---|
| Inglés | **Fortune Files** | Money Unfolded · The Billion Files · Richer Stories | Corto, se entiende a la primera, suena a "expedientes" (misterio + dinero) |
| Español | **Expediente Fortuna** | Archivos del Dinero · Imperios y Ruinas · Dinero Oculto | Es la versión española de la misma marca, así que puedes reutilizar logo y estilo |

Antes de crearlos, busca el nombre en YouTube, en Instagram y en TikTok, y reserva el @usuario en las tres.
Si ya está cogido, usa una alternativa o añade "HQ" o "TV".

**Identidad visual**: fondo negro, amarillo (#FFD600) y blanco (los colores de las miniaturas que genera el sistema).
El logo puede ser un simple icono de carpeta o expediente con un símbolo de $ o € (puedes hacerlo gratis en Canva).

## ¿Español latino o de España?

**Latino neutro** (voz `es-MX-JorgeNeural`):
- Tiene cinco veces más audiencia (México, Colombia, Argentina, EE. UU. hispano y el resto de Latinoamérica), y en España se entiende sin problema.
- El público hispano de EE. UU. tiene RPM de nivel estadounidense.
- Si prefieres castellano, cambia la voz a `es-ES-AlvaroNeural` en `config/canales.yaml`.

## Horas de publicación

Programa los vídeos en YouTube Studio (Subir → Visibilidad → **Programar**). Puedes subirlos a las 3:00 y dejarlos
programados: no hace falta estar despierto a la hora de publicación. Las horas están en **horario peninsular español**.

| Canal | Vídeo largo | Short | Público al que apunta |
|---|---|---|---|
| Inglés | **18:00** | 23:00 | Sale a las 12:00 en Nueva York y a las 9:00 en Los Ángeles, y coge fuerza para la tarde y noche de EE. UU. A las 18:00 también es tarde en Reino Unido (17:00). |
| Español | **22:00** | 19:00 | Sale a las 14:00-15:00 en México, 15:00-16:00 en Colombia y 17:00 en Argentina, justo antes de su franja fuerte, y a las 22:00 en España, que es horario de máxima audiencia. |

- **Mejores días**: de jueves a domingo. Si algún día vas a publicar menos, que sea de lunes a miércoles.
- Mantén siempre la misma hora: el algoritmo y tus suscriptores se acostumbran a ella.
- Pasados 2-3 meses, mira en YouTube Studio → Estadísticas → Audiencia → "Cuándo están conectados tus espectadores" y ajusta las horas en `config/canales.yaml`.

## Lo que tienes que saber para cobrar (importante)

1. **Requisitos del Programa de Socios**: 1.000 suscriptores y 4.000 horas de visualización en 12 meses, o 1.000 suscriptores y 10 millones de visualizaciones de Shorts en 90 días.
   Lo normal en un canal nuevo es tardar entre 3 y 9 meses publicando cada día.
2. **Política de "contenido no auténtico"**: YouTube desmonetiza los canales que suben en masa vídeos repetitivos hechos
   con plantilla. Para no tener problemas:
   - **Revisa cada vídeo antes de subirlo.** Son 5 minutos: comprueba los datos de la lista "REVISA ESTOS DATOS" de `LEEME_SUBIR.txt` y cambia el título si se te ocurre uno mejor.
   - Varía los temas (el sistema rota solo entre los pilares del canal y no repite temas).
   - Cuando el canal empiece a funcionar, mejóralo: graba tú la voz, añade gráficos propios o edita las miniaturas en Canva.
3. **Divulgación de IA**: marca "contenido alterado o sintético" solo si el vídeo muestra personas, sucesos o lugares realistas que no existen. Voz sintética narrando con imágenes de archivo reales no lo requiere, pero si tienes dudas, márcalo (no afecta a la monetización).
4. **Música**: usa solo pistas de la Biblioteca de audio de YouTube (Studio → Biblioteca de audio), que es gratis y no da problemas de derechos. Descarga 5-10 pistas instrumentales tranquilas y súbelas a `assets/musica/`.
5. **Los Shorts** hacen crecer los suscriptores rápido, pero pagan poco. Los vídeos largos (de más de 8 minutos, para poder poner anuncios a mitad) son los que dan dinero. Por eso el sistema genera los dos cada día.
