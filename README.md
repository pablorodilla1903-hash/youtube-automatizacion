# youtube-automatizacion

Cada noche, sin que tengas que hacer nada, este repositorio genera para **cada canal**:

- un **vídeo largo** de 8 a 10 minutos en 1080p (con guion, voz, imágenes de archivo y música),
- un **Short** vertical con subtítulos grandes,
- la **miniatura**, los **subtítulos .srt**, el **título** (y 2 alternativos), la **descripción SEO**, las **etiquetas**, un comentario para fijar y la **hora a la que debes programarlo**.

Todo aparece en tu **Google Drive** (carpeta `YouTube Automático/<canal>/AAAA-MM-DD - título/`; la marca del canal está en `YouTube Automático/<canal>/0_Marca y textos/`) hacia la **1:30-2:00 de la madrugada**,
bastante antes de las 3:00. Coste: **0 €**.

La estrategia (nichos, nombres y horas de publicación) está en **[ESTRATEGIA.md](ESTRATEGIA.md)**.

## Cómo funciona

```
GitHub Actions (gratis, cada noche 01:17 hora de España)
  ├─ 1. Google Gemini (gratis)      → elige un tema nuevo y escribe guion, título, descripción, etiquetas
  ├─ 2. Voces de Microsoft Edge     → locución neuronal (gratis, sin cuenta)
  ├─ 3. Pexels (gratis)             → vídeos de archivo para cada frase
  ├─ 4. ffmpeg                      → montaje 1080p + Short 9:16 + música + subtítulos
  ├─ 5. Pillow                      → miniatura con texto grande
  └─ 6. Google Drive                → lo sube todo y borra las carpetas de hace más de 7 días
```

### ¿Por qué no Google "Chirp 3 HD" para la voz?

La voz que mencionas ("chip3d") es **Chirp 3 HD**, de Google Cloud Text-to-Speech. Suena muy bien, pero **pide dar de alta una
tarjeta** en Google Cloud: si te pasas de la cuota gratuita, te cobran automáticamente. Como tu condición es no gastar
ni un euro, el sistema usa por defecto las **voces neuronales de Microsoft Edge**, que son gratis, no necesitan cuenta
y tienen una calidad muy parecida. Si más adelante quieres probar Chirp 3 HD, ya está programado: añade el secreto
`GOOGLE_TTS_API_KEY` y crea la variable `TTS_PROVIDER` con el valor `google`. Si Google falla, el sistema vuelve solo a la voz de Edge.

> **Tú no me das acceso a nada.** Las claves se guardan cifradas como *secretos* de tu repositorio de GitHub, y quien
> genera los vídeos cada noche es GitHub Actions. No hace falta que estés conectado ni que yo esté activo.

---

## Puesta en marcha (unos 30 minutos, una sola vez)

### Paso 0 · Activar el código en la rama principal
GitHub solo ejecuta las tareas programadas desde la rama principal (`main`). Fusiona la rama
`claude/youtube-channels-automation-lat0ib` en `main`. Puedes pedirme que abra el Pull Request y tú solo pulsas **Merge**.

### Paso 1 · Clave de IA gratuita (Google Gemini)
1. Entra en <https://aistudio.google.com/apikey> con tu cuenta de Google.
2. Pulsa **Create API key** y cópiala. No pide tarjeta.

*(Opcional, de respaldo: crea una clave gratis en <https://console.groq.com/keys> por si Gemini falla algún día.)*

### Paso 2 · Clave de vídeos de archivo (Pexels)
1. Regístrate en <https://www.pexels.com/join/>.
2. Entra en <https://www.pexels.com/api/new/>, rellena el formulario (en *proyecto* pon "YouTube channel") y copia la clave.

### Paso 3 · Permiso para subir a tu Google Drive
Esto crea una "llave" que solo puede tocar los archivos que la propia automatización crea en tu Drive.

1. Entra en <https://console.cloud.google.com/> → selector de proyecto (arriba) → **Nuevo proyecto** → nombre: `youtube-auto` → **Crear**. No actives la facturación.
2. Con ese proyecto seleccionado, busca **"Google Drive API"** en la barra de búsqueda → **Habilitar**.
3. Menú → **APIs y servicios → Pantalla de consentimiento de OAuth** (o *Google Auth Platform*) → **Comenzar**:
   - Nombre de la aplicación: `youtube-auto`, y tu correo como correo de asistencia.
   - Público: **Externo**. Correo de contacto: el tuyo → **Crear**.
4. En **Público** pulsa **Publicar aplicación** → Confirmar.
   ⚠️ Este paso es importante: si la dejas en modo "Prueba", el permiso caduca a los 7 días.
5. Ve a **Clientes** (o *Credenciales*) → **Crear cliente** → tipo **Aplicación web**:
   - En *URI de redireccionamiento autorizados* añade: `https://developers.google.com/oauthplayground`
   - **Crear**. Copia el **ID de cliente** y el **Secreto de cliente**.
6. Abre <https://developers.google.com/oauthplayground>:
   - Pulsa el engranaje ⚙️ (arriba a la derecha) → marca **Use your own OAuth credentials** → pega el ID y el secreto.
   - En el cuadro de la izquierda *Input your own scopes* escribe `https://www.googleapis.com/auth/drive.file` → **Authorize APIs**.
   - Inicia sesión con **tu** cuenta. Verás el aviso "Google no ha verificado esta aplicación", que es normal porque la app es tuya: pulsa **Configuración avanzada → Ir a youtube-auto** → **Continuar**.
   - Pulsa **Exchange authorization code for tokens** y copia el **Refresh token**.

### Paso 4 · Guardar las claves en GitHub
En tu repositorio: **Settings → Secrets and variables → Actions → New repository secret**. Crea estos secretos:

| Nombre | Valor |
|---|---|
| `GEMINI_API_KEY` | clave del paso 1 |
| `PEXELS_API_KEY` | clave del paso 2 |
| `GDRIVE_CLIENT_ID` | ID de cliente (paso 3.5) |
| `GDRIVE_CLIENT_SECRET` | secreto de cliente (paso 3.5) |
| `GDRIVE_REFRESH_TOKEN` | refresh token (paso 3.6) |
| `GROQ_API_KEY` | *(opcional)* respaldo de IA |

### Paso 5 · Música (opcional, recomendado)
En YouTube Studio → **Biblioteca de audio** descarga 5-10 pistas instrumentales tranquilas (géneros *Ambient* o *Cinematic*)
y súbelas a la carpeta `assets/musica/` del repositorio (**Add file → Upload files**). Cada vídeo usará una al azar.

### Paso 6 · Primera prueba
Pestaña **Actions → Vídeos diarios → Run workflow**. Tarda unos 30-40 minutos. Cuando acabe, revisa tu Drive.
Si algo falla, GitHub te manda un correo. Puedes pegarme el error aquí y lo arreglo.

### Paso 7 · Crear los canales de YouTube
1. En <https://www.youtube.com/account> → **Crear un canal** → "Usar un nombre personalizado". Así se crea como *cuenta de marca*, que te permite gestionar varios canales con una sola cuenta de Google.
2. Nombres, logo y colores: consulta [ESTRATEGIA.md](ESTRATEGIA.md).
3. Verifica el canal con tu teléfono en <https://www.youtube.com/verify>. Sin esto no puedes subir miniaturas propias ni vídeos de más de 15 minutos.
4. En YouTube Studio → Configuración → Canal: país, palabras clave y el idioma del canal (inglés o español).

---

## Tu rutina diaria (5-10 minutos)

1. Abre Drive → `YouTube Automático/<canal>/<fecha - título>/`.
2. Lee `LEEME_SUBIR.txt` y **comprueba los datos de la lista "REVISA ESTOS DATOS"**. Te protege de errores y de la política de contenido no auténtico.
3. En YouTube Studio → **Crear → Subir vídeo** → `1_VIDEO.mp4`: pega el título, la descripción y las etiquetas, sube la miniatura `2_MINIATURA.jpg` y en Subtítulos sube `3_SUBTITULOS.srt`.
4. En Visibilidad elige **Programar** y pon la hora que indica el archivo.
5. Haz lo mismo con `4_SHORT.mp4` (título y descripción del Short).
6. Cuando se publique, fija el comentario que viene en el archivo.

La app de YouTube Studio para móvil permite hacerlo todo desde el teléfono.

## Personalizar (sin programar)

- **`config/canales.yaml`**: nombre, voz, nicho, pilares de contenido, duración, horas de publicación, volumen de la música, si se genera Short o no, y los días que se guardan en Drive. Para **añadir un canal nuevo**, copia uno de los bloques, cambia el identificador (`de`, `fr`…) y ya está.
- **`config/temas_<canal>.txt`**: escribe temas concretos, uno por línea, y se usarán antes que los que invente la IA.
- **`data/historial/`**: los temas ya publicados, para que no se repitan. Se actualiza solo.
- **Voces**: cualquier voz de Edge sirve. Algunas: `en-US-AndrewNeural`, `en-US-BrianNeural`, `en-GB-RyanNeural`, `es-MX-JorgeNeural`, `es-ES-AlvaroNeural`, `es-CO-GonzaloNeural`.

## Límites gratuitos (sobra margen)

| Servicio | Gratis | Uso de 2 canales |
|---|---|---|
| GitHub Actions (repo privado) | 2.000 min/mes | unas 1.000-1.200 min/mes |
| Gemini API | cuota diaria gratuita | 2 peticiones al día |
| Pexels | 20.000 peticiones/mes | unas 3.000/mes |
| Google Drive | 15 GB | unos 5 GB (se guardan 7 días) |

Si abres más de 3 canales, haz el repositorio **público** (Settings → General → Change visibility): en repositorios
públicos GitHub Actions no tiene límite de minutos, y las claves siguen protegidas porque los secretos nunca se muestran.

## Probar en tu ordenador (opcional)

```bash
pip install -r requirements.txt
cd src && python -m yt.main --offline       # prueba sin claves: guion de ejemplo, sin voz, fondos de color
```
