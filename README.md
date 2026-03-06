# RepoWhisperer

Chat with any GitHub repository using AI. Paste a repo URL, and RepoWhisperer clones the codebase, indexes it into searchable chunks, and lets you ask questions, explore architecture, find code, and generate new code through a conversational interface.

Built for the [DigitalOcean Gradient AI Hackathon](https://digitalocean.devpost.com/) using [DigitalOcean Gradient AI](https://www.digitalocean.com/products/gradient/platform).

![Powered by DigitalOcean Gradient AI](https://img.shields.io/badge/Powered%20by-DigitalOcean%20Gradient%20AI-0080FF?style=for-the-badge)

---

## Features

- **Paste and Index** - Provide a GitHub URL and the entire repo is cloned, parsed, and indexed for AI consumption.
- **Chat with Code** - Ask natural language questions about any part of the codebase.
- **Architecture Overview** - Get high-level summaries and structure breakdowns.
- **Code Search** - Locate where specific functionality is implemented.
- **Code Generation** - Generate tests, refactors, and documentation that match the repo's style.
- **Multi-Model Support** - Switch between Llama 3.3 70B, DeepSeek R1, Mistral Nemo, and Llama 3 8B at any time.
- **Streaming Responses** - Real-time token-by-token output via Server-Sent Events.
- **File Tree View** - Browse the indexed repo structure in the sidebar.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+, FastAPI, uvicorn, httpx, GitPython, pydantic-settings |
| Frontend | React 19, Vite 6, Tailwind CSS 3.4, react-markdown, rehype-highlight, lucide-react |
| AI | DigitalOcean Gradient AI Serverless Inference (`inference.do-ai.run/v1`) |
| Deployment | Docker (multi-stage), nginx, DigitalOcean App Platform |

## Architecture

```
┌──────────────┐     ┌─────────────────────────────────┐
│   React UI   │────>│      FastAPI Backend            │
│  (Vite +     │     │                                 │
│  Tailwind)   │<────│  ┌──────────────────────────┐   │
└──────────────┘     │  │   Repo Ingestion         │   │
                     │  │   - Clone via GitPython  │   │
                     │  │   - Parse and chunk files│   │
                     │  │   - Language detection   │   │
                     │  └────────────┬─────────────┘   │
                     │               │                 │
                     │  ┌────────────v─────────────┐   │
                     │  │   RAG Context Builder    │   │
                     │  │   - Keyword retrieval    │   │
                     │  │   - Relevance scoring    │   │
                     │  │   - Context assembly     │   │
                     │  └────────────┬─────────────┘   │
                     │               │                 │
                     │  ┌────────────v─────────────┐   │
                     │  │ DO Gradient AI Service   │   │
                     │  │   - Serverless Inference │   │
                     │  │   - Multi-model support  │   │
                     │  │   - Streaming responses  │   │
                     │  └──────────────────────────┘   │
                     └─────────────────────────────────┘
```

## DigitalOcean Gradient AI Usage

Every AI-powered feature in RepoWhisperer runs through the DigitalOcean Gradient Serverless Inference API.

### Integration Details

| Gradient Feature | Implementation |
|------------------|----------------|
| **Serverless Inference API** | All LLM calls go through `inference.do-ai.run/v1` using the OpenAI-compatible `/chat/completions` route. No GPU provisioning or infrastructure management required. |
| **Multi-Model Selection** | Users can switch models from the chat UI. Four models are available through the same Gradient endpoint: `llama3.3-70b-instruct`, `deepseek-r1-distill-llama-70b`, `mistral-nemo-instruct-2407`, and `llama3-8b-instruct`. |
| **Streaming (SSE)** | Requests are sent with `"stream": true`. The backend pipes Server-Sent Events to the frontend for real-time, token-by-token output using `httpx.AsyncClient.stream()`. |
| **RAG Pipeline** | Repositories are cloned, parsed, and chunked into contextual segments. On each query, the most relevant chunks are retrieved via keyword scoring and assembled into the system prompt sent to Gradient AI. |
| **App Platform Deployment** | Production-ready deployment via `.do/app.yaml` with secrets management for the Gradient API key. |

### RAG Pipeline Flow

```
User Message
    |
    v
┌─────────────────────────┐
│  RepoContextBuilder     │  Keyword-based RAG retrieval
│  - Score file chunks    │  from indexed repository
│  - Assemble top-k       │
└───────────┬─────────────┘
            |
            v
┌─────────────────────────┐
│  System Prompt +        │  Repo context injected into
│  Conversation History   │  the system message
└───────────┬─────────────┘
            |
            v
┌─────────────────────────────────────────┐
│  DigitalOcean Gradient AI               │
│  POST inference.do-ai.run/v1/           │
│       chat/completions                  │
│  Headers: Bearer <Model Access Key>     │
│  Body: { model, messages, stream:true } │
└───────────┬─────────────────────────────┘
            |
            v
   SSE stream to frontend (token by token)
```

### Available Models

| Model | ID | Best For |
|-------|-----|----------|
| Llama 3.3 70B | `llama3.3-70b-instruct` | General code understanding (default) |
| DeepSeek R1 70B | `deepseek-r1-distill-llama-70b` | Deep reasoning and complex analysis |
| Mistral Nemo | `mistral-nemo-instruct-2407` | Fast, efficient responses |
| Llama 3 8B | `llama3-8b-instruct` | Quick queries, lower latency |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- A [DigitalOcean account](https://mlh.link/digitalocean-signup) with Gradient AI access

### 1. Clone and Configure

```bash
git clone https://github.com/YOUR_USERNAME/repo-whisperer.git
cd repo-whisperer
cp .env.example .env
```

Edit `.env` with your DigitalOcean Gradient AI credentials:

```env
DO_AGENT_KEY=your_gradient_model_access_key
DO_AGENT_ENDPOINT=https://inference.do-ai.run/v1
```

Get your Model Access Key at [cloud.digitalocean.com/gen-ai/model-access-keys](https://cloud.digitalocean.com/gen-ai/model-access-keys).

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and paste a GitHub repo URL to get started.

### Deploy to DigitalOcean App Platform

```bash
doctl apps create --spec .do/app.yaml
```

## Project Structure

```
├── .env.example            Environment variable template
├── Dockerfile              Multi-stage build (backend + frontend + nginx)
├── nginx.conf              Reverse proxy configuration
├── start.sh                Container entrypoint
├── backend/
│   ├── main.py             FastAPI app and all API routes
│   ├── config.py           Settings via pydantic-settings, reads .env
│   ├── models.py           Pydantic request/response models
│   ├── agent_service.py    Gradient AI service, RAG context builder, demo mode
│   ├── repo_ingestion.py   Git clone, file parsing, chunking, language detection
│   └── requirements.txt    Python dependencies
└── frontend/
    ├── vite.config.js      Dev server with API proxy to backend
    └── src/
        ├── api.js           Fetch helpers with safe JSON parsing
        ├── App.jsx          Root component
        └── components/
            ├── ChatView.jsx     Chat interface with streaming and model selection
            └── LandingView.jsx  Landing page with repo URL input
```

## Demo Mode

If no `DO_AGENT_KEY` is set, the application runs in demo mode. Demo mode uses local analysis of the indexed repository to generate responses without making any API calls. This is useful for development and testing.

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome. Open an issue or submit a pull request.
