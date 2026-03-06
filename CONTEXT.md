# RepoWhisperer — Contexto de sesión

> Lee este archivo completo antes de continuar. Contiene TODO el estado del proyecto.

## Qué es el proyecto

**RepoWhisperer** — una app web que permite pegar una URL de un repo de GitHub, lo clona e indexa, y luego puedes chatear con el código usando IA. Combina RAG (keyword-based) + streaming + multi-modelo.

- **Hackathon**: DigitalOcean Gradient™ AI Hackathon (https://digitalocean.devpost.com/)
- **Deadline**: 18 marzo 2026, 5pm ET
- **Nombre del repo en GitHub**: `repo-whisperer`
- **Descripción del repo**: `Chat with any GitHub repo using AI — powered by DigitalOcean Gradient™ AI`

## Stack técnico

- **Backend**: FastAPI + Python 3.13, uvicorn, httpx, gitpython, pydantic-settings
- **Frontend**: React 19 + Vite 6 + Tailwind CSS 3.4, react-markdown, remark-gfm, rehype-highlight, highlight.js, lucide-react
- **AI**: DigitalOcean Gradient AI — Serverless Inference en `https://inference.do-ai.run/v1`
- **Modelos disponibles** (los que acepta nuestra key):
  - `llama3.3-70b-instruct` (default)
  - `deepseek-r1-distill-llama-70b`
  - `mistral-nemo-instruct-2407`
  - `llama3-8b-instruct`
- **Modelos NO disponibles en nuestro tier**: todos los `openai-*` y `anthropic-*` (devuelven 401)

## Estructura del proyecto

```
c:\Users\Lenovo\Documents\march_hackathon\
├── .env                    ← Tiene la API key real (NO subir a GitHub, está en .gitignore)
├── .env.example            ← Template sin keys (SÍ se sube)
├── .gitignore
├── .do/app.yaml            ← Config de DigitalOcean App Platform
├── Dockerfile
├── LICENSE                 ← MIT License
├── README.md               ← Documentación completa con uso detallado de Gradient AI
├── nginx.conf
├── start.sh
├── backend/
│   ├── .venv/              ← Virtual env Python (NO subir)
│   ├── config.py           ← Settings con pydantic, lee .env de la raíz del proyecto
│   ├── main.py             ← FastAPI app, todas las rutas API
│   ├── models.py           ← Pydantic models
│   ├── agent_service.py    ← GradientAIService + RepoContextBuilder + demo mode
│   ├── repo_ingestion.py   ← Clonado y chunking de repos
│   ├── requirements.txt
│   └── repos/              ← Repos clonados (NO subir)
└── frontend/
    ├── package.json
    ├── vite.config.js       ← Proxy a backend en 127.0.0.1:8000
    ├── src/
    │   ├── api.js           ← Fetch helpers con safeJson()
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── index.css
    │   └── components/
    │       ├── ChatView.jsx  ← Chat con streaming, modelo default: llama3.3-70b-instruct
    │       └── LandingView.jsx
    └── node_modules/        ← (NO subir)
```

## API Key (configurada en .env)

```
DO_AGENT_KEY=sk-do-mlYdVx-WZngCzDCSsxmg4Oc9KNVQVIXMt1t88vaZk2BvQX_AeYTnYEB99O
DO_AGENT_ENDPOINT=https://inference.do-ai.run/v1
```

## Cómo arrancar

### Backend (PowerShell, desde la raíz del proyecto):
```powershell
cd c:\Users\Lenovo\Documents\march_hackathon\backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (PowerShell, otro terminal):
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cd c:\Users\Lenovo\Documents\march_hackathon\frontend
npm run dev
```

Frontend en http://localhost:3000, backend en http://localhost:8000.

## Bugs arreglados en esta sesión

1. **.env no se encontraba**: `config.py` buscaba `.env` relativo al CWD. Arreglado para usar ruta absoluta `os.path.join(os.path.dirname(__file__), "..", ".env")`
2. **Endpoint incorrecto**: Era `cluster-api.do-ai.run` → cambiado a `inference.do-ai.run` en `.env`, `config.py`, `.env.example`, `app.yaml`
3. **Nombres de modelos incorrectos**: `gpt-4o` → `llama3.3-70b-instruct` (y otros) en `main.py`, `agent_service.py`, `ChatView.jsx`
4. **delete_repo no persistía**: Añadido `_save_store()` en `main.py`
5. **CORS**: Cambiado a `allow_origins=["*"]`
6. **repos_dir relativo**: Cambiado a ruta absoluta
7. **Frontend JSON parse error**: Añadido `safeJson()` en `api.js`
8. **Syntax highlighting**: Conectado `rehype-highlight` + CSS en `ChatView.jsx`
9. **WSL vs Windows**: Todo se ejecuta desde Windows PowerShell (NO WSL)
10. **Node.js**: Instalado v25.8.0 en Windows via winget

## Checklist hackathon — Lo que FALTA

| # | Tarea | Estado |
|---|-------|--------|
| A | **Crear repo público en GitHub** (`repo-whisperer`) | PENDIENTE |
| B | **Hacer push del código** | PENDIENTE |
| C | **Grabar video demo (< 3 min)** y subir a YouTube | PENDIENTE |
| D | **Registrarse en la hackathon** en Devpost ("Join Hackathon") | PENDIENTE |
| E | **Completar submission en Devpost** (repo URL, video, descripción, uso de Gradient AI) | PENDIENTE |
| F | **Deploy en DO App Platform** (opcional pero recomendado) | PENDIENTE |

## Checklist hackathon — Lo que YA cumplimos

- ✅ Usa DigitalOcean Gradient™ AI (Serverless Inference, multi-modelo, streaming)
- ✅ Software funcional
- ✅ Proyecto nuevo (creado durante el periodo 28 ene – 18 mar 2026)
- ✅ Licencia MIT (OSI-approved)
- ✅ README con descripción detallada del uso de Gradient AI
- ✅ Modelos correctos en toda la documentación
- ✅ .env.example y app.yaml con endpoint correcto
- ✅ .gitignore protege .env
- ✅ Materiales en inglés
- ✅ Código propio/original

## Notas importantes

- Los créditos de $200 de DO se gastan PRIMERO antes de cobrar la tarjeta
- Los modelos OpenAI/Anthropic requieren tier superior; solo tenemos acceso a modelos open-source
- El `@lru_cache` en `config.py` cachea settings — si cambias .env, reinicia el backend
- Node.js está en `C:\Program Files\nodejs\` — a veces hay que refrescar PATH con el comando de arriba
