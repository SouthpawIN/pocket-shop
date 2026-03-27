# Browser Automation Guide for Pocket-Shop

*Hermes Documentation Extract - March 25, 2026*

---

## Overview

Browser automation is the **primary tool** for Pocket-Shop. It enables:
- Price lookups on TCGPlayer
- Set monitoring on MTGStocks
- Email checking via Gmail browser interface
- Creating eBay listings (if API not available)

---

## Browser Automation Documentation

**Full Docs:** https://hermes-agent.nousresearch.com/docs/user-guide/features/browser

### Backend Options

1. **Browserbase cloud mode** - Managed cloud browsers with anti-bot tooling
2. **Browser Use cloud mode** - Alternative cloud browser provider  
3. **Local Chrome via CDP** - Connect to your own Chrome instance
4. **Local browser mode** - Via agent-browser CLI

### Key Capabilities

- Navigate websites, interact with page elements, fill forms
- Pages represented as **accessibility trees** (text-based snapshots)
- Interactive elements get ref IDs (`@e1`, `@e2`) for clicking/typing
- Multi-provider cloud execution
- Session isolation - each task gets own browser session
- Automatic cleanup after timeout
- Vision analysis - screenshot + AI analysis

---

## Browser Tools Reference

### browser_navigate
Navigate to a URL. Initializes the session and loads the page.

```python
browser_navigate(url="https://tcgplayer.com/products/search?q=Black+Lotus")
```

### browser_snapshot
Get text-based snapshot of current page's accessibility tree.

```python
# Compact view with interactive elements only
browser_snapshot(full=false)

# Complete page content
browser_snapshot(full=true)
```

Returns interactive elements with ref IDs (`@e1`, `@e2`) for subsequent commands.

### browser_click
Click on an element identified by its ref ID from the snapshot.

```python
browser_click(ref="@e5")  # Click element with ref @e5
```

### browser_type
Type text into an input field identified by its ref ID. Clears the field first, then types new text.

```python
browser_type(ref="@e3", text="search query")
```

### browser_press
Press a keyboard key. Useful for submitting forms (Enter), navigating (Tab), or shortcuts.

```python
browser_press(key="Enter")
browser_press(key="Tab")
browser_press(key="Escape")
```

### browser_scroll
Scroll the page in a direction to reveal more content.

```python
browser_scroll(direction="down")
browser_scroll(direction="up")
```

### browser_vision
Take a screenshot and analyze with vision AI. Use when you need to visually understand what's on the page.

```python
browser_vision(
    question="What cards are shown and what are their prices?",
    annotate=false  # If true, overlay numbered labels on elements
)
```

### browser_console
Get browser console output and JavaScript errors.

```python
browser_console(clear=false)  # If true, clear buffers after reading
```

### browser_close
Close the browser session and release resources.

```python
browser_close()
```

---

## Vision Analysis for Card Identification

**Full Docs:** https://hermes-agent.nousresearch.com/docs/user-guide/features/vision

### vision_analyze Tool

Analyze images using AI vision. Provides comprehensive description and answers specific questions.

```python
vision_analyze(
    image_url="/path/to/card/photo.jpg",
    question="""Identify this trading card. Tell me:
1. Card name
2. Set name and set code
3. Card number (if visible)
4. Condition assessment (Mint, Near Mint, Excellent, Good, Lightly Played, Heavily Played, Damaged)
5. Any foil/stamp/variant details

Respond with just the card name and set info."""
)
```

### How Image Paste Works

1. Copy image to clipboard (screenshot, browser image, etc.)
2. Attach using `/paste` command or Ctrl+V/Cmd+V
3. Type your question and press Enter
4. Image appears as `[📎 Image #1]` badge above input
5. On submit, image is sent to model as vision content block

Images are saved to `~/.hermes/images/` as PNG files with timestamped filenames.

---

## Pocket-Shop Workflow Example

### Price Lookup on TCGPlayer

```python
# 1. Navigate to search
browser_navigate(url="https://tcgplayer.com/products/search?q=Black+Lotus")

# 2. Get snapshot of page
snapshot = browser_snapshot(full=false)

# 3. Extract price information from page content
# The snapshot will show elements like:
# - search results with card names
# - Price information (@e1, @e2, etc.)
# - Product links to click

# 4. Click on product if needed
browser_click(ref="@e5")  # Example: click first result

# 5. Get detailed price page
browser_snapshot(full=true)  # Full content for parsing
```

### Card Identification Workflow

```python
# 1. Capture card image (from phone camera or file)
card_image = "/tmp/card-scan-001.jpg"

# 2. Identify the card using vision
identification = vision_analyze(
    image_url=card_image,
    question="""Identify this Magic: The Gathering card:
- Card name
- Set code (e.g., LEA, 4ED)
- Condition assessment
- Any foil/variant details"""
)

# 3. Extract name and set from identification
# Then use browser to look up price on TCGPlayer
```

---

## Tips & Best Practices

### For Browser Automation:

1. **Always start with browser_navigate** - Must be called before other browser tools
2. **Use browser_snapshot(full=false)** first - Compact view shows interactive elements
3. **Use ref IDs from snapshot** - Elements shown as `@e1`, `@e2`, etc.
4. **Scroll for more content** - Use browser_scroll to reveal hidden elements
5. **Close when done** - Call browser_close() to free resources

### For Vision Analysis:

1. **Be specific in questions** - Tell the model exactly what you need
2. **Use structured prompts** - Numbered lists work well
3. **Combine with browser** - Use browser_vision for visual page understanding

---

## Related Documentation

- **Tools Overview:** https://hermes-agent.nousresearch.com/docs/user-guide/features/tools
- **Vision & Image Paste:** https://hermes-agent.nousresearch.com/docs/user-guide/features/vision
- **Complete Hermes Docs:** See `Hermes/Source/docs/COMPLETE-HERMES-DOCS.md`
