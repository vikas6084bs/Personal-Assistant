import os
import pickle
import uuid
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import re


# Calendar API scope
SCOPES = ['https://www.googleapis.com/auth/calendar']


class SmartTimeParser:
    """Time parsing utility for natural language"""
    def __init__(self):
        self.months = {
            'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
            'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
            'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
            'nov': 11, 'november': 11, 'dec': 12, 'december': 12
        }

    def extract_datetime(self, text):
        """Extract datetime from natural language"""
        text_lower = text.lower()
        now = datetime.now()

        # Extract date
        target_date = self._extract_date(text_lower, now)

        # Extract time
        hour, minute = self._extract_time(text_lower)

        # Combine date and time
        try:
            target_datetime = datetime.combine(
                target_date, datetime.min.time()
            ).replace(hour=hour, minute=minute)
            return target_datetime
        except Exception:
            # Fallback
            return datetime.combine(
                target_date + timedelta(days=1),
                datetime.min.time()
            ).replace(hour=hour, minute=minute)

    def _extract_date(self, text, now):
        """Extract date from text"""
        # Check for specific dates like "26 nov"
        date_patterns = [
            r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*',
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if match.group(1).isdigit():
                        day = int(match.group(1))
                        month_str = match.group(2).lower()[:3]
                    else:
                        day = int(match.group(2))
                        month_str = match.group(1).lower()[:3]

                    month = self.months.get(month_str, now.month)
                    year = now.year

                    target_date = datetime(year, month, day).date()
                    if target_date < now.date():
                        target_date = target_date.replace(year=year + 1)
                    return target_date
                except (ValueError, IndexError):
                    pass

        # Check for date keywords
        if 'tomorrow' in text:
            return now.date() + timedelta(days=1)
        elif 'day after tomorrow' in text:
            return now.date() + timedelta(days=2)
        elif 'yesterday' in text:
            return now.date() - timedelta(days=1)
        elif 'next week' in text:
            return now.date() + timedelta(days=7)
        elif 'next month' in text:
            return now.date() + timedelta(days=30)

        # Default to today
        return now.date()

    def _extract_time(self, text):
        """Extract time from text"""
        # Pattern 1: 12-hour with colon and am/pm "6:30 pm"
        match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)\b', text, re.IGNORECASE)
        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2))
                period = match.group(3).lower()

                if period == 'pm' and hour < 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0

                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return hour, minute
            except (ValueError, IndexError):
                pass

        # Pattern 2: 12-hour without colon "6 pm"
        match = re.search(r'(\d{1,2})\s*(am|pm)\b', text, re.IGNORECASE)
        if match:
            try:
                hour = int(match.group(1))
                period = match.group(2).lower()

                if period == 'pm' and hour < 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0

                if 0 <= hour <= 23:
                    return hour, 0
            except (ValueError, IndexError):
                pass

        # Pattern 3: 24-hour format "18:30"
        match = re.search(r'(\d{1,2}):(\d{2})', text)
        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return hour, minute
            except (ValueError, IndexError):
                pass

        # Pattern 4: Natural language times
        if any(word in text for word in ['noon', 'midday']):
            return 12, 0
        elif 'midnight' in text:
            return 0, 0
        elif 'morning' in text:
            return 9, 0
        elif 'afternoon' in text:
            return 14, 0
        elif 'evening' in text:
            return 18, 0
        elif any(word in text for word in ['night', 'tonight']):
            return 20, 0

        # Default to 2 PM
        return 14, 0


def extract_event_title(user_input):
    """Extract clean event title - STOPS AT FIRST STOPWORD"""
    print(f"DEBUG extract_event_title START:")
    print(f"  Original input: '{user_input}'")

    text = user_input.lower()
    text = re.sub(r'^(create|add|make|new|event)\s+', '', text)
    text = re.sub(r'\s+(event|appointment)\s+', ' ', text)

    print(f"  After command removal: '{text}'")

    words = text.split()
    title_words = []
    stop_words = {
        'on', 'at', 'tomorrow', 'today', 'next', 'this',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
        'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
        'am', 'pm'
    }

    for word in words:
        if (
            word in stop_words or
            re.match(r'^\d{1,2}:\d{2}$', word) or      # 6:30
            re.match(r'^\d{1,2}(?:am|pm)$', word) or   # 6pm
            re.match(r'^\d+$', word)                   # 6
        ):
            print(f"  STOPPING at first stopword: '{word}'")
        break
        title_words.append(word)
        print(f"  Added word: '{word}'")

    title = ' '.join(title_words).strip()
    title = ' '.join(word.capitalize() for word in title.split())

    if not title:
        title = "Event"

    print(f"  Final title: '{title}'")
    return title


def get_calendar_service():
    """Authenticate and return calendar service"""
    creds = None

    # Use the google_credentials folder
    credentials_path = os.path.join('google_credentials', 'credentials.json')
    token_path = os.path.join('google_credentials', 'token_calendar.pickle')

    # Token file stores user access/refresh tokens
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                print(f"Calendar credentials file '{credentials_path}' not found.")
                print("Please download from Google Cloud Console and save in google_credentials folder.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def create_event(user_input):
    """Create calendar event with Google Meet link from natural language."""
    try:
        service = get_calendar_service()
        if not service:
            return {
                'status': 'error',
                'message': 'Calendar authentication failed. Check credentials.'
            }

        parser = SmartTimeParser()
        event_time = parser.extract_datetime(user_input)
        title = extract_event_title(user_input)

        # Start/end time in ISO
        start_time = event_time.isoformat()
        end_time = (event_time + timedelta(hours=1)).isoformat()  # 1 hour default

        # Optional: extract attendee email from the input
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)
        attendee_email = email_match.group(0) if email_match else None

        event_body = {
            'summary': title,
            'description': f'Created from personal assistant: {user_input}',
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/New_York',  # adjust timezone as needed
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/New_York',
            },
        }

        if attendee_email:
            event_body['attendees'] = [{'email': attendee_email}]

        # Request a Google Meet link
        event_body['conferenceData'] = {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
            }
        }

        created_event = service.events().insert(
            calendarId='primary',
            body=event_body,
            conferenceDataVersion=1,
            sendUpdates='all'
        ).execute()

        meet_link = created_event.get('hangoutLink')

        return {
            'status': 'success',
            'title': title,
            'start_time': event_time.strftime("%Y-%m-%d %H:%M"),
            'event_id': created_event.get('id'),
            'meet_link': meet_link,
            'message': 'Event created successfully in Google Calendar'
        }

    except Exception as e:
        return {'status': 'error', 'message': f'Failed to create event: {str(e)}'}


def delete_event(event_title):
    """Delete event by title"""
    try:
        service = get_calendar_service()
        if not service:
            return {'status': 'error', 'message': 'Calendar authentication failed'}

        # Search for events with matching title
        events = get_upcoming_events(30)
        event_to_delete = None

        for event in events:
            if event.get('summary', '').lower() == event_title.lower():
                event_to_delete = event
                break

        if not event_to_delete:
            return {'status': 'error', 'message': f'Event "{event_title}" not found'}

        # Delete the event
        service.events().delete(calendarId='primary', eventId=event_to_delete['id']).execute()

        return {
            'status': 'success',
            'title': event_title,
            'message': f'Event "{event_title}" deleted successfully'
        }

    except Exception as e:
        return {'status': 'error', 'message': f'Failed to delete event: {str(e)}'}


def reschedule_event(event_title, new_time_input):
    """Reschedule event by title to new time"""
    try:
        service = get_calendar_service()
        if not service:
            return {'status': 'error', 'message': 'Calendar authentication failed'}

        # Search for events with matching title
        events = get_upcoming_events(30)
        event_to_reschedule = None

        for event in events:
            if event.get('summary', '').lower() == event_title.lower():
                event_to_reschedule = event
                break

        if not event_to_reschedule:
            return {'status': 'error', 'message': f'Event "{event_title}" not found'}

        # Parse new time - handle both natural language and formatted dates
        new_time = None

        # Try to parse as formatted date first
        try:
            new_time = datetime.strptime(new_time_input, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                new_time = datetime.strptime(new_time_input, "%Y-%m-%d")
                new_time = new_time.replace(hour=14, minute=0)  # 2 PM default
            except ValueError:
                parser = SmartTimeParser()
                new_time = parser.extract_datetime(new_time_input)

        print(f"DEBUG: Parsed new_time: {new_time}")
        print(f"DEBUG: Formatted date: {new_time.strftime('%b %d')}")

        new_start_time = new_time.isoformat()
        new_end_time = (new_time + timedelta(hours=1)).isoformat()

        updated_event = {
            'summary': event_to_reschedule['summary'],
            'description': event_to_reschedule.get('description', ''),
            'start': {
                'dateTime': new_start_time,
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': new_end_time,
                'timeZone': 'America/New_York',
            },
        }

        for field in ['location', 'attendees', 'reminders']:
            if field in event_to_reschedule:
                updated_event[field] = event_to_reschedule[field]

        service.events().update(
            calendarId='primary',
            eventId=event_to_reschedule['id'],
            body=updated_event
        ).execute()

        display_date = new_time.strftime("%I:%M %p on %b %d")
        print(f"DEBUG: display_date: {display_date}")

        return {
            'status': 'success',
            'old_title': event_title,
            'new_time': new_time.strftime("%Y-%m-%d %H:%M"),
            'display_time': display_date,
            'message': f'Event "{event_title}" rescheduled to {display_date}'
        }

    except Exception as e:
        return {'status': 'error', 'message': f'Failed to reschedule event: {str(e)}'}


def get_events_today():
    """Get today's events"""
    try:
        service = get_calendar_service()
        if not service:
            return []

        now = datetime.utcnow().isoformat() + 'Z'
        end_of_day = (datetime.now() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_of_day_utc = end_of_day.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end_of_day_utc,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    except Exception as e:
        print(f"Error getting today's events: {e}")
        return []


def get_events_tomorrow():
    """Get tomorrow's events"""
    try:
        service = get_calendar_service()
        if not service:
            return []

        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat() + 'Z'
        end_time = (tomorrow + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_time,
            timeMax=end_time,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    except Exception as e:
        print(f"Error getting tomorrow's events: {e}")
        return []


def get_upcoming_events(days=7):
    """Get upcoming events for specified days"""
    try:
        service = get_calendar_service()
        if not service:
            return []

        now = datetime.utcnow().isoformat() + 'Z'
        end_time = (datetime.now() + timedelta(days=days)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end_time,
            maxResults=30,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    except Exception as e:
        print(f"Error getting upcoming events: {e}")
        return []


def search_events(query):
    """Search events by title"""
    try:
        service = get_calendar_service()
        if not service:
            return []

        now = datetime.utcnow().isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            q=query,
            timeMin=now,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    except Exception as e:
        print(f"Error searching events: {e}")
        return []


def get_calendar_statistics():
    """Get calendar statistics"""
    try:
        today = get_events_today()
        tomorrow = get_events_tomorrow()
        upcoming = get_upcoming_events(7)

        return {
            'events_today': len(today),
            'events_tomorrow': len(tomorrow),
            'upcoming_week': len(upcoming),
            'busiest_day': 'Today' if len(today) >= len(tomorrow) else 'Tomorrow'
        }

    except Exception as e:
        print(f"Error getting calendar statistics: {e}")
        return {'events_today': 0, 'events_tomorrow': 0, 'upcoming_week': 0, 'busiest_day': 'Today'}


def get_formatted_events_today():
    """Get formatted today's events for display"""
    events = get_events_today()
    formatted = []

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            time_str = event_time.strftime('%I:%M %p')
        else:
            time_str = "All day"
            event_time = datetime.fromisoformat(start)

        formatted.append({
            'title': event.get('summary', 'No title'),
            'time': time_str,
            'date': datetime.now().strftime('%b %d, %Y')
        })

    return formatted


def get_formatted_events_tomorrow():
    """Get formatted tomorrow's events for display"""
    events = get_events_tomorrow()
    formatted = []
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%b %d, %Y')

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            time_str = event_time.strftime('%I:%M %p')
        else:
            time_str = "All day"

        formatted.append({
            'title': event.get('summary', 'No title'),
            'time': time_str,
            'date': tomorrow
        })

    return formatted


def parse_datetime_for_event(text: str):
    """
    Parse natural language expressions into (YYYY-MM-DD, HH:MM) for events.
    More sophisticated than task parser, handles more expressions.
    """
    if not isinstance(text, str):
        return None, None

    t = text.lower().strip()
    now = datetime.now()

    # Default time for events is 2 PM (14:00) - common meeting time
    default_hour, default_minute = 14, 0

    # ===== 1. Handle absolute dates with different formats =====

    date_patterns = [
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:\s*,\s*(\d{4}))?',
        r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s*,\s*(\d{4}))?',
        r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?',
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})'
    ]

    months = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
        'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }

    for pattern in date_patterns:
        match = re.search(pattern, t, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()
                if pattern.startswith('(jan|feb'):  # Month Day pattern
                    month_str = groups[0].lower()[:3]
                    day = int(groups[1])
                    year = int(groups[2]) if groups[2] else now.year
                    month = months.get(month_str)
                elif pattern.startswith('(\\d{1,2})\\s+(jan'):  # Day Month pattern
                    day = int(groups[0])
                    month_str = groups[1].lower()[:3]
                    year = int(groups[2]) if groups[2] else now.year
                    month = months.get(month_str)
                elif pattern.startswith('(\\d{1,2})[/-]'):  # DD/MM or MM/DD
                    if len(groups) == 3:
                        num1, num2, year_part = groups
                        num1, num2 = int(num1), int(num2)
                        if num1 > 12:
                            day, month = num1, num2
                        else:
                            month, day = num1, num2
                        year = int(year_part) if year_part else now.year
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                elif pattern.startswith('(\\d{4})'):  # YYYY-MM-DD
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])

                event_date = datetime(year, month, day)

                hour, minute = default_hour, default_minute
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', t, re.IGNORECASE)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    period = time_match.group(3).lower() if time_match.group(3) else ''

                    if period == 'pm' and hour < 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0

                event_datetime = event_date.replace(hour=hour, minute=minute)
                return (
                    event_datetime.strftime("%Y-%m-%d"),
                    event_datetime.strftime("%H:%M")
                )

            except (ValueError, TypeError):
                continue

    # ===== 2. Handle relative dates =====

    if "today" in t:
        dt_ = now.replace(hour=default_hour, minute=default_minute)
        return dt_.strftime("%Y-%m-%d"), dt_.strftime("%H:%M")

    if "tomorrow" in t and "day after" not in t:
        dt_ = now + timedelta(days=1)
        dt_ = dt_.replace(hour=default_hour, minute=default_minute)
        return dt_.strftime("%Y-%m-%d"), dt_.strftime("%H:%M")

    if "day after tomorrow" in t:
        dt_ = now + timedelta(days=2)
        dt_ = dt_.replace(hour=default_hour, minute=default_minute)
        return dt_.strftime("%Y-%m-%d"), dt_.strftime("%H:%M")

    if "yesterday" in t:
        dt_ = now - timedelta(days=1)
        dt_ = dt_.replace(hour=default_hour, minute=default_minute)
        return dt_.strftime("%Y-%m-%d"), dt_.strftime("%H:%M")

    if "next week" in t:
        dt_ = now + timedelta(days=7)
        dt_ = dt_.replace(hour=default_hour, minute=default_minute)
        return dt_.strftime("%Y-%m-%d"), dt_.strftime("%H:%M")

    if "next month" in t:
        dt_ = now + timedelta(days=30)
        dt_ = dt_.replace(hour=default_hour, minute=default_minute)
        return dt_.strftime("%Y-%m-%d"), dt_.strftime("%H:%M")

    # ===== 3. Handle weekdays =====

    weekdays = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }

    weekday_match = re.search(
        r'\b(this|next|coming)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b',
        t,
        re.IGNORECASE
    )

    if weekday_match:
        prefix = weekday_match.group(1) or ''
        day_name = weekday_match.group(2).lower()

        if day_name in weekdays:
            target_weekday = weekdays[day_name]
            current_weekday = now.weekday()
            days_ahead = target_weekday - current_weekday

            if prefix.lower() in ['next', 'coming']:
                if days_ahead <= 0:
                    days_ahead += 7
                days_ahead += 7
            else:
                if days_ahead < 0:
                    days_ahead += 7

            event_date = now + timedelta(days=days_ahead)

            hour, minute = default_hour, default_minute
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', t, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                period = time_match.group(3).lower() if time_match.group(3) else ''

                if period == 'pm' and hour < 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0

            event_datetime = event_date.replace(hour=hour, minute=minute)
            return (
                event_datetime.strftime("%Y-%m-%d"),
                event_datetime.strftime("%H:%M")
            )

    # ===== 4. Time-of-day expressions =====

    time_expressions = {
        'morning': (9, 0),
        'afternoon': (14, 0),
        'evening': (18, 0),
        'night': (20, 0),
        'tonight': (20, 0),
        'noon': (12, 0),
        'midnight': (0, 0),
        'lunch': (12, 30),
        'dinner': (19, 0),
        'breakfast': (8, 0),
    }

    for expr, (hour, minute) in time_expressions.items():
        if expr in t:
            date_found = False

            for pattern in date_patterns[:2]:
                match = re.search(pattern, t, re.IGNORECASE)
                if match:
                    try:
                        groups = match.groups()
                        if pattern.startswith('(jan|feb'):
                            month_str = groups[0].lower()[:3]
                            day = int(groups[1])
                            year = int(groups[2]) if groups[2] else now.year
                            month = months.get(month_str)
                        else:
                            day = int(groups[0])
                            month_str = groups[1].lower()[:3]
                            year = int(groups[2]) if groups[2] else now.year
                            month = months.get(month_str)

                        event_date = datetime(year, month, day)
                        event_datetime = event_date.replace(hour=hour, minute=minute)
                        return (
                            event_datetime.strftime("%Y-%m-%d"),
                            event_datetime.strftime("%H:%M")
                        )
                    except Exception:
                        continue

            if hour < 12:
                dt_ = now.replace(hour=hour, minute=minute)
                if dt_ < now:
                    dt_ += timedelta(days=1)
            else:
                dt_ = now.replace(hour=hour, minute=minute)
                if dt_ < now:
                    dt_ += timedelta(days=1)

            return dt_.strftime("%Y-%m-%d"), dt_.strftime("%H:%M")

    # ===== 5. Try dateparser as fallback =====

    try:
        import dateparser
        parsed = dateparser.parse(
            t,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': now,
                'PREFER_DAY_OF_MONTH': 'first'
            }
        )
        if parsed:
            if parsed.hour == 0 and parsed.minute == 0:
                parsed = parsed.replace(hour=default_hour, minute=default_minute)
            return parsed.strftime("%Y-%m-%d"), parsed.strftime("%H:%M")
    except ImportError:
        pass

    # ===== 6. Ultimate fallback =====
    fallback = now + timedelta(days=1)
    fallback = fallback.replace(hour=default_hour, minute=default_minute)
    return fallback.strftime("%Y-%m-%d"), fallback.strftime("%H:%M")


def get_formatted_upcoming_events(days=7):
    """Get formatted upcoming events for display"""
    events = get_upcoming_events(days)
    formatted = []

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:
            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            time_str = event_time.strftime('%I:%M %p')
            date_str = event_time.strftime('%b %d, %Y')
        else:
            time_str = "All day"
            event_date = datetime.fromisoformat(start)
            date_str = event_date.strftime('%b %d, %Y')

        formatted.append({
            'title': event.get('summary', 'No title'),
            'time': time_str,
            'date': date_str
        })

    return formatted
