// AUGIS Client Scripting & Interactive Utilities
document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Toggle for Mobile / Tablet
    const sidebarToggle = document.getElementById('sidebarToggle');
    const appSidebar = document.querySelector('.app-sidebar');

    if (sidebarToggle && appSidebar) {
        sidebarToggle.addEventListener('click', function () {
            appSidebar.classList.toggle('show');
        });

        // Close sidebar on outer click on mobile
        document.addEventListener('click', function (e) {
            if (window.innerWidth < 992 && 
                !appSidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target) && 
                appSidebar.classList.contains('show')) {
                appSidebar.classList.remove('show');
            }
        });
    }

    // 2. Dark / Light Theme Toggle
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const currentTheme = localStorage.getItem('augis_theme') || 'light';
    
    if (currentTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        if (themeToggleBtn) themeToggleBtn.innerHTML = '<i class="bi bi-sun-fill text-warning"></i>';
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            const activeTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('augis_theme', newTheme);

            if (newTheme === 'dark') {
                themeToggleBtn.innerHTML = '<i class="bi bi-sun-fill text-warning"></i>';
            } else {
                themeToggleBtn.innerHTML = '<i class="bi bi-moon-stars"></i>';
            }
        });
    }

    // 3. Quick Global Search Shortcut (Press '/' to jump to search)
    const searchInput = document.querySelector('input[name="q"]');
    document.addEventListener('keydown', function (e) {
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        }
    });

    // 4. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (err) {}
        }, 5000);
    });
});
