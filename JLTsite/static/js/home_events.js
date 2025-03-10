document.addEventListener('DOMContentLoaded', function() {
    const pageEffect = document.getElementById('pageTurnEffect');
    
    // Ensure it resets when coming back to the page
    pageEffect.style.visibility = "hidden";
    pageEffect.style.opacity = "0";
    pageEffect.style.transform = "rotateY(90deg)";
    
    document.getElementById('turnPageBtn').addEventListener('click', function() {
        console.log('Button clicked'); // Logging button click
        
        pageEffect.style.visibility = "visible"; 
        pageEffect.style.opacity = "1"; 
        pageEffect.style.transform = "rotateY(0)";
        
        console.log('Page effect triggered'); // Logging transition

        // Navigate to another page after animation completes
        const targetUrl = turnPageBtn.getAttribute('data-target-url');
        setTimeout(() => {
            window.location.href = targetUrl; // Change to your actual page URL
        }, 1000); // Wait for the animation to finish
    });
});