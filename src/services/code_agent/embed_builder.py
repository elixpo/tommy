"""
Discord embed builder for code task progress updates.

Creates a single embed that updates in real-time with:
- Task header (issue title, PR title, etc.)
- Checklist of steps (✅ 🔄 ⬜)
- Current status message
- Footer with elapsed time
"""

import asyncio
import discord
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging


class StepStatus(Enum):
    """Status of a checklist step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ChecklistStep:
    """A step in the progress checklist."""
    name: str
    status: StepStatus = StepStatus.PENDING
    details: Optional[str] = None

    def to_string(self) -> str:
        """Convert step to Discord-friendly string."""
        emoji_map = {
            StepStatus.PENDING: "⬜",
            StepStatus.IN_PROGRESS: "🔄",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
            StepStatus.SKIPPED: "⏭️",
        }
        emoji = emoji_map.get(self.status, "⬜")
        text = f"{emoji} {self.name}"
        if self.details:
            text += f"\n   └ {self.details}"
        return text


@dataclass
class ProgressEmbed:
    """
    Builder for Discord progress embeds.

    Usage:
        embed = ProgressEmbed(
            title="Fixing Issue #5735",
            description="URL encoding breaks with % characters"
        )
        embed.add_step("Analyze issue")
        embed.add_step("Find root cause")
        embed.add_step("Apply fix")
        embed.add_step("Run tests")
        embed.add_step("Create PR")

        # Update as work progresses
        embed.complete_step(0)
        embed.start_step(1)
        embed.set_status("Found bug in getImageURL.js")

        # Get Discord embed object
        discord_embed = embed.build()
    """

    title: str
    description: str = ""
    steps: List[ChecklistStep] = field(default_factory=list)
    status_message: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    color: int = 0x5865F2  # Discord blurple

    # Links
    issue_url: Optional[str] = None
    pr_url: Optional[str] = None
    repo_url: Optional[str] = None

    # State
    is_complete: bool = False
    is_failed: bool = False

    def add_step(self, name: str, details: Optional[str] = None) -> int:
        """Add a step to the checklist. Returns step index."""
        step = ChecklistStep(name=name, details=details)
        self.steps.append(step)
        return len(self.steps) - 1

    def start_step(self, index: int, details: Optional[str] = None):
        """Mark a step as in progress."""
        if 0 <= index < len(self.steps):
            self.steps[index].status = StepStatus.IN_PROGRESS
            if details:
                self.steps[index].details = details

    def complete_step(self, index: int, details: Optional[str] = None):
        """Mark a step as completed."""
        if 0 <= index < len(self.steps):
            self.steps[index].status = StepStatus.COMPLETED
            if details:
                self.steps[index].details = details

    def fail_step(self, index: int, details: Optional[str] = None):
        """Mark a step as failed."""
        if 0 <= index < len(self.steps):
            self.steps[index].status = StepStatus.FAILED
            if details:
                self.steps[index].details = details

    def skip_step(self, index: int, details: Optional[str] = None):
        """Mark a step as skipped."""
        if 0 <= index < len(self.steps):
            self.steps[index].status = StepStatus.SKIPPED
            if details:
                self.steps[index].details = details

    def set_status(self, message: str):
        """Set the current status message."""
        self.status_message = message

    def mark_complete(self, success: bool = True):
        """Mark the entire task as complete."""
        self.is_complete = True
        self.is_failed = not success
        self.color = 0x57F287 if success else 0xED4245  # Green or red

    def elapsed_time(self) -> str:
        """Get formatted elapsed time."""
        seconds = int((datetime.utcnow() - self.started_at).total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        seconds = seconds % 60
        if minutes < 60:
            return f"{minutes}m {seconds}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"

    def _get_status_emoji(self) -> str:
        """Get emoji for current overall status."""
        if self.is_complete:
            return "✅" if not self.is_failed else "❌"
        if self.is_failed:
            return "❌"
        # Check if any step is in progress
        for step in self.steps:
            if step.status == StepStatus.IN_PROGRESS:
                return "🔄"
        return "🔧"

    def build(self) -> discord.Embed:
        """Build the Discord embed object."""
        # Title with status emoji
        status_emoji = self._get_status_emoji()
        embed = discord.Embed(
            title=f"{status_emoji} {self.title}",
            description=self.description,
            color=self.color,
            timestamp=self.started_at
        )

        # Checklist
        if self.steps:
            checklist_text = "\n".join(step.to_string() for step in self.steps)
            embed.add_field(
                name="Progress",
                value=checklist_text[:1024],  # Discord field limit
                inline=False
            )

        # Current status message
        if self.status_message:
            embed.add_field(
                name="Status",
                value=f"💬 {self.status_message[:500]}",
                inline=False
            )

        # Links
        links = []
        if self.issue_url:
            links.append(f"[Issue]({self.issue_url})")
        if self.pr_url:
            links.append(f"[PR]({self.pr_url})")
        if self.repo_url:
            links.append(f"[Repo]({self.repo_url})")
        if links:
            embed.add_field(
                name="Links",
                value=" | ".join(links),
                inline=False
            )

        # Footer with elapsed time
        status_text = "Working" if not self.is_complete else ("Done" if not self.is_failed else "Failed")
        embed.set_footer(text=f"⏱️ {self.elapsed_time()} | {status_text}")

        return embed


class ProgressEmbedManager:
    """
    Manages a progress embed with Discord message updates.

    Usage:
        manager = ProgressEmbedManager(channel)
        await manager.start(title="Fixing Issue #5735", description="Bug in URL encoding")

        manager.add_step("Analyze")
        manager.add_step("Fix")
        manager.add_step("Test")
        await manager.update()

        manager.complete_step(0)
        manager.start_step(1)
        manager.set_status("Found the bug!")
        await manager.update()
    """

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.message: Optional[discord.Message] = None
        self.embed: Optional[ProgressEmbed] = None
        self._update_lock = asyncio.Lock()
        self._last_update: datetime = datetime.utcnow()
        self._min_update_interval = 1.0  # Minimum seconds between updates

    async def start(
        self,
        title: str,
        description: str = "",
        issue_url: Optional[str] = None,
        repo_url: Optional[str] = None,
    ) -> discord.Message:
        """Create and send the initial embed."""
        self.embed = ProgressEmbed(
            title=title,
            description=description,
            issue_url=issue_url,
            repo_url=repo_url,
        )

        discord_embed = self.embed.build()
        self.message = await self.channel.send(embed=discord_embed)
        return self.message

    def add_step(self, name: str, details: Optional[str] = None) -> int:
        """Add a step. Returns step index."""
        if self.embed:
            return self.embed.add_step(name, details)
        return -1

    def start_step(self, index: int, details: Optional[str] = None):
        """Mark step as in progress."""
        if self.embed:
            self.embed.start_step(index, details)

    def complete_step(self, index: int, details: Optional[str] = None):
        """Mark step as completed."""
        if self.embed:
            self.embed.complete_step(index, details)

    def fail_step(self, index: int, details: Optional[str] = None):
        """Mark step as failed."""
        if self.embed:
            self.embed.fail_step(index, details)

    def set_status(self, message: str):
        """Set status message."""
        if self.embed:
            self.embed.set_status(message)

    def set_pr_url(self, url: str):
        """Set the PR URL."""
        if self.embed:
            self.embed.pr_url = url

    def mark_complete(self, success: bool = True):
        """Mark task as complete."""
        if self.embed:
            self.embed.mark_complete(success)

    async def update(self, force: bool = False):
        """
        Update the Discord message with current embed state.

        Throttles updates to avoid rate limiting.
        """
        if not self.message or not self.embed:
            return

        async with self._update_lock:
            # Throttle updates
            now = datetime.utcnow()
            elapsed = (now - self._last_update).total_seconds()
            if not force and elapsed < self._min_update_interval:
                return

            try:
                discord_embed = self.embed.build()
                await self.message.edit(embed=discord_embed)
                self._last_update = now
            except discord.HTTPException as e:
                # Log but don't crash on rate limits
                logging.getLogger(__name__).warning(f"Failed to update embed: {e}")

    async def finish(self, success: bool = True, final_status: Optional[str] = None):
        """Mark complete and do final update."""
        if self.embed:
            self.embed.mark_complete(success)
            if final_status:
                self.embed.set_status(final_status)
        await self.update(force=True)
