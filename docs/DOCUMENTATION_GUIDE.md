# CloneAI Documentation Guide

**How to maintain and update CloneAI's documentation website**

---

## 📖 Overview

CloneAI uses a modern, static documentation website that automatically reads from a single `MASTER.md` file. The website features:

- ✅ Automatic navigation generation from markdown headers
- ✅ Dark/light mode with persistent preference
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Search functionality
- ✅ On-page table of contents
- ✅ Syntax highlighting for code blocks
- ✅ Professional typography with Inter and JetBrains Mono fonts

---

## 🏗️ File Structure

```
docs/
├── index.html              # Main HTML structure
├── styles.css              # All styling (light/dark modes)
├── script.js               # JavaScript for navigation & rendering
├── MASTER.md               # ⭐ Single source of truth for all documentation
└── DOCUMENTATION_GUIDE.md  # This file
```

---

## 📝 Writing Documentation

### File Format

All documentation should be written in **MASTER.md** using standard Markdown syntax.

### Header Hierarchy

```markdown
# Main Section (H1) - Creates top-level navigation items

## Subsection (H2) - Creates sub-navigation items

### Topic (H3) - Appears in on-page TOC

#### Subtopic (H4) - Used for detailed breakdowns

##### Detail (H5) - Rarely used
```

**Important Rules:**
1. Use **only ONE H1** per major section
2. H2 headers create the main navigation structure
3. H3 and below appear in the right-side "On this page" TOC
4. Keep header text concise (navigation labels come from these)

### Section Categories

The website automatically categorizes sections based on keywords in headers:

| Category | Keywords |
|----------|----------|
| Getting Started | quick start, installation, setup, prerequisites, what is |
| User Guide | commands, usage, email, calendar, document, natural language, workflow |
| Architecture | architecture, system, components, flow, tiered, workflow system |
| Advanced Features | voice, scheduler, priority, web search, generation, gpt |
| Development | testing, security, implementation, migration, token |
| Reference | troubleshooting, reference, tips, best practices, command reference |

**Tip:** Include relevant keywords in your section headers for automatic categorization.

---

## ✍️ Markdown Best Practices

### Code Blocks

Always specify the language for syntax highlighting:

````markdown
```bash
clai do "mail:list last 5"
```

```python
def hello_world():
    print("Hello, CloneAI!")
```

```javascript
const theme = localStorage.getItem('theme');
```
````

### Links

```markdown
[External Link](https://example.com)
[Internal Section](#section-name)
```

### Tables

```markdown
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

### Alerts/Callouts

Use blockquotes with emojis for visual callouts:

```markdown
> ⚠️ **Warning:** This is important information.

> 📌 **Note:** This is a helpful tip.

> ✅ **Success:** This indicates completion.

> 🚀 **Pro Tip:** Advanced users might find this useful.
```

### Lists

```markdown
**Unordered:**
- Item 1
- Item 2
  - Nested item
  - Another nested item

**Ordered:**
1. First step
2. Second step
3. Third step

**Task Lists:**
- [x] Completed task
- [ ] Pending task
```

### Horizontal Rules

```markdown
---
```

Use sparingly to separate major sections.

---

## 🔄 Updating the Documentation

### Step 1: Edit MASTER.md

Make your changes directly in `MASTER.md`:

```bash
cd /Users/adarsh/Documents/GitHub/CloneAI/docs
nano MASTER.md  # or use your preferred editor
```

### Step 2: Verify Markdown Syntax

Ensure your markdown is valid:
- Headers have proper hierarchy
- Code blocks are closed
- Links are correctly formatted
- Lists are properly indented

### Step 3: Preview Changes

Open the website locally:

```bash
# Option 1: Simple HTTP server (Python 3)
python3 -m http.server 8000

# Option 2: Using Node.js
npx http-server -p 8000

# Then open: http://localhost:8000
```

### Step 4: Automatic Reload

The website automatically:
1. Reads `MASTER.md` on page load
2. Parses markdown into HTML with marked.js
3. Generates navigation from headers
4. Applies syntax highlighting
5. Creates the on-page TOC

**No build step required!** Just refresh the browser.

---

## 🎨 Customizing the Website

### Changing Colors

Edit `styles.css` CSS variables:

```css
:root {
    /* Light Mode */
    --color-primary: #0066cc;        /* Main accent color */
    --color-bg: #ffffff;             /* Background */
    --color-text: #1a1a1a;           /* Text color */
    /* ... */
}

[data-theme="dark"] {
    /* Dark Mode */
    --color-primary: #58a6ff;
    --color-bg: #0d1117;
    --color-text: #e6edf3;
    /* ... */
}
```

### Changing Fonts

Update the Google Fonts import in `index.html`:

```html
<link href="https://fonts.googleapis.com/css2?family=YourFont:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

Then update the CSS variable:

```css
--font-base: 'YourFont', sans-serif;
```

### Modifying Layout

Key CSS variables in `styles.css`:

```css
:root {
    --sidebar-width: 280px;        /* Left navigation width */
    --toc-width: 240px;            /* Right TOC width */
    --content-max-width: 900px;    /* Main content max width */
}
```

---

## 📦 Deployment

### Local Testing

```bash
cd /Users/adarsh/Documents/GitHub/CloneAI/docs
python3 -m http.server 8000
```

Visit: `http://localhost:8000`

### Port Forwarding (Your Use Case)

Since you mentioned port forwarding:

```bash
# Example: Forward local port 8000 to public port 80
ssh -R 80:localhost:8000 serveo.net

# Or use ngrok
ngrok http 8000
```

The documentation will automatically update when you edit `MASTER.md` - just refresh the browser!

### GitHub Pages (Optional)

If you want to host on GitHub Pages:

1. Push the `docs/` folder to your repository
2. Go to repository Settings → Pages
3. Set source to: **main branch / docs folder**
4. Your site will be at: `https://pabsthegreat.github.io/CloneAI/`

**Note:** Changes to `MASTER.md` will auto-update on next page load.

---

## 🔍 Search Functionality

The search box filters navigation items in real-time:

- Type keywords to filter sections
- Case-insensitive matching
- Searches section titles only (not content)
- Instantly shows/hides matching items

**Note:** For full-text search, consider integrating Algolia DocSearch or Lunr.js in the future.

---

## 📱 Mobile Responsiveness

The website is fully responsive:

- **Desktop (>1280px):** Sidebar + Content + TOC
- **Tablet (768px-1280px):** Sidebar + Content (TOC hidden)
- **Mobile (<768px):** Hamburger menu, collapsible sidebar

Test on different devices or use browser dev tools.

---

## 🎯 Best Practices

### Do's ✅

- ✅ Keep `MASTER.md` as the single source of truth
- ✅ Use descriptive header names for better navigation
- ✅ Include code examples with proper syntax highlighting
- ✅ Add emojis to headers for visual appeal (e.g., 🚀 Quick Start)
- ✅ Break long sections into subsections
- ✅ Use tables for structured data
- ✅ Test locally before pushing changes
- ✅ Keep line length reasonable (80-100 chars for readability)

### Don'ts ❌

- ❌ Don't create separate markdown files (use sections in MASTER.md)
- ❌ Don't skip header levels (H1 → H3 without H2)
- ❌ Don't use HTML in markdown unless necessary
- ❌ Don't forget to close code blocks with ```
- ❌ Don't use vague header names ("Section 1", "Part A")
- ❌ Don't duplicate content across sections
- ❌ Don't forget to update MASTER.md when features change

---

## 🐛 Troubleshooting

### Documentation not loading

**Problem:** Website shows "Error loading documentation"

**Solution:**
1. Ensure `MASTER.md` is in the `docs/` folder
2. Check browser console for errors (F12)
3. Verify file permissions: `chmod 644 MASTER.md`
4. Ensure HTTP server is running in the correct directory

### Broken navigation

**Problem:** Navigation not showing or sections missing

**Solution:**
1. Check header hierarchy in `MASTER.md`
2. Ensure H1 and H2 headers are properly formatted
3. Verify no duplicate section IDs
4. Clear browser cache and reload

### Code not highlighted

**Problem:** Code blocks appear unstyled

**Solution:**
1. Ensure language is specified: \`\`\`python (not just \`\`\`)
2. Check that highlight.js is loading (view page source)
3. Verify internet connection (CDN dependency)

### Search not working

**Problem:** Search box doesn't filter items

**Solution:**
1. Check browser console for JavaScript errors
2. Ensure `script.js` is loading correctly
3. Try hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)

---

## 🚀 Quick Reference

### Adding a New Section

1. Open `MASTER.md`
2. Add a new H1 or H2 header:
   ```markdown
   ## My New Section
   
   Content goes here...
   ```
3. Save file
4. Refresh website
5. New section appears in navigation automatically!

### Reordering Sections

Simply reorder headers in `MASTER.md`. The navigation will update automatically.

### Removing a Section

Delete the header and its content from `MASTER.md`. The navigation will update on reload.

### Updating Content

Edit any content under a header in `MASTER.md`. Changes appear instantly on refresh.

---

## 📊 Performance Tips

1. **Keep MASTER.md under 2MB** for fast loading
2. **Optimize images** before adding (use PNG/JPEG compression)
3. **Use CDN for libraries** (already configured: marked.js, highlight.js)
4. **Minimize inline HTML** (stick to markdown when possible)
5. **Test on slow connections** to ensure reasonable load times

---

## 🔮 Future Enhancements

Consider adding:

- [ ] Full-text search with Lunr.js or Algolia
- [ ] Version selector (for multiple versions)
- [ ] PDF export functionality
- [ ] Copy-to-clipboard for code blocks
- [ ] Edit-on-GitHub links for each section
- [ ] Analytics integration (Google Analytics, Plausible)
- [ ] A/B testing for different documentation structures

---

## 📚 Resources

- **Markdown Guide:** https://www.markdownguide.org/
- **Marked.js:** https://marked.js.org/
- **Highlight.js:** https://highlightjs.org/
- **Inter Font:** https://rsms.me/inter/
- **GitHub Markdown:** https://guides.github.com/features/mastering-markdown/

---

## ✨ Summary

CloneAI's documentation website is designed for **simplicity** and **automation**:

1. **One file:** All docs in `MASTER.md`
2. **Auto-update:** Edit markdown, refresh browser - done!
3. **Zero build:** No compilation, bundling, or processing needed
4. **Beautiful:** Professional design with dark mode
5. **Fast:** Static files, CDN libraries, instant loading

**Just edit `MASTER.md` and the website updates itself!** 🎉

---

*Last Updated: November 1, 2025*
*Maintained by: CloneAI Team*
