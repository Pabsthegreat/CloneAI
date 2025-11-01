// ========================================
// Documentation Website JavaScript
// Auto-loads content from MASTER.md
// ========================================

// Theme Management
const themeToggle = document.getElementById('theme-toggle');
const html = document.documentElement;

// Load saved theme or default to light
const savedTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', savedTheme);

themeToggle.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
});

// Mobile Menu Toggle
const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
const sidebar = document.getElementById('sidebar');

mobileMenuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('active');
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
            sidebar.classList.remove('active');
        }
    }
});

// ========================================
// Markdown Parser with Section Detection
// ========================================

// Configure marked.js
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(code, { language: lang }).value;
            } catch (err) {}
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

class DocumentationParser {
    constructor() {
        this.sections = [];
        this.currentSection = null;
    }

    async loadMarkdown() {
        try {
            const response = await fetch('MASTER.md');
            const markdown = await response.text();
            return this.parseMarkdown(markdown);
        } catch (error) {
            console.error('Error loading MASTER.md:', error);
            return { sections: [], content: '<p>Error loading documentation. Please ensure MASTER.md exists.</p>' };
        }
    }

    parseMarkdown(markdown) {
        // Parse the markdown into sections based on headers
        // Your markdown uses ## for H1 and ### for H2
        const lines = markdown.split('\n');
        const sections = [];
        let inCodeBlock = false;

        lines.forEach((line) => {
            // Track code blocks to skip them
            if (line.trim().startsWith('```')) {
                inCodeBlock = !inCodeBlock;
                return;
            }

            // Skip lines inside code blocks
            if (inCodeBlock) {
                return;
            }

            // Match H1 headers (## Title) - NOT preceded by #
            const h1Match = line.match(/^##\s+([^#].+)$/);
            if (h1Match) {
                const title = h1Match[1].trim();
                // Skip if title is empty or looks like a comment
                if (title && !title.startsWith('=') && title.length > 0) {
                    const id = this.createId(title);
                    sections.push({ id, title, level: 1 });
                }
                return;
            }

            // Match H2 headers (### Title)
            const h2Match = line.match(/^###\s+(.+)$/);
            if (h2Match) {
                const title = h2Match[1].trim();
                if (title && title.length > 0) {
                    const id = this.createId(title);
                    sections.push({ id, title, level: 2 });
                }
                return;
            }
        });

        console.log('Parsed sections:', sections.length);
        return { sections, fullContent: markdown };
    }



    createId(text) {
        return text
            .toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .trim();
    }

    renderMarkdown(markdown) {
        // Use marked.js for proper markdown rendering
        return marked.parse(markdown);
    }
}

// ========================================
// Navigation & Content Management
// ========================================

class NavigationManager {
    constructor(parser) {
        this.parser = parser;
        this.sections = [];
    }

    async initialize() {
        console.log('Initializing NavigationManager...');
        const { sections, fullContent } = await this.parser.loadMarkdown();
        console.log('Loaded', sections.length, 'sections');
        this.sections = sections;
        this.renderNavigation();
        this.renderContent(fullContent);
        this.setupSearch();
        this.setupScrollSpy();
        this.handleHashNavigation();
        console.log('NavigationManager initialized!');
    }

    renderNavigation() {
        const navSections = document.getElementById('nav-sections');
        if (!navSections) {
            console.error('nav-sections element not found!');
            return;
        }
        
        navSections.innerHTML = '';

        console.log('Rendering navigation with', this.sections.length, 'sections');

        // Group sections by category
        const categories = this.categorizeSection();
        console.log('Categories:', categories);
        
        categories.forEach(category => {
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'nav-section';
            
            const title = document.createElement('div');
            title.className = 'nav-section-title';
            title.textContent = category.name;
            sectionDiv.appendChild(title);

            const ul = document.createElement('ul');
            ul.className = 'nav-items';

            category.items.forEach(section => {
                const li = document.createElement('li');
                li.className = 'nav-item';
                
                const a = document.createElement('a');
                a.href = `#${section.id}`;
                a.className = 'nav-link';
                a.textContent = section.title;
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log('Clicked:', section.id);
                    this.scrollToSection(section.id);
                    const sidebar = document.getElementById('sidebar');
                    if (window.innerWidth <= 768 && sidebar) {
                        sidebar.classList.remove('active');
                    }
                });
                
                li.appendChild(a);
                ul.appendChild(li);
            });

            sectionDiv.appendChild(ul);
            navSections.appendChild(sectionDiv);
        });
        
        console.log('Navigation rendered successfully!');
    }

    categorizeSection() {
        // Simple approach: just show all H1 sections, grouped logically
        const allSections = [];
        
        this.sections.forEach(section => {
            // Only show H1 level sections in nav
            if (section.level === 1) {
                allSections.push(section);
            }
        });

        // Return as a single category
        return [{
            name: 'Documentation',
            items: allSections
        }];
    }

    renderContent(markdown) {
        const content = document.getElementById('content');
        content.innerHTML = this.parser.renderMarkdown(markdown);
        this.generateTableOfContents();
        this.addAnchorLinks();
    }

    generateTableOfContents() {
        const content = document.getElementById('content');
        const headings = content.querySelectorAll('h2, h3');
        const tocNav = document.getElementById('toc-nav');
        tocNav.innerHTML = '';

        headings.forEach((heading, index) => {
            const id = heading.textContent.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');
            heading.id = id;

            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = `#${id}`;
            a.textContent = heading.textContent;
            a.style.paddingLeft = heading.tagName === 'H3' ? 'calc(var(--spacing-unit) * 4)' : 'calc(var(--spacing-unit) * 2)';
            
            a.addEventListener('click', (e) => {
                e.preventDefault();
                this.scrollToSection(id);
            });

            li.appendChild(a);
            tocNav.appendChild(li);
        });
    }

    addAnchorLinks() {
        const content = document.getElementById('content');
        const headings = content.querySelectorAll('h1, h2, h3, h4, h5, h6');
        
        headings.forEach(heading => {
            if (!heading.id) {
                const id = heading.textContent.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');
                heading.id = id;
            }
        });
    }

    scrollToSection(id) {
        const element = document.getElementById(id);
        if (element) {
            const offset = 80; // Account for fixed header
            const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
            window.scrollTo({
                top: elementPosition - offset,
                behavior: 'smooth'
            });
            
            // Update URL without triggering scroll
            history.pushState(null, null, `#${id}`);
            this.updateActiveLinks();
        }
    }

    setupSearch() {
        const searchInput = document.getElementById('search');
        const navItems = document.querySelectorAll('.nav-link');

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            
            navItems.forEach(item => {
                const text = item.textContent.toLowerCase();
                const listItem = item.closest('.nav-item');
                
                if (text.includes(query) || query === '') {
                    listItem.style.display = 'block';
                } else {
                    listItem.style.display = 'none';
                }
            });
        });
    }

    setupScrollSpy() {
        const observerOptions = {
            rootMargin: '-80px 0px -80% 0px',
            threshold: 0
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.updateActiveLinks(entry.target.id);
                }
            });
        }, observerOptions);

        const content = document.getElementById('content');
        const headings = content.querySelectorAll('h1, h2, h3');
        headings.forEach(heading => observer.observe(heading));
    }

    updateActiveLinks(activeId = null) {
        const navLinks = document.querySelectorAll('.nav-link');
        const tocLinks = document.querySelectorAll('#toc-nav a');
        
        navLinks.forEach(link => link.classList.remove('active'));
        tocLinks.forEach(link => link.classList.remove('active'));

        if (activeId) {
            const activeNavLink = document.querySelector(`.nav-link[href="#${activeId}"]`);
            const activeTocLink = document.querySelector(`#toc-nav a[href="#${activeId}"]`);
            
            if (activeNavLink) activeNavLink.classList.add('active');
            if (activeTocLink) activeTocLink.classList.add('active');
        }
    }

    handleHashNavigation() {
        window.addEventListener('load', () => {
            if (window.location.hash) {
                const id = window.location.hash.substring(1);
                setTimeout(() => this.scrollToSection(id), 100);
            }
        });
    }
}

// ========================================
// Initialize Application
// ========================================

document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('Starting initialization...');
        const parser = new DocumentationParser();
        const nav = new NavigationManager(parser);
        await nav.initialize();
        console.log('📚 CloneAI Documentation loaded successfully!');
    } catch (error) {
        console.error('Error initializing documentation:', error);
        const content = document.getElementById('content');
        if (content) {
            content.innerHTML = `<div style="padding: 20px; color: red;">
                <h2>Error Loading Documentation</h2>
                <p>${error.message}</p>
                <pre>${error.stack}</pre>
            </div>`;
        }
    }
});
