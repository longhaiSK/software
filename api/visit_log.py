# Required imports
import os
import base64
import json
from datetime import datetime
import pytz
from github import Github, GithubIntegration, Auth
from github.GithubException import UnknownObjectException
# NOTE: No streamlit dependencies here!

# --- Configuration (Read from Environment Variables) ---
# These MUST be set in your serverless environment settings
GITHUB_APP_ID = os.environ.get("GITHUB_APP_ID")
GITHUB_INSTALLATION_ID = os.environ.get("GITHUB_INSTALLATION_ID")
# Private key often needs careful handling regarding newlines when setting env var
GITHUB_PRIVATE_KEY = os.environ.get("GITHUB_PRIVATE_KEY", "").replace('\\n', '\n')
LOG_REPO_NAME = os.environ.get("LOG_REPO_NAME")
LOG_FILE_PATH = os.environ.get("LOG_FILE_PATH")
TIMEZONE = os.environ.get("TIMEZONE", "UTC") # Default to UTC if not set

# CORS Headers - Adjust origins as needed for security
# '*' allows all origins, replace with your github.io domain for better security
# e.g., 'https://your-username.github.io'
ALLOWED_ORIGIN = '*' # Or specific domain 'https://your-username.github.io'
CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', # Allow GET/POST for logging, OPTIONS for preflight
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600'
}

# --- Helper Functions ---

def get_github_app_token(app_id, private_key, installation_id):
    """Generates a GitHub App installation access token."""
    try:
        auth = Auth.AppAuth(app_id, private_key)
        gi = GithubIntegration(auth=auth)
        token = gi.get_access_token(installation_id).token
        return token
    except Exception as e:
        print(f"ERROR generating GitHub token: {e}")
        # In a real app, consider more specific error handling/logging
        raise ValueError(f"Failed to generate GitHub token: {e}") from e

def log_daily_session_count(gh_token, repo_name, file_path, timezone):
    """Reads/Updates the daily session count JSON file in the GitHub repo."""
    # This function contains the core logic adapted from the previous version
    try:
        g = Github(auth=Auth.Token(gh_token))
        repo = g.get_repo(repo_name)
        tz = pytz.timezone(timezone)
        current_date_str = datetime.now(pytz.utc).astimezone(tz).strftime("%Y-%m-%d")

        daily_counts = {}
        sha = None

        try:
            contents = repo.get_contents(file_path, ref="main")
            sha = contents.sha
            existing_content_bytes = base64.b64decode(contents.content)
            existing_content_str = existing_content_bytes.decode("utf-8")
            try:
                daily_counts = json.loads(existing_content_str)
                if not isinstance(daily_counts, dict):
                     print(f"WARNING: Existing content in {file_path} is not a dict. Resetting.")
                     daily_counts = {}
            except json.JSONDecodeError:
                print(f"WARNING: Could not decode JSON from {file_path}. Resetting.")
                daily_counts = {}
        except UnknownObjectException:
            print(f"Log file '{file_path}' not found. Will create.")
        except Exception as e:
            print(f"ERROR retrieving file content: {type(e).__name__} - {e}")
            raise # Re-raise the exception to be caught by the handler

        # Increment count
        current_count = daily_counts.get(current_date_str, 0)
        daily_counts[current_date_str] = current_count + 1
        new_count = daily_counts[current_date_str]

        # Prepare new content
        new_content_str = json.dumps(daily_counts, indent=4)
        new_content_bytes = new_content_str.encode("utf-8")

        # Update or create file
        if sha:
            commit_message = f"Increment session count for {current_date_str} to {new_count}"
            repo.update_file(path=file_path, message=commit_message, content=new_content_bytes, sha=sha, branch="main")
            print(f"Successfully updated count for {current_date_str}")
        else:
            commit_message = f"Create session count log, starting {current_date_str} at 1"
            repo.create_file(path=file_path, message=commit_message, content=new_content_bytes, branch="main")
            print(f"Successfully created log for {current_date_str}")

    except Exception as e:
        print(f"ERROR during GitHub logging operation: {type(e).__name__} - {e}")
        raise # Re-raise the exception to be caught by the handler

# --- Serverless Handler Function ---
# This structure is common for Google Cloud Functions (HTTP Trigger)
# Adapt as needed for AWS Lambda (event, context), Vercel, Netlify etc.

def main_handler(request):
    """
    Handles HTTP requests to log a session visit.
    Responds to OPTIONS requests for CORS preflight.
    Responds to GET/POST requests by attempting to log the visit.
    """

    # --- CORS Preflight Handling (OPTIONS request) ---
    if request.method == 'OPTIONS':
        return ('', 204, CORS_HEADERS) # Respond to preflight request

    # --- Actual Logging Request Handling (GET, POST, etc.) ---
    # Check if required environment variables are set
    if not all([GITHUB_APP_ID, GITHUB_INSTALLATION_ID, GITHUB_PRIVATE_KEY, LOG_REPO_NAME, LOG_FILE_PATH]):
        print("ERROR: Missing required environment variables for GitHub configuration.")
        # Return server error, but include CORS headers
        return ("Configuration Error", 500, CORS_HEADERS)

    try:
        # 1. Get GitHub Token
        print("Attempting to get GitHub token...")
        github_token = get_github_app_token(GITHUB_APP_ID, GITHUB_PRIVATE_KEY, GITHUB_INSTALLATION_ID)
        print("GitHub token obtained.")

        # 2. Log the session count
        print(f"Attempting to log session count to {LOG_REPO_NAME}/{LOG_FILE_PATH}...")
        log_daily_session_count(github_token, LOG_REPO_NAME, LOG_FILE_PATH, TIMEZONE)
        print("Session count logged successfully.")

        # 3. Return success response
        # Simple success message, can be customized
        return ("Log recorded", 200, CORS_HEADERS)

    except Exception as e:
        # Log the exception details on the server side
        print(f"ERROR processing request: {type(e).__name__} - {e}")
        # Return a generic server error response to the client
        return ("Internal Server Error", 500, CORS_HEADERS)

# --- Example for local testing (won't work without setting env vars) ---
# if __name__ == '__main__':
#     # This part is for local testing simulation, requires env vars to be set
#     # In a real serverless environment, the platform calls main_handler directly.
#     if not all([GITHUB_APP_ID, GITHUB_INSTALLATION_ID, GITHUB_PRIVATE_KEY, LOG_REPO_NAME, LOG_FILE_PATH]):
#          print("Please set environment variables: GITHUB_APP_ID, GITHUB_INSTALLATION_ID, GITHUB_PRIVATE_KEY, LOG_REPO_NAME, LOG_FILE_PATH, [TIMEZONE]")
#     else:
#         print("Simulating request...")
#         # Simulate a request object (structure depends on framework, e.g., Flask request)
#         class MockRequest:
#             method = 'POST' # Or 'GET'
#             # Add other attributes if needed by your framework's request object
#
#         response_text, status_code, headers = main_handler(MockRequest())
#         print(f"Status: {status_code}")
#         print(f"Headers: {headers}")
#         print(f"Response: {response_text}")

