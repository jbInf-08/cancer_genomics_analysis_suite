/**
 * Sidebar Toggle Functionality - Fixed Version
 * Handles opening/closing the sidebar
 */

function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.add('open');
        localStorage.setItem('sidebarOpen', 'true');
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.remove('open');
        localStorage.setItem('sidebarOpen', 'false');
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('open')) {
        closeSidebar();
    } else {
        openSidebar();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    
    // Initialize sidebar state
    const sidebarOpen = localStorage.getItem('sidebarOpen') === 'true';
    if (sidebarOpen && sidebar) {
        openSidebar();
    }
    
    // Attach click handler to toggle button
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleSidebar();
        });
    }
    
    // Handle sidebar link clicks to switch tabs
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const tabName = this.getAttribute('data-tab');
            
            // Update active link
            sidebarLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Find and click the corresponding Dash tab
            if (tabName) {
                // Dash tabs use specific structure - find the tab by label
                const tabs = document.getElementById('tabs');
                if (tabs) {
                    // Wait a bit for Dash to be ready
                    setTimeout(() => {
                        const tabElements = tabs.querySelectorAll('[role="tab"]');
                        tabElements.forEach(tab => {
                            const tabLabel = tab.textContent.trim();
                            if (tabLabel === tabName) {
                                tab.click();
                                // Also trigger Dash's change event
                                const event = new Event('change', { bubbles: true });
                                tabs.dispatchEvent(event);
                            }
                        });
                    }, 100);
                }
            }
            
            // Close sidebar on mobile after selection
            if (window.innerWidth <= 768) {
                setTimeout(() => closeSidebar(), 300);
            }
        });
    });
    
    // Sync active tab with sidebar when Dash updates tabs
    function syncActiveTab() {
        const tabs = document.getElementById('tabs');
        if (tabs) {
            const activeTab = tabs.querySelector('[role="tab"][aria-selected="true"]');
            if (activeTab) {
                const activeTabLabel = activeTab.textContent.trim();
                sidebarLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('data-tab') === activeTabLabel) {
                        link.classList.add('active');
                    }
                });
            }
        }
    }
    
    // Watch for tab changes
    const tabs = document.getElementById('tabs');
    if (tabs) {
        // Use MutationObserver to watch for tab changes
        const observer = new MutationObserver(syncActiveTab);
        observer.observe(tabs, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['aria-selected']
        });
        
        // Also listen for clicks on tabs
        tabs.addEventListener('click', function() {
            setTimeout(syncActiveTab, 100);
        });
    }
    
    // Initial sync
    setTimeout(syncActiveTab, 500);
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && 
            sidebar && 
            sidebar.classList.contains('open') && 
            !sidebar.contains(e.target) && 
            sidebarToggle && 
            !sidebarToggle.contains(e.target)) {
            closeSidebar();
        }
    });
    
    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });
});

// Make functions globally available
window.SidebarToggle = {
    open: openSidebar,
    close: closeSidebar,
    toggle: toggleSidebar
};
