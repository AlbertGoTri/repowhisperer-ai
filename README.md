# 🔍 RepoWhisperer

**Chat with any GitHub repository using AI.** Paste a repo URL, and RepoWhisperer indexes the entire codebase so you can ask questions, understand architecture, find code, and generate new code — all in a conversational interface.

Built with [DigitalOcean Gradient™ AI](https://www.digitalocean.com/products/gradient/platform) for the [DigitalOcean Gradient™ AI Hackathon](https://digitalocean.devpost.com/).

![RepoWhisperer](https://img.shields.io/badge/Powered%20by-DigitalOcean%20Gradient%20AI-0080FF?style=for-the-badge)

---

## ✨ Features

- **🔗 Paste & Index** — Drop a GitHub URL and the entire repo gets cloned and indexed for AI consumption
- **💬 Chat with Code** — Ask natural language questions about any part of the codebase
- **🏗️ Architecture Overview** — Get high-level summaries and structure breakdowns
- **🔍 Code Search** — Find where specific functionality is implemented
- **✍️ Code Generation** — Generate tests, refactors, and documentation matching the repo's style
- **🎛️ Multi-Model** — Switch between Llama 3.3 70B, DeepSeek R1, Mistral Nemo and more via Gradient AI
- **🌊 Streaming Responses** — Real-time streaming output for a smooth experience
- **📂 File Tree View** — Browse the indexed repo structure in the sidebar

## 🏗️ Architecture

```
┌──────────────┐     ┌───────────────────────────────┐
│   React UI   │────▶│      FastAPI Backend           │
│  (Vite +     │     │                                │
│  Tailwind)   │◀────│  ┌─────────────────────────┐   │
└──────────────┘     │  │   Repo Ingestion        │   │
                     │  │   - Clone via GitPython  │   │
                     │  │   - Parse & chunk files  │   │
                     │  │   - Language detection   │   │
                     │  └────────────┬────────────┘   │
                     │               │                 │
                     │  ┌────────────▼────────────┐   │
                     │  │   RAG Context Builder    │   │
                     │  │   - Keyword retrieval    │   │
                     │  │   - Relevance scoring    │   │
                     │  │   - Context assembly     │   │
                     │  └────────────┬────────────┘   │
                     │               │                 │
                     │  ┌────────────▼────────────┐   │
                     │  │ DO Gradient AI Service   │   │
                     │  │   - Serverless Inference │   │
                     │  │   - Multi-model support  │   │
                     │  │   - Streaming responses  │   │
                     │  └─────────────────────────┘   │
                     └───────────────────────────────┘
```

## 🔧 DigitalOcean Gradient™ AI Usage

RepoWhisperer leverages DigitalOcean's Gradient™ AI Platform extensively — every AI-powered feature runs through the Gradient Serverless Inference API.

### How We Use Gradient AI

| Gradient Feature | Implementation Detail |
|------------------|----------------------|
| **Serverless Inference API** | All LLM calls go through the `inference.do-ai.run/v1` endpoint using the OpenAI-compatible `/chat/completions` route. No GPU provisioning or infrastructure management required. |
| **Multi-Model Selection** | Users can switch models at any time from the chat UI. We support `llama3.3-70b-instruct`, `deepseek-r1-distill-llama-70b`, `mistral-nemo-instruct-2407`, and `llama3-8b-instruct` — all served through the same Gradient endpoint. |
| **Streaming Responses (SSE)** | We use `"stream": true` on the Gradient API and pipe Server-Sent Events to the frontend for real-time, token-by-token output via `httpx.AsyncClient.stream()`. |
| **RAG Pipeline** | Repositories are cloned, parsed, and chunked into contextual segments. On each user query, the most relevant chunks are retrieved using keyword scoring and assembled into the system prompt sent to Gradient AI. |
| **App Platform Deployment** | Production-ready deployment via `.do/app.yaml` with secrets management for the Gradient API key. |

### Gradient AI Integration Architecture

```
User Message
    │
    ▼
┌─────────────────────────┐
│  RepoContextBuilder     │  ← Keyword-based RAG retrieval
│  - Score file chunks    │     from indexed repository
│  - Assemble top-k       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  System Prompt +        │  ← Repo context injected into
│  Conversation History   │     the system message
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  DigitalOcean Gradient AI               │
│  POST inference.do-ai.run/v1/           │
│       chat/completions                  │
│  Headers: Bearer <Model Access Key>     │
│  Body: { model, messages, stream:true } │
└───────────┬─────────────────────────────┘
            │
            ▼
   SSE stream → Frontend (token by token)
```

### Available Models

| Model | ID | Best For |
|-------|-----|----------|
| **Llama 3.3 70B** | `llama3.3-70b-instruct` | General code understanding (default) |
| **DeepSeek R1 70B** | `deepseek-r1-distill-llama-70b` | Deep reasoning and complex analysis |
| **Mistral Nemo** | `mistral-nemo-instruct-2407` | Fast, efficient responses |
| **Llama 3 8B** | `llama3-8b-instruct` | Quick queries, lower latency |

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- A [DigitalOcean account](https://mlh.link/digitalocean-signup) with Gradient AI access

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/repowhisperer.git
cd repowhisperer
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

Open [http://localhost:3000](http://localhost:3000) and paste a GitHub repo URL!

### Deploy to DigitalOcean App Platform

```bash
doctl apps create --spec .do/app.yaml
```

## 🎯 Hackathon Criteria

| Criteria | How RepoWhisperer Delivers |
|----------|---------------------------|
| **Technological Implementation** | Deep use of Gradient AI (Serverless Inference, multi-model, streaming, RAG pipeline) |
| **Design** | Clean, intuitive chat UX with dark theme, streaming responses, and file tree sidebar |
| **Potential Impact** | Democratizes codebase understanding — free & open-source alternative to paid tools |
| **Quality of the Idea** | Novel combination of RAG + multi-model inference for code understanding |

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a PR.

---

Built with ❤️ using [DigitalOcean Gradient™ AI](https://www.digitalocean.com/products/gradient/platform)
