"""
Code Agent - Autonomous AI developer for Polli Discord bot.

Philosophy: Give the AI raw capabilities and let it work like a human developer.
No predefined workflows. No forced phases. Just shell access, web search, and intelligence.

AutonomousAgent (PRIMARY):
- AI has full shell access to a sandboxed repo
- Decides everything: what to read, write, test, commit
- Works like a human developer with a terminal
- Minimal tools: shell, web_search, ask_user, done

CodeAgent (LEGACY):
- Fixed flow (plan -> code -> test -> fix)
- Kept for backwards compatibility

Models (via Pollinations API):
- claude-large: Best quality for coding tasks
- gemini-large: Large context (1M) for codebase understanding
- claude: Fast iteration for testing/fixes
- kimi-k2-thinking: Deep reasoning for complex problems
- perplexity-fast: Quick web search
- perplexity-reasoning: Complex web search with reasoning

Mode System (optional, for structured workflows):
- orchestrator, code-reviewer, bug-fixer, feature-builder, etc.
"""

from .agent import CodeAgent, code_agent
from .autonomous import AutonomousAgent, autonomous_agent, AutonomousResult
from .models import ModelRouter, model_router
from .sandbox import SandboxManager, sandbox_manager, Sandbox
from .session_embeddings import SessionEmbeddings, SessionEmbeddingsManager, session_embeddings_manager
from .discord_progress import (
    DiscordProgressReporter,
    HumanFeedback,
    HumanFeedbackType,
    NotificationMode,
    register_reporter,
    unregister_reporter,
    route_reply,
)
# Modes system
from .modes import (
    # Base classes
    AgentMode,
    ModeConfig,
    WorkflowStep,
    ToolGroup,
    ModeState,
    # Orchestrator
    Orchestrator,
    get_mode_capabilities,
    list_mode_capabilities,
    # Specialized modes
    CodeReviewer,
    BugFixer,
    FeatureBuilder,
    TestWriter,
    Refactorer,
    DocWriter,
    Researcher,
    Investigator,
    IssueFixer,
    PRFixer,
    # Registry
    MODES,
    get_mode,
    list_modes,
    get_mode_by_task,
    # Runner
    ModeRunner,
    ModeRunResult,
    mode_runner,
    init_mode_runner,
)

__all__ = [
    # Core agent
    "CodeAgent",
    "code_agent",
    # Autonomous agent (AI decides workflow)
    "AutonomousAgent",
    "autonomous_agent",
    "AutonomousResult",
    # Model router
    "ModelRouter",
    "model_router",
    # Sandbox & Session Embeddings
    "SandboxManager",
    "sandbox_manager",
    "Sandbox",
    "SessionEmbeddings",
    "SessionEmbeddingsManager",
    "session_embeddings_manager",
    # Discord integration
    "DiscordProgressReporter",
    "HumanFeedback",
    "HumanFeedbackType",
    "NotificationMode",
    "register_reporter",
    "unregister_reporter",
    "route_reply",
    # Modes base classes
    "AgentMode",
    "ModeConfig",
    "WorkflowStep",
    "ToolGroup",
    "ModeState",
    # Orchestrator
    "Orchestrator",
    "get_mode_capabilities",
    "list_mode_capabilities",
    # Specialized modes
    "CodeReviewer",
    "BugFixer",
    "FeatureBuilder",
    "TestWriter",
    "Refactorer",
    "DocWriter",
    "Researcher",
    "Investigator",
    "IssueFixer",
    "PRFixer",
    # Registry
    "MODES",
    "get_mode",
    "list_modes",
    "get_mode_by_task",
    # Runner
    "ModeRunner",
    "ModeRunResult",
    "mode_runner",
    "init_mode_runner",
]
