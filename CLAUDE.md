# Tommy

Tommy is a Discord-to-GitHub orchestrator bot. It enables users to interact with GitHub repositories directly from Discord, including code scanning, security analysis, project management, PR author assignment, and issue tracking.

## Project Structure

- `src/bot.py` - Main Discord bot (TommyBot extends commands.Bot)
- `src/api/tommy_api.py` - OpenAI-compatible REST API
- `src/services/` - Core services (pollinations, webhooks, code agent, sandbox)
- `src/services/code_agent/tools/tommy_agent.py` - GitHub code tool handler
- `.github/workflows/` - CI/CD workflows for PR review, issue assist, project management
- `tests/` - Test suite

## Key Conventions

- Bot name is **Tommy** everywhere (code, configs, docs, workflows)
- The trigger phrase in GitHub workflows is `tommy` (lowercase)
- Docker sandbox container is named `tommy_sandbox`
- API model name is `tommy`
- The bot is designed to be general-purpose and open source

## Development

- Python 3.10+
- Discord.py for bot framework
- FastAPI for the HTTP API
- Docker for sandboxed code execution
