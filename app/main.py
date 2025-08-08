import os
import json
from flask import Flask, jsonify, render_template, request, abort
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import time

# --- Configuration ---
# Google Sheet details
SHEET_NAME = os.environ.get("SHEET_NAME", "products") # Or get from environment variable
# Credentials file for Google Sheets API
# IMPORTANT: This file should be kept secret.
# You can create this file from your Google Cloud Platform project.
# See: https://developers.google.com/sheets/api/guides/authorizing#creating_a_service_account
CREDENTIALS_FILE = 'client_secret.json'

# Cache invalidation token
# IMPORTANT: Use a strong, randomly generated token in a real application.
# You can pass this as an environment variable.
INVALIDATE_TOKEN = os.environ.get("INVALIDATE_TOKEN", "your-secret-token")

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Caching ---
# In-memory cache for product data
products_cache = None
# A lock to ensure thread-safe access to the cache
cache_lock = threading.Lock()
# File-based cache for persistence
LOCAL_CACHE_FILE = 'products_cache.json'
MAX_LOCAL_CACHE_ITEMS = 10

def get_products_from_sheet():
    """
    Fetches product data from the Google Sheet.
    """
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        products = sheet.get_all_records() # Assumes first row is header
        return products
    except Exception as e:
        print(f"Error fetching data from Google Sheet: {e}")
        return None

def load_products_from_local_cache():
    """Loads products from the local JSON file cache."""
    if os.path.exists(LOCAL_CACHE_FILE):
        with open(LOCAL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def save_products_to_local_cache(products):
    """Saves a subset of products to the local JSON file cache."""
    with open(LOCAL_CACHE_FILE, 'w') as f:
        json.dump(products[:MAX_LOCAL_CACHE_ITEMS], f)

def get_products():
    """
    Gets product data, using the cache if available.
    Reloads the cache from the Google Sheet if it's empty.
    """
    global products_cache
    with cache_lock:
        if products_cache is None:
            print("Cache is empty. Attempting to load from local cache first.")
            products_cache = load_products_from_local_cache()
            if products_cache is None:
                 print("Local cache is empty or not found. Fetching from Google Sheet.")
                 products_cache = get_products_from_sheet()
                 if products_cache:
                     save_products_to_local_cache(products_cache)
        return products_cache

# --- Flask Routes ---

@app.route('/')
def index():
    """Serves the main single-page application."""
    return render_template('index.html')

@app.route('/api/products')
def api_products():
    """API endpoint to get the list of all products."""
    # This will trigger a cache refresh if the cache is empty
    products = get_products()
    if products is None:
        return jsonify({"error": "Could not retrieve product data."}), 500

    # The listing page only needs thumbnails, name, and links.
    # The 'id' will be the row index + 2 (for header and 0-indexing)
    # or we can just use the index in the list as an ID.
    thumbnails = [
        {
            "id": i,
            "name": p.get("Name"),
            "thumbnail_url": p.get("Image URL"), # Assuming the same URL is used for thumbnail and full image
            "purchase_link": p.get("Purchase Link")
        } for i, p in enumerate(products)
    ]
    return jsonify(thumbnails)

@app.route('/api/products/<int:product_id>')
def api_product_detail(product_id):
    """API endpoint to get the details of a single product."""
    products = get_products()
    if products is None or product_id >= len(products):
        return jsonify({"error": "Product not found."}), 404

    product = products[product_id]
    product_details = {
        "id": product_id,
        "name": product.get("Name"),
        "image_url": product.get("Image URL"),
        "purchase_link": product.get("Purchase Link"),
        "description": product.get("Description"),
        "tags": [tag.strip() for tag in product.get("Tags", "").split(',') if tag.strip()]
    }
    return jsonify(product_details)

@app.route('/api/invalidate-cache')
def invalidate_cache():
    """
    A private endpoint to force-invalidate the cache.
    Requires a token for access.
    """
    token = request.args.get('token')
    if token != INVALIDATE_TOKEN:
        abort(403) # Forbidden

    global products_cache
    with cache_lock:
        print("Invalidating cache by request.")
        products_cache = None # Set cache to None to force a reload on next request
        # Optionally, clear the local file cache as well
        if os.path.exists(LOCAL_CACHE_FILE):
            os.remove(LOCAL_CACHE_FILE)

    # Trigger a reload immediately in the background
    threading.Thread(target=get_products).start()

    return jsonify({"message": "Cache invalidated. Reloading in the background."})


if __name__ == '__main__':
    # The `get_products` call will pre-load the cache on startup.
    get_products()
    # In a production environment, use a proper WSGI server like Gunicorn or uWSGI.
    app.run(debug=True)
