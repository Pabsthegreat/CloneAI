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
        // Parse the markdown into sections based on H1 and H2 headers
        const lines = markdown.split('\n');
        let currentSection = null;
        let currentSubsection = null;
        const sections = [];
        let contentBuffer = [];

        lines.forEach((line, index) => {
            // H1 headers create main sections
            if (line.startsWith('# ') && !line.startsWith('## ')) {
                if (currentSection) {
                    this.saveSection(sections, currentSection, contentBuffer);
                    contentBuffer = [];
                }
                
                const title = line.replace(/^#\s+/, '').trim();
                const id = this.createId(title);
                currentSection = { id, title, subsections: [], content: [] };
                currentSubsection = null;
            }
            // H2 headers create subsections
            else if (line.startsWith('## ')) {
                if (currentSubsection) {
                    currentSection.subsections.push({
                        ...currentSubsection,
                        content: contentBuffer.join('\n')
                    });
                    contentBuffer = [];
                }
                
                const title = line.replace(/^##\s+/, '').trim();
                const id = this.createId(title);
                currentSubsection = { id, title };
                contentBuffer.push(line);
            }
            else {
                contentBuffer.push(line);
            }
        });

        // Save the last section
        if (currentSection) {
            this.saveSection(sections, currentSection, contentBuffer);
        }

        return { sections, fullContent: markdown };
    }

    saveSection(sections, section, contentBuffer) {
        if (section.subsections.length === 0) {
            section.content = contentBuffer.join('\n');
        } else {
            // Save last subsection
            section.subsections.push({
                ...section.subsections[section.subsections.length - 1],
                content: contentBuffer.join('\n')
            });
        }
        sections.push(section);
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
        const { sections, fullContent } = await this.parser.loadMarkdown();
        this.sections = sections;
        this.renderNavigation();
        this.renderContent(fullContent);
        this.setupSearch();
        this.setupScrollSpy();
        this.handleHashNavigation();
    }

    renderNavigation() {
        const navSections = document.getElementById('nav-sections');
        navSections.innerHTML = '';

        // Group sections by category
        const categories = this.categorizeSection();
        
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
                    this.scrollToSection(section.id);
                    if (window.innerWidth <= 768) {
                        sidebar.classList.remove('active');
                    }
                });
                
                li.appendChild(a);
                ul.appendChild(li);
            });

            sectionDiv.appendChild(ul);
            navSections.appendChild(sectionDiv);
        });
    }

    categorizeSection() {
        // Define categories based on content
        const categories = [
            {
                name: 'Getting Started',
                keywords: ['quick start', 'installation', 'setup', 'prerequisites', 'what is'],
                items: []
            },
            {
                name: 'User Guide',
                keywords: ['commands', 'usage', 'email', 'calendar', 'document', 'natural language', 'workflow'],
                items: []
            },
            {
                name: 'Architecture',
                keywords: ['architecture', 'system', 'components', 'flow', 'tiered', 'workflow system'],
                items: []
            },
            {
                name: 'Advanced Features',
                keywords: ['voice', 'scheduler', 'priority', 'web search', 'generation', 'gpt'],
                items: []
            },
            {
                name: 'Development',
                keywords: ['testing', 'security', 'implementation', 'migration', 'token'],
                items: []
            },
            {
                name: 'Reference',
                keywords: ['troubleshooting', 'reference', 'tips', 'best practices', 'command reference'],
                items: []
            }
        ];

        // Categorize sections
        this.sections.forEach(section => {
            let categorized = false;
            const lowerTitle = section.title.toLowerCase();

            for (const category of categories) {
                if (category.keywords.some(keyword => lowerTitle.includes(keyword))) {
                    category.items.push(section);
                    categorized = true;
                    break;
                }
            }

            // If not categorized, add to reference
            if (!categorized) {
                categories[categories.length - 1].items.push(section);
            }
        });

        // Filter out empty categories
        return categories.filter(cat => cat.items.length > 0);
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
    const parser = new DocumentationParser();
    const nav = new NavigationManager(parser);
    await nav.initialize();
    
    console.log('📚 CloneAI Documentation loaded successfully!');
});
