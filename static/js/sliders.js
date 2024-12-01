const galleryContainer = document.querySelector('.gallery-container');
const galleryItems = document.querySelectorAll('.gallery-item');

class Carousel {
    constructor(container, items) {
        this.carouselContainer = container;
        this.carouselArray = [...items];
        this.init();
    }

    // Update the gallery to apply the correct classes
    updateGallery() {
        this.carouselArray.forEach(el => {
            el.classList.remove(
                'gallery-item-1',
                'gallery-item-2',
                'gallery-item-3',
                'gallery-item-4',
                'gallery-item-5',
                'gallery-item-6',
                'gallery-item-7'
            );
        });

        this.carouselArray.slice(0, 7).forEach((el, i) => {
            el.classList.add(`gallery-item-${i + 1}`);
        });
    }

    // Automatically rotate the gallery items
    autoSlide() {
        setInterval(() => {
            this.carouselArray.push(this.carouselArray.shift()); // Rotate the array
            this.updateGallery(); // Refresh the gallery display
        }, 2000); // Adjust the interval as needed
    }

    // Initialize the gallery
    init() {
        this.updateGallery();
        this.autoSlide();
    }
}

// Instantiate the Carousel
const exampleCarousel = new Carousel(galleryContainer, galleryItems);
