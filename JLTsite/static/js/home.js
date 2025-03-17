$(document).ready(function() {
    $('.category-item').on('click', function() {
        const categoryId = $(this).data('category-id');

        // Remove 'selected' class from all category items
        $('.category-item').removeClass('selected');
        $(this).addClass('selected');

        // Fade out previous Boîte à Lunch items and then empty the container
        $('#boitess-container').fadeOut(200, function() {
            $(this).empty(); // Clear the container after fade out

            // Construct the URL for the AJAX request
            const url = `/get_boites/${categoryId}/`;

            // Send AJAX request
            $.ajax({
                url: url,
                method: 'GET',
                success: function(data) {
                    console.log(data); // Log received data for debugging
                    if (data.length > 0) {
                        // Use the first item's name as the category title
                        const categoryName = data[0].categorie.nom; 
                        $('#category-title').fadeOut(200, function() {
                            $(this).text(categoryName).fadeIn(200);
                        });

                        // Create new content for each Boîte
                        const newContent = data.map(boite => `
                            <div class="col-md-4 boite-item" style="display: none;">
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
                                            <a href="#" class="card-details">Détail de la boîte</a>
                                            <p class="card-text" style="display: none;">${boite.description}</p>
                                        </div>
                                        <p class="card-price" style="margin-left: auto;">${boite.prix || "N/A"} $</p>
                                    </div>
                                </div>
                            </div>
                        `).join('');

                        // Append new content to the container and fade in new items
                        $('#boitess-container').append(newContent).fadeIn(300, function() {
                            $('.boite-item').each(function(index) {
                                $(this).delay(index * 100).fadeIn(300); // Animate each item with a slight delay
                            });
                        });

                        // Smooth hover effect for image transition
                        $('.image-container img:last-child').css('opacity', 0);
                        $('.image-container').hover(
                            function() {
                                $(this).find('img:first').stop().fadeTo(200, 0);
                                $(this).find('img:last').stop().fadeTo(200, 1);
                            },
                            function() {
                                $(this).find('img:first').stop().fadeTo(200, 1);
                                $(this).find('img:last').stop().fadeTo(200, 0);
                            }
                        );
                    } else {
                        $('#boites-container').append('<p style="text-align:center; font-size:1.2rem;">No Boites à Lunch found for this category.</p>').fadeIn(300);
                    }
                },
                error: function() {
                    $('#boites-container').append('<p style="text-align:center; font-size:1.2rem; color:red;">An error occurred while fetching data.</p>').fadeIn(300);
                }
            });
        });
    });

    // Smooth search filtering
    $('#search-input').on('keyup', function() {
        const value = $(this).val().toLowerCase();
        $('.boite-item').each(function() {
            const titre = $(this).find('.card-title').text().toLowerCase();
            const description = $(this).find('.card-text').text().toLowerCase();
            if (titre.indexOf(value) > -1 || description.indexOf(value) > -1) {
                $(this).stop().fadeIn(200);
            } else {
                $(this).stop().fadeOut(200);
            }
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

document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.getElementById("toggle-button");
    const menuIcon = document.getElementById("menu-icon");

    toggleButton.addEventListener("click", function () {
        if (menuIcon.classList.contains("fa-bars")) {
            menuIcon.classList.remove("fa-bars");
            menuIcon.classList.add("fa-times", "rotate"); // Change to cross with rotation
        } else {
            menuIcon.classList.remove("fa-times", "rotate");
            menuIcon.classList.add("fa-bars"); // Change back to bars
        }
    });
});

