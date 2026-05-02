# Bot de gastos (Twilio + Gemini + PostgreSQL + Streamlit)

Flujo: mensaje de WhatsApp vía Twilio → webhook FastAPI → extracción con Google Gemini → persistencia en PostgreSQL → visualización en Streamlit.

## Requisitos

- Python 3.11+
- PostgreSQL (por ejemplo en [Railway](https://railway.app))
- Cuenta [Twilio](https://www.twilio.com) con WhatsApp Sandbox o número aprobado
- API key de [Google AI Studio](https://aistudio.google.com) (Gemini)

## Variables de entorno

| Variable | Uso |
|----------|-----|
| `DATABASE_URL` | URL de PostgreSQL (Railway suele entregar `postgresql://...`; si ves `postgres://`, el código la normaliza). |
| `GEMINI_API_KEY` | Clave de la API Gemini. |
| `GEMINI_MODEL` | (Opcional) Si lo definís, ese ID se prueba **primero** y después el fallback automático. Sin variable, el orden es: `gemini-2.5-flash-lite` → `gemini-2.5-flash` → `gemini-2.0-flash-lite` → `gemini-1.5-flash` (útil ante cuota o modelo no disponible). No dejes la variable definida pero vacía. |

## Cómo correr en local

1. Crear entorno e instalar dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Exportar variables (PowerShell):

```powershell
$env:DATABASE_URL = "postgresql://usuario:password@localhost:5432/finanzas"
$env:GEMINI_API_KEY = "tu_clave"
```

3. API (webhook) — cualquiera de estas dos:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
python main.py
```

(`python main.py` usa la variable `PORT` si es un entero válido; si no, 8000.)

4. Dashboard:

```bash
streamlit run dashboard.py --server.address 0.0.0.0
```

La tabla `expenses` se crea automáticamente al levantar la API (si `DATABASE_URL` está definida).

## Docker Compose (local)

PostgreSQL + API + dashboard en contenedores, con volúmenes para editar código en el host y `--reload` en FastAPI.

1. Copiá variables de ejemplo y editá la clave de Gemini:

```bash
copy .env.example .env
```

(PowerShell en Windows; en macOS/Linux: `cp .env.example .env`.)

En `.env` definí al menos:

```
GEMINI_API_KEY=tu_clave
```

Docker Compose lee `.env` del directorio del proyecto para interpolar variables en `docker-compose.yml`.

2. Levantá todo:

```bash
docker compose up --build
```

3. URLs:

- API / webhook: `http://localhost:8000` (`POST /webhook`, `GET /health`)
- Dashboard: `http://localhost:8501`
- Postgres en el host: `localhost:5432` (usuario/contraseña/db: `finanzas` / `finanzas` / `finanzas`)

Los servicios `web` y `dashboard` montan el código local en `/app` y ejecutan `pip install -r requirements.txt` al arrancar para que las dependencias sigan disponibles a pesar del volumen.

**Solo API o solo dashboard:**

```bash
docker compose up --build postgres web
docker compose up --build postgres dashboard
```

Imagen de producción (sin volúmenes): construí con el `Dockerfile` y pasá `DATABASE_URL` / `GEMINI_API_KEY` en runtime; el `CMD` por defecto es `python main.py`.

## Cómo testear los mensajes (sin WhatsApp)

Twilio manda un `POST` con formulario (`application/x-www-form-urlencoded`) y el campo **`Body`** con el texto. Podés imitar eso en local con la API levantada (`docker compose up` o `uvicorn`).

### 1) Salud del servicio

```bash
curl http://localhost:8000/health
```

### 2) Swagger (rápido)

Abrí `http://localhost:8000/docs`, expandí **POST /webhook**, **Try it out**, completá **Body** con por ejemplo `gasté 5000 en comida` y ejecutá. La respuesta es TwiML (XML) con el texto `Guardado: ...` o `No entendí el gasto`.

### 3) cURL (como Twilio)

```bash
curl -s -X POST "http://localhost:8000/webhook" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "Body=gasté 5000 en comida"
```

### 4) PowerShell

```powershell
$mensaje = "gasté 5000 en comida"
$body = "Body=" + [uri]::EscapeDataString($mensaje)
Invoke-RestMethod -Uri "http://localhost:8000/webhook" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded"
```

### 5) Comprobar que quedó guardado

- Abrí el dashboard (`http://localhost:8501` con Compose) y revisá la tabla / totales.
- O probá la cuota forzada: `pagué la visa 3000 ayer` → categoría `cuotas`.

Necesitás **`GEMINI_API_KEY`** válida y **`DATABASE_URL`** apuntando a una Postgres accesible (el contenedor `postgres` de Compose ya la define para el servicio `web`).

## Deploy en Railway (dos servicios)

El mismo repositorio puede desplegarse **dos veces** como servicios independientes que comparten la misma base de datos.

Railway (Nixpacks) a veces propone un comando con `--port $PORT` donde `$PORT` no se expande y falla. La forma estable es **definir el Start Command a mano** (sin `$PORT` en el texto del comando; Railway igual inyecta la variable `PORT` numérica en el entorno):

### 1) Base de datos

- En Railway: **New** → **Database** → **PostgreSQL**.
- Copiá la variable `DATABASE_URL` (o `PRIVATE_URL` / connection string que Railway provee para Postgres).

### 2) Servicio **backend** (webhook)

- **New** → **GitHub Repo** (o deploy desde CLI) con este proyecto.
- **Variables**: `DATABASE_URL`, `GEMINI_API_KEY`.
- **Settings → Deploy → Custom Start Command**:

```bash
python main.py
```

`main.py` lee `PORT` desde el entorno (ignora valores basura tipo `$PORT`).

- Asigná un dominio público y usá la URL base para Twilio (ver más abajo).

### 3) Servicio **dashboard** (Streamlit)

- **New** → **Empty service** o segundo deploy del mismo repo.
- **Variables**: `DATABASE_URL`. No hace falta `GEMINI_API_KEY`.
- **Custom Start Command**:

```bash
streamlit run dashboard.py --server.address 0.0.0.0
```

Al inicio, `dashboard.py` copia un `PORT` válido a `STREAMLIT_SERVER_PORT` o usa 8501.

- Generá dominio público para el dashboard.

No agregues variables `PORT` ni `STREAMLIT_SERVER_PORT` con el texto `$PORT`. Si existían, borralas.

**Dockerfile**: `CMD` por defecto `python main.py` (API). Para desplegar solo el dashboard con esta imagen, sobreescribí el comando en Railway con el de Streamlit de arriba.

**Procfile**: referencia para otros hosts (`web` / `dashboard`).

## Conectar Twilio (WhatsApp)

1. En la consola Twilio, abrí tu número / sandbox de WhatsApp.
2. En **Messaging** → **Webhook** (incoming messages), configurá:
   - **URL**: `https://TU-DOMINIO-RAILWAY/webhook`
   - **HTTP**: `POST`
3. Guardá. Los mensajes entrantes envían `Body` (texto) que procesa `main.py`.

Probar localmente con túnel ([ngrok](https://ngrok.com), etc.):

```bash
ngrok http 8000
```

Usá `https://xxxx.ngrok-free.app/webhook` como webhook temporal.

## Endpoints útiles

- `POST /webhook` — Webhook Twilio (form-urlencoded).
- `GET /health` — Estado del servicio.

## Estructura de archivos

- `main.py` — FastAPI + webhook Twilio.
- `ai.py` — Gemini (`extract_expense`, reglas de categorías y montos).
- `db.py` — Motor SQLAlchemy y creación de tablas.
- `models.py` — Modelo `Expense`.
- `crud.py` — Altas y consultas (`get_expenses`, `get_expenses_by_date_range`, `get_summary_by_category`, `get_daily_spending`).
- `dashboard.py` — Streamlit (normaliza puerto antes de cargar Streamlit).
- `Procfile` — `python main.py` / `streamlit run …`.
- `Dockerfile` — Imagen Python; arranque API con `python main.py`.
- `docker-compose.yml` — Postgres + `web` + `dashboard` para desarrollo local.
- `.env.example` — Plantilla para `GEMINI_API_KEY` (usada con Compose).

## Ejemplo de uso

Desde WhatsApp: **"gasté 5000 en comida"** → se guarda en PostgreSQL y aparece en el dashboard con filtros y gráficos.
