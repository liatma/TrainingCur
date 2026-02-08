// Frontend JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const messageEl = document.getElementById('message');
    const loadBtn = document.getElementById('loadBtn');
    
    async function loadMessage() {
        try {
            loadBtn.disabled = true;
            loadBtn.textContent = 'Loading...';
            messageEl.textContent = 'Loading...';
            
            const response = await fetch('/api/hello');
            const data = await response.json();
            
            messageEl.textContent = data.message;
        } catch (error) {
            messageEl.textContent = 'Error loading message: ' + error.message;
        } finally {
            loadBtn.disabled = false;
            loadBtn.textContent = 'Load Message';
        }
    }
    
    loadBtn.addEventListener('click', loadMessage);
    
    // Load message on page load
    loadMessage();
});

