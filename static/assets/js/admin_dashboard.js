document.addEventListener("DOMContentLoaded", function() {
        const wrapper = document.getElementById('wrapper');
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
        const overlay = document.getElementById('sidebar-overlay');

        function toggleSidebar() {
            wrapper.classList.toggle('toggled');
        }

        // Toggle button in navbar
        sidebarToggle.addEventListener('click', toggleSidebar);

        // Close buttons (X and Overlay)
        if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', toggleSidebar);
        if (overlay) overlay.addEventListener('click', toggleSidebar);

        // Handle window resize: Auto-close sidebar if switching from mobile to desktop
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                wrapper.classList.remove('toggled');
            }
        });
    });