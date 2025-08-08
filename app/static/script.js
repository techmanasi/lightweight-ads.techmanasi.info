// --- App State ---
const appRoot = document.getElementById('app-root');

// --- API Functions ---
async function fetchProducts() {
    const response = await fetch('/api/products');
    if (!response.ok) {
        throw new Error('Failed to fetch products');
    }
    return response.json();
}

async function fetchProductDetail(id) {
    const response = await fetch(`/api/products/${id}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch product detail for id: ${id}`);
    }
    return response.json();
}

// --- Rendering Functions ---
function renderProductList(products) {
    const productListHTML = `
        <ul id="product-list">
            ${products.map(product => `
                <li class="product-item" data-product-id="${product.id}">
                    <img src="${product.thumbnail_url}" alt="${product.name}">
                    <h3>${product.name}</h3>
                    <a href="${product.purchase_link}" target="_blank" rel="noopener noreferrer" class="purchase-button">Purchase</a>
                </li>
            `).join('')}
        </ul>
    `;
    appRoot.innerHTML = productListHTML;

    // Add event listeners to each product item
    document.querySelectorAll('.product-item').forEach(item => {
        item.addEventListener('click', (e) => {
            const target = e.target;
            // Don't navigate if the purchase link was clicked
            if (target.classList.contains('purchase-button')) {
                return;
            }
            const productId = item.getAttribute('data-product-id');
            if (productId) {
                // Use hash-based routing to show the detail page
                window.location.hash = `product/${productId}`;
            }
        });
    });
}

function renderProductDetail(product) {
    const tagsHTML = product.tags.map(tag => `<span class="tag">${tag}</span>`).join('');
    const productDetailHTML = `
        <div id="product-detail">
            <a href="#" class="back-button">&larr; Back to list</a>
            <img src="${product.image_url}" alt="${product.name}">
            <h2>${product.name}</h2>
            <p>${product.description}</p>
            <div class="tags">${tagsHTML}</div>
            <a href="${product.purchase_link}" target="_blank" rel="noopener noreferrer" class="purchase-link">Buy Now</a>
        </div>
    `;
    appRoot.innerHTML = productDetailHTML;

    // Add event listener to the back button
    document.querySelector('.back-button')?.addEventListener('click', (e) => {
        e.preventDefault();
        // Go back to the main list view
        window.location.hash = '';
    });
}

function renderError(message) {
    appRoot.innerHTML = `<p class="error">${message}</p>`;
}

// --- Router ---
async function router() {
    const hash = window.location.hash;

    if (hash.startsWith('#product/')) {
        const productId = parseInt(hash.substring('#product/'.length), 10);
        if (!isNaN(productId)) {
            try {
                const product = await fetchProductDetail(productId);
                renderProductDetail(product);
            } catch (error) {
                console.error(error);
                renderError('Could not load product details. Please try again.');
            }
        } else {
            renderError('Invalid product ID.');
        }
    } else {
        try {
            const products = await fetchProducts();
            renderProductList(products);
        } catch (error) {
            console.error(error);
            renderError('Could not load products. Please try again.');
        }
    }
}

// --- Initial Load ---
// Listen for hash changes to handle navigation
window.addEventListener('hashchange', router);
// Load the initial route
document.addEventListener('DOMContentLoaded', router);
