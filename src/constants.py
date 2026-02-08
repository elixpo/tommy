import os
import re

API_TIMEOUT = 60
POLLINATIONS_API_BASE = "https://gen.pollinations.ai"
MODEL_MONITOR_URL = "https://model-monitor.pollinations.ai"

SESSION_TIMEOUT = 300

MAX_MESSAGE_LENGTH = 2000
MAX_TITLE_LENGTH = 80
MAX_ERROR_LENGTH = 200

DEFAULT_REPO = "pollinations/pollinations"

TEAM_ROLE_ID = 1447964393148125194

_repo_info_path = os.path.join(os.path.dirname(__file__), "data", "repo_info.txt")
try:
    with open(_repo_info_path, "r", encoding="utf-8") as f:
        REPO_INFO = f.read()
except FileNotFoundError:
    REPO_INFO = "Pollinations.AI - AI media generation platform with image and text generation APIs."

BRIDGE_SYSTEM_PROMPT = ""
BRIDGE_SYSTEM_PROMPT = BRIDGE_SYSTEM_PROMPT.format(repo_info=REPO_INFO)

GITHUB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "github_issue",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform (get, search, create, close, comment, etc.)",
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "Issue number (for get, close, comment, edit, label, assign, etc.)",
                    },
                    "keywords": {
                        "type": "string",
                        "description": "Search terms (for search, find_similar)",
                    },
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "Filter state (for search actions)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Issue title (for create, edit)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Issue body/description (for create)",
                    },
                    "body": {
                        "type": "string",
                        "description": "New body text (for edit)",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment text (for comment, close, reopen)",
                    },
                    "reason": {
                        "type": "string",
                        "enum": ["completed", "not_planned", "duplicate"],
                        "description": "Close reason (for close)",
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels (for label, unlabel, search)",
                    },
                    "assignees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "GitHub usernames (for assign, unassign)",
                    },
                    "milestone": {
                        "type": "string",
                        "description": "Milestone name or 'none' (for milestone)",
                    },
                    "lock": {
                        "type": "boolean",
                        "description": "True to lock, false to unlock (for lock)",
                    },
                    "related_issues": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Related issue numbers (for link)",
                    },
                    "relationship": {
                        "type": "string",
                        "enum": [
                            "duplicate",
                            "related",
                            "blocks",
                            "blocked_by",
                            "parent",
                            "child",
                        ],
                        "description": "Relationship type (for link)",
                    },
                    "discord_username": {
                        "type": "string",
                        "description": "Discord username (for search_user)",
                    },
                    "include_comments": {
                        "type": "boolean",
                        "description": "Include comments (for get)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (for search, find_similar)",
                    },
                    "child_issue_number": {
                        "type": "integer",
                        "description": "Child/sub-issue number (for add_sub_issue, remove_sub_issue)",
                    },
                    "comment_id": {
                        "type": "integer",
                        "description": "Comment ID (for edit_comment, delete_comment) - get from issue comments",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_project",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action: list, view, list_items, get_item, add, remove, set_status, set_field",
                    },
                    "project_number": {
                        "type": "integer",
                        "description": "Project number from URL (e.g., 20 from projects/20). NOT required for action='list'",
                    },
                    "issue_number": {
                        "type": "integer",
                        "description": "Issue number to add/update",
                    },
                    "status": {
                        "type": "string",
                        "description": "Status/column name (e.g., 'Todo', 'In Progress', 'Done')",
                    },
                    "field_name": {
                        "type": "string",
                        "description": "Custom field name (for set_field)",
                    },
                    "field_value": {
                        "type": "string",
                        "description": "Field value to set (for set_field)",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_overview",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "issues_limit": {
                        "type": "integer",
                        "description": "Number of recent issues to include (default 10, max 50)",
                    },
                    "include_projects": {
                        "type": "boolean",
                        "description": "Include projects list (default true)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_custom",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "What data you need in plain English",
                    },
                    "include_body": {
                        "type": "boolean",
                        "description": "Include full body text? (for spam detection, etc.)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max items (default 50, max 100)",
                    },
                },
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_pr",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action: get, list, get_files, get_diff, get_checks, get_commits, get_threads, get_review_comments, get_file_at_ref, request_review, remove_reviewer, approve, request_changes, merge, update, close, reopen, create, convert_to_draft, ready_for_review, update_branch, comment, inline_comment, suggest, resolve_thread, unresolve_thread, enable_auto_merge, disable_auto_merge, review",
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number (for most actions)",
                    },
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "merged", "all"],
                        "description": "Filter state (for list)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (for list, default 10)",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base branch filter (for list, create)",
                    },
                    "title": {
                        "type": "string",
                        "description": "PR title (for create, update)",
                    },
                    "body": {
                        "type": "string",
                        "description": "PR body or review comment (for create, update, approve, request_changes)",
                    },
                    "head": {
                        "type": "string",
                        "description": "Head branch name (for create)",
                    },
                    "draft": {
                        "type": "boolean",
                        "description": "Create as draft (for create)",
                    },
                    "reviewers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "GitHub usernames (for request_review, remove_reviewer)",
                    },
                    "team_reviewers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Team slugs (for request_review, remove_reviewer)",
                    },
                    "merge_method": {
                        "type": "string",
                        "enum": ["merge", "squash", "rebase"],
                        "description": "Merge method (for merge, enable_auto_merge)",
                    },
                    "commit_title": {
                        "type": "string",
                        "description": "Custom merge commit title (for merge)",
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Custom merge commit message (for merge)",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment text (for comment, inline_comment, suggest)",
                    },
                    "post_review_to_github": {
                        "type": "boolean",
                        "description": "Post AI review as GitHub comment? (for review action, default false)",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path for inline comment/suggestion (e.g., 'src/main.py')",
                    },
                    "line": {
                        "type": "integer",
                        "description": "Line number for inline comment/suggestion",
                    },
                    "side": {
                        "type": "string",
                        "enum": ["LEFT", "RIGHT"],
                        "description": "Diff side: LEFT=deletions, RIGHT=additions (default RIGHT)",
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "Suggested code replacement (for suggest action)",
                    },
                    "thread_id": {
                        "type": "string",
                        "description": "Review thread ID (for resolve_thread, unresolve_thread)",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path for get_file_at_ref (e.g., '.github/workflows/ci.yml', 'src/main.py')",
                    },
                    "ref": {
                        "type": "string",
                        "description": "Git ref (branch name, tag, or commit SHA) for get_file_at_ref",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "meaw_agent",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "task",
                            "status",
                            "list_tasks",
                            "ask_user",
                            "push",
                            "open_pr",
                        ],
                        "description": "Action: task (do coding work), push (push to GitHub), open_pr (create PR), status/list_tasks (check progress), ask_user (get user input)",
                    },
                    "task": {
                        "type": "string",
                        "description": "REQUIRED for action='task'. Describe the CODE EDIT to make - what to fix, implement, or modify. Be specific!",
                    },
                    "question": {
                        "type": "string",
                        "description": "Question for ask_user action",
                    },
                    "pr_title": {
                        "type": "string",
                        "description": "PR title (for open_pr)",
                    },
                    "pr_body": {
                        "type": "string",
                        "description": "PR description (for open_pr)",
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository (default: pollinations/pollinations)",
                    },
                },
                "required": ["action"],
            },
        },
    },
]

CODE_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "code_search",
        "description": "",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query describing what code you're looking for",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 10)",
                },
            },
            "required": ["query"],
        },
    },
}

DOC_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "doc_search",
        "description": "",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query describing what documentation you're looking for",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 10)",
                },
            },
            "required": ["query"],
        },
    },
}

NATIVE_GOOGLE_SEARCH = {
    "type": "function",
    "function": {
        "name": "google_search",
    },
}

NATIVE_CODE_EXECUTION = {
    "type": "function",
    "function": {
        "name": "code_execution",
    },
}

NATIVE_URL_CONTEXT = {
    "type": "function",
    "function": {
        "name": "url_context",
    },
}

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query - be specific for better results",
                },
            },
            "required": ["query"],
        },
    },
}

WEB_SCRAPE_TOOL = {
    "type": "function",
    "function": {
        "name": "web_scrape",
        "description": "",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "scrape",
                        "extract",
                        "css_extract",
                        "semantic",
                        "regex",
                        "multi",
                        "fetch_file",
                        "parse_file",
                    ],
                    "description": "Action to perform",
                },
                "url": {
                    "type": "string",
                    "description": "URL to scrape (for URL-based actions)",
                },
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs (for multi action, max 10)",
                },
                "extract": {
                    "type": "string",
                    "description": "LLM extraction instruction (e.g., 'Extract product prices and descriptions')",
                },
                "schema": {
                    "type": "object",
                    "description": "CSS extraction schema: {baseSelector: 'div.item', fields: [{name: 'title', selector: 'h2', type: 'text'}]}",
                },
                "semantic_filter": {
                    "type": "string",
                    "description": "Keywords for semantic/cosine filtering (e.g., 'pricing features')",
                },
                "patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Regex patterns: email, url, phone, date, ip, currency, hashtag, twitter, all",
                },
                "content_filter": {
                    "type": "string",
                    "enum": ["bm25", "pruning"],
                    "description": "Pre-filter content (bm25=keyword relevance, pruning=remove boilerplate)",
                },
                "filter_query": {
                    "type": "string",
                    "description": "Query for content filtering",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["markdown", "fit_markdown", "html"],
                    "description": "Output format (fit_markdown=filtered/cleaner)",
                },
                "js_code": {
                    "type": "string",
                    "description": "JavaScript to execute before extraction (e.g., click buttons, scroll)",
                },
                "wait_for": {
                    "type": "string",
                    "description": "CSS selector to wait for before extraction",
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Include page links in result",
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Include image URLs in result",
                },
                "include_tables": {
                    "type": "boolean",
                    "description": "Extract tables as structured data",
                },
                "screenshot": {
                    "type": "boolean",
                    "description": "Capture screenshot of page",
                },
                "stealth_mode": {
                    "type": "boolean",
                    "description": "Enable stealth to avoid bot detection",
                },
                "simulate_user": {
                    "type": "boolean",
                    "description": "Simulate human behavior (delays, movements)",
                },
                "magic_mode": {
                    "type": "boolean",
                    "description": "Auto anti-bot bypass (stealth + simulation combined)",
                },
                "scan_full_page": {
                    "type": "boolean",
                    "description": "Scroll entire page to load lazy/infinite scroll content",
                },
                "process_iframes": {
                    "type": "boolean",
                    "description": "Extract content from iframes",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for browser reuse (faster repeated scrapes)",
                },
                "file_url": {
                    "type": "string",
                    "description": "Discord attachment URL (for fetch_file action)",
                },
                "file_content": {
                    "type": "string",
                    "description": "Raw file content (for parse_file action)",
                },
                "file_type": {
                    "type": "string",
                    "enum": ["text", "code", "json", "yaml", "log"],
                    "description": "File type hint for parsing",
                },
            },
            "required": ["action"],
        },
    },
}

DISCORD_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "discord_search",
        "description": "",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "messages",
                        "members",
                        "channels",
                        "threads",
                        "roles",
                        "history",
                        "context",
                        "thread_history",
                    ],
                    "description": "What to search",
                },
                "query": {
                    "type": "string",
                    "description": "Search text (required for messages). Mentions auto-parsed.",
                },
                "channel_id": {
                    "type": "integer",
                    "description": "Filter to specific channel",
                },
                "channel_name": {
                    "type": "string",
                    "description": "Find channel by name (alternative to channel_id)",
                },
                "user_id": {
                    "type": "integer",
                    "description": "Filter by author or look up member",
                },
                "role_id": {"type": "integer", "description": "Filter members by role"},
                "role_name": {
                    "type": "string",
                    "description": "Find role by name",
                },
                "message_id": {
                    "type": "integer",
                    "description": "Target message for context action",
                },
                "thread_id": {
                    "type": "integer",
                    "description": "Target thread for thread_history",
                },
                "channel_type": {
                    "type": "string",
                    "enum": ["text", "voice", "forum", "category", "news", "stage"],
                    "description": "Filter channels by type",
                },
                "has": {
                    "type": "string",
                    "enum": ["link", "embed", "file", "video", "image", "sound", "sticker", "poll"],
                    "description": "Filter by attachment type",
                },
                "before": {
                    "type": "string",
                    "description": "Messages before this date/snowflake ID",
                },
                "after": {
                    "type": "string",
                    "description": "Messages after this date/snowflake ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 25, max 100 for history)",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["timestamp", "relevance"],
                    "description": "Sort by time (default) or relevance to query",
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["desc", "asc"],
                    "description": "desc=newest first (default), asc=oldest first",
                },
                "author_type": {
                    "type": "string",
                    "enum": ["user", "bot", "webhook", "-bot"],
                    "description": "Filter by author type. -bot excludes bots.",
                },
                "pinned": {
                    "type": "boolean",
                    "description": "Filter to pinned messages only",
                },
                "link_hostname": {
                    "type": "string",
                    "description": "Filter by URL domain (e.g., 'github.com', 'youtube.com')",
                },
                "attachment_extension": {
                    "type": "string",
                    "description": "Filter by file type (e.g., 'pdf', 'png', 'txt')",
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (max 9975, use with limit for paging)",
                },
                "include_archived": {
                    "type": "boolean",
                    "description": "Include archived threads (default true)",
                },
                "include_members": {
                    "type": "boolean",
                    "description": "Include member list for roles (default false)",
                },
            },
            "required": ["action"],
        },
    },
}

WEB_TOOL = {
    "type": "function",
    "function": {
        "name": "web",
        "description": "",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language request. Examples: 'Find top 10 laptops on Amazon and compare specs', 'Research latest AI news and summarize', 'Scrape this Discord CDN URL and parse the JSON'",
                },
            },
            "required": ["query"],
        },
    },
}


def get_tools_with_embeddings(base_tools: list, embeddings_enabled: bool, doc_embeddings_enabled: bool = False) -> list:
    tools = base_tools.copy()

    tools.append(NATIVE_GOOGLE_SEARCH)
    tools.append(NATIVE_CODE_EXECUTION)
    tools.append(NATIVE_URL_CONTEXT)

    tools.append(WEB_SEARCH_TOOL)
    tools.append(WEB_SCRAPE_TOOL)
    tools.append(DISCORD_SEARCH_TOOL)
    tools.append(WEB_TOOL)

    if embeddings_enabled:
        tools.append(CODE_SEARCH_TOOL)

    if doc_embeddings_enabled:
        tools.append(DOC_SEARCH_TOOL)

    return tools

ADMIN_ACTIONS = {
    "github_issue": {
        "close",
        "reopen",
        "edit",
        "label",
        "unlabel",
        "assign",
        "unassign",
        "milestone",
        "lock",
        "link",
        "create_sub_issue",
        "add_sub_issue",
        "remove_sub_issue",
    },
    "github_pr": {
        "request_review",
        "remove_reviewer",
        "approve",
        "request_changes",
        "merge",
        "update",
        "create",
        "convert_to_draft",
        "ready_for_review",
        "update_branch",
        "inline_comment",
        "suggest",
        "resolve_thread",
        "unresolve_thread",
        "enable_auto_merge",
        "disable_auto_merge",
        "close",
        "reopen",
    },
    "github_project": {"add", "remove", "set_status", "set_field"},
}

def filter_admin_actions_from_tools(tools: list, is_admin: bool) -> list:
    if is_admin:
        return tools

    import copy

    filtered_tools = []

    for tool in tools:
        tool_name = tool.get("function", {}).get("name", "")

        if tool_name == "meaw_agent":
            continue

        if tool_name not in ADMIN_ACTIONS:
            filtered_tools.append(tool)
            continue

        tool_copy = copy.deepcopy(tool)
        description = tool_copy["function"]["description"]

        lines = description.split("\n")
        filtered_lines = [line for line in lines if "[admin]" not in line.lower()]
        tool_copy["function"]["description"] = "\n".join(filtered_lines)

        params = tool_copy["function"].get("parameters", {})
        props = params.get("properties", {})
        action_prop = props.get("action", {})

        if "enum" in action_prop:
            admin_actions = ADMIN_ACTIONS.get(tool_name, set())
            action_prop["enum"] = [
                a for a in action_prop["enum"] if a not in admin_actions
            ]

        filtered_tools.append(tool_copy)

    return filtered_tools

RISKY_ACTIONS = {
    "merge": "merge this PR",
    "close": "close this",
    "delete_branch": "delete this branch",
    "lock": "lock this issue",
}

TOOL_KEYWORDS = {
    "github_issue": re.compile(
        r"\b(issues?|bugs?|reports?|#\d+|problems?|errors?|feature requests?|enhancements?|"
        r"subscrib\w*|labels?|assign\w*|close[ds]?|reopen\w*|milestones?|"
        r"sub.?issues?|child|parent|my issues|duplicates?|similar|ticket)\b",
        re.IGNORECASE,
    ),
    "github_pr": re.compile(
        r"\b(prs?|pull\s*requests?|merge[ds]?|review\w*|approv\w*|diffs?|"
        r"checks?|ci|workflow|drafts?|auto.?merge)\b",
        re.IGNORECASE,
    ),
    "github_project": re.compile(
        r"\b(projects?\s*(board)?|boards?|kanban|sprint|columns?|todo|in\s*progress|done|backlog)\b",
        re.IGNORECASE,
    ),
    "meaw_agent": re.compile(
        r"\b(implement\w*|refactor\w*|coding\s*agent|"
        r"write\s+(the\s+)?(code|function|class|method)|"
        r"edit\s+(the\s+)?(code|file)|modify\s+(the\s+)?(code|file)|"
        r"create\s+(a\s+)?branch|make\s+(a\s+)?branch|new\s+branch|delete\s+branch|"
        r"commit\s+(the\s+)?changes|push\s+(the\s+)?changes|open\s+(a\s+)?pr|"
        r"code\s+this|build\s+this|develop\s+this|"
        r"fix\s+(the\s+)?(bug|issue|error|problem)|"
        r"change\s+(the\s+)?(code|file)|update\s+(the\s+)?(code|file)|"
        r"add\s+(a\s+)?(feature|function|method)|remove\s+(the\s+)?(code|function))\b",
        re.IGNORECASE,
    ),
    "github_custom": re.compile(
        r"\b(stats?|statistics?|activit\w*|stale|spam|health|contributors?|history)\b",
        re.IGNORECASE,
    ),
    "github_overview": re.compile(
        r"\b(overview|summary|show\s*(me\s*)?(the\s*)?repo|what.*(issues|labels|milestones).*exist|"
        r"whats?\s*(in\s*)?the\s*repo|repo\s*(status|info))\b",
        re.IGNORECASE,
    ),
    "web_scrape": re.compile(
        r"\b(scrape|scraping|crawl|fetch\s+(this\s+)?(page|url|website|site|link)|"
        r"read\s+(this\s+)?(page|url|website|article|doc)|"
        r"get\s+(the\s+)?(content|text|data)\s+(from|of)\s+(this\s+)?(url|page|site)|"
        r"extract\s+(from|data)|whats?\s+(on|at)\s+(this\s+)?(url|page|site|link))\b",
        re.IGNORECASE,
    ),
}

def filter_tools_by_intent(
    user_message: str, all_tools: list[dict], is_admin: bool = False
) -> list[dict]:
    matched_tools = set()
    message_lower = user_message.lower()

    for tool_name, pattern in TOOL_KEYWORDS.items():
        if pattern.search(message_lower):
            matched_tools.add(tool_name)

    if not matched_tools:
        return all_tools

    if re.search(r"#\d+", user_message):
        matched_tools.add("github_issue")
        if len(matched_tools) == 1:
            matched_tools.add("github_pr")

    AI_CONTROLLED_TOOLS = {"web_search", "code_search", "discord_search"}
    if is_admin:
        AI_CONTROLLED_TOOLS.add("meaw_agent")

    filtered = [
        tool
        for tool in all_tools
        if tool.get("function", {}).get("name") in matched_tools
        or tool.get("function", {}).get("name") in AI_CONTROLLED_TOOLS
    ]

    return filtered if filtered else all_tools

TOOL_SYSTEM_PROMPT = ""
ADMIN_TOOLS_SECTION = "- `github_overview` - Repo summary (issues, labels, milestones, projects)\n- `github_issue` - Issues: get, search, create, comment, close, label, assign\n- `github_pr` - PRs: get, list, review, approve, merge, inline comments\n- `github_project` - Projects V2: list, view, add items, set status\n- `meaw_agent` - **Code agent** (implement, edit code, create branches, PRs)\n- `github_custom` - Raw data (commits, history, stats)\n- `web_search` - Web search with reasoning (Perplexity)\n- `web_scrape` - Full Crawl4AI: scrape, extract, css_extract (fast!), semantic, regex, fetch_file (Discord attachments)\n- `code_search` - Semantic code search\n- `doc_search` - Documentation search (enter.pollinations.ai, kpi.myceli.ai, gsoc.pollinations.ai)\n- `discord_search` - Search Discord server (messages, members, channels, threads, roles)"
NON_ADMIN_TOOLS_SECTION = "- `github_overview` - Repo summary (issues, labels, milestones, projects)\n- `github_issue` - Issues: get, search, create, comment (read + create only)\n- `github_pr` - PRs: get, list, comment (read-only)\n- `github_project` - Projects V2: list, view (read-only)\n- `github_custom` - Raw data (commits, history, stats)\n- `web_search` - Web search with reasoning (Perplexity)\n- `web_scrape` - Full Crawl4AI: scrape, extract, css_extract (fast!), semantic, regex, fetch_file (Discord attachments)\n- `code_search` - Semantic code search\n- `doc_search` - Documentation search (enter.pollinations.ai, kpi.myceli.ai, gsoc.pollinations.ai)\n- `discord_search` - Search Discord server (messages, members, channels, threads, roles)"
meaw_AGENT_SECTION = ""

def get_tool_system_prompt(is_admin: bool = True) -> str:
    from datetime import datetime, timezone

    current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if is_admin:
        tools_section = ADMIN_TOOLS_SECTION
        meaw_agent_section = meaw_AGENT_SECTION
    else:
        tools_section = NON_ADMIN_TOOLS_SECTION
        meaw_agent_section = ""

    return TOOL_SYSTEM_PROMPT.format(
        repo_info=REPO_INFO,
        current_utc=current_utc,
        tools_section=tools_section,
        meaw_agent_section=meaw_agent_section,
    )

TOOL_SYSTEM_PROMPT_STATIC = TOOL_SYSTEM_PROMPT.format(
    repo_info=REPO_INFO,
    current_utc="[dynamic]",
    tools_section=ADMIN_TOOLS_SECTION,
    meaw_agent_section=meaw_AGENT_SECTION,
)

CONVERSATION_SYSTEM_PROMPT = BRIDGE_SYSTEM_PROMPT


