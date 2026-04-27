document.addEventListener('DOMContentLoaded', function() {
    var sidebarToggle = document.getElementById('sidebarToggle');
    // New: Get the close button element
    var sidebarCloseBtn = document.getElementById('sidebarCloseBtn'); 
    
    var wrapper = document.getElementById('wrapper');
    // var pageContent = document.getElementById('page-content-wrapper'); <-- No longer needed

    // Function to toggle the sidebar state
    function toggleSidebar(e) {
        if (e) e.preventDefault();
        wrapper.classList.toggle('toggled');
    }

    if (sidebarToggle && wrapper) {
        // Attach toggle function to the hamburger icon
        sidebarToggle.addEventListener('click', toggleSidebar);
        
        // Attach toggle function to the new close button
        if (sidebarCloseBtn) {
            sidebarCloseBtn.addEventListener('click', toggleSidebar);
        }

        // Auto-collapse sidebar on small screens when page loads
        if (window.innerWidth < 768) {
            wrapper.classList.add('toggled');
        }
        
        // --- REMOVED SECTION ---
        /* // Dismissal via outside click (for mobile) - REMOVED
        pageContent.addEventListener('click', function(e) {
            if (window.innerWidth < 768 && !wrapper.classList.contains('toggled')) {
                wrapper.classList.add('toggled');
            }
        }); 
        */
    }
});