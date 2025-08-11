document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('add-product-form');
    const messageDiv = document.getElementById('message');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        messageDiv.textContent = '';
        messageDiv.style.color = 'red';

        // Create a data object from the form fields
        const formData = new FormData(form);
        const productData = {
            "Name": formData.get('name'),
            "Image URL": formData.get('image_url'),
            "Purchase Link": formData.get('purchase_link'),
            "Description": formData.get('description'),
            "Tags": formData.get('tags'),
        };

        try {
            const response = await fetch('/api/products/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(productData),
            });

            const result = await response.json();

            if (response.ok) {
                messageDiv.textContent = result.message || 'Product added successfully!';
                messageDiv.style.color = 'green';
                form.reset(); // Clear the form
            } else {
                messageDiv.textContent = result.error || 'An unknown error occurred.';
                // If unauthorized, redirect to login
                if (response.status === 401 || response.status === 403) {
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                }
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            messageDiv.textContent = 'A network error occurred. Please try again.';
        }
    });
});
