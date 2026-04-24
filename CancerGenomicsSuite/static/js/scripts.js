/**
 * Cancer Genomics Analysis Suite - Main JavaScript
 * Handles core functionality, theme management, and UI interactions
 */

// Global namespace for the application
window.CancerGenomicsSuite = {
    version: '1.0.0',
    initialized: false,
    theme: 'light',
    sidebarOpen: false
};

/**
 * Initialize the application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Main application initialization
 */
function initializeApp() {
    console.log('Initializing Cancer Genomics Analysis Suite...');
    
    // Initialize theme system
    initializeTheme();
    
    // Initialize sidebar
    initializeSidebar();
    
    // Initialize tooltips and interactive elements
    initializeTooltips();
    
    // Initialize data tables
    initializeDataTables();
    
    // Initialize charts
    initializeCharts();
    
    // Set up event listeners
    setupEventListeners();
    
    // Mark as initialized
    window.CancerGenomicsSuite.initialized = true;
    
    console.log('Cancer Genomics Analysis Suite initialized successfully');
}

/**
 * Theme Management
 */
function initializeTheme() {
    const savedTheme = localStorage.getItem('cgs-theme') || 'light';
    setTheme(savedTheme);
    
    // Listen for theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Listen for system theme changes
    if (window.matchMedia) {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', function(e) {
            if (!localStorage.getItem('cgs-theme')) {
                setTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
}

function setTheme(theme) {
    const body = document.body;
    const themeToggle = document.getElementById('theme-toggle');
    
    // Remove existing theme classes
    body.classList.remove('light-theme', 'dark-theme');
    
    // Add new theme class
    body.classList.add(`${theme}-theme`);
    body.setAttribute('data-theme', theme);
    
    // Update toggle button
    if (themeToggle) {
        themeToggle.textContent = theme === 'dark' ? '☀️' : '🌓';
        themeToggle.title = `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`;
    }
    
    // Save theme preference
    localStorage.setItem('cgs-theme', theme);
    window.CancerGenomicsSuite.theme = theme;
    
    // Update external libraries
    updateExternalLibraryThemes(theme);
    
    // Dispatch theme change event
    const event = new CustomEvent('themeChanged', { detail: { theme } });
    document.dispatchEvent(event);
}

function toggleTheme() {
    const currentTheme = window.CancerGenomicsSuite.theme;
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

function updateExternalLibraryThemes(theme) {
    // Update Plotly theme
    if (window.Plotly) {
        window.plotlyTheme = theme === 'dark' ? 'plotly_dark' : 'plotly';
    }
    
    // Update Chart.js theme
    if (window.Chart) {
        Chart.defaults.color = theme === 'dark' ? '#f1f5f9' : '#1e293b';
        Chart.defaults.borderColor = theme === 'dark' ? '#334155' : '#e2e8f0';
        Chart.defaults.backgroundColor = theme === 'dark' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(37, 99, 235, 0.1)';
    }
}

/**
 * Sidebar Management
 */
function initializeSidebar() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    
    // Check saved sidebar state
    const savedState = localStorage.getItem('cgs-sidebar-open') === 'true';
    if (savedState) {
        openSidebar();
    }
    
    // Toggle sidebar
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            if (window.CancerGenomicsSuite.sidebarOpen) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }
    
    // Handle sidebar links
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            
            // Update active state
            sidebarLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Switch to corresponding tab
            if (tabName) {
                switchToTab(tabName);
            }
            
            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                closeSidebar();
            }
        });
    });
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && 
            window.CancerGenomicsSuite.sidebarOpen && 
            !sidebar.contains(e.target) && 
            !sidebarToggle.contains(e.target)) {
            closeSidebar();
        }
    });
    
    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && window.CancerGenomicsSuite.sidebarOpen) {
            closeSidebar();
        }
    });
}

function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar) {
        sidebar.classList.add('open');
        sidebar.classList.add('slide-in-left');
    }
    if (mainContent) {
        mainContent.classList.add('sidebar-open');
    }
    
    window.CancerGenomicsSuite.sidebarOpen = true;
    localStorage.setItem('cgs-sidebar-open', 'true');
    
    // Update button state
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.setAttribute('aria-expanded', 'true');
        sidebarToggle.title = 'Close Sidebar';
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar) {
        sidebar.classList.remove('open');
        sidebar.classList.remove('slide-in-left');
    }
    if (mainContent) {
        mainContent.classList.remove('sidebar-open');
    }
    
    window.CancerGenomicsSuite.sidebarOpen = false;
    localStorage.setItem('cgs-sidebar-open', 'false');
    
    // Update button state
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.setAttribute('aria-expanded', 'false');
        sidebarToggle.title = 'Open Sidebar';
    }
}

/**
 * Tab Management
 */
function switchToTab(tabName) {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Update tab buttons
    tabButtons.forEach(button => {
        if (button.getAttribute('data-value') === tabName) {
            button.classList.add('tab-button--selected');
            button.click(); // Trigger Dash callback if present
        } else {
            button.classList.remove('tab-button--selected');
        }
    });
    
    // Update tab contents
    tabContents.forEach(content => {
        if (content.getAttribute('data-tab') === tabName) {
            content.style.display = 'block';
            content.classList.add('fade-in');
        } else {
            content.style.display = 'none';
            content.classList.remove('fade-in');
        }
    });
}

/**
 * Tooltip System
 */
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const text = e.target.getAttribute('data-tooltip');
    if (!text) return;
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
        position: absolute;
        background: var(--bg-sidebar);
        color: var(--text-inverse);
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 14px;
        z-index: 10000;
        pointer-events: none;
        box-shadow: var(--shadow-lg);
        max-width: 200px;
        word-wrap: break-word;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    e.target._tooltip = tooltip;
}

function hideTooltip(e) {
    if (e.target._tooltip) {
        document.body.removeChild(e.target._tooltip);
        delete e.target._tooltip;
    }
}

/**
 * Data Table Enhancements
 */
function initializeDataTables() {
    const tables = document.querySelectorAll('.data-table');
    
    tables.forEach(table => {
        // Add sorting functionality
        const headers = table.querySelectorAll('th[data-sortable]');
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                sortTable(table, header);
            });
        });
        
        // Add search functionality
        const searchInput = table.parentElement.querySelector('.table-search');
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                filterTable(table, this.value);
            });
        }
    });
}

function sortTable(table, header) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const columnIndex = Array.from(header.parentElement.children).indexOf(header);
    const isAscending = header.classList.contains('sort-asc');
    
    // Remove existing sort classes
    header.parentElement.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Add new sort class
    header.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
    
    // Sort rows
    rows.sort((a, b) => {
        const aValue = a.children[columnIndex].textContent.trim();
        const bValue = b.children[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? bNum - aNum : aNum - bNum;
        }
        
        // Sort as strings
        return isAscending ? bValue.localeCompare(aValue) : aValue.localeCompare(bValue);
    });
    
    // Reorder rows in DOM
    rows.forEach(row => tbody.appendChild(row));
}

function filterTable(table, searchTerm) {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matches = text.includes(searchTerm.toLowerCase());
        row.style.display = matches ? '' : 'none';
    });
}

/**
 * Chart Management
 */
function initializeCharts() {
    // Initialize any existing charts
    const chartContainers = document.querySelectorAll('.chart-container');
    
    chartContainers.forEach(container => {
        const chartType = container.getAttribute('data-chart-type');
        if (chartType) {
            createChart(container, chartType);
        }
    });
}

function createChart(container, type, data, options = {}) {
    const canvas = container.querySelector('canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Default options
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: getComputedStyle(document.body).getPropertyValue('--text-primary')
                }
            }
        },
        scales: {
            x: {
                ticks: {
                    color: getComputedStyle(document.body).getPropertyValue('--text-secondary')
                },
                grid: {
                    color: getComputedStyle(document.body).getPropertyValue('--border-color')
                }
            },
            y: {
                ticks: {
                    color: getComputedStyle(document.body).getPropertyValue('--text-secondary')
                },
                grid: {
                    color: getComputedStyle(document.body).getPropertyValue('--border-color')
                }
            }
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    if (window.Chart) {
        return new Chart(ctx, {
            type: type,
            data: data,
            options: finalOptions
        });
    }
}

/**
 * Event Listeners
 */
function setupEventListeners() {
    // Window resize handler
    window.addEventListener('resize', handleResize);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Theme change handler
    document.addEventListener('themeChanged', handleThemeChange);
}

function handleResize() {
    // Close sidebar on mobile when resizing to desktop
    if (window.innerWidth > 768 && window.CancerGenomicsSuite.sidebarOpen) {
        // Keep sidebar open on desktop
    } else if (window.innerWidth <= 768 && window.CancerGenomicsSuite.sidebarOpen) {
        closeSidebar();
    }
}

function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + T: Toggle theme
    if ((e.ctrlKey || e.metaKey) && e.key === 't') {
        e.preventDefault();
        toggleTheme();
    }
    
    // Ctrl/Cmd + B: Toggle sidebar
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        if (window.CancerGenomicsSuite.sidebarOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }
}

function handleThemeChange(e) {
    // Update any charts or visualizations when theme changes
    updateExternalLibraryThemes(e.detail.theme);
}

/**
 * Utility Functions
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: var(--bg-primary);
        color: var(--text-primary);
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        border-left: 4px solid var(--${type === 'error' ? 'error' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'accent'}-color);
        transform: translateX(100%);
        transition: transform 0.3s ease-in-out;
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto remove
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentElement) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, duration);
}

function showLoading(element, show = true) {
    if (show) {
        element.classList.add('loading');
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        spinner.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 1000;
        `;
        element.style.position = 'relative';
        element.appendChild(spinner);
    } else {
        element.classList.remove('loading');
        const spinner = element.querySelector('.spinner');
        if (spinner) {
            element.removeChild(spinner);
        }
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export functions for external use
window.CancerGenomicsSuite = {
    ...window.CancerGenomicsSuite,
    setTheme,
    toggleTheme,
    openSidebar,
    closeSidebar,
    switchToTab,
    showNotification,
    showLoading,
    createChart,
    debounce,
    throttle
};
