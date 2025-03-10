document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('turnPageBtn').addEventListener('click', function() {
        const pageEffect = document.getElementById('pageTurnEffect');
        pageEffect.classList.remove('hidden');
        setTimeout(() => {
            pageEffect.classList.add('show');
        }, 100);

        // Uncomment the following line to navigate to a new page after the effect
        // setTimeout(() => window.location.href = 'newpage.html', 1000);
    });
});
