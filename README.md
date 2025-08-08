# Lightweight Product Lister SPA

This is a lightweight single-page application (SPA) that lists product thumbnails and details from a Google Sheet. It's built with Flask for the backend and plain JavaScript for the frontend.

## Features

*   **Product Listing:** Displays a grid of product thumbnails with names and purchase links.
*   **Product Details:** Shows a detailed view of a product with a larger image, description, and tags.
*   **Google Sheets Backend:** Product data is fetched directly from a Google Sheet.
*   **Caching:** Product data is cached in memory and to a local file to reduce API calls and improve performance.
*   **Cache Invalidation:** A secure endpoint allows for manual cache invalidation.
*   **Lightweight:** Minimal dependencies and a simple, clean design.

## Setup and Installation

### 1. Python Environment

It's recommended to use a Python virtual environment to manage dependencies.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### 2. Google Sheets API Setup

To allow the application to read your Google Sheet, you need to create a service account in the Google Cloud Platform and share the sheet with it.

**Step 1: Create a Service Account and Credentials**

1.  Go to the [Google Cloud Platform Console](https://console.cloud.google.com/).
2.  Create a new project or select an existing one.
3.  Navigate to **APIs & Services > Credentials**.
4.  Click **Create Credentials** and select **Service account**.
5.  Give the service account a name (e.g., "product-sheet-reader") and click **Create and Continue**.
6.  Grant the service account the **Viewer** role (or a more restrictive role if you prefer). Click **Continue**.
7.  Skip the "Grant users access to this service account" step and click **Done**.
8.  Find the service account you just created in the list and click on it.
9.  Go to the **Keys** tab, click **Add Key**, and select **Create new key**.
10. Choose **JSON** as the key type and click **Create**. A JSON file will be downloaded to your computer.
11. Rename this file to `client_secret.json` and place it in the root directory of this project.

**Step 2: Enable the Google Sheets and Google Drive APIs**

1.  In the Google Cloud Platform Console, go to **APIs & Services > Library**.
2.  Search for and enable the **Google Sheets API**.
3.  Search for and enable the **Google Drive API**.

**Step 3: Create and Share Your Google Sheet**

1.  Create a new Google Sheet.
2.  The first row of your sheet **must be a header row** with the following column names: `Name`, `Purchase Link`, `Image URL`, `Description`, `Tags`.
3.  Populate the sheet with your product data. For the `Tags` column, separate multiple tags with commas (e.g., `tag1, tag2, tag3`).
4.  Open the `client_secret.json` file and find the `client_email` address (it will look something like `your-service-account-name@your-project-id.iam.gserviceaccount.com`).
5.  In your Google Sheet, click the **Share** button, paste the `client_email` address, and give it **Viewer** access.

### 3. Application Configuration

The application is configured using environment variables. You can set these in your shell or in the `gcr-service.service` file for deployment.

*   `SHEET_NAME`: The name of your Google Sheet (e.g., "My Products").
*   `INVALIDATE_TOKEN`: A secret token for the cache invalidation endpoint. Choose a long, random string.

## Running the Application

### For Development

To run the app in development mode with debugging enabled:

```bash
# Set environment variables
export SHEET_NAME="your_sheet_name"
export INVALIDATE_TOKEN="your_secret_token"

# Run the Flask development server
python app/main.py
```

The application will be available at `http://127.0.0.1:5000`.

### For Production (with Gunicorn and Systemd)

The included `gcr-service.service` file is a template for running the application as a systemd service.

1.  **Edit the service file:**
    *   Replace `your_user` with the username you want to run the service as.
    *   Replace `/path/to/your/app` with the absolute path to the project directory.
    *   Update the `Environment` variables with your sheet name and token.
2.  **Copy the service file:**
    ```bash
    sudo cp gcr-service.service /etc/systemd/system/
    ```
3.  **Start and enable the service:**
    ```bash
    sudo systemctl start gcr-service
    sudo systemctl enable gcr-service
    ```

## Cache Invalidation

To force the application to reload data from the Google Sheet, you can send a GET request to the `/api/invalidate-cache` endpoint with your secret token.

```
http://your_domain.com/api/invalidate-cache?token=your_secret_token
```

This will clear the in-memory and file-based caches and trigger a background refresh from the Google Sheet.
