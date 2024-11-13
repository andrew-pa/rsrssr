# RSRSSR (Really Simple RSS Reader)

RSRSSR is a web-based RSS feed reader that allows users to manage and view RSS feeds, track updates, and visualize update statistics. It is built using Flask, SQLAlchemy, and Plotly.

## Features

- **Manage Feeds**: Add or delete RSS feeds.
- **View Items**: Browse through items from all feeds, with options to filter by specific feeds.
- **Track Visits**: Mark items as visited when clicked.
- **Update Statistics**: View statistics about feed updates, including the number of new items and update durations.

## Data Storage

The application uses SQLite to store data. The database includes tables for feeds, items, and update statistics. SQLAlchemy is used as the ORM to interact with the database.

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
   python update.py
   ```

5. **Run the Server**:
   ```bash
   python server.py
   ```

   The server will start in development mode and can be accessed at `http://127.0.0.1:5000`.

## Working on the Code Locally

- Ensure your virtual environment is activated.
- Make changes to the codebase as needed.
- Use a tool like `flake8` for linting and `pytest` for testing to maintain code quality.

## Running for Production

1. **Install Gunicorn**:
   Ensure Gunicorn is installed in your environment:
   ```bash
   pip install gunicorn
   ```

2. **Run the Server with Gunicorn**:
   ```bash
   gunicorn -w 4 server:app
   ```

   This will start the server with 4 worker processes, suitable for handling production traffic.

## Source Code Overview

The source code is organized into several key files, each serving a specific purpose:

- **server.py**: This is the main entry point for the Flask application. It sets up the routes and initializes the database connection using SQLAlchemy.

- **update.py**: Contains functions to update RSS feeds, parse feed data, and store new items in the database. It also manages the update statistics.

- **models.py**: Defines the database models using SQLAlchemy ORM. It includes models for `Feed`, `Item`, and `UpdateStat`.

- **logic.py**: Implements the core logic for managing feeds, items, and update statistics. It includes functions for adding, deleting, and listing feeds, as well as recording item visits.

- **stats_plot.py**: Responsible for generating visualizations of update statistics using Plotly. It creates subplots to display various metrics related to feed updates.

- **__init__.py**: An empty file that marks the directory as a Python package.

- **Static Files**: Located in the `static` directory, including styles and JavaScript modules.
- **Templates**: HTML templates are located in the `templates` directory.
- **Systemd Services**: Configuration files for running the update script as a systemd service are located in the `systemd` directory.
