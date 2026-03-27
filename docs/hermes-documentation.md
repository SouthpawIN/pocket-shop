# Hermes Documentation for Pocket-Shop

*Generated: March 25, 2026*
*Purpose: Reference documentation for building out the automated MTG card shop*

---

## 🔧 Core Hermes Features Used

### Browser Automation (Primary Tool)
**Docs:** https://hermes-agent.nousresearch.com/docs/user-guide/features/tools

Tools:
- `browser_navigate` - Navigate to URLs (TCGPlayer, MTGStocks, eBay)
- `browser_snapshot` - Get page content as text
- `browser_click` - Click elements by ref ID
- `browser_type` - Type into input fields
- `browser_vision` - Visual analysis of page state
- `browser_scroll` - Scroll up/down for more content

**Use Cases:**
- Price lookups on TCGPlayer
- Set monitoring on MTGStocks  
- Email checking via Gmail browser interface
- Creating eBay listings (if API not available)

---

### Vision Analysis
**Docs:** https://hermes-agent.nousresearch.com/docs/user-guide/features/tools

Tool: `vision_analyze`

**Use Cases:**
- Card identification from photos
- Reading card names, set codes, conditions
- Verifying browser page state visually

---

### Web Search
**Docs:** https://hermes-agent.nousresearch.com/docs/user-guide/features/tools

Tools: `web_search`, `web_extract`

**Use Cases:**
- Finding card information
- Researching market trends
- Looking up set release dates

---

### Terminal & File Operations
**Docs:** https://hermes-agent.nousresearch.com/docs/user-guide/features/tools

Tools:
- `terminal` - Execute shell commands
- `read_file` / `write_file` - Read/write files
- `patch` - Edit files with find/replace
- `search_files` - Search file contents
- `execute_code` - Run Python scripts with Hermes tools

**Use Cases:**
- Running card scanner scripts
- Managing finance.json
- Processing captured images
- Running automation scripts

---

### Agent Orchestration
Tools: `todo`, `clarify`, `delegate_task`, `execute_code`

**Use Cases:**
- Breaking down complex tasks (card scanning workflow)
- Asking for clarification on ambiguous cards
- Delegating subtasks (pricing multiple cards)

---

## 📝 Key Documentation Pages to Reference

1. **Tools & Toolsets** - https://hermes-agent.nousresearch.com/docs/user-guide/features/tools
2. **Skills System** - https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
3. **Browser Tools** - (check Web & Media section)
4. **Configuration** - https://hermes-agent.nousresearch.com/docs/user-guide/configuration

---

## 🛠️ Implementation Notes

### Browser Automation Pattern
```python
# 1. Navigate to page
browser_navigate(url="https://tcgplayer.com/products/search?q=Black Lotus")

# 2. Get snapshot of page
browser_snapshot(full=false)  # Gets interactive elements with @e1, @e2 refs

# 3. Click or type
browser_click(ref="@e5")  # Click element with ref @e5
browser_type(ref="@e3", text="search query")

# 4. Extract data
browser_snapshot(full=true)  # Full page content for parsing
```

### Vision Analysis Pattern
```python
vision_analyze(
    image_url="/path/to/card/photo.jpg",
    question="Identify this trading card: name, set code, condition"
)
```

---

## 🔗 Related Projects Documentation

- **Burner-Phone** - For phone camera integration, see voice mode docs
- **Hermes** - Framework reference for skills and personality
