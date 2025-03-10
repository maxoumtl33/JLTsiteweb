$(document).ready(function() {
    $('.category-item').on('click', function() {
        const categoryId = $(this).data('category-id');

        // Remove 'selected' class from all category items
        $('.category-item').removeClass('selected');

        // Add 'selected' class to the clicked category
        $(this).addClass('selected');

        // Clear the previous BoiteALunch items
        $('#boites-container').empty();

        // Construct the URL for the AJAX request
        const url = `/get_boites/${categoryId}/`;

        // Send AJAX request to get BoiteALunch items for the selected category
        $.ajax({
            url: url,
            method: 'GET',
            success: function(data) {
                // Check if there are results
                if (data.length > 0) {
                    const categoryName = data[0].categorie.nom;
                    $('#category-title').text(`${categoryName}`); // Update title

                    data.forEach(function(boite) {
                        $('#boites-container').append(`
                        <div class="col-md-4 boite-item">
                            <div class="card" style="width: 25rem; margin: 10px; border: none; background: transparent;">
                                <div class="image-container">
                                    <img src="${boite.photo1}" 
                                         alt="${boite.nom} Photo 1" 
                                         class="card-img-top" 
                                         style="cursor: pointer;">
                                    <img src="${boite.photo2}" 
                                         alt="${boite.nom} Photo 2" 
                                         class="card-img-top hover-img">
                                </div>
                                <div class="card-body" style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <h2 class="card-title" style="color: #FDC000;">${boite.nom}</h2>
                                        <a href="${boite.detail_url}" class="card-details">Détail de la boîte</a>
                                        <p class="card-text" style="display: none;">${boite.description}</p>
                                    </div>
                                    <p class="card-price" style="margin-left: auto;">${boite.prix} $</p>
                                </div>
                            </div>
                        </div>
                        `);
                    });

                    // Add hover effect for images
                    $('.image-container').hover(
                        function() {
                            $(this).find('img:first').css('opacity', 0);  // Hide first image
                            $(this).find('img:last').css('opacity', 1);   // Show second image
                        }, 
                        function() {
                            $(this).find('img:first').css('opacity', 1);   // Show first image
                            $(this).find('img:last').css('opacity', 0);    // Hide second image
                        }
                    );
                } else {
                    $('#boites-container').append('<p>No Boites à Lunch found for this category.</p>');
                }
            },
            error: function() {
                $('#boites-container').append('<p>An error occurred while fetching data.</p>');
            }
        });
    });

   // Search functionality for name and description
   $('#search-input').on('keyup', function() {
    const value = $(this).val().toLowerCase(); // Get the search input value
    $('.boite-item').filter(function() {
        const titre = $(this).find('.card-title').text().toLowerCase(); // Get the title
        const description = $(this).find('.card-text').text().toLowerCase(); // Get the description
        // Show the item if the search term matches the title or the description
        $(this).toggle(titre.indexOf(value) > -1 || description.indexOf(value) > -1);
    });
});
});






$(document).ready(function() {
    var categories = document.getElementById("categories");
    var sticky = categories.offsetTop; // Get the original offset position of the categories div

    $(window).scroll(function() {
        if (window.pageYOffset > sticky) {
            categories.classList.add("sticky"); // Add sticky class when scrolled beyond
        } else {
            categories.classList.remove("sticky"); // Remove sticky class when not scrolled beyond
        }
    });
});


document.querySelector('a[href="#category-title"]').addEventListener('click', function(event) {
    event.preventDefault(); // Prevent default anchor click behavior
    const target = document.querySelector('#category-title');
    
    // Smooth scroll to the target section
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

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





