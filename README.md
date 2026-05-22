# Multi-Agent Starter

A production-ready monorepo starter for building Multi-Agent Systems with LangGraph.
hi
## Stack

| Layer | Technology |
|---|---|
| Agent framework | LangGraph |
| Backend | FastAPI + Python 3.12 |
| Package manager | uv |
| CLI | Typer |
| Frontend | Next.js 15 + shadcn/ui |
| JS runtime | Bun |
| Database | PostgreSQL 16 (LangGraph checkpointer) |
| Cache | Redis 7 |
| Containers | Docker Compose |

## Project Structure

```
multi-agent-starter/
├── apps/
│   ├── api/          # FastAPI + LangGraph backend
│   └── web/          # Next.js + shadcn/ui frontend
├── packages/         # Shared packages (future use)
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Quick Start

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

- API: http://localhost:8000
- Web: http://localhost:3000
- API docs: http://localhost:8000/docs

### 3. Local development (without Docker)

**Backend:**

```bash
cd apps/api
uv sync
uv run api serve
```

**Frontend:**

```bash
cd apps/web
bun install
bun dev
```

> Make sure Postgres and Redis are running locally (or use `docker compose up postgres redis`).

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/chat` | Send message, get full response |
| POST | `/api/chat/stream` | Send message, get SSE token stream |

## LangGraph Agent

The starter agent is a **ReAct-style graph** with:

- `call_model` node — invokes GPT-4o-mini with bound tools
- `tools` node — executes tool calls via `ToolNode`
- Conditional routing: tool calls loop back, otherwise end
- **Postgres checkpointer** for persistent conversation threads across restarts

### Starter Tools

| Tool | Description |
|---|---|
| `get_current_time` | Returns the current UTC time |
| `calculate` | Evaluates a basic math expression |

## Environment Variables

See `.env.example` for all variables and descriptions.

## Adding New Agents

1. Create a new graph in `apps/api/src/api/agent/`
2. Register a new router in `apps/api/src/api/routers/`
3. Mount the router in `apps/api/src/api/main.py`
