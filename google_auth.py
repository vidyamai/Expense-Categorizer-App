# Google authentication blueprint for Flask

import json
import os
import logging
import secrets
import traceback
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import requests
from flask import Blueprint, redirect, request, url_for, flash, session, current_app
from flask_login import login_required, login_user, logout_user, current_user
from models import db, User
from oauthlib.oauth2 import WebApplicationClient

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Make sure to use this redirect URL. It has to match the one in the whitelist
DEV_REDIRECT_URL = 'http://localhost:5000/google_login/callback'

# Important: For testing, also add an alternative URL that uses your specific Replit instance
ALT_REDIRECT_URL = f'https://{os.environ.get("REPLIT_DEV_DOMAIN", "")}/login'
JS_ORIGIN = f'https://{os.environ.get("REPLIT_DEV_DOMAIN", "")}'

# Display setup instructions to the user
print(f"""To make Google authentication work:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add these URIs to "Authorized redirect URIs":
   - {DEV_REDIRECT_URL}
   - {ALT_REDIRECT_URL}
4. Add this URI to "Authorized JavaScript origins":
   - {JS_ORIGIN}

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Google OAuth redirect URL: {DEV_REDIRECT_URL}")
logger.info(f"Alternative redirect URL: {ALT_REDIRECT_URL}")
logger.info(f"JavaScript Origin: {JS_ORIGIN}")
logger.info(f"GOOGLE_CLIENT_ID: {'Configured' if GOOGLE_CLIENT_ID else 'Not configured'}")
logger.info(f"GOOGLE_CLIENT_SECRET: {'Configured' if GOOGLE_CLIENT_SECRET else 'Not configured'}")

# For debugging, print the exact credentials
if GOOGLE_CLIENT_ID:
    # Only print first few and last few characters for security
    masked_id = f"{GOOGLE_CLIENT_ID[:5]}...{GOOGLE_CLIENT_ID[-5:]}"
    logger.info(f"Client ID (masked): {masked_id}")

client = WebApplicationClient(GOOGLE_CLIENT_ID)

google_auth = Blueprint("google_auth", __name__)


@google_auth.route("/google_login")
def login():
    # Check if Google OAuth credentials are configured
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash("Google OAuth credentials are not configured. Please set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables.", "danger")
        return redirect(url_for("login"))
    
    # Log credentials and request information
    logging.info(f"Google OAuth credentials status - CLIENT_ID: {'SET' if GOOGLE_CLIENT_ID else 'NOT SET'}, CLIENT_SECRET: {'SET' if GOOGLE_CLIENT_SECRET else 'NOT SET'}")
    logging.info(f"Request headers: {dict(request.headers)}")
    logging.info(f"Request host: {request.host}")
    logging.info(f"Request url: {request.url}")
    
    try:
        # Fetch Google's OAuth configuration
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        # Build the redirect URI - Always use the full static redirect URI
        # This should exactly match what's configured in the Google Cloud Console
        redirect_uri = DEV_REDIRECT_URL
        logging.info(f"Using static redirect URI: {redirect_uri}")
        
        # Create simple direct Google auth URL without the OAuth client library
        # This avoids potential conflicts and simplifies debugging
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'consent',
        }
        
        request_uri = f"{authorization_endpoint}?{urlencode(params)}"
        logging.info(f"Redirecting to Google with simplified params: {request_uri}")
        return redirect(request_uri)
    except Exception as e:
        error_msg = f"Error initiating Google OAuth: {str(e)}"
        logging.error(error_msg)
        logging.error(f"Traceback: {traceback.format_exc()}")
        flash(error_msg, "danger")
        return redirect(url_for("login"))


@google_auth.route("/auth_debug")
def auth_debug():
    """Debug route for testing Google auth configuration"""
    debug_info = {
        "client_id_configured": bool(GOOGLE_CLIENT_ID),
        "client_secret_configured": bool(GOOGLE_CLIENT_SECRET),
        "redirect_urls": {
            "main": DEV_REDIRECT_URL,
            "alternative": ALT_REDIRECT_URL,
            "js_origin": JS_ORIGIN,
        },
        "session_available": hasattr(request, "session"),
        "auth_endpoints": {
            "discovery_url": GOOGLE_DISCOVERY_URL,
        }
    }
    
    # Get Google's discovery configuration
    try:
        google_config = requests.get(GOOGLE_DISCOVERY_URL).json()
        debug_info["google_discovery"] = {
            "authorization_endpoint": google_config.get("authorization_endpoint"),
            "token_endpoint": google_config.get("token_endpoint"),
            "userinfo_endpoint": google_config.get("userinfo_endpoint"),
        }
    except Exception as e:
        debug_info["google_discovery_error"] = str(e)
    
    # Create a response with formatted debug info
    response_text = "<h1>Google OAuth Debug Info</h1>"
    response_text += "<h2>Auth Configuration</h2>"
    response_text += f"<p>Client ID configured: {debug_info['client_id_configured']}</p>"
    response_text += f"<p>Client Secret configured: {debug_info['client_secret_configured']}</p>"
    
    response_text += "<h2>Redirect URLs</h2>"
    response_text += f"<p>Main callback: {debug_info['redirect_urls']['main']}</p>"
    response_text += f"<p>Alternative: {debug_info['redirect_urls']['alternative']}</p>"
    response_text += f"<p>JavaScript Origin: {debug_info['redirect_urls']['js_origin']}</p>"
    
    response_text += "<h2>Session</h2>"
    response_text += f"<p>Session available: {debug_info['session_available']}</p>"
    
    response_text += "<h2>Google Discovery Configuration</h2>"
    if "google_discovery" in debug_info:
        for key, value in debug_info["google_discovery"].items():
            response_text += f"<p>{key}: {value}</p>"
    else:
        response_text += f"<p>Error: {debug_info.get('google_discovery_error', 'Unknown error')}</p>"
    
    response_text += "<h2>Test Authentication Flow</h2>"
    response_text += f'<p><a href="{url_for("google_auth.login")}" class="btn btn-primary">Test Google Login</a></p>'
    
    return response_text

@google_auth.route("/google_login/callback")
def callback():
    # Log all request details for debugging
    logging.info(f"Callback request received: {request.url}")
    logging.info(f"Callback headers: {dict(request.headers)}")
    logging.info(f"Callback args: {dict(request.args)}")
    
    # Check if we have an error parameter in the request
    if request.args.get("error"):
        error_msg = f"Google OAuth error: {request.args.get('error')}"
        error_desc = request.args.get("error_description", "No description provided")
        logging.error(f"{error_msg}: {error_desc}")
        flash(f"{error_msg}: {error_desc}", "danger")
        return redirect(url_for("login"))
    
    # Check if we have the code parameter
    code = request.args.get("code")
    if not code:
        error_msg = "No authorization code received from Google"
        logging.error(error_msg)
        flash(error_msg, "danger")
        return redirect(url_for("login"))
    
    # Check the state parameter if it was set
    state = request.args.get("state")
    if hasattr(request, "session") and "oauth_state" in session:
        expected_state = session.pop("oauth_state")
        if state != expected_state:
            logging.warning(f"OAuth state mismatch: got {state}, expected {expected_state}")
    
    logging.info("Received authorization code from Google, proceeding to token exchange")
    
    try:
        # Get token endpoint
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        token_endpoint = google_provider_cfg["token_endpoint"]
        
        # Use static redirect URL for token request - this must match what Google expects
        redirect_url = DEV_REDIRECT_URL
        
        logging.info(f"Token request redirect URL: {redirect_url}")
        
        # Prepare token request directly without using the client library
        # This provides more control and easier debugging
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_url
        }
        
        logging.info(f"Token endpoint: {token_endpoint}")
        logging.info(f"Token request data: {token_data}")
        
        # Exchange code for tokens
        token_response = requests.post(
            token_endpoint,
            data=token_data
        )
        
        # Check token response
        logging.info(f"Token response status: {token_response.status_code}")
        
        if token_response.status_code != 200:
            error_msg = f"Failed to obtain access token from Google: {token_response.text}"
            logging.error(error_msg)
            flash(error_msg, "danger")
            return redirect(url_for("login"))
        
        logging.info("Successfully obtained access token from Google")
        
        # Parse the token response
        token_data = token_response.json()
        logging.info(f"Token data keys: {list(token_data.keys())}")
        
        # Get access token from response
        access_token = token_data.get('access_token')
        if not access_token:
            error_msg = "No access token in response"
            logging.error(error_msg)
            flash(error_msg, "danger")
            return redirect(url_for("login"))
        
        # Get user info using the access token
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        headers = {'Authorization': f'Bearer {access_token}'}
        logging.info(f"User info request URL: {userinfo_endpoint}")
        
        userinfo_response = requests.get(userinfo_endpoint, headers=headers)
        logging.info(f"User info response status: {userinfo_response.status_code}")
        
        if userinfo_response.status_code != 200:
            error_msg = f"Failed to get user info from Google: {userinfo_response.text}"
            logging.error(error_msg)
            flash(error_msg, "danger")
            return redirect(url_for("login"))
        
        # Process user info
        userinfo = userinfo_response.json()
        logging.info(f"User info keys: {list(userinfo.keys())}")
        
        if not userinfo.get("email_verified"):
            error_msg = "Google account email is not verified"
            logging.error(error_msg)
            flash(error_msg, "danger")
            return redirect(url_for("login"))
        
        users_email = userinfo["email"]
        users_name = userinfo.get("given_name") or userinfo.get("name", users_email.split('@')[0])
        
        logging.info(f"Successfully authenticated user: {users_email}")
        
        # Find or create user
        user = User.query.filter_by(email=users_email).first()
        if not user:
            logging.info(f"Creating new user with email: {users_email}")
            user = User(username=users_name, email=users_email)
            db.session.add(user)
            db.session.commit()
        else:
            logging.info(f"User with email {users_email} already exists")
        
        # Log the user in
        login_user(user)
        flash(f"Successfully signed in with Google as {users_email}", "success")
        
        return redirect(url_for("upload"))
    except Exception as e:
        error_msg = f"Error during Google OAuth callback: {str(e)}"
        logging.error(error_msg)
        logging.error(f"Traceback: {traceback.format_exc()}")
        flash(error_msg, "danger")
        return redirect(url_for("login"))
