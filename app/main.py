import os
import json
from flask import Flask, jsonify, render_template, request, abort, make_response, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import time
import jwt
from datetime import datetime, timedelta
from functools import wraps

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

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "a-super-secret-key-that-is-long-and-secure")
AUTHORIZED_EMAILS = [
    "admin@example.com",
    "user1@example.com",
    "test@example.com"
]


# --- Flask App Initialization ---
app = Flask(__name__)

# --- Authentication ---

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            current_user_email = data['email']
            if current_user_email not in AUTHORIZED_EMAILS:
                return render_template('unauthorized.html'), 403
        except jwt.ExpiredSignatureError:
            return redirect(url_for('login', message='Token has expired. Please log in again.'))
        except jwt.InvalidTokenError:
            return redirect(url_for('login', message='Invalid token. Please log in again.'))

        return f(current_user_email, *args, **kwargs)
    return decorated

# --- Caching ---
# In-memory cache for product data
products_cache = None
# A lock to ensure thread-safe access to the cache
cache_lock = threading.Lock()
# File-based cache for persistence
LOCAL_CACHE_FILE = 'products_cache.json'
MAX_LOCAL_CACHE_ITEMS = 10

def setup_sheets():
    """
    Ensures the Google Sheet is configured correctly with an audit log
    and the necessary columns in the products sheet.
    """
    try:
        print("Performing initial sheet setup check...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SHEET_NAME)

        # 1. Ensure 'audit_log' sheet exists
        try:
            audit_sheet = spreadsheet.worksheet('audit_log')
            print("'audit_log' sheet already exists.")
        except gspread.WorksheetNotFound:
            print("Creating 'audit_log' sheet...")
            audit_sheet = spreadsheet.add_worksheet(title="audit_log", rows="100", cols="20")
            audit_sheet.append_row(['Timestamp', 'User', 'Action', 'Details'])

        # 2. Ensure 'Added By' column exists in the products sheet
        product_sheet = spreadsheet.sheet1
        header = product_sheet.row_values(1)
        if 'Added By' not in header:
            print("Adding 'Added By' column to products sheet...")
            # Find the first empty column in the header row and add it there
            product_sheet.update_cell(1, len(header) + 1, 'Added By')
        else:
            print("'Added By' column already exists.")
        print("Sheet setup check complete.")
        return True
    except Exception as e:
        print(f"Error during sheet setup: {e}")
        print("Please ensure the service account has editor permissions for the Google Sheet.")
        return False

def log_to_audit_sheet(user, action, details):
    """Appends a log entry to the 'audit_log' sheet."""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        audit_sheet = client.open(SHEET_NAME).worksheet('audit_log')

        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        log_row = [timestamp, user, action, details]

        audit_sheet.append_row(log_row)
        return True
    except Exception as e:
        print(f"Error writing to audit log: {e}")
        return False

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

def add_product_to_sheet(product_data):
    """
    Appends a new product row to the Google Sheet.
    """
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1

        # Get header row to ensure correct order
        header = sheet.row_values(1)
        # Create a new row with values in the correct order, handling missing keys
        new_row = [product_data.get(h, "") for h in header]

        sheet.append_row(new_row)
        return True
    except Exception as e:
        print(f"Error adding product to Google Sheet: {e}")
        return False

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


# --- Auth Routes ---
@app.route('/login')
def login():
    """Serves the login page."""
    message = request.args.get('message')
    return render_template('login.html', message=message)

@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login using a pre-generated token."""
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({"error": "Token is required."}), 400

    try:
        # Decode the token to validate it and get the user's email
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        email = payload.get('email')

        if not email or email not in AUTHORIZED_EMAILS:
            return jsonify({"error": "Token is invalid or for an unauthorized user."}), 401

        # The token is valid and authorized, set it as a secure cookie
        response = make_response(jsonify({"message": "Login successful."}))
        response.set_cookie('token', token, httponly=True, samesite='Lax')
        return response

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token is invalid."}), 401

# --- Add Product Routes ---
@app.route('/add')
@token_required
def add_product_page(current_user_email):
    """Serves the page for adding a new product."""
    # The current_user_email is passed by the decorator, you can use it if needed
    return render_template('add_product.html')

@app.route('/api/products/add', methods=['POST'])
@token_required
def api_add_product(current_user_email):
    """API endpoint to add a new product."""
    product_data = request.get_json()
    product_name = product_data.get('Name')
    if not product_data or not product_name:
        return jsonify({"error": "Product Name is a required field."}), 400

    # Add the user's email to the product data
    product_data['Added By'] = current_user_email

    print(f"User '{current_user_email}' is adding a new product: {product_name}")

    if add_product_to_sheet(product_data):
        # Log the audit event
        log_to_audit_sheet(
            user=current_user_email,
            action="ADD_PRODUCT",
            details=f"Added product: '{product_name}'"
        )

        # Invalidate cache after adding a new product
        global products_cache
        with cache_lock:
            products_cache = None
            if os.path.exists(LOCAL_CACHE_FILE):
                os.remove(LOCAL_CACHE_FILE)

        # Trigger a reload in the background
        threading.Thread(target=get_products).start()

        return jsonify({"message": "Product added successfully."}), 201
    else:
        return jsonify({"error": "Failed to add product to the sheet."}), 500


if __name__ == '__main__':
    # Perform one-time setup of the Google Sheets
    setup_sheets()
    # The `get_products` call will pre-load the cache on startup.
    # get_products() # Disabled pre-loading to prevent potential startup crash
    # In a production environment, use a proper WSGI server like Gunicorn or uWSGI.
    app.run(debug=True)
