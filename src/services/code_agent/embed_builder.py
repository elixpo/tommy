"""
Discord embed builder for code task progress updates.

Creates a single embed that updates in real-time with:
- Task header (issue title, PR title, etc.)
- Checklist of steps (✅ 🔄 ⬜)
- Current status message
- Footer with elapsed time
- Close Terminal button (for thread-based tasks)
"""

import asyncio
import discord
from discord.ui import View, Button
from datetime import datetime
from typing import Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CLOSE TERMINAL BUTTON VIEW
# =============================================================================

# Type for the callback function
CloseTerminalCallback = Callable[[str], Awaitable[bool]]


class CloseTerminalView(View):
    """
    Discord View with a "Close Terminal" button.

    Only the user who started the terminal (owner_user_id) can click the button.
    This view is added to the final task completion embed when there are git changes.
    """

    def __init__(
        self,
        thread_id: str,
        owner_user_id: int,
        close_callback: CloseTerminalCallback,
        timeout: Optional[float] = None,  # No timeout - button stays forever
    ):
        """
        Args:
            thread_id: Discord thread ID (the universal key)
            owner_user_id: Discord user ID who started the terminal (only they can close it)
            close_callback: Async function to call when closing: callback(thread_id) -> success
            timeout: Optional timeout for the view (None = no timeout)
        """
        super().__init__(timeout=timeout)
        self.thread_id = thread_id
        self.owner_user_id = owner_user_id
        self.close_callback = close_callback
        self._closed = False

    @discord.ui.button(
        label="Close Terminal",
        style=discord.ButtonStyle.secondary,
        emoji="🔒",
        custom_id="close_terminal",
    )
    async def close_terminal_button(
        self, interaction: discord.Interaction, button: Button
    ):
        """Handle the Close Terminal button click."""
        # Verify user is the owner
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message(
                f"Only <@{self.owner_user_id}> can close this terminal session.",
                ephemeral=True,
            )
            return

        # Already closed?
        if self._closed:
            await interaction.response.send_message(
                "Terminal session already closed.",
                ephemeral=True,
            )
            return

        # Defer response (closing might take a moment)
        await interaction.response.defer(ephemeral=True)

        try:
            # Call the close callback
            success = await self.close_callback(self.thread_id)

            if success:
                self._closed = True
                # Disable the button
                button.disabled = True
                button.label = "Terminal Closed"
                button.emoji = "✅"
                await interaction.message.edit(view=self)

                await interaction.followup.send(
                    "Terminal session closed successfully.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "Failed to close terminal session. It may already be closed.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error closing terminal {self.thread_id}: {e}")
            await interaction.followup.send(
                f"Error closing terminal: {str(e)[:100]}",
                ephemeral=True,
            )


# Type for reset stale callback
ResetStaleCallback = Callable[[str], None]


class StaleTerminalView(View):
    """
    Discord View for stale terminal notification.

    Shown after 1 hour of inactivity to ask user if they want to keep or close.
    """

    def __init__(
        self,
        thread_id: str,
        owner_user_id: int,
        close_callback: CloseTerminalCallback,
        reset_stale_callback: Optional[ResetStaleCallback] = None,
        timeout: float = 3600,  # 1 hour timeout for this notification
    ):
        super().__init__(timeout=timeout)
        self.thread_id = thread_id
        self.owner_user_id = owner_user_id
        self.close_callback = close_callback
        self.reset_stale_callback = reset_stale_callback
        self._handled = False

    @discord.ui.button(
        label="Keep Open",
        style=discord.ButtonStyle.primary,
        emoji="▶️",
        custom_id="keep_terminal",
    )
    async def keep_terminal_button(
        self, interaction: discord.Interaction, button: Button
    ):
        """User wants to keep the terminal open."""
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message(
                f"Only <@{self.owner_user_id}> can manage this terminal.",
                ephemeral=True,
            )
            return

        if self._handled:
            await interaction.response.send_message(
                "Already handled.",
                ephemeral=True,
            )
            return

        self._handled = True

        # Reset the stale notification flag so user gets notified again after another hour
        if self.reset_stale_callback:
            self.reset_stale_callback(self.thread_id)

        # Disable buttons
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"<@{self.owner_user_id}> Terminal kept open. Will check again in 1 hour.",
            view=self,
        )

    @discord.ui.button(
        label="Close Terminal",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_stale_terminal",
    )
    async def close_terminal_button(
        self, interaction: discord.Interaction, button: Button
    ):
        """User wants to close the terminal."""
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message(
                f"Only <@{self.owner_user_id}> can manage this terminal.",
                ephemeral=True,
            )
            return

        if self._handled:
            await interaction.response.send_message(
                "Already handled.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            success = await self.close_callback(self.thread_id)
            self._handled = True

            # Disable buttons
            for child in self.children:
                child.disabled = True

            if success:
                await interaction.message.edit(
                    content=f"<@{self.owner_user_id}> Terminal session closed.",
                    view=self,
                )
            else:
                await interaction.message.edit(
                    content=f"<@{self.owner_user_id}> Failed to close terminal (may already be closed).",
                    view=self,
                )

        except Exception as e:
            logger.error(f"Error closing stale terminal {self.thread_id}: {e}")
            await interaction.followup.send(
                f"Error: {str(e)[:100]}",
                ephemeral=True,
            )

    async def on_timeout(self):
        """Called when the view times out (after 1 hour of no interaction)."""
        # The stale check loop will handle re-notifying
        pass


# =============================================================================
# PROGRESS EMBED - CLAUDE CODE STYLE
# =============================================================================

class StepStatus(Enum):
    """Status of a todo item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TodoItem:
    """A todo item in the progress list."""
    content: str
    status: StepStatus = StepStatus.PENDING

    def to_string(self) -> str:
        """Convert to Claude Code style string."""
        # Claude Code style: ☐ pending, ◉ in progress, ✓ done, ✗ failed
        emoji_map = {
            StepStatus.PENDING: "☐",
            StepStatus.IN_PROGRESS: "◉",
            StepStatus.COMPLETED: "✓",
            StepStatus.FAILED: "✗",
        }
        emoji = emoji_map.get(self.status, "☐")
        return f"{emoji} {self.content}"


@dataclass
class ProgressEmbed:
    """
    Claude Code-style progress embed.

    Minimal design:
    - Title: Current action with spinner (✻ Working on X...)
    - Body: Todo list (☐ pending, ◉ in progress, ✓ done)
    - Footer: Elapsed time only

    Usage:
        embed = ProgressEmbed(current_action="Analyzing code")
        embed.add_todo("Read the file")
        embed.add_todo("Make changes")
        embed.add_todo("Run tests")

        embed.complete_todo(0)
        embed.start_todo(1)
        embed.set_action("Making changes")

        discord_embed = embed.build()
    """

    current_action: str = "Working..."
    todos: List[TodoItem] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    color: int = 0x5865F2  # Discord blurple

    # State
    is_complete: bool = False
    is_failed: bool = False

    # Legacy compatibility
    title: str = ""
    description: str = ""
    status_message: str = ""
    issue_url: Optional[str] = None
    pr_url: Optional[str] = None
    repo_url: Optional[str] = None

    @property
    def steps(self) -> List[TodoItem]:
        """Alias for todos (backward compatibility)."""
        return self.todos

    def add_todo(self, content: str) -> int:
        """Add a todo item. Returns index."""
        self.todos.append(TodoItem(content=content))
        return len(self.todos) - 1

    def add_step(self, name: str, details: Optional[str] = None) -> int:
        """Backward compatible alias for add_todo."""
        return self.add_todo(name)

    def start_todo(self, index: int):
        """Mark a todo as in progress and update current action."""
        if 0 <= index < len(self.todos):
            self.todos[index].status = StepStatus.IN_PROGRESS
            self.current_action = self.todos[index].content

    def start_step(self, index: int, details: Optional[str] = None):
        """Backward compatible alias."""
        self.start_todo(index)

    def complete_todo(self, index: int):
        """Mark a todo as completed."""
        if 0 <= index < len(self.todos):
            self.todos[index].status = StepStatus.COMPLETED

    def complete_step(self, index: int, details: Optional[str] = None):
        """Backward compatible alias."""
        self.complete_todo(index)

    def fail_todo(self, index: int):
        """Mark a todo as failed."""
        if 0 <= index < len(self.todos):
            self.todos[index].status = StepStatus.FAILED

    def fail_step(self, index: int, details: Optional[str] = None):
        """Backward compatible alias."""
        self.fail_todo(index)

    def skip_step(self, index: int, details: Optional[str] = None):
        """Mark as completed (no skip in Claude Code style)."""
        self.complete_todo(index)

    def set_action(self, action: str):
        """Set the current action shown in title."""
        self.current_action = action

    def set_status(self, message: str):
        """Backward compatible - sets current action."""
        self.current_action = message

    def mark_complete(self, success: bool = True):
        """Mark the task as complete."""
        self.is_complete = True
        self.is_failed = not success
        self.color = 0x57F287 if success else 0xED4245  # Green or red

    def elapsed_time(self) -> str:
        """Get formatted elapsed time."""
        seconds = int((datetime.utcnow() - self.started_at).total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        secs = seconds % 60
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"

    def _get_title(self) -> str:
        """Build the title with spinner/status."""
        if self.is_complete:
            emoji = "✓" if not self.is_failed else "✗"
            status = "Done" if not self.is_failed else "Failed"
            return f"{emoji} {status}"
        else:
            # Spinner + current action
            return f"✻ {self.current_action}…"

    def build(self) -> discord.Embed:
        """Build the Discord embed object."""
        embed = discord.Embed(
            title=self._get_title(),
            color=self.color,
        )

        # Todo list as description (cleaner than fields)
        if self.todos:
            todo_lines = [todo.to_string() for todo in self.todos]
            embed.description = "\n".join(todo_lines)

        # Minimal footer - just time
        embed.set_footer(text=f"⏱ {self.elapsed_time()}")

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
        title: str = "",
        description: str = "",
        issue_url: Optional[str] = None,
        repo_url: Optional[str] = None,
        current_action: str = "Starting...",
    ) -> discord.Message:
        """Create and send the initial embed."""
        self.embed = ProgressEmbed(
            current_action=current_action or title or "Working...",
        )

        discord_embed = self.embed.build()
        self.message = await self.channel.send(embed=discord_embed)
        return self.message

    def set_action(self, action: str):
        """Set the current action (shown in title)."""
        if self.embed:
            self.embed.set_action(action)

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

    async def finish(
        self,
        success: bool = True,
        final_status: Optional[str] = None,
        view: Optional[View] = None,
    ):
        """
        Mark complete and do final update.

        Args:
            success: Whether task completed successfully
            final_status: Final status message to display
            view: Optional Discord View (e.g., CloseTerminalView) to attach to the message
        """
        if self.embed:
            self.embed.mark_complete(success)
            if final_status:
                self.embed.set_status(final_status)

        if not self.message or not self.embed:
            return

        async with self._update_lock:
            try:
                discord_embed = self.embed.build()
                if view:
                    await self.message.edit(embed=discord_embed, view=view)
                else:
                    await self.message.edit(embed=discord_embed)
                self._last_update = datetime.utcnow()
            except discord.HTTPException as e:
                logger.warning(f"Failed to finish embed: {e}")
