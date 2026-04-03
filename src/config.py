import logging
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

# ============================================================================
# HARDCODED CONFIGURATION VARIABLES
# ============================================================================

# Bot Configuration
bot_name = "meaw"
default_repo = "elixpo/elixpo_chapter"

# Discord Configuration
admin_role_ids: List[int] = []  # Set in .env if needed
discord_token = os.getenv("DISCORD_TOKEN", "")

# GitHub Configuration
github_bot_username = "meaw-bot"
github_admin_users: List[str] = ["admin_github_username1", "admin_github_username2"]
whitelisted_repos: List[str] = ["elixpo/elixpo_chapter"]
github_admin_only_mentions = True
github_token = os.getenv("POLLI_PAT", "")
github_app_id = os.getenv("GITHUB_APP_ID", "")
github_installation_id = os.getenv("GITHUB_INSTALLATION_ID", "")
github_project_pat = os.getenv("GITHUB_PROJECT_PAT", "")

# Load GitHub Private Key
def _load_private_key() -> str:
    key_value = os.getenv("GITHUB_PRIVATE_KEY", "")
    if not key_value:
        return ""

    key_path = Path(key_value)
    if not key_path.is_absolute():
        key_path = PROJECT_ROOT / key_value

    if key_path.is_file():
        try:
            content = key_path.read_text()
            logger.info(f"Loaded private key from {key_path}")
            return content
        except Exception as e:
            logger.error(f"Failed to read private key file {key_path}: {e}")
            return ""

    return key_value.replace("\\n", "\n")

github_private_key = _load_private_key()

# Webhook Configuration
webhook_port = 8002
webhook_enabled = True
webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# AI Model Configuration
pollinations_model = "kimi"
fallback_model = "openai"
pollinations_token = os.getenv("POLLINATIONS_TOKEN", "")

# Features Configuration
sandbox_enabled = True
local_embeddings_enabled = True
embeddings_repo = "elixpo/elixpo_chapter"
doc_embeddings_enabled = True
doc_sites = [
    "https://enter.pollinations.ai",
    "https://kpi.myceli.ai",
    "https://gsoc.pollinations.ai",
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def github_repo() -> str:
    """Get the configured GitHub repository."""
    return default_repo

def use_github_app() -> bool:
    """Check if GitHub App authentication is configured."""
    return bool(github_app_id and github_installation_id and github_private_key)

def has_project_access() -> bool:
    """Check if GitHub Project V2 access is available."""
    return bool(github_project_pat)

def is_github_admin(username: str) -> bool:
    """Check if a user is a GitHub admin."""
    if not username:
        return False
    return username.lower() in [u.lower() for u in github_admin_users]

def is_repo_whitelisted(repo: str) -> bool:
    """Check if a repository is whitelisted."""
    if not whitelisted_repos:
        return True
    return repo.lower() in [r.lower() for r in whitelisted_repos]

def validate() -> bool:
    """Validate configuration and exit if errors found."""
    errors = []

    if not discord_token:
        errors.append("DISCORD_TOKEN is required in .env")

    if not use_github_app() and not github_token:
        errors.append(
            "GitHub auth required in .env. Either:\n"
            "  - Set GITHUB_APP_ID, GITHUB_INSTALLATION_ID, and GITHUB_PRIVATE_KEY\n"
            "  - Or set POLLI_PAT"
        )

    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("\nCheck your .env file")
        sys.exit(1)

    logger.info(f"Bot: {bot_name}")
    logger.info(f"Default repo: {default_repo}")
    logger.info(f"GitHub auth: {'App' if use_github_app() else 'PAT'}")
    logger.info(f"Webhook: {'enabled' if webhook_enabled else 'disabled'} on port {webhook_port}")
    logger.info(f"AI model: {pollinations_model}")
    logger.info(f"GitHub admins: {len(github_admin_users)} users")
    logger.info(f"Whitelisted repos: {len(whitelisted_repos) if whitelisted_repos else 'all'}")

    if has_project_access():
        logger.info("ProjectV2 access: enabled")

    return True
