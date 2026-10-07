# meeting-minutes-alan-vo

> AI meeting transcription and summarization tool that extracts action items, decisions, owners, and deadlines from raw meeting text, then generates Slack-ready summaries and calendar follow-ups.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-React-3178C6)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)
![SSO](https://img.shields.io/badge/SSO-SAML%20%2F%20OAuth2-8A2BE2)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Powered-purple)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

</div>

## Why meeting-minutes-alan-vo?

AI meeting transcription and summarization tool that extracts action items, decisions, owners, and deadlines from raw meeting text, then generates Slack-ready summaries and calendar follow-ups.

Built by [Alan Vo](https://github.com/ALANDVO) — AI/ML & cybersecurity engineer.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     meeting-minutes-alan-vo                                    │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  Frontend   │   API Layer │  Services   │   LLM Engine      │
│  React/TS   │  FastAPI    │  Domain     │  Multi-provider   │
│  Dashboard  │  SSO/SAML   │  Logic      │  OpenAI/Claude/   │
│  Real-time  │  JWT Auth   │  Processing │  Gemini/Ollama    │
└─────────────┴─────────────┴─────────────┴───────────────────┘
         │              │              │               │
         ▼              ▼              ▼               ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────┐
    │ Browser │   │  REST   │   │  Domain │   │  LLM API    │
    │  SPA    │   │  API    │   │  Logic  │   │  (any)      │
    └─────────┘   └─────────┘   └─────────┘   └─────────────┘
```

## Features

- **Raw transcript → structured minutes with decisions, action items, and open questions**
- **Action item extraction with owner assignment and deadline parsing**
- **Decision log with context and rationale capture**
- **Slack-ready summary generation with emoji formatting and thread structure**
- **Calendar follow-up suggestions with proposed dates and attendees**
- **Meeting type detection: standup, design review, 1:1, planning, retro**
- **Export to Markdown, JSON, or plain text for any workflow**

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/ALANDVO/meeting-minutes-alan-vo.git
cd meeting-minutes-alan-vo
cp .env.example .env
docker compose up -d
# Open http://localhost:3000
```

### Local Development

```bash
git clone https://github.com/ALANDVO/meeting-minutes-alan-vo.git
cd meeting-minutes-alan-vo
pip install -r requirements.txt
```

## Usage

```
python main.py minutes --file transcript.txt
python main.py actions --file transcript.txt --assign
python main.py slack --file transcript.txt --channel #eng-standup
python main.py followups --file transcript.txt --start-date 2026-10-08
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | LLM API key (OpenAI, Anthropic, Gemini) | Required |
| `LLM_BASE_URL` | Custom LLM endpoint (Ollama, vLLM) | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `SAML_IDP_ENTITY` | SAML Identity Provider URL | — |
| `JWT_SECRET` | JWT signing secret | Generate one |

## Tech Stack

`Python` `OpenAI/Anthropic/Gemini` `NLP` `Information Extraction` `Productivity`

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login (SSO or email) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Statistics & metrics |
| `POST` | `/api/process` | Main processing endpoint |
| `GET` | `/api/results` | Query results |

## SSO Setup

### SAML
1. Set `SAML_IDP_ENTITY` to your IdP URL
2. Set `SAML_IDP_CERT` to your IdP certificate
3. Set `SAML_ACS_URL` to `https://yourdomain.com/saml/acs`

### OAuth2
1. Register your app with the OAuth provider
2. Set `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`
3. Set `OAUTH_REDIRECT_URI`

## License

MIT — see [LICENSE](LICENSE)

---

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & Cybersecurity


