# CloneAI Fixes Summary

## Date: October 16, 2025

### Issues Fixed

#### 1. **Command Parameter Quoting Issue** ✅

**Problem:**
- Commands with multi-word parameter values were failing with "Unexpected positional argument" errors
- Example: `calendar:create title:Meeting with John` would split into `title:Meeting`, `with`, `John`

**Root Cause:**
- The LLM was generating commands without quotes around multi-word values
- `shlex.split()` in the parser correctly handles quotes, but the commands weren't quoted

**Solution:**
- Updated `agent/tools/tiered_planner.py` to include explicit quoting rules in the LLM prompt
- Added detailed examples showing CORRECT vs WRONG formatting:
  ```
  CORRECT: title:"Meeting with John" body:"Thank you for your message"
  WRONG: title:Meeting with John body:Thank you for your message
  ```

**Files Changed:**
- `agent/tools/tiered_planner.py` (lines ~317-330)

---

#### 2. **Calendar Workflow Parameter Mismatch** ✅

**Problem:**
- `calendar:create` was failing with: `create_calendar_event() got an unexpected keyword argument 'title'`

**Root Cause:**
- The workflow handler was passing `title=title` to the function
- But `create_calendar_event()` expects `summary` (not `title`)
- Also was passing `duration` instead of `duration_minutes`

**Solution:**
- Fixed parameter mapping in `calendar_create_handler`:
  ```python
  return create_calendar_event(
      summary=title,           # Changed from title=title
      start_time=start,
      end_time=end,
      duration_minutes=duration if duration else 60,  # Changed from duration=duration
      location=location,
      description=description
  )
  ```

**Files Changed:**
- `agent/workflows/calendar.py` (lines ~62-69)

---

### New Features Added

#### 3. **System Management Commands** 🆕

Created new system commands for managing CloneAI state and Ollama:

**a) `system:clear`**
- Clears Ollama model context by stopping and restarting the model
- Usage: `clai do system:clear`

**b) `system:clear-history`**
- Clears command history (requires confirmation)
- Usage: `clai do system:clear-history confirm:yes`

**c) `system:status`**
- Shows system status including:
  - Ollama connection status
  - Available models
  - Command history count
  - Credential files status
  - Generated workflows count
- Usage: `clai do system:status`

**d) `system:refresh`**
- Clears Ollama context + refreshes command reference
- Usage: `clai do system:refresh`

**Files Created:**
- `agent/workflows/system.py`

**Files Modified:**
- `agent/state/logger.py` (added `clear_history()` and `get_command_history()`)
- `agent/state/__init__.py` (added exports)

---

### Memory Architecture Clarification

#### Is chat memory retained across runs?

**Answer: NO** ❌

**What happens:**
1. Each `clai auto "command"` starts with a fresh slate
2. `WorkflowMemory` is created per-execution and destroyed when done
3. Ollama has NO persistent conversation memory
4. Each Ollama call is completely stateless

**What IS persisted:**
- ✅ Command history (last 100 commands in `~/.clai/command_history.json`)
- ✅ Authentication tokens (Gmail, Calendar)
- ✅ Generated workflow files

**What is NOT persisted:**
- ❌ Chat context/conversation with Qwen
- ❌ Workflow memory between runs
- ❌ Email IDs or other runtime context

**Why this design:**
- Ollama CLI is stateless by design
- Each subprocess call is independent
- Memory would require persistent storage + session management
- Current design is simpler and more reliable

**Workaround:**
- Use `clai do system:status` to check system state
- Use `clai history` to see past commands
- For complex multi-step tasks, use `clai auto` with full context in one request

---

### Testing

To test the fixes, try these commands:

```bash
# Test parameter quoting fix
clai auto "send me an email about the benefits of exercise"

# Test calendar fix
clai auto "create a meeting at 2pm tomorrow with title Test Meeting"

# Test new system commands
clai do system:status
clai do system:clear
clai do system:refresh

# View history
clai history --limit 5

# Clear history (requires confirmation)
clai do system:clear-history confirm:yes
```

---

### Migration Notes

**Breaking Changes:** None

**Backward Compatibility:** ✅ Fully compatible

**Recommendations:**
1. Run `clai do system:refresh` after pulling these changes
2. Test calendar and email commands to verify fixes
3. Use `system:status` to verify your setup

---

### Future Improvements

Potential enhancements to consider:

1. **Persistent Chat Sessions**
   - Store conversation history in `~/.clai/sessions/`
   - Allow users to continue previous conversations
   - Use `--session SESSION_NAME` flag

2. **Enhanced Memory Management**
   - Store workflow context between runs
   - Allow reference to previous commands: "reply to the same email"
   - Implement context TTL (time-to-live)

3. **Better Error Recovery**
   - Auto-retry with corrected quoting on parsing errors
   - Suggest fixes when commands fail

4. **Performance Monitoring**
   - Track Ollama response times
   - Log token usage per command
   - Identify slow operations

---

### Contributors

- Fixed by: GitHub Copilot
- Date: October 16, 2025
- Issues resolved: #1 (quoting), #2 (calendar parameters)
- Features added: System management commands
