import re
from datetime import datetime as dt, timedelta

from rapidfuzz import process, fuzz
from google_tasks import (
    create_task, get_pending_tasks, get_completed_tasks, get_all_tasks,
    get_tasks_due_today, get_tasks_due_tomorrow, get_upcoming_tasks,
    get_overdue_tasks, search_tasks, get_task_statistics,
    complete_task, delete_task, get_task_lists, create_task_list,
    delete_task_list, update_task, reschedule_task,
    move_task_between_lists,
)
from email_assistant import (
    send_email, log_email, generate_email_content, extract_subject,
)
from google_calendar import (
    create_event, get_events_today, get_events_tomorrow,
    get_upcoming_events, search_events, delete_event,
    get_calendar_statistics, get_formatted_events_today,
    get_formatted_events_tomorrow, get_formatted_upcoming_events,
    reschedule_event, parse_datetime_for_event,
)

TASKS_AVAILABLE = True
EMAIL_AVAILABLE = True
CALENDAR_AVAILABLE = True

class SmartTimeParser:
    def __init__(self):
        self.months = {
            'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
            'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
            'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
            'nov': 11, 'november': 11, 'dec': 12, 'december': 12
        }

    def extract_datetime(self, text):
        text_lower = text.lower()
        now = dt.now()
        target_date = self._extract_date(text_lower, now)
        hour, minute = self._extract_time(text_lower)
        try:
            target_datetime = dt.combine(target_date, dt.min.time()).replace(
                hour=hour, minute=minute
            )
            if (target_datetime < now and
                'tomorrow' not in text_lower and
                'today' not in text_lower and
                not any(month in text_lower for month in self.months.keys())):
                target_datetime += timedelta(days=1)
            return target_datetime
        except Exception:
            return dt.combine(
                target_date + timedelta(days=1),
                dt.min.time()
            ).replace(hour=hour, minute=minute)

    def _extract_date(self, text, now):
        text_lower = text.lower()
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6
        }
        for day_name, day_num in weekdays.items():
            if day_name in text_lower:
                if f'next {day_name}' in text_lower:
                    days_ahead = (day_num - now.weekday()) % 7
                    if days_ahead <= 0:
                        days_ahead += 7
                    days_ahead += 7
                    return now.date() + timedelta(days=days_ahead)
                else:
                    days_ahead = (day_num - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    return now.date() + timedelta(days=days_ahead)

        date_patterns = [
            r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*',
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
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
                    target_date = dt(year, month, day).date()
                    if target_date < now.date():
                        target_date = target_date.replace(year=year + 1)
                    return target_date
                except (ValueError, IndexError):
                    continue

        if 'today' in text_lower:
            return now.date()
        if 'day after tomorrow' in text_lower:
            return now.date() + timedelta(days=2)
        if 'tomorrow' in text_lower:
            return now.date() + timedelta(days=1)
        if 'yesterday' in text_lower:
            return now.date() - timedelta(days=1)
        if 'next week' in text_lower:
            return now.date() + timedelta(days=7)
        if 'next month' in text_lower:
            return now.date() + timedelta(days=30)
        return now.date()

    def extract_datetime_for_email(self, text):
        text_lower = text.lower()
        now = dt.now()
        hour, minute = self._extract_time(text_lower)
        target_date = self._extract_date(text_lower, now)
        try:
            target_datetime = dt.combine(
                target_date, dt.min.time()
            ).replace(hour=hour, minute=minute)
            has_specific_date = any(pattern in text_lower for pattern in [
                'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
            ]) or re.search(r'\d{1,2}[/-]\d{1,2}', text_lower)
            if target_datetime < now and not has_specific_date:
                target_datetime += timedelta(days=1)
            return target_datetime
        except Exception:
            fallback = now + timedelta(days=1)
            return fallback.replace(hour=hour, minute=minute)

def _extract_time(self, text):
    text_lower = text.lower()

    # 1) Exact "HH:MM am/pm" (12-hour) -> convert to 24-hour
    match = re.search(
        r'(\d{1,2}):(\d{2})\s*(am|pm)\b', text_lower, re.IGNORECASE
    )
    if not match:
        match = re.search(
            r'(\d{1,2}):(\d{2})(am|pm)\b', text_lower, re.IGNORECASE
        )
    if match:
        try:
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3).lower()
            if period == 'pm' and hour < 12:
                hour += 12
            if period == 'am' and hour == 12:
                hour = 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
        except (ValueError, IndexError):
            pass

    # 2) "HH am/pm" (no minutes) -> convert to 24-hour
    match = re.search(r'(\d{1,2})\s*(am|pm)\b', text_lower, re.IGNORECASE)
    if not match:
        match = re.search(r'(\d{1,2})(am|pm)\b', text_lower, re.IGNORECASE)
    if match:
        try:
            hour = int(match.group(1))
            period = match.group(2).lower()
            if period == 'pm' and hour < 12:
                hour += 12
            if period == 'am' and hour == 12:
                hour = 0
            if 0 <= hour <= 23:
                return hour, 0
        except (ValueError, IndexError):
            pass

    # 3) Plain "HH:MM" ONLY when there is NO 'am' or 'pm' anywhere
    if 'am' not in text_lower and 'pm' not in text_lower:
        match = re.search(r'(\d{1,2}):(\d{2})', text_lower)
        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return hour, minute
            except (ValueError, IndexError):
                pass

    # 4) "at HH[:MM] am/pm"
    match = re.search(
        r'\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_lower, re.IGNORECASE
    )
    if match:
        try:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            period = match.group(3).lower() if match.group(3) else ''
            if period:
                if period == 'pm' and hour < 12:
                    hour += 12
                if period == 'am' and hour == 12:
                    hour = 0
            # If no period, and hour <= 11, treat as afternoon (optional)
            elif hour <= 11:
                hour += 12
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
        except (ValueError, IndexError):
            pass

    # 5) Semantic fallbacks
    if any(word in text_lower for word in ['noon', 'midday']):
        return 12, 0
    if 'midnight' in text_lower:
        return 0, 0
    if 'morning' in text_lower:
        return 9, 0
    if 'afternoon' in text_lower:
        return 14, 0
    if 'evening' in text_lower:
        return 18, 0
    if any(word in text_lower for word in ['night', 'tonight']):
        return 20, 0
    if 'lunch' in text_lower:
        return 12, 30
    if 'dinner' in text_lower:
        return 19, 0

    # Final default
    return 14, 0

def extract_event_title(user_input):
    text = user_input.lower()
    text = re.sub(r'^(create|add|make|new|schedule|event)\s+', '', text)
    text = re.sub(r'\s+(event|appointment)\s+', ' ', text)
    words = text.split()
    title_words = []

    time_patterns = [
        r'\d{1,2}:\d{2}',
        r'\d{1,2}(?:am|pm)',
        r'\b(at|from|to)\b',
    ]
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{1,2}-\d{1,2}-\d{4}',
        r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}',
    ]

    for i, word in enumerate(words):
        is_time_word = any(re.match(p, word, re.IGNORECASE) for p in time_patterns)
        is_date_word = any(re.match(p, word, re.IGNORECASE) for p in date_patterns)
        if word == 'on' and i + 1 < len(words):
            next_word = words[i + 1].lower()
            weekdays = [
                'monday', 'tuesday', 'wednesday', 'thursday',
                'friday', 'saturday', 'sunday',
                'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
            ]
            if next_word in weekdays:
                break
        if is_time_word or is_date_word:
            break
        title_words.append(word)

    title = ' '.join(title_words).strip()
    if not title:
        title = re.sub(
            r'\b(on|at|from|to|today|tomorrow|next)\b', '',
            text, flags=re.IGNORECASE
        ).strip()
    title = ' '.join(word.capitalize() for word in title.split())
    if not title:
        title = "Event"
    return title

def extract_event_title(user_input):
    text = user_input.lower()
    text = re.sub(r'^(create|add|make|new|schedule|event)\s+', '', text)
    text = re.sub(r'\s+(event|appointment)\s+', ' ', text)
    words = text.split()
    title_words = []

    time_patterns = [
        r'\d{1,2}:\d{2}',
        r'\d{1,2}(?:am|pm)',
        r'\b(at|from|to)\b',
    ]
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{1,2}-\d{1,2}-\d{4}',
        r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}',
    ]

    for i, word in enumerate(words):
        is_time_word = any(re.match(p, word, re.IGNORECASE) for p in time_patterns)
        is_date_word = any(re.match(p, word, re.IGNORECASE) for p in date_patterns)
        if word == 'on' and i + 1 < len(words):
            next_word = words[i + 1].lower()
            weekdays = [
                'monday', 'tuesday', 'wednesday', 'thursday',
                'friday', 'saturday', 'sunday',
                'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
            ]
            if next_word in weekdays:
                break
        if is_time_word or is_date_word:
            break
        title_words.append(word)

    title = ' '.join(title_words).strip()
    if not title:
        title = re.sub(
            r'\b(on|at|from|to|today|tomorrow|next)\b', '',
            text, flags=re.IGNORECASE
        ).strip()
    title = ' '.join(word.capitalize() for word in title.split())
    if not title:
        title = "Event"
    return title
