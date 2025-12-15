import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# -------------------------------------------------------
# SCOPES define what permissions your app will request.
# -------------------------------------------------------
SCOPES = [
    'https://www.googleapis.com/auth/tasks',          # Google Tasks
    'https://www.googleapis.com/auth/calendar',       # Google Calendar
    'https://www.googleapis.com/auth/gmail.compose',  # Gmail compose
    'https://www.googleapis.com/auth/gmail.send',     # Gmail send
      
]

def authenticate_google():
    """Authenticate with Google APIs and return credentials"""
    creds = None

    # Load token if exists
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token_file:
            creds = pickle.load(token_file)

    # If credentials are invalid or don't exist, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. "
                    "Please download it from Google Cloud Console and place it in the current directory."
                )
            
            print("🌐 Opening browser for Google Sign-In...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open('token.pkl', 'wb') as token_file:
            pickle.dump(creds, token_file)
        print("✅ Login successful — token.pkl created/updated")

    return creds

def get_tasks_service(creds):
    """Get Google Tasks service"""
    return build('tasks', 'v1', credentials=creds)

def get_calendar_service(creds):
    """Get Google Calendar service"""
    return build('calendar', 'v3', credentials=creds)

def get_gmail_service(creds):
    """Get Gmail service"""
    return build('gmail', 'v1', credentials=creds)

def test_google_services(creds):
    """Test Tasks, Calendar, Gmail access."""
    
    print("\n📝 Testing Google Tasks...")
    try:
        tasks_service = get_tasks_service(creds)
        tasklists = tasks_service.tasklists().list(maxResults=5).execute().get('items', [])
        for t in tasklists:
            print("   • Tasklist:", t["title"])
    except Exception as e:
        print(f"   ❌ Tasks error: {e}")

    print("\n📅 Testing Google Calendar...")
    try:
        cal_service = get_calendar_service(creds)
        calendars = cal_service.calendarList().list(maxResults=5).execute().get('items', [])
        for c in calendars:
            print("   • Calendar:", c["summary"])
    except Exception as e:
        print(f"   ❌ Calendar error: {e}")

    print("\n✉️ Testing Gmail Access...")
    try:
        gmail_service = get_gmail_service(creds)
        profile = gmail_service.users().getProfile(userId='me').execute()
        print("   • Gmail connected as:", profile["emailAddress"])
    except Exception as e:
        print(f"   ❌ Gmail error: {e}")

if __name__ == "__main__":
    try:
        creds = authenticate_google()
        test_google_services(creds)
    except Exception as e:
        print(f"❌ Authentication failed: {e}")