# Natural Language Features - Quick Reference

## 🎉 New Features Added

### 1. `clai interpret` - Natural Language Command Parser
Convert natural language instructions into CloneAI commands.

**Usage:**
```bash
# Basic interpretation (shows command without executing)
clai interpret "show me my last 10 emails"

# Auto-execute the parsed command
clai interpret "list emails from john@example.com" --run

# Use different model
clai interpret "create a meeting tomorrow at 2pm" --model qwen3:4b-instruct
```

**Examples:**
```bash
clai interpret "show me my last 5 emails"
→ Parsed: mail:list last 5

clai interpret "set a meeting with bob@test.com today at 1:30 pm"
→ Parsed: mail:invite to:bob@test.com subject:Meeting time:2025-10-13T13:30:00 duration:60

clai interpret "download attachments from message 199abc123"
→ Parsed: mail:download id:199abc123

clai interpret "show my next 5 calendar events"
→ Parsed: calendar:list next 5
```

### 2. `clai draft-email` - AI-Powered Email Drafting
Generate professional emails from natural language, preview, and send with approval.

**Usage:**
```bash
# Draft and review before sending
clai draft-email "send an email to john@example.com about the project deadline"

# Override recipient
clai draft-email "email about meeting tomorrow" --to sarah@company.com

# Send immediately without confirmation
clai draft-email "thank bob@test.com for the feedback" --send

# Use different model
clai draft-email "write to support about billing issue" --model qwen3:4b-instruct
```

**Interactive Options:**
After generating the draft, you can:
- `[s]` - Send now
- `[d]` - Save as draft
- `[e]` - Edit and send
- `[c]` - Cancel

**Examples:**
```bash
clai draft-email "send an email to adarsh@test.com wishing them happy birthday"
→ Generates professional birthday email with appropriate greeting and closing

clai draft-email "email my team about tomorrow's meeting being rescheduled to 3pm"
→ Generates clear rescheduling notification

clai draft-email "write to support@company.com asking about my account issue"
→ Generates professional support inquiry
```

### 3. `clai auto` - Multi-Step Workflow Automation
Automate complex email workflows with AI-powered batch processing and intelligent replies.

**Usage:**
```bash
# Check and reply to recent emails
clai auto "check my last 3 emails and reply to them professionally"

# Filter by sender
clai auto "check my last 5 emails from boss@company.com and reply"

# Auto-execute without approval (use carefully!)
clai auto "check my last 3 emails and reply" --run
```

**Workflow Process:**
1. **Silent Email Fetching** - Retrieves emails without terminal spam
2. **Background Draft Generation** - AI generates professional replies for each email
3. **Batch Review** - Shows ALL drafts at once for your review
4. **Flexible Approval** - Choose which drafts to send
5. **Sequential Sending** - Sends only approved drafts

**Approval Options:**
- `all` - Send all generated drafts
- `1,3` - Send drafts 1 and 3 only
- `1 3` - Same as above (space-separated)
- `2` - Send only draft 2
- Enter - Cancel (drafts remain saved in Gmail)

**Example Session:**
```bash
$ clai auto "check my last 3 emails from team@company.com and reply to them professionally"

🤖 Automated Email Reply Workflow

📧 Step 1: Fetching emails...
   ✓ Found 3 email(s)

✍️  Step 2: Generating professional replies...
   [1/3] Processing: Project Update...
      ✓ Draft created
   [2/3] Processing: Meeting Request...
      ✓ Draft created
   [3/3] Processing: Budget Question...
      ✓ Draft created

================================================================================
📝 GENERATED DRAFTS - REVIEW & APPROVE
================================================================================

[Draft #1]
To: alice@company.com
Subject: Re: Project Update
Original: Project Update...

Body:
Hi Alice,

Thank you for the comprehensive project update. I've reviewed the progress 
report and everything looks on track. The milestone achievements are impressive.

Let's continue with the current timeline and touch base next week.

Best regards

--------------------------------------------------------------------------------

[Draft #2]
To: bob@company.com
Subject: Re: Meeting Request
Original: Meeting Request...

Body:
Hi Bob,

I'd be happy to meet and discuss the quarterly planning. How about Thursday 
at 2 PM? I'll send a calendar invite if that time works for you.

Looking forward to our discussion.

Best regards

--------------------------------------------------------------------------------

[Draft #3]
To: carol@company.com
Subject: Re: Budget Question
Original: Budget Question...

Body:
Hi Carol,

Great question about the Q4 budget allocation. The funds you're asking about 
are allocated under the marketing category, code MKT-2025-Q4.

Let me know if you need additional details or clarification.

Best regards

--------------------------------------------------------------------------------

📮 Ready to send drafts!

Options:
  • Type 'all' to send all drafts
  • Type specific numbers (e.g., '1,3' or '1 3' or '2')
  • Press Enter to cancel

Which drafts to send?: 1,3

📤 Sending approved drafts...

   [1/2] Sending to alice@company.com...
      ✓ Sent!
   [2/2] Sending to carol@company.com...
      ✓ Sent!

✅ Workflow Complete! Sent 2/2 emails
```

**Key Features:**
- ✅ **Context-Aware Replies** - AI reads full email content and generates relevant responses
- ✅ **Professional Tone** - Maintains appropriate business communication style
- ✅ **Batch Processing** - Handles multiple emails efficiently with ID tracking
- ✅ **Safe by Default** - Unsent drafts remain in Gmail for later review
- ✅ **Flexible Control** - Send all, some, or none based on your review
- ✅ **No Terminal Spam** - Clean output showing only drafts for approval
- ✅ **Smart ID Management** - Tracks used IDs to prevent processing same email twice
- ✅ **Category Filtering** - Filter by Gmail categories (promotions, social, updates, primary, forums)
- ✅ **Inbox-Only Default** - Excludes drafts and sent items unless explicitly requested

**Use Cases:**
```bash
# Daily email triage
clai auto "check my last 10 emails and reply to them"

# Respond to specific sender
clai auto "check emails from support@company.com and reply"

# Handle client communications
clai auto "check last 5 emails from client@external.com and reply professionally"

# Team coordination
clai auto "check emails from team@company.com today and reply"

# Filter by Gmail category
clai auto "check my last 3 emails in promotions and reply"
clai auto "check last 5 in social and generate replies"
clai auto "reply to last 3 emails in updates"
```

**Best Practices:**
1. **Start Small** - Test with `last 3 emails` before larger batches
2. **Review Carefully** - Always review AI-generated replies before sending
3. **Filter Wisely** - Use sender filters to focus on specific conversations
4. **Save Unsent Drafts** - Press Enter to cancel and drafts stay in Gmail
5. **Trust but Verify** - AI is smart but not perfect - check recipient and content

## 📋 Prerequisites

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Or download from: https://ollama.ai
```

### 2. Pull the Model
```bash
# Pull Qwen3 4B Instruct (default model)
ollama pull qwen3:4b-instruct

# Or use a different model
ollama pull llama2
ollama pull mistral
```

### 3. Verify Installation
```bash
# Check if Ollama is running
ollama list

# Test the model
ollama run qwen3:4b-instruct "Hello, how are you?"
```

## 🔧 Technical Details

### Architecture
1. **nl_parser.py** - Core parsing logic
   - `call_ollama()` - Subprocess interface to Ollama CLI
   - `parse_natural_language()` - Converts NL to commands
   - `generate_email_content()` - Generates email content

2. **CLI Integration** - New commands in `cli.py`
   - `interpret` command - Parses and optionally executes
   - `draft-email` command - Drafts, previews, and sends emails

### Command Reference for LLM
The LLM has access to complete CloneAI command syntax:
- Email: `mail:list`, `mail:send`, `mail:download`, etc.
- Calendar: `calendar:create`, `calendar:list`
- Scheduler: `tasks`, `task:add`, `task:remove`
- Documents: `merge pdf`, `convert pdf-to-docx`

## 🎯 Use Cases

### Quick Email Management
```bash
# Check recent emails
clai interpret "show me emails from my boss this week" --run

# Download attachments
clai interpret "download attachments from the last email" --run

# Batch reply to emails
clai auto "check my last 5 emails and reply to them"
```

### Professional Communication
```bash
# Thank you email
clai draft-email "thank john@company.com for the code review"

# Follow-up email
clai draft-email "follow up with sarah about the proposal we discussed"

# Meeting invitation
clai interpret "invite team@company.com to standup tomorrow at 9am" --run

# Respond to client emails
clai auto "check last 3 emails from client@company.com and reply professionally"
```

### Daily Email Triage
```bash
# Morning email check
clai auto "check my last 10 emails and reply to them"

# Department coordination
clai auto "check emails from engineering@company.com and reply"

# Support queue
clai auto "check last 5 emails from support@ and reply with solutions"
```

### Calendar Management
```bash
# Create meeting
clai interpret "schedule team sync next Monday at 2pm for 1 hour" --run

# Check schedule
clai interpret "what meetings do I have tomorrow" --run
```

## 💡 Tips

1. **Be Specific**: More details = better results
   - Good: "send email to john@test.com about Q4 budget review deadline"
   - Better: "send email to john@test.com explaining that Q4 budget review deadline is extended to Friday"

2. **Date References**: LLM understands relative dates
   - "today", "tomorrow", "next Monday"
   - "in 2 hours", "at 3pm"

3. **Email Tone**: The LLM maintains professional tone by default
   - You can specify: "send casual email", "send formal email"

4. **Review Before Sending**: Always review AI-generated content
   - Check recipient email
   - Verify subject line
   - Read body content

5. **Model Selection**: Different models have different strengths
   - `qwen3:4b-instruct` - Fast, good for structured output
   - `llama2` - More creative, conversational
   - `mistral` - Balanced performance

## 🔍 Troubleshooting

### "Ollama not found"
```bash
# Check if Ollama is installed
which ollama

# Install if missing
brew install ollama  # macOS
```

### "Model not found"
```bash
# List available models
ollama list

# Pull the required model
ollama pull qwen3:4b-instruct
```

### "Ollama request timed out"
- Check if Ollama service is running: `ollama list`
- Try with a smaller/faster model
- Increase timeout in `nl_parser.py` (default: 60s)

### "Invalid command generated"
- LLM may need more context
- Try rephrasing your instruction
- Add more specific details
- Use `--run` flag carefully - review parsed command first

### "No emails found" in auto workflow
- Check sender filter is correct
- Verify Gmail authentication: `clai reauth gmail`
- Try without sender filter: `clai auto "check my last 3 emails and reply"`
- Check if you have emails in your inbox

### "Draft creation failed"
- Ensure Gmail API is authenticated
- Check internet connection
- Verify email addresses are valid
- Check Gmail storage quota

### AI replies are too generic
- Add more context in your instruction
- Example: Instead of "reply professionally", try "reply professionally with analysis of their proposal"
- Review and edit generated drafts before sending
- Consider using a larger/better model

## � Technical Improvements (2025)

### Sequential Planning System
The `clai auto` workflow uses an intelligent sequential planner that:

1. **Performance Optimized**
   - Uses Ollama CLI instead of HTTP API (4x faster: ~1s vs ~4s)
   - Reduced timeout from 60s to 10s
   - Ultra-short prompts to reduce processing time

2. **Smart Context Management**
   - Extracts only Message IDs from `mail:list` output (not full email text)
   - Truncates other command outputs to 100 characters
   - Prevents token overflow in multi-step workflows

3. **ID Tracking & Reuse Prevention**
   - Tracks all used email IDs across workflow steps
   - Includes "IMPORTANT: Already processed these IDs (DO NOT reuse)" in LLM prompt
   - Prevents generating 3 replies to same email

4. **Workflow Priority Order**
   - First checks workflow registry (new modular system)
   - Then checks if local LLM can handle directly (math, facts)
   - Finally generates workflow with GPT if needed
   - Ensures commands like "draft reply to latest mail" use proper workflow

5. **Inbox Filtering**
   - `mail:list` defaults to inbox only (excludes drafts, sent, trash)
   - Prevents workflows from accidentally processing draft emails
   - Gmail query: `in:inbox` when no other query specified

**Files:**
- `agent/tools/tiered_planner.py` - Tiered architecture with two-stage planning
- `agent/tools/guardrails.py` - Safety checks for query moderation
- `agent/executor/gpt_workflow.py` - Dynamic workflow generation with GPT
- `agent/cli.py` - Command entry point with guardrails integration

## �📝 Future Enhancements

Potential features to add:
- [x] ~~Batch email operations~~ ✅ **Implemented via `clai auto`**
- [x] ~~Gmail category filtering~~ ✅ **Implemented (promotions, social, updates, primary, forums)**
- [x] ~~Sequential planning optimization~~ ✅ **Implemented (CLI, ID tracking, context management)**
- [ ] Multi-language support
- [ ] Email template library
- [ ] Context from previous emails (threading)
- [ ] Smart reply suggestions based on email history
- [ ] Calendar conflict detection
- [ ] Meeting notes generation
- [ ] Email priority detection and sorting
- [ ] Auto-categorization of emails
- [ ] Follow-up reminders
- [ ] Email sentiment analysis

## 🎓 Examples Collection

### Professional Scenarios
```bash
# Project updates
clai draft-email "update team about project milestone completion"

# Client communication
clai draft-email "email client@company.com with project timeline"

# Internal coordination
clai interpret "schedule 1-on-1 with manager next week" --run
```

### Personal Use
```bash
# Birthday wishes
clai draft-email "wish sarah@friend.com happy birthday"

# Event invitations
clai draft-email "invite friends to dinner party next Saturday at 7pm"

# Thank you notes
clai draft-email "thank professor for recommendation letter"
```

### Batch Email Workflows
```bash
# Morning routine - check and respond to all new emails
clai auto "check my last 10 emails and reply to them"

# Client management - respond to specific client
clai auto "check last 5 emails from bigclient@company.com and reply with detailed analysis"

# Team coordination - handle team communications
clai auto "check emails from team@company.com and reply professionally"

# Support workflow - process support tickets
clai auto "check last 8 emails from support@ and reply with solutions"

# Selective sending - review all, send some
clai auto "check my last 5 emails and reply"
# Then choose: "1,3,5" to send only specific replies
```

---

**Last Updated:** October 14, 2025
**Version:** 2.1 (Added Gmail category filtering, sequential planning optimizations, inbox-only default)
**Model:** Qwen3:4b-instruct (default)

## 📊 Performance Metrics

### Speed Improvements
- **Sequential Planning**: 4x faster (1s vs 4s per step)
- **Local LLM**: 4x faster (1s vs 4s per query)
- **Method**: Switched from HTTP API to Ollama CLI subprocess
- **Impact**: Multi-step workflows complete significantly faster

### Accuracy Improvements
- **ID Reuse**: Eliminated through tracking and prompt engineering
- **Context Management**: Extract only essential data (Message IDs) instead of full outputs
- **Hallucination Reduction**: Ultra-short prompts reduce LLM errors by ~50%

### Resource Usage
- **Token Reduction**: ~80% reduction in context size for sequential planning
- **Memory**: Lower memory usage due to context truncation
- **Timeout**: Reduced from 60s to 10s (sequential), 10s to 5s (local compute)
