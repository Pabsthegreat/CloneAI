# CloneAI Documentation Website

Modern, responsive documentation website for CloneAI with automatic content updates.

## 🚀 Quick Start

### View Documentation Locally

```bash
# Navigate to docs folder
cd /Users/adarsh/Documents/GitHub/CloneAI/docs

# Start server (Python 3)
python3 serve.py

# Or use the simple method
python3 -m http.server 8000
```

Then open: **http://localhost:8000**

## 📁 Files Overview

```
docs/
├── index.html              # Main HTML structure
├── styles.css              # Styling (light/dark modes)
├── script.js               # Navigation & rendering logic
├── MASTER.md               # ⭐ Single source of documentation
├── DOCUMENTATION_GUIDE.md  # How to update docs
├── serve.py                # Development server
└── README.md               # This file
```

## ✏️ Updating Documentation

**Step 1:** Edit `MASTER.md` with your changes

**Step 2:** Save the file

**Step 3:** Refresh your browser

**That's it!** The website automatically reads and renders the latest content.

See [DOCUMENTATION_GUIDE.md](DOCUMENTATION_GUIDE.md) for detailed instructions.

## 🎨 Features

- ✅ **Auto-generated Navigation** from markdown headers
- ✅ **Dark/Light Mode** with persistent preference
- ✅ **Responsive Design** (mobile, tablet, desktop)
- ✅ **Search** - Filter sections in real-time
- ✅ **Syntax Highlighting** for code blocks (via highlight.js)
- ✅ **On-page TOC** - Quick navigation within sections
- ✅ **Professional Typography** - Inter & JetBrains Mono fonts
- ✅ **Zero Build Process** - Static files only

## 🌐 Deployment

### Local (Current)

```bash
python3 serve.py
```

### Port Forwarding

```bash
# Example with serveo.net
ssh -R 80:localhost:8000 serveo.net

# Or with ngrok
ngrok http 8000
```

### GitHub Pages

1. Push the `docs/` folder to your repository
2. Go to: **Settings → Pages**
3. Set source: **main branch / docs folder**
4. Access at: `https://pabsthegreat.github.io/CloneAI/`

## 🛠️ Tech Stack

- **Markdown Parser:** [Marked.js](https://marked.js.org/) v10.0+
- **Syntax Highlighting:** [Highlight.js](https://highlightjs.org/) v11.9+
- **Fonts:** [Inter](https://rsms.me/inter/) & [JetBrains Mono](https://www.jetbrains.com/lp/mono/)
- **Icons:** Inline SVG
- **Framework:** Vanilla JavaScript (no dependencies beyond CDN libraries)

## 📚 Documentation Structure

```markdown
# Main Section (H1)
## Subsection (H2)
### Topic (H3)
#### Subtopic (H4)
```

- **H1:** Creates top-level navigation sections
- **H2:** Creates sub-navigation items
- **H3+:** Appears in "On this page" TOC

## 🎯 Automatic Categorization

Sections are automatically categorized based on header keywords:

| Category | Keywords |
|----------|----------|
| Getting Started | quick start, installation, setup, prerequisites |
| User Guide | commands, usage, email, calendar, workflow |
| Architecture | architecture, system, components, flow |
| Advanced Features | voice, scheduler, priority, web search, gpt |
| Development | testing, security, implementation, migration |
| Reference | troubleshooting, reference, tips, best practices |

## 🔧 Customization

### Change Theme Colors

Edit `styles.css`:

```css
:root {
    --color-primary: #0066cc;  /* Your brand color */
    --color-bg: #ffffff;
    --color-text: #1a1a1a;
}
```

### Change Fonts

Update `index.html` Google Fonts import and `styles.css` variables.

### Modify Layout

Adjust in `styles.css`:

```css
:root {
    --sidebar-width: 280px;
    --toc-width: 240px;
    --content-max-width: 900px;
}
```

## 🐛 Troubleshooting

### Documentation not loading

**Cause:** `MASTER.md` not found or has syntax errors

**Fix:**
1. Ensure `MASTER.md` is in `docs/` folder
2. Check browser console (F12) for errors
3. Verify markdown syntax is valid

### Code blocks not highlighted

**Cause:** Language not specified in code fence

**Fix:**
```markdown
```python  ← Specify language
print("Hello")
```
\```
```

### Navigation not updating

**Cause:** Browser cache

**Fix:** Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

## 📊 Performance

- **Load Time:** ~500ms (first visit)
- **Cached:** ~50ms (subsequent visits)
- **File Size:** ~200KB total (HTML+CSS+JS+MD)
- **Dependencies:** CDN-hosted (marked.js, highlight.js, fonts)

## 🚦 Browser Support

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 📝 Version History

- **v1.0** (Nov 2025) - Initial release
  - Auto-loading from MASTER.md
  - Dark/light mode
  - Responsive design
  - Search functionality
  - Syntax highlighting

## 🤝 Contributing

To improve the documentation:

1. Edit `MASTER.md` with your changes
2. Test locally: `python3 serve.py`
3. Commit and push
4. Changes go live automatically!

## 📖 Learn More

- [DOCUMENTATION_GUIDE.md](DOCUMENTATION_GUIDE.md) - Complete guide for writers
- [MASTER.md](MASTER.md) - The actual documentation content
- [Main README](../README.md) - CloneAI project overview

## 💡 Tips

1. **Keep MASTER.md organized** - Use clear header hierarchy
2. **Test locally first** - Always preview before pushing
3. **Use descriptive headers** - They become navigation labels
4. **Add emojis** - Makes documentation more engaging 🎉
5. **Include code examples** - With language specification for highlighting

## 🎓 Resources

- [Markdown Guide](https://www.markdownguide.org/)
- [GitHub Flavored Markdown](https://github.github.com/gfm/)
- [Marked.js Documentation](https://marked.js.org/)
- [Highlight.js Language Support](https://highlightjs.org/static/demo/)

---

**Made with ❤️ for CloneAI**

*Last Updated: November 1, 2025*
