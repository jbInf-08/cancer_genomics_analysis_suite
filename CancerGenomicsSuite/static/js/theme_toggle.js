/**
 * Theme Toggle Functionality - Simon Sexton Style
 * Exact implementation matching simonsexton.com
 */

const darkColors = {
    background: "#111",
    first: "#DE29BE",
    second: "#333",
    third: "#aaa",
    fourth: "#6c63ff",
    text: "#fff",
    menu: "rgba(1, 1, 1, 0.9)",
    border: "1px solid #fff",
};

const lightColors = {
    background: "#fff",
    first: "#6c63ff",
    second: "#eee",
    third: "#333",
    fourth: "#DE29BE",
    text: "#111",
    menu: "rgba(255, 255, 255, 0.9)",
    border: "1px solid #333",
};

function selectLightMode() {
    console.log("selectLightMode called");
    localStorage.setItem("theme", "light");
    const root = document.querySelector(":root");
    if (root) {
        root.style.setProperty("--background-color", lightColors.background);
        root.style.setProperty("--first-color", lightColors.first);
        root.style.setProperty("--second-color", lightColors.second);
        root.style.setProperty("--third-color", lightColors.third);
        root.style.setProperty("--fourth-color", lightColors.fourth);
        root.style.setProperty("--text-color", lightColors.text);
        root.style.setProperty("--menu-background-color", lightColors.menu);
        root.style.setProperty("--border", lightColors.border);
    }
    
    // Update stylesheets
    const lightTheme = document.getElementById("light-theme");
    const darkTheme = document.getElementById("dark-theme");
    if (lightTheme) {
        lightTheme.media = "all";
    }
    if (darkTheme) {
        darkTheme.media = "none";
    }
}

function selectDarkMode() {
    console.log("selectDarkMode called");
    localStorage.setItem("theme", "dark");
    const root = document.querySelector(":root");
    if (root) {
        root.style.setProperty("--background-color", darkColors.background);
        root.style.setProperty("--first-color", darkColors.first);
        root.style.setProperty("--second-color", darkColors.second);
        root.style.setProperty("--third-color", darkColors.third);
        root.style.setProperty("--fourth-color", darkColors.fourth);
        root.style.setProperty("--text-color", darkColors.text);
        root.style.setProperty("--menu-background-color", darkColors.menu);
        root.style.setProperty("--border", darkColors.border);
    }
    
    // Update stylesheets
    const lightTheme = document.getElementById("light-theme");
    const darkTheme = document.getElementById("dark-theme");
    if (lightTheme) {
        lightTheme.media = "none";
    }
    if (darkTheme) {
        darkTheme.media = "all";
    }
}

// Make functions globally available immediately (before DOMContentLoaded)
// This ensures they're available for inline onclick handlers
window.selectLightMode = selectLightMode;
window.selectDarkMode = selectDarkMode;

// Initialize theme on page load
if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", () => {
        initializeTheme();
    });
} else {
    // DOM already loaded
    initializeTheme();
}

function initializeTheme() {
    console.log("Theme toggle script loaded");
    
    const theme = localStorage.getItem("theme");
    if (theme) {
        if (theme === "dark") {
            selectDarkMode();
        } else if (theme === "light") {
            selectLightMode();
        }
    } else {
        // Check system preference
        const osDayOrNight = window.matchMedia("(prefers-color-scheme: light)");
        if (osDayOrNight.matches) {
            selectLightMode();
        } else {
            selectDarkMode();
        }
    }
    
    // Attach onclick handlers to icons (simonsexton style)
    const lightIcon = document.getElementById("light-mode-icon");
    const darkIcon = document.getElementById("dark-mode-icon");
    
    if (lightIcon) {
        lightIcon.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log("Light icon clicked");
            selectLightMode();
        };
        console.log("Light icon handler attached");
    } else {
        console.log("Light icon not found");
    }
    
    if (darkIcon) {
        darkIcon.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log("Dark icon clicked");
            selectDarkMode();
        };
        console.log("Dark icon handler attached");
    } else {
        console.log("Dark icon not found");
    }
}
