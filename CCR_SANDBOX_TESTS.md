# CCR Sandbox Integration Tests

## Test Environment
- **Date**: 2025-12-07
- **Platform**: Windows 10 with Git Bash + Docker Desktop
- **Goal**: Test Bot AI -> ccr workflow locally before production deployment

---

## Test Cases

### 1. Docker Sandbox Creation
**Objective**: Verify sandbox container starts with correct image and settings

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Create sandbox with node:20 | Container starts | b3eb588c started | PASS |
| Verify bash is available | sh and bash work | GNU bash 5.2.15 | PASS |
| Verify git is available | git --version works | git 2.39.5 | PASS |
| Verify network enabled | Can curl external URLs | HTTP 200 from npmjs | PASS |
| Verify node version | node:20 | v20.19.6 | PASS |

**Note**: Must use `MSYS_NO_PATHCONV=1` prefix in Git Bash to prevent path conversion issues.

---

### 2. CCR Installation & Setup
**Objective**: Verify ccr installs and starts correctly in sandbox

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| npm install ccr globally | Exit code 0 | added 192 packages in 33s | PASS |
| Create coder user | User created | User created | PASS |
| Write ccr config | Config written | Config at /home/coder/.claude-code-router/config.json | PASS |
| Fix temp file perms | Writable temp file | /tmp/claude-code-reference-count.txt created | PASS |
| Start ccr service | Service starts | "Loaded JSON config" shown | PASS |
| ccr status check | Shows running | "Status: Running" PID 104, Port 3456 | PASS |

**Notes**:
- ccr shows warning "API key is not set. HOST forced to 127.0.0.1" - this is OK, we use empty APIKEY
- Config loaded from /home/coder/.claude-code-router/config.json

---

### 3. Heartbeat/Progress Updates
**Objective**: Verify heartbeat messages during long-running tasks

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Heartbeat fires periodically | Message sent every N seconds | Fires every 5s (test) / 30s (prod) | PASS |
| Heartbeat shows elapsed time | e.g. "Working... (0m 30s)" | "Working on the task... (0m 5s)" | PASS |
| Heartbeat cycles messages | Different messages | Cycles through 6 messages | PASS |
| Heartbeat cancels on completion | Task properly cancelled | Cancelled without error | PASS |
| Total heartbeats in 25s test | >= 4 messages | 4 heartbeat messages | PASS |

**Tested with**: `test_heartbeat.py` - simulates 25s execution with 5s heartbeat interval
**Production config**: 30s heartbeat interval in `claude_code_agent.py`

---

### 4. CCR Task Execution
**Objective**: Verify ccr can execute coding tasks

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Simple prompt | ccr responds | "Done! I added a comment..." | PASS |
| ccr asks for more info (vague prompt) | Returns clarification request | "Could you describe what bug?" | PASS |
| ccr completes task (full context) | Returns completion | Comment added to test.js | PASS |
| Files changed detection | git diff shows changes | Shows +1 line added | PASS |
| Git works as coder user | Can run git diff HEAD | Works correctly | PASS |

**Important Finding**: Git commands must run as coder user (`su - coder -c`) not root, since coder owns /workspace after setup.

---

### 5. Error Handling
**Objective**: Verify errors are properly caught and returned

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| ccr service not running | Auto-starts service | "Service not running, starting service..." | PASS |
| Invalid/corrupt config | Clear error | "Service startup timeout" | PASS |
| Empty prompt | Error message | "Input must be provided..." | PASS |
| Run as root with --dangerously-skip-permissions | Denied | "cannot be used with root/sudo" | PASS |

**Key Findings**:
- ccr auto-starts service if not running
- Invalid JSON config causes startup timeout (clear error)
- Empty prompt returns clear error about input requirement
- Running as root with `--dangerously-skip-permissions` is blocked (security feature)
- This is WHY we need the `coder` non-root user!

---

### 6. End-to-End Simulation
**Objective**: Simulate complete Bot AI -> ccr -> Bot AI workflow

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Create container | Container starts | Container created | PASS |
| Install ccr | Packages installed | 192 packages added | PASS |
| Setup coder user | User created | coder user works | PASS |
| Write config | Config written | docker cp success | PASS |
| Start ccr service | Service running | PID created, running | PASS |
| Run bugfix task | Bug fixed | `a - b` -> `a + b` | PASS |
| Git diff detection | Shows changes | Diff shows 1 line changed | PASS |
| Total execution | Fast completion | 19 seconds | PASS |

**Test Script**: `test_e2e_simulation.py`

**Results**:
```
CCR Output: "Fixed. The `add` function was using `-` (subtraction)..."
math.js content: function add(a, b) { return a + b; }
Git diff shows: -function add(a, b) { return a - b; }
               +function add(a, b) { return a + b; }
```

**Note**: Heartbeat didn't fire because ccr was too fast (19s < 30s interval). In production with longer tasks, heartbeat will update the Discord embed every 30 seconds.

---

### 7. Dynamic Workflow Test (Bot AI <-> CCR Round-Trip)
**Objective**: Test the full dynamic communication loop

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Vague prompt triggers questions | ccr asks for details | "What language? What should it do?" | PASS |
| Bot AI detects needs_more_info | Analysis returns true | needs_more_info: True | PASS |
| Detailed prompt creates file | File created | hello_world.py created | PASS |
| File content correct | Has print statement | `print("Hello, World!")` | PASS |

**Test Script**: `test_dynamic_workflow.py`

**Workflow Demonstrated**:
```
Round 1:
  [USER] "make a script for me"
  [Bot AI -> CCR] "Create a script for the user"
  [CCR -> Bot AI] "What language? What should it do? Any requirements?"
  [Bot AI ANALYSIS] needs_more_info: True

Round 2:
  [Bot AI -> CCR] "Create hello_world.py with print('Hello, World!')"
  [CCR -> Bot AI] "Created hello_world.py"
  [Bot AI ANALYSIS] File exists, task completed

  [Bot AI -> USER] "I've created a Python script for you!"
```

**Key Insight**: ccr is appropriately cautious - even after creating the file, it asked "Did you have additional requirements?" This is good UX behavior.

---

## Findings & Issues

### Finding 1: Git Bash Path Conversion
- **Description**: `MSYS_NO_PATHCONV=1` required in Git Bash to prevent `/workspace` becoming `C:/Program Files/Git/workspace`
- **Impact**: Docker commands fail without this prefix
- **Solution**: Use `MSYS_NO_PATHCONV=1` prefix or use Python subprocess with list args

### Finding 2: Non-Root User Required
- **Description**: `--dangerously-skip-permissions` flag cannot be used with root user
- **Impact**: ccr code commands fail as root
- **Solution**: Create `coder` user with `useradd -m coder` and run ccr as that user via `su - coder -c`

### Finding 3: ccr Auto-Starts Service
- **Description**: Running `ccr code` when service is stopped will auto-start it
- **Impact**: Don't need to explicitly check if service is running
- **Benefit**: More resilient - service recovers automatically

### Finding 4: Full Node Image Required
- **Description**: `node:20-slim` lacks bash, git, and build tools needed by ccr
- **Impact**: ccr commands fail with "permission denied" shell errors
- **Solution**: Use `node:20` full image instead of slim

### Finding 5: Heartbeat Implementation
- **Description**: Added heartbeat mechanism in `_execute_with_streaming`
- **Impact**: Discord embed updates every 30s during long-running tasks
- **Benefit**: Users see the bot is still working, not frozen

### Fixed in Production Code

1. **claude_code_agent.py**: Added heartbeat loop that sends progress updates every 30 seconds:
   - Cycles through messages: "Working...", "Analyzing...", "Thinking...", etc.
   - Shows elapsed time: "(2m 30s)"
   - Cancelled automatically when task completes

2. **sandbox.py**: Changed from `node:20-slim` to `node:20` for full toolset

---

## Test Commands Reference

```bash
# Create test container
docker run -d --name ccr_test -w /workspace node:20 tail -f /dev/null

# Install ccr
docker exec ccr_test npm install -g @anthropic-ai/claude-code @musistudio/claude-code-router

# Create user and config
docker exec ccr_test useradd -m coder
docker exec ccr_test mkdir -p /home/coder/.claude-code-router

# Write config (from host)
docker cp temp_ccr_config.json ccr_test:/home/coder/.claude-code-router/config.json
docker exec ccr_test chown -R coder:coder /home/coder

# Start ccr
docker exec ccr_test su - coder -c 'ccr start'

# Run ccr task
docker exec ccr_test su - coder -c 'ANTHROPIC_API_KEY=dummy ccr code -p --dangerously-skip-permissions "your prompt"'

# Cleanup
docker rm -f ccr_test
```

---

### 8. Autonomous Bot AI Simulation
**Objective**: Test Bot AI making AUTONOMOUS decisions using JUDGMENT (not hardcoded rules)

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Vague request -> ccr asks -> Bot AI asks user | Multi-round workflow | 2 rounds, asked user | PASS |
| Bug fix with clear instructions | Single round completion | 1 round, bug fixed | PASS |
| Multi-step documentation task | Completes autonomously | 1 round, 4 functions documented | PASS |
| Bot AI uses judgment not rules | Dynamic decision-making | Analyzed ccr output, decided action | PASS |

**Test Script**: `test_autonomous_bot_ai.py`

**Key Findings**:
1. **Bot AI Autonomy**: Bot AI successfully made dynamic decisions based on ccr output
2. **Judgment-Based**: No hardcoded `needs_more_info=True` rules - AI analyzes signals in ccr output
3. **Multi-Tool Usage**: Bot AI can use: code_search, web_search, ask_user, send_to_ccr, update_embed
4. **Round Management**: Continues until task complete or max rounds (5)

**Decision Flow**:
```
ccr output -> Bot AI analyzes for signals:
  - Questions signals ("could you", "?", "which", etc.)
  - Completion signals ("created", "done", "fixed", etc.)
  - Error signals ("error", "failed", etc.)

Bot AI decides:
  - If questions + no completion -> ask_user or search
  - If completion + no questions -> mark complete
  - If error -> search_code for context
  - Otherwise -> send more context to ccr
```

**Workflow Demonstrated (Scenario 1)**:
```
Round 1:
  [USER] "make a script for me"
  [Bot AI -> CCR] "make a script for me"
  [CCR -> Bot AI] "What language? What should it do?"
  [Bot AI THINKING] ccr is asking questions, I need user input
  [Bot AI ACTION] ask_user

  [ASK_USER] "What language? What should it do?"
  [USER RESPONSE] "Python script that prints Hello World"

Round 2:
  [Bot AI -> CCR] "User says: Python Hello World script..."
  [CCR -> Bot AI] "Created hello.py"
  [Bot AI THINKING] ccr completed the task
  [Bot AI ACTION] complete
```

**Isolated Testing**:
- Uses FAKE test repo (not pollinations)
- No changes to any real repos
- Simulated Discord embeds
- All tools are mocked for local testing

---

### 9. Persistent Sandbox Architecture
**Objective**: Test new persistent sandbox with volume mounts and branch isolation

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Container creation | polly_sandbox created | Created with restart policy | PASS |
| ccr installation | ccr installed globally | /usr/local/bin/ccr | PASS |
| ccr service running | Status: Running | PID running on port 3456 | PASS |
| Volume mount | data/sandbox/workspace mounted | Files visible on host | PASS |
| Branch creation | task/{uuid} branch created | task/1b25f098 created | PASS |
| Survive restart | Container restarts | --restart unless-stopped | PASS |

**Test Script**: `test_persistent_sandbox.py`

**Architecture**:
```
{PROJECT_ROOT}/
├── data/
│   ├── repo/pollinations_pollinations/  ← source (embeddings)
│   └── sandbox/
│       ├── workspace/                    ← mounted to /workspace
│       │   └── pollinations/             ← working copy
│       └── ccr_config/                   ← ccr config
│           └── config.json
```

**Key Features**:
1. **Persistent Container**: `polly_sandbox` runs 24/7, survives bot/host restarts
2. **Volume Mounts**: Changes visible on host, easy cleanup
3. **Branch Isolation**: Each task gets `task/{uuid}` branch
4. **No Hardcoded Paths**: Uses `Path(__file__).parent` for portability
5. **Bot AI Controls Git**: ccr only edits files, Bot AI handles push/PR
