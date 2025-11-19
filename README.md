# RSRSSR (Really Simple RSS Reader)

RSRSSR is a web-based RSS feed reader that allows users to manage and view RSS feeds, track updates, and visualize update statistics. It is built using Flask, SQLAlchemy, and Plotly.
RSRSSR only supports a single user, so there is no authentication/authorization code.

## Features

- **Overview**: The main page shows new items from each feed for the last two weeks, limited to the seven most recent items. This view strikes a balance between readability, information density and freshness.
- **Manage Feeds**: Add or delete RSS feeds.
- **View Items**: Browse through items from all feeds, with options to filter by specific feeds.
- **Track Visits**: Mark items as visited when clicked.
- **Update Statistics**: View statistics about feed updates, including the number of new items and update durations.

## Data Storage

The application uses SQLite to store data. The database includes tables for feeds, items, and update statistics. SQLAlchemy is used as the ORM to interact with the database. The on-disk location can be overridden via the `RSRSSR_DB_PATH` environment variable (defaults to `instance/rss_feeds.db`), and Cloud deployments can mirror the file to Google Cloud Storage by pointing `RSRSSR_DB_GCS_URI` at a `gs://` object.

## Running the Server Locally

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/andrew-pa/rsrssr
   cd rsrssr
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the Database**:
   Ensure the `instance` directory exists and run the following to create the database:
   ```bash
   mkdir instance
   python update.py
   ```

5. **Run the Server**:
   ```bash
   python server.py
   ```

   The server will start in development mode and can be accessed at `http://127.0.0.1:5000`.
   Nothing will appear until you add some feeds in the 'Manage Feeds' page.

## Working on the Code Locally

- Ensure your virtual environment is activated.
- Make changes to the codebase as needed.
- Use `black` to format code.

## Running for Production

1. **Install Gunicorn**:
   Ensure Gunicorn is installed in your environment:
   ```bash
   pip install gunicorn
   ```

2. **Run the Server with Gunicorn**:
   ```bash
   gunicorn server:app
   ```

3. **Run the updater**:
    ```bash
    python update.py
    ```

    The update script needs to be run periodically to fetch new items for all feeds. It shouldn't run more than once an hour, as each time it runs it will make a request for each feed. We do attempt to correctly implement caching to prevent unnecessary load on the feed servers.

## Database Storage

The application stores its state in a SQLite database. By default the file lives under `instance/rss_feeds.db`, but two environment variables control where the data is read from and how it is persisted:

- `RSRSSR_DB_PATH` — Absolute path to the local SQLite file. In Cloud Run we keep the file inside `/tmp/rsrssr/rss_feeds.db` so all reads and writes happen on the container's in-memory filesystem.
- `RSRSSR_DB_GCS_URI` — Optional `gs://bucket/object` URI. When set, the service downloads the database blob into `RSRSSR_DB_PATH` at startup and uploads it back to Cloud Storage whenever changes are committed (after each web request and when the update job completes). Uploads use the blob's generation number via `if_generation_match` so we never clobber a newer copy that was written by another process.

## Deploying on Google Cloud

Terraform configuration is provided in the `terraform/` directory to deploy RSRSSR in a low-cost, serverless architecture:

- **Cloud Run service** for the Flask web UI. The container writes to `/tmp/rsrssr/rss_feeds.db` and uses the Cloud Storage JSON API (via `google-cloud-storage`) to pull/push the database blob with optimistic concurrency control.
- **Cloud Run job** for `update.py`. It shares the same image and database sync logic, and Cloud Scheduler triggers it every six hours (4× daily) via an authenticated HTTP call.
- **Artifact Registry** for storing container images and a dedicated service account with the minimal IAM roles required for Cloud Run, Cloud Scheduler, and bucket access.

To deploy:

1. **Build the container image** using the provided `Dockerfile` and tag it for Artifact Registry. Example:
   ```bash
   REGION=us-central1
   PROJECT_ID=my-project
   IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/rsrssr/rsrssr:latest"
   docker build -t "$IMAGE" .
   docker push "$IMAGE"
   ```

2. **Configure Terraform**. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars`, set `project_id`, `region`, and (optionally) `container_image` if you pushed a custom tag.

3. **Apply the infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```

Terraform outputs the public Cloud Run URL and the name of the Cloud Storage bucket that stores the SQLite file. Both the web service and the update job use the same object URI exposed via `RSRSSR_DB_GCS_URI`, so user actions and feed updates are mirrored back to Cloud Storage with generation checks to prevent overwriting concurrent writes.

## Source Code Overview

The source code is organized into several key files, each serving a specific purpose:

- **server.py**: This is the main entry point for the Flask application. It sets up the routes and initializes the database connection using SQLAlchemy.

- **update.py**: This standalone script fetches updates for all feeds. Contains functions to update RSS feeds, parse feed data, and store new items in the database. It also manages the update statistics.

- **models.py**: Defines the database models using SQLAlchemy ORM. It includes models for `Feed`, `Item`, and `UpdateStat`.

- **logic.py**: Implements the core logic for managing feeds, items, and update statistics. It includes functions for adding, deleting, and listing feeds, as well as recording item visits.

- **stats_plot.py**: Responsible for generating visualizations of update statistics using Plotly. It creates subplots to display various metrics related to feed updates.

- **__init__.py**: An empty file that marks the directory as a Python package.

- **Static Files**: Located in the `static` directory, including styles and JavaScript modules.
- **Templates**: HTML templates are located in the `templates` directory.
- **Systemd Services**: Example configuration files for running the webapp as a systemd service are located in the `systemd` directory.
