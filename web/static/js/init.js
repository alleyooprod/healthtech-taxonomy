/**
 * App initialization: window.onload and mermaid setup.
 */

// Mermaid init (before DOMContentLoaded for early setup)
document.addEventListener('DOMContentLoaded', () => {
    if (window.mermaid) {
        mermaid.initialize({
            startOnLoad: false,
            theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default',
            securityLevel: 'strict',
        });
    }
});

// Main app init
window.onload = () => {
    initTheme();
    initNotyf();
    initDayjs();
    initHotkeys();
    startHeartbeat();
    loadProjects();
};
