import re
import time
import threading
from datetime import datetime as dt, timedelta
from rapidfuzz import process, fuzz

try:
    from google_tasks import *
    TASKS_AVAILABLE = True
    print("Google Tasks module loaded successfully")
except ImportError as e:
    print(f"Google Tasks module not available - {e}")
    TASKS_AVAILABLE = False
    
    def task_function_error():
        raise ImportError("Google Tasks module not available")
    
    def create_task(title): 
        raise ImportError("Google Tasks module not available")
    
    def get_pending_tasks(): 
        raise ImportError("Google Tasks module not available")
    
    def get_completed_tasks(): 
        raise ImportError("Google Tasks module not available")
    
    def get_all_tasks(): 
        raise ImportError("Google Tasks module not available")
    
    def get_tasks_due_today(): 
        raise ImportError("Google Tasks module not available")
    
    def get_tasks_due_tomorrow(): 
        raise ImportError("Google Tasks module not available")
    
    def get_upcoming_tasks(): 
        raise ImportError("Google Tasks module not available")
    
    def get_overdue_tasks(): 
        raise ImportError("Google Tasks module not available")
    
    def search_tasks(query): 
        raise ImportError("Google Tasks module not available")
    
    def get_task_statistics(): 
        raise ImportError("Google Tasks module not available")
    
    def complete_task(title): 
        raise ImportError("Google Tasks module not available")
    
    def delete_task(title): 
        raise ImportError("Google Tasks module not available")
    
    def get_task_lists(): 
        raise ImportError("Google Tasks module not available")
    
    def create_task_list(name): 
        raise ImportError("Google Tasks module not available")
    
    def delete_task_list(name): 
        raise ImportError("Google Tasks module not available")
    
    def update_task(title): 
        raise ImportError("Google Tasks module not available")
    
    def reschedule_task(title, new_date): 
        raise ImportError("Google Tasks module not available")
    
    def move_task_between_lists(title, target_list): 
        raise ImportError("Google Tasks module not available")

try:
    from email_assistant import send_email, log_email, generate_email_content, extract_subject
    EMAIL_AVAILABLE = True
    print("Email assistant loaded successfully")
except ImportError as e:
    print(f"Email assistant not available - {e}")
    EMAIL_AVAILABLE = False
    
    def send_email(to, cc, bcc, subject, body, scheduled_time=None): 
        raise ImportError("Email assistant not available")
    
    def log_email(*args): 
        raise ImportError("Email assistant not available")
    
    def generate_email_content(prompt): 
        raise ImportError("Email assistant not available")
    
    def extract_subject(text): 
        raise ImportError("Email assistant not available")

try:
    from google_calendar import (
        create_event, get_events_today, get_events_tomorrow,
        get_upcoming_events, search_events,delete_event,
        get_calendar_statistics, get_formatted_events_today,
        get_formatted_events_tomorrow, get_formatted_upcoming_events,reschedule_event,
        parse_datetime_for_event
    )
    
    CALENDAR_AVAILABLE = True
    print("Google Calendar module loaded successfully")
    
except ImportError as e:
    print(f"Google Calendar module not available - {e}")
    CALENDAR_AVAILABLE = False
    
    def create_event(user_input):
        raise ImportError("Google Calendar module not available")
    
    def get_events_today():
        raise ImportError("Google Calendar module not available")
    
    def get_events_tomorrow():
        raise ImportError("Google Calendar module not available")
    
    def get_upcoming_events(days=7):
        raise ImportError("Google Calendar module not available")
    
    def search_events(query):
        raise ImportError("Google Calendar module not available")
    
    def delete_event(title, delete_all=False):
        raise ImportError("Google Calendar module not available")

    def get_calendar_statistics():
        raise ImportError("Google Calendar module not available")
    
    def get_formatted_events_today():
        raise ImportError("Google Calendar module not available")
    
    def get_formatted_events_tomorrow():
        raise ImportError("Google Calendar module not available")
    
    def get_formatted_upcoming_events(days=7):
        raise ImportError("Google Calendar module not available")

class SmartTimeParser:
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
        now = dt.now()
        
        target_date = self._extract_date(text_lower, now)
        
        hour, minute = self._extract_time(text_lower)
        
        try:
            target_datetime = dt.combine(target_date, dt.min.time()).replace(hour=hour, minute=minute)
            
            if (target_datetime < now and 
                'tomorrow' not in text_lower and 
                'today' not in text_lower and
                not any(month in text_lower for month in self.months.keys())):
                target_datetime += timedelta(days=1)
                
            return target_datetime
        except Exception:
            return dt.combine(target_date + timedelta(days=1), dt.min.time()).replace(hour=hour, minute=minute)

    def _extract_date(self, text, now):
        """Extract date from text - IMPROVED to handle weekdays"""
        text_lower = text.lower()
        
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
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
        elif 'tomorrow' in text_lower and 'day after' not in text_lower:
            return now.date() + timedelta(days=1)
        elif 'day after tomorrow' in text_lower:
            return now.date() + timedelta(days=2)
        elif 'yesterday' in text_lower:
            return now.date() - timedelta(days=1)
        elif 'next week' in text_lower:
            return now.date() + timedelta(days=7)
        elif 'next month' in text_lower:
            return now.date() + timedelta(days=30)
        
        return now.date()

    def extract_datetime_for_email(self, text):

        """Extract datetime specifically for email scheduling"""
        text_lower = text.lower()
        now = dt.now()
        
        print(f"DEBUG extract_datetime_for_email: parsing '{text}'")
        print(f"DEBUG extract_datetime_for_email: full text lower: '{text_lower}'")
        
        hour, minute = self._extract_time(text_lower)
        print(f"DEBUG extract_datetime_for_email: extracted time: {hour}:{minute:02d}")
        
        target_date = self._extract_date(text_lower, now)
        print(f"DEBUG extract_datetime_for_email: extracted date: {target_date}")
        
        try:
            target_datetime = dt.combine(target_date, dt.min.time()).replace(hour=hour, minute=minute)
            
            has_specific_date = any(pattern in text_lower for pattern in [
                'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
            ]) or re.search(r'\d{1,2}[/-]\d{1,2}', text_lower)
            
            if (target_datetime < now and not has_specific_date):
                print(f"DEBUG: Time in past ({target_datetime}), moving to next day")
                target_datetime += timedelta(days=1)
            
            print(f"DEBUG: Final datetime: {target_datetime}")
            print(f"DEBUG: Final datetime formatted: {target_datetime.strftime('%Y-%m-%d %H:%M')}")
            return target_datetime
            
        except Exception as e:
            print(f"DEBUG: Error combining date/time: {e}")
            fallback = now + timedelta(days=1)
            fallback = fallback.replace(hour=hour, minute=minute)
            return fallback

    def _extract_time(self, text):
        """Extract time from text - FIXED 12am/12pm handling"""
        text_lower = text.lower()
        
        match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)\b', text_lower, re.IGNORECASE)
        if not match:
            match = re.search(r'(\d{1,2}):(\d{2})(am|pm)\b', text_lower, re.IGNORECASE)
        
        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2))
                period = match.group(3).lower()
                
                if period == 'pm':
                    if hour < 12:
                        hour += 12
                elif period == 'am':
                    if hour == 12:
                        hour = 0 
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    print(f"DEBUG _extract_time: Found {hour}:{minute} from pattern 1")
                    return hour, minute
            except (ValueError, IndexError):
                pass
        
        match = re.search(r'(\d{1,2})\s*(am|pm)\b', text_lower, re.IGNORECASE)
        if not match:
            match = re.search(r'(\d{1,2})(am|pm)\b', text_lower, re.IGNORECASE)
        
        if match:
            try:
                hour = int(match.group(1))
                period = match.group(2).lower()
                
                if period == 'pm':
                    if hour < 12:
                        hour += 12
                elif period == 'am':
                    if hour == 12:
                        hour = 0  
                
                if 0 <= hour <= 23:
                    print(f"DEBUG _extract_time: Found {hour}:00 from pattern 2")
                    return hour, 0
            except (ValueError, IndexError):
                pass
        
        match = re.search(r'(\d{1,2}):(\d{2})', text_lower)
        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    print(f"DEBUG _extract_time: Found {hour}:{minute} from pattern 3")
                    return hour, minute
            except (ValueError, IndexError):
                pass
        
        match = re.search(r'\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_lower, re.IGNORECASE)
        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                period = match.group(3).lower() if match.group(3) else ''
                
                if period:
                    if period == 'pm':
                        if hour < 12:
                            hour += 12
                    elif period == 'am':
                        if hour == 12:
                            hour = 0
                elif hour <= 11:
                    hour += 12 
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    print(f"DEBUG _extract_time: Found {hour}:{minute} from pattern 4")
                    return hour, minute
            except (ValueError, IndexError):
                pass
        
        if any(word in text_lower for word in ['noon', 'midday']):
            print(f"DEBUG _extract_time: Found noon from pattern 5")
            return 12, 0
        elif 'midnight' in text_lower:
            print(f"DEBUG _extract_time: Found midnight from pattern 5")
            return 0, 0
        elif 'morning' in text_lower:
            print(f"DEBUG _extract_time: Found morning from pattern 5")
            return 9, 0
        elif 'afternoon' in text_lower:
            print(f"DEBUG _extract_time: Found afternoon from pattern 5")
            return 14, 0
        elif 'evening' in text_lower:
            print(f"DEBUG _extract_time: Found evening from pattern 5")
            return 18, 0
        elif any(word in text_lower for word in ['night', 'tonight']):
            print(f"DEBUG _extract_time: Found night from pattern 5")
            return 20, 0
        elif 'lunch' in text_lower:
            print(f"DEBUG _extract_time: Found lunch from pattern 5")
            return 12, 30
        elif 'dinner' in text_lower:
            print(f"DEBUG _extract_time: Found dinner from pattern 5")
            return 19, 0
        
        print(f"DEBUG _extract_time: Using default time 14:00")
        return 14, 0

def extract_event_title(user_input):    
    "Extract clean event title - IMPROVED to handle 'on [day]'"
    print(f"DEBUG extract_event_title START:")
    print(f"  Original input: '{user_input}'")
    
    text = user_input.lower()
    text = re.sub(r'^(create|add|make|new|schedule|event)\s+', '', text)
    text = re.sub(r'\s+(event|appointment)\s+', ' ', text)
    
    print(f"  After command removal: '{text}'")
    
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
        is_time_word = any(re.match(pattern, word, re.IGNORECASE) for pattern in time_patterns)
        is_date_word = any(re.match(pattern, word, re.IGNORECASE) for pattern in date_patterns)
        
        if word == 'on' and i + 1 < len(words):
            next_word = words[i + 1].lower()
            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                       'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            if next_word in weekdays:
                break
        
        if is_time_word or is_date_word:
            break
            
        title_words.append(word)
    
    title = ' '.join(title_words).strip()
    
    if not title:
        title = re.sub(r'\b(on|at|from|to|today|tomorrow|next)\b', '', text, flags=re.IGNORECASE)
        title = title.strip()
    
    title = ' '.join(word.capitalize() for word in title.split())
    
    if not title:
        title = "Event"
    
    print(f"  Final title: '{title}'")
    return title

class EmailScheduler:
    def __init__(self):
        self.scheduled_emails = []
        self.running = False
     
    def start_scheduler(self):
        self.running = True
        threading.Thread(target=self._scheduler_loop, daemon=True).start()
    
    def stop_scheduler(self):
        self.running = False
    
    def schedule_email(self, to_email, subject, body, scheduled_time, user_input=""):
        """
        Schedule or send email immediately based on keywords in user_input
        """
        # Check for immediate sending keywords FIRST
        if user_input:
            user_input_lower = user_input.lower()
            immediate_keywords = ['now', 'immediately', 'right away', 'asap', 'straight away', 'instantly']
            
            for keyword in immediate_keywords:
                if keyword in user_input_lower:
                    print(f"DEBUG: Immediate sending keyword '{keyword}' detected, sending now")
                    # Send immediately
                    try:
                        success = send_email([to_email], [], [], subject, body)
                        if success:
                            return True, "sent immediately"
                        else:
                            return False, "failed to send immediately"
                    except Exception as e:
                        return False, f"error sending immediately: {str(e)}"
        
        # If no immediate keywords, proceed with scheduling
        try:
            scheduled_dt = dt.strptime(scheduled_time, "%Y-%m-%d %H:%M")
            if scheduled_dt <= dt.now():
                print(f"DEBUG: Scheduled time is in the past, sending now")
                return send_email([to_email], [], [], subject, body), "sent"
            
            self.scheduled_emails.append({
                'to_email': to_email, 'subject': subject, 'body': body,
                'scheduled_time': scheduled_dt, 'sent': False
            })
            print(f"DEBUG: Email scheduled for {scheduled_time}")
            return True, f"scheduled for {scheduled_time}"
        except Exception as e:
            return False, f"error: {str(e)}"
    
    def _scheduler_loop(self):
        while self.running:
            try:
                now = dt.now()
                for email in self.scheduled_emails[:]:
                    if not email['sent'] and email['scheduled_time'] <= now:
                        print(f"DEBUG: Sending scheduled email: {email['subject']}")
                        send_email([email['to_email']], [], [], email['subject'], email['body'])
                        email['sent'] = True
                        self.scheduled_emails.remove(email)
                time.sleep(30)
            except:
                time.sleep(60)

class SmartChatbot:
    def __init__(self):
        self.time_parser = SmartTimeParser()
        self.email_scheduler = EmailScheduler()
        self.email_scheduler.start_scheduler()
        self.caches = {'tasks': None, 'events': None}
        self.cache_times = {'tasks': 0, 'events': 0}
        
        print(f"\nPersonal Assistant - Module Status:")
        print(f"  Tasks: {'Available' if TASKS_AVAILABLE else 'NOT Available'}")
        print(f"  Email: {'Available' if EMAIL_AVAILABLE else 'NOT Available'}")
        print(f"  Calendar: {'Available' if CALENDAR_AVAILABLE else 'NOT Available'}")
        print(f"\nType 'help' for available commands\n")

    def __del__(self):
        self.email_scheduler.stop_scheduler()

    def _get_cached(self, cache_type, fetch_func):
        """Generic cache with 5-second TTL"""
        if (self.caches[cache_type] and 
            time.time() - self.cache_times[cache_type] < 5):
            return self.caches[cache_type]
        
        self.caches[cache_type] = fetch_func()
        self.cache_times[cache_type] = time.time()
        return self.caches[cache_type]

    def _extract_email_subject(self, text):
        """Extract email subject from natural language"""
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text, flags=re.IGNORECASE)
        
        scheduling_phrases = [
            r'send\s+(?:mail|email)\s+on\s+.+',
            r'email\s+on\s+.+',
            r'mail\s+on\s+.+',
            r'schedule\s+(?:mail|email)\s+for\s+.+',
            r'send\s+(?:mail|email)\s+at\s+.+',
            r'remind\s+(?:him|her|them)\s+to\s+.+',
            r'keep\s+.+\s+in\s+cc',
            r'\bin\s+cc\b',
        ]
        
        for phrase in scheduling_phrases:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE)
        
        command_words = [
            r'^write\s+a\s+',
            r'^send\s+',
            r'^email\s+',
            r'^mail\s+',
            r'\bto\s+',
            r'\bfor\s+',
            r'\bcc\b',
            r'\bbcc\b',
            r'\band\b',
        ]
        
        for word in command_words:
            text = re.sub(word, '', text, flags=re.IGNORECASE)
        
        match = re.search(r'for\s+(.+)', text, re.IGNORECASE)
        if match:
            subject = match.group(1).strip()
        else:
            words = text.split()
            meaningful_words = []
            stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'on', 'at', 'in', 'to', 'of', 'bring', 'his', 'her', 'their'}
            
            for word in words:
                if word.lower() not in stop_words and len(word) > 2:
                    meaningful_words.append(word)
                if len(meaningful_words) >= 6: 
                    break
            
            subject = ' '.join(meaningful_words) if meaningful_words else "Important Message"
        
        subject = re.sub(r'\s+', ' ', subject)
        subject = subject.strip()
        
        if subject:
            subject = subject[0].upper() + subject[1:]
        
        return subject if subject else "Email"

    def split_multiple_commands(self, user_input):
        """Split complex input into individual commands"""
        commands = []
        
        quoted_sections = []
        def protect_quotes(match):
            quoted_sections.append(match.group(0))
            return f"__QUOTE_{len(quoted_sections)-1}__"
        
        protected_text = re.sub(r'["\'][^"\']*["\']', protect_quotes, user_input)
        split_pattern = r'\s+(?:and|also|then)\s+|\s*,\s*|\s*;\s*|\.\s+(?=[A-Z])'
        parts = re.split(split_pattern, protected_text)
        
        for i, part in enumerate(parts):
            for j in range(len(quoted_sections)):
                placeholder = f"__QUOTE_{j}__"
                if placeholder in part:
                    part = part.replace(placeholder, quoted_sections[j])
            parts[i] = part.strip()
        
        commands = [cmd for cmd in parts if cmd]
        
        if len(commands) == 0:
            commands = [user_input.strip()]
        
        return commands

    def _process_multiple_commands(self, user_input):
        """Process multiple commands in a single input"""
        commands = self.split_multiple_commands(user_input)
        
        if len(commands) == 1:
            return self.process_single_command(commands[0])
        
        responses = []
        
        for i, cmd in enumerate(commands):
            response = self.process_single_command(cmd)
            responses.append(response)
        
        if len(responses) == 0:
            return "No commands processed."
        
        return "\n".join(responses)

    def _find_match(self, query, items, threshold=70):
        """Generic fuzzy matching"""
        if not items:
            return None, 0
        
        titles = []
        for item in items:
            if isinstance(item, dict):
                title = (item.get('title') or item.get('summary') or 
                        item.get('name') or '')
                if title:
                    titles.append(title)
                else:
                    titles.append('No title')
            else:
                titles.append(str(item))
        
        if not titles:
            return None, 0
        
        query_lower = query.lower()
        for title in titles:
            if title.lower() == query_lower:
                return title, 100
        
        for title in titles:
            if query_lower in title.lower():
                return title, 90
        
        best_match, score, _ = process.extractOne(query, titles, scorer=fuzz.partial_ratio)
        
        return best_match if score >= threshold else None, score

    def _reschedule_task(self, text, user_input):
        """Reschedule task due date"""
        query = re.sub(r'\b(reschedule|move|change|task|todo)\b', '', text, flags=re.IGNORECASE).strip()
        
        if not query:
            return "Please specify which task to reschedule"
        
        try:
            new_date = self.time_parser.extract_datetime(user_input)
            new_date_str = new_date.strftime("%Y-%m-%d")
            time_str = new_date.strftime("%H:%M")
            due_input = (new_date_str, time_str)  
        except Exception as e:
            return f"Please specify a valid date. Error: {str(e)}"
        
        tasks = self._get_cached('tasks', get_all_tasks)
        best_match, score = self._find_match(query, tasks)
        
        if best_match:
            try:
                result = update_task(best_match, new_due_raw=due_input)
                self.caches['tasks'] = None
                
                if result and 'id' in result:
                    return f"Task '{best_match}' due date updated to {new_date.strftime('%b %d, %Y')}"
                else:
                    return f"Failed to update task"
                    
            except ValueError as e:
                return f"Task not found: {str(e)}"
            except Exception as e:
                return f"Error updating task: {str(e)}"
        
        return f"Task '{query}' not found"

    def process_message(self, user_input):
        """Main message processing"""
        text = user_input.lower().strip()
        
        if 'reschedule task' in text or 'update task' in text:
            return self._reschedule_task(text, user_input)
        elif 'reschedule event' in text or 'update event' in text:
            return self._reschedule_event(text, user_input)
        
        if any(kw in text for kw in ['reschedule', 'move', 'change', 'update']):
            if 'task' in text:
                return self._reschedule_task(text, user_input)
            elif any(kw in text for kw in ['event', 'meeting', 'appointment']):
                return self._reschedule_event(text, user_input)
            else:
                return self._reschedule_item(text, user_input)
        
        if re.search(r'@[\w\.-]+\.\w+', text) and any(kw in text for kw in ['send', 'email']):
            return self._process_email(user_input)
        
        if any(keyword in text for keyword in ['task', 'todo', 'reminder']):
            if any(kw in text for kw in ['create', 'add', 'make', 'new']):
                return self._create_task(user_input)
            elif any(kw in text for kw in ['show', 'list', 'view']):
                return self._view_tasks(text)
            elif any(kw in text for kw in ['complete', 'finish', 'done']):
                return self._complete_item(text, user_input)
            elif any(kw in text for kw in ['delete', 'remove']):
                return self._delete_task(text)
        
        if any(keyword in text for keyword in ['event', 'meeting', 'appointment', 'calendar']):
            if any(kw in text for kw in ['create', 'add', 'make', 'new', 'schedule']):
                return self._create_event(user_input)
            elif any(kw in text for kw in ['show', 'list', 'view']):
                return self._view_calendar(text)
            elif any(kw in text for kw in ['delete', 'remove', 'cancel']):
                return self._delete_event(text)
            elif any(kw in text for kw in ['reschedule', 'move', 'change']):
                return self._reschedule_event(text, user_input)
        
        command_handlers = {
            'calendar': self._process_calendar,
            'event': self._process_calendar,
            'meeting': self._process_calendar,
            'appointment': self._process_calendar,
            'show': self._view_items,
            'list': self._view_items,
            'view': self._view_items,
            'complete': self._complete_item,
            'finish': self._complete_item,
            'delete': self._delete_item,
            'remove': self._delete_item,
            'cancel': self._delete_item,
            'create': self._create_item,
            'add': self._create_item,
            'search': self._search_items,
            'find': self._search_items,
            'stats': self._show_stats,
            'statistics': self._show_stats,
            'help': self._show_help
        }
        
        for keyword, handler in command_handlers.items():
            if keyword in text:
                return handler(text, user_input)
        
        if 'create' in text:
            return "Please specify what you want to create: 'create task' or 'create event'"
        
        return "I'm not sure what you want to do. Type 'help' for available commands."

    def _process_calendar(self, text, user_input):
        """Handle calendar operations"""
        try:
            if any(kw in text for kw in ['show', 'list', 'view']):
                return self._view_calendar(text)
            elif any(kw in text for kw in ['create', 'add', 'make', 'schedule']):
                return self._create_event(user_input)
            elif any(kw in text for kw in ['delete', 'remove', 'cancel']):
                return self._delete_event(text)
            elif any(kw in text for kw in ['reschedule', 'move', 'change']):
                return self._reschedule_event(text, user_input)
            elif any(kw in text for kw in ['search', 'find']):
                return self._search_events(text)
            elif any(kw in text for kw in ['stats', 'statistics']):
                return self._calendar_statistics()
            else:
                return "Try: 'show calendar', 'create event', or 'delete event'"
        except Exception as e:
            return f"Calendar error: {str(e)}"

    def _create_event(self, user_input):
        """Create event - with direct title parameter for Google Calendar"""
        try:
            print(f"DEBUG _create_event START:")
            print(f"  User input: '{user_input}'")
            
            clean_title = extract_event_title(user_input)
            print(f"  Clean title extracted: '{clean_title}'")
            
            time_parser = SmartTimeParser()
            event_time = time_parser.extract_datetime(user_input)
            start_time = event_time.strftime("%Y-%m-%d %H:%M")
            
            print(f"  Extracted time: {start_time}")
            print(f"  Extracted date should be: {event_time.strftime('%A, %B %d')}")
            
            if CALENDAR_AVAILABLE:
                try:
                    result = create_event(title=clean_title, start_time=start_time)
                except TypeError:
                    print("  Google Calendar API doesn't accept separate parameters, using fallback")
                    processed_input = f"{clean_title} at {event_time.strftime('%I:%M %p')} on {event_time.strftime('%b %d')}"
                    result = create_event(processed_input)
            else:
                raise ImportError("Google Calendar module not available")
            
            print(f"DEBUG _create_event AFTER create_event:")
            print(f"  Result: {result}")
            
            if result.get('status') == 'success':
                self.caches['events'] = None
                
                response = f"Event created: {clean_title}"
                if result.get('start_time'):
                    try:
                        event_time = dt.strptime(result['start_time'], "%Y-%m-%d %H:%M")
                        display_time = result.get('display_time', event_time.strftime('%I:%M %p'))
                        response += f" on {event_time.strftime('%A, %b %d')} at {display_time}"
                    except ValueError:
                        response += f" at {result['start_time']}"
                
                print(f"DEBUG _create_event SUCCESS: {response}")
                return response
            
            error_msg = result.get('message', 'Unknown error')
            print(f"DEBUG _create_event FAILED: {error_msg}")
            return f"Failed to create event: {error_msg}"
                
        except Exception as e:
            print(f"DEBUG _create_event EXCEPTION: {e}")
            return f"Error creating event: {str(e)}"

    def _delete_event(self, text):
        """Delete event - with debugging"""
        query = re.sub(r'\b(delete|remove|cancel|event|meeting|appointment)\b', '', text, flags=re.IGNORECASE).strip()
        
        if not query:
            return "Please specify which event to delete"
        
        print(f"DEBUG _delete_event START:")
        print(f"  Query to delete: '{query}'")
        
        events = self._get_cached('events', lambda: get_upcoming_events(30))
        print(f"  Total events found: {len(events)}")
        print(f"  Available events: {[e.get('title', 'No title') for e in events]}")
        
        if not events:
            return "No events found to delete"
        
        best_match, score = self._find_match(query, events)
        
        print(f"  Best match found: '{best_match}' with score: {score}")
        
        if best_match:
            print(f"  Calling delete_event with: '{best_match}'")
            result = delete_event(best_match)
            
            print(f"  Delete result: {result}")
            
            self.caches['events'] = None  
            if result.get('status') == 'success':
                return f"Event deleted: {best_match}"
            else:
                return f"Failed to delete event: {result.get('message', 'Unknown error')}"
        
        print(f"  No matching event found for: '{query}'")
        return f"Event '{query}' not found"

    def _view_calendar(self, text):
        """View calendar events with exact titles"""
        try:
            if 'today' in text:
                events = get_formatted_events_today()
                title = "Today's Events"
            elif 'tomorrow' in text:
                events = get_formatted_events_tomorrow()
                title = "Tomorrow's Events"
            elif 'all' in text:
                events = get_formatted_upcoming_events(30)
                title = "All Events"
            else:
                days_match = re.search(r'(\d+)\s*days?', text)
                days = int(days_match.group(1)) if days_match else 7
                events = get_formatted_upcoming_events(days)
                title = f"Upcoming Events ({days} days)"
            
            if not events:
                return f"No {title.lower()}"
            
            response = [title]
            for event in events[:10]:
                event_title = event.get('title', 'Unknown')
                event_time = event.get('time', 'No time')
                response.append(f"• {event_time}: {event_title}")
            
            return "\n".join(response)
        except Exception as e:
            return f"Error: {str(e)}"

    def _search_events(self, text):
        """Search events"""
        query = re.sub(r'\b(search|find|event)\b', '', text).strip()
        if not query:
            return "Please specify search query"
        
        events = search_events(query)
        if not events:
            return f"No events found for '{query}'"
        
        response = [f"Found {len(events)} events:"]
        for event in events[:5]:
            if isinstance(event, dict):
                response.append(f"• {event.get('title', 'Unknown')}")
            else:
                response.append(f"• {event}")
        
        return "\n".join(response)

    def _calendar_statistics(self):
        """Show calendar stats"""
        stats = get_calendar_statistics()
        if isinstance(stats, dict):
            response = f"Calendar Stats: {stats.get('events_today', 0)} today, {stats.get('events_tomorrow', 0)} tomorrow, {stats.get('upcoming_week', 0)} this week"
            return response
        return "Unable to get calendar statistics"

    def _process_email(self, user_input):
        """Process email sending - ONLY schedule when explicitly asked"""
        if not EMAIL_AVAILABLE:
            return "Email functionality not available"
        
        email_addresses = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)
        if not email_addresses:
            return "Please specify a valid email address"
        
        to_email = email_addresses[0]
        
        cc_emails = []
        if 'cc' in user_input.lower() or 'in cc' in user_input.lower():
            cc_text = user_input.lower()
            cc_index = cc_text.find('cc')
            if cc_index != -1:
                cc_part = user_input[cc_index + 2:]
                cc_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', cc_part)
        
        for email in email_addresses[1:]:  
            if email not in cc_emails:
                cc_emails.append(email)

        
        scheduled_time = None
        email_text_lower = user_input.lower()

        print(f"DEBUG: Checking for scheduling in: '{email_text_lower}'")

        date_time_patterns = [
            r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}:\d{2}\s*(?:am|pm)?)',
            r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\s+\d{1,2}:\d{2}\s*(?:am|pm)?)',
            
            r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)',
            r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})',
            
            r'(\d{1,2}[/-]\d{1,2}[/-]?\d{2,4}?)',
            
            r'(\d{1,2}:\d{2}\s*(?:am|pm)?)',
            r'(\d{1,2}\s*(?:am|pm))',
        ]

        scheduling_keywords = [
            r'(?:send|email|mail).*?\s+on\s+([^.,;]+(?:am|pm|:\d{2}|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov)?)',
            r'(?:send|email|mail).*?\s+at\s+([^.,;]+(?:am|pm|:\d{2}|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov)?)',
            r'(?:schedule).*?\s+for\s+([^.,;]+(?:am|pm|:\d{2}|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov)?)',
        ]

        date_time_text = None
        scheduling_phrase_found = False

        on_patterns = [
            r'on\s+(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}:\d{2}\s*(?:am|pm)?)',
            r'on\s+((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\s+\d{1,2}:\d{2}\s*(?:am|pm)?)',
            r'on\s+(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)',
            r'on\s+((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})',
            r'on\s+(\d{1,2}[/-]\d{1,2}[/-]?\d{2,4}?\s+\d{1,2}:\d{2}\s*(?:am|pm)?)',
            r'on\s+(\d{1,2}:\d{2}\s*(?:am|pm)?)',
        ]

        for pattern in on_patterns:
            matches = list(re.finditer(pattern, email_text_lower, re.IGNORECASE))
            if matches:
                last_match = matches[-1]
                date_time_text = last_match.group(1)
                scheduling_phrase_found = True
                print(f"DEBUG: Found 'on' pattern (last): '{date_time_text}'")
                break

        if not date_time_text:
            all_matches = []
            for pattern in date_time_patterns:
                matches = list(re.finditer(pattern, email_text_lower, re.IGNORECASE))
                all_matches.extend(matches)
            
            if all_matches:
                all_matches.sort(key=lambda m: m.end())
                last_match = all_matches[-1]
                date_time_text = last_match.group(1)
                scheduling_phrase_found = True
                print(f"DEBUG: Found date/time pattern (last): '{date_time_text}'")

        if not date_time_text:
            for pattern in scheduling_keywords:
                matches = list(re.finditer(pattern, email_text_lower, re.IGNORECASE))
                if matches:
                    last_match = matches[-1]
                    date_time_text = last_match.group(1)
                    scheduling_phrase_found = True
                    print(f"DEBUG: Found scheduling keyword (last): '{date_time_text}'")
                    break

        if not date_time_text:
            immediate_words = ['immediately', 'now', 'right away', 'asap']
            if any(word in email_text_lower for word in immediate_words):
                print(f"DEBUG: Immediate sending requested")
                scheduled_time = None
                scheduling_phrase_found = True
            else:
                if any(word in email_text_lower for word in ['today', 'tomorrow', 'next', 'morning', 'afternoon', 'evening']):
                    words = email_text_lower.split()
                    date_words = []
                    found_time_word = False
                    
                    for word in reversed(words):
                        if word in ['today', 'tomorrow', 'next', 'morning', 'afternoon', 'evening', 'night']:
                            found_time_word = True
                            date_words.insert(0, word)
                        elif found_time_word and word not in ['on', 'at', 'for', 'send', 'email', 'mail', 'about']:
                            date_words.insert(0, word)
                        elif found_time_word:
                            break
                    
                    if date_words:
                        date_time_text = ' '.join(date_words)
                        scheduling_phrase_found = True
                        print(f"DEBUG: Found time words: '{date_time_text}'")
        
        if date_time_text:
            try:
                print(f"DEBUG: Attempting to parse date text: '{date_time_text}'")
                
                clean_date_text = date_time_text
                
                if clean_date_text.lower().startswith('on '):
                    clean_date_text = clean_date_text[3:]
                elif clean_date_text.lower().startswith('at '):
                    clean_date_text = clean_date_text[3:]
                
                clean_date_text = clean_date_text.strip()
                print(f"DEBUG: Clean date text for parsing: '{clean_date_text}'")
                
                if re.match(r'^\d{1,2}[:]?\d{0,2}\s*(?:am|pm)?$', clean_date_text, re.IGNORECASE):
                    print(f"DEBUG: Only time found, looking for date in full input")
                    
                    date_patterns = [
                        r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)',
                        r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})',
                        r'(\d{1,2}[/-]\d{1,2}[/-]?\d{2,4}?)',
                    ]
                    
                    full_date_text = None
                    for pattern in date_patterns:
                        match = re.search(pattern, email_text_lower, re.IGNORECASE)
                        if match:
                            full_date_text = match.group(1)
                            print(f"DEBUG: Found date in full text: '{full_date_text}'")
                            break
                    
                    if full_date_text:
                        clean_date_text = f"{full_date_text} {clean_date_text}"
                        print(f"DEBUG: Combined date-time: '{clean_date_text}'")
                
                event_time = self.time_parser.extract_datetime_for_email(clean_date_text)                
                if event_time:  
                    scheduled_time = event_time.strftime("%Y-%m-%d %H:%M")
                    print(f"DEBUG: Successfully parsed scheduled time: {scheduled_time}")
                    print(f"DEBUG: That's {event_time.strftime('%A, %B %d at %I:%M %p')}")
                else:
                    print(f"DEBUG: Could not parse time from: '{clean_date_text}'")
                    scheduled_time = None
                    
            except Exception as e:
                print(f"DEBUG: Error parsing time: {e}")
                import traceback
                traceback.print_exc()
                scheduled_time = None
        elif scheduling_phrase_found and not date_time_text:
            print(f"DEBUG: Scheduling phrase found but no date/time - sending immediately")
            scheduled_time = None
        
        subject = self._extract_email_subject(user_input)
        
        body = generate_email_content(user_input)
        
        print(f"\nEmail Preview:")
        print(f"   To: {to_email}")
        if cc_emails:
            print(f"   CC: {', '.join(cc_emails)}")
        print(f"   Subject: {subject}")
        
        if scheduled_time:
            scheduled_dt = dt.strptime(scheduled_time, "%Y-%m-%d %H:%M")
            print(f"   Scheduled: {scheduled_time}")
            print(f"   Time interpretation: {scheduled_dt.strftime('%I:%M %p on %A, %B %d, %Y')}")
            
            if scheduled_dt < dt.now():
                print(f"     WARNING: Scheduled time is in the past!")
        else:
            if scheduling_phrase_found:
                print("   Sending: Immediately (scheduling phrase found but no specific time)")
            else:
                print("   Sending: Immediately (no scheduling phrase found)")
        
        print(f"   Body preview: {body[:100]}...")
        
        confirm = input(f"\nSend this email? (y/n): ").lower()
        if confirm in ['y', 'yes']:
            if scheduled_time:
                success, status = self.email_scheduler.schedule_email(to_email, subject, body, scheduled_time)
                if cc_emails:
                    for cc_email in cc_emails:
                        self.email_scheduler.schedule_email(cc_email, f"FW: {subject}", body, scheduled_time)
                return f"Email {status} (CC: {', '.join(cc_emails) if cc_emails else 'none'})" if success else f"Failed: {status}"
            else:
                success = send_email([to_email], cc_emails, [], subject, body)
                return f"Email sent successfully! (CC: {', '.join(cc_emails) if cc_emails else 'none'})" if success else "Failed to send email"
        return "Email cancelled"

    def _view_tasks(self, text):
        """View tasks"""
        try:
            if 'today' in text:
                tasks = get_tasks_due_today()
                title = "Today's Tasks"
            elif 'tomorrow' in text:
                tasks = get_tasks_due_tomorrow()
                title = "Tomorrow's Tasks"
            elif 'completed' in text:
                tasks = get_completed_tasks()
                title = "Completed Tasks"
            elif 'all' in text:
                tasks = get_all_tasks()
                title = "All Tasks"   
            else:
                tasks = get_pending_tasks()
                title = "Pending Tasks"
            
            if not tasks:
                return f"No {title.lower()}"
            
            response = [title]
            for task in tasks[:10]:
                status = "[X]" if task.get('status') == 'completed' else "[ ]"
                response.append(f"{status} {task.get('title', 'Unknown')}")
            
            return "\n".join(response)
        except Exception as e:
            return f"Error: {str(e)}"

    def _complete_item(self, text, user_input):
        """Complete task"""
        query = re.sub(r'\b(complete|finish|done|task)\b', '', text).strip()
        if not query:
            return "Please specify task to complete"
        
        tasks = self._get_cached('tasks', get_all_tasks)
        best_match, score = self._find_match(query, tasks)
        
        if best_match:
            result = complete_task(best_match)
            self.caches['tasks'] = None
            return f"Completed: {best_match}"
        return f"Task '{query}' not found"

    def _delete_item(self, text, user_input):
        """Delete task or event"""
        if any(kw in text for kw in ['event', 'meeting', 'appointment']):
            return self._delete_event(text)
        else:
            return self._delete_task(text)

    def _delete_task(self, text):
        """Delete task"""
        query = re.sub(r'\b(delete|remove|cancel|task)\b', '', text).strip()
        if not query:
            return "Please specify task to delete"
        
        tasks = self._get_cached('tasks', get_all_tasks)
        best_match, score = self._find_match(query, tasks)
        
        if best_match:
            result = delete_task(best_match)
            self.caches['tasks'] = None
            return f"Deleted: {best_match}"
        return f"Task '{query}' not found"

    def _create_item(self, text, user_input):
        """Create task or event - FIXED ambiguity handling"""
        text_lower = text.lower()
        user_input_lower = user_input.lower()
        
        if 'task' in text_lower:
            return self._create_task(user_input)
        
        elif any(kw in text_lower for kw in ['event', 'meeting', 'appointment']):
            return self._create_event(user_input)
        
        elif (any(time_indicator in user_input_lower for time_indicator in ['at', ':', 'am', 'pm', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']) or('on' in user_input_lower and any(day in user_input_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']))):
            return self._create_event(user_input)
        
        else:
            return self._create_task(user_input)

    def _create_task(self, user_input):
        """Create task - FIXED to properly extract task title"""
        task_title = user_input
        
        command_patterns = [
            r'^create\s+',
            r'^add\s+',
            r'^make\s+',
            r'^new\s+',
            r'\btask\s+',
            r'\btodo\s+',
            r'\breminder\s+',
        ]
        
        for pattern in command_patterns:
            task_title = re.sub(pattern, '', task_title, flags=re.IGNORECASE)
        
        task_title = re.sub(r'\s+', ' ', task_title).strip()
        
        if not task_title:
            task_title = re.sub(r'^(create|add|make|new)\s+', '', user_input, flags=re.IGNORECASE)
            task_title = re.sub(r'\s+', ' ', task_title).strip()
        
        result = create_task(task_title)
        self.caches['tasks'] = None
        
        if result.get('status') == 'success':
            return f"Task created: {result.get('title', 'task')}"
        else:
            return f"Failed to create task: {result.get('message', 'Unknown error')}"

    def _reschedule_event(self, text, user_input):
        """Reschedule existing event"""
        query = re.sub(r'\b(reschedule|move|change)\b', '', text, flags=re.IGNORECASE).strip()
        
        if not query:
            return "Please specify which event to reschedule and the new time"
        
        print(f"DEBUG _reschedule_event START:")
        print(f"  Query: '{query}'")
        print(f"  Full input: '{user_input}'")
        
        events = self._get_cached('events', lambda: get_upcoming_events(30))
        
        if not events:
            return "No events found to reschedule"
        
        matching_events = []
        for event in events:
            if isinstance(event, dict):
                event_title = (event.get('summary') or event.get('title') or '')
                if event_title and query.lower() in event_title.lower():
                    matching_events.append((event_title, event))
        
        print(f"  Matching events found: {len(matching_events)}")
        
        if not matching_events:
            return f"No events found matching '{query}'"
        
        if len(matching_events) == 1:
            event_title, event_data = matching_events[0]
            result = reschedule_event(event_title, user_input)
            self.caches['events'] = None
            if result.get('status') == 'success':
                return result.get('message', f"Event '{event_title}' rescheduled")
            else:
                return f"Failed to reschedule event: {result.get('message', 'Unknown error')}"
        
        response = [f"Found {len(matching_events)} events matching '{query}':"]
        for i, (event_title, event_data) in enumerate(matching_events, 1):
            start = event_data.get('start', {}).get('dateTime', event_data.get('start', {}).get('date', ''))
            if 'T' in start:
                event_time = dt.fromisoformat(start.replace('Z', '+00:00'))
                time_str = event_time.strftime('%I:%M %p on %b %d')
            else:
                time_str = "All day event"
            
            response.append(f"{i}. {event_title} ({time_str})")
        
        response.append(f"\nWhich event do you want to reschedule? (1-{len(matching_events)} or 'cancel')")
        
        print("\nAssistant: " + "\n".join(response))
        
        try:
            selection = input("\nEnter number: ").strip().lower()
            
            if selection in ['cancel', 'c', 'no']:
                return "Reschedule cancelled"
            
            selection_num = int(selection)
            if 1 <= selection_num <= len(matching_events):
                event_title, event_data = matching_events[selection_num - 1]
                
                # Ask for new time
                new_time = input(f"Enter new time for '{event_title}' (e.g., 'tomorrow at 2pm'): ").strip()
                if not new_time:
                    return "Reschedule cancelled - no time specified"
                
                result = reschedule_event(event_title, new_time)
                self.caches['events'] = None
                if result.get('status') == 'success':
                    return result.get('message', f"Event '{event_title}' rescheduled")
                else:
                    return f"Failed to reschedule event: {result.get('message', 'Unknown error')}"
            else:
                return f"Invalid selection. Please choose between 1 and {len(matching_events)}"
        
        except (ValueError, KeyboardInterrupt):
            return "Reschedule cancelled"

    def _search_items(self, text, user_input):
        """Search tasks or events"""
        if any(kw in text for kw in ['event', 'meeting']):
            return self._search_events(text)
        else:
            return self._search_tasks(text)

    def _search_tasks(self, text):
        """Search tasks"""
        query = re.sub(r'\b(search|find|task)\b', '', text).strip()
        if not query:
            return "Please specify search query"
        
        tasks = search_tasks(query)
        if not tasks:
            return f"No tasks found for '{query}'"
        
        response = [f"Found {len(tasks)} tasks:"]
        for task in tasks[:5]:
            response.append(f"• {task.get('title', 'Unknown')}")
        return "\n".join(response)

    # In your chatbot.py - UPDATE THE _reschedule_event method

    def _reschedule_event(self, text, user_input):
        """Reschedule existing event - FIXED matching logic"""
        # Extract the event title from the command
        # Remove reschedule keywords and time/date parts
        query = text
        
        # Remove reschedule/change keywords
        query = re.sub(r'\b(reschedule|move|change|update)\b', '', query, flags=re.IGNORECASE)
        
        # Remove date/time patterns that might be in the query
        time_patterns = [
            r'to\s+\d{1,2}\s+[a-z]+\s+\d{1,2}[:]?\d{0,2}\s*[ap]?m?',
            r'to\s+\d{1,2}\s+[a-z]+',
            r'to\s+\d{1,2}[/-]\d{1,2}',
            r'at\s+\d{1,2}[:]?\d{0,2}\s*[ap]m',
            r'for\s+.+',
        ]
        
        for pattern in time_patterns:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        
        # Remove remaining time/date keywords
        date_keywords = ['to', 'at', 'on', 'tomorrow', 'today', 'next']
        for keyword in date_keywords:
            query = re.sub(rf'\b{keyword}\b', '', query, flags=re.IGNORECASE)
        
        query = query.strip()
        
        print(f"DEBUG _reschedule_event:")
        print(f"  Original input: '{user_input}'")
        print(f"  Cleaned query: '{query}'")
        
        if not query:
            return "Please specify which event to reschedule"
        
        # Get all events
        events = self._get_cached('events', lambda: get_upcoming_events(30))
        
        if not events:
            return "No events found to reschedule"
        
        # Find ALL matching events - IMPROVED matching
        matching_events = []
        for event in events:
            if isinstance(event, dict):
                event_title = (event.get('summary') or event.get('title') or '').lower()
                event_id = event.get('id', '')
                
                # Clean the event title for better matching
                clean_event_title = event_title
                clean_query = query.lower()
                
                # Try different matching strategies
                
                # 1. Exact word match (most reliable)
                query_words = set(clean_query.split())
                title_words = set(clean_event_title.split())
                common_words = query_words.intersection(title_words)
                
                # 2. Partial string match
                is_partial_match = False
                for word in clean_query.split():
                    if len(word) > 3 and word in clean_event_title:
                        is_partial_match = True
                        break
                
                # 3. Similarity match
                is_similar = clean_query in clean_event_title or clean_event_title in clean_query
                
                print(f"  Checking event: '{event_title[:50]}...'")
                print(f"    Query words: {query_words}")
                print(f"    Title words: {title_words}")
                print(f"    Common words: {common_words}")
                print(f"    Partial match: {is_partial_match}")
                print(f"    Similar match: {is_similar}")
                
                # If we have at least 2 common words OR partial match OR similarity
                if len(common_words) >= 2 or is_partial_match or is_similar:
                    matching_events.append((event_title, event, len(common_words)))
        
        # Sort by number of common words (best match first)
        matching_events.sort(key=lambda x: x[2], reverse=True)
        
        print(f"  Matching events found: {len(matching_events)}")
        
        if not matching_events:
            print(f"  No matches. Available events:")
            for event in events[:5]:
                if isinstance(event, dict):
                    print(f"    - {event.get('summary', 'No title')[:50]}...")
            return f"No events found matching '{query}'"
        
        # Extract the new time from the original input
        # Look for patterns like "to 8 dec 8am"
        new_time_match = re.search(r'to\s+(.+)', user_input, re.IGNORECASE)
        if not new_time_match:
            new_time_match = re.search(r'on\s+(.+)', user_input, re.IGNORECASE)
        
        if new_time_match:
            new_time_text = new_time_match.group(1)
            print(f"  New time text extracted: '{new_time_text}'")
        else:
            # If no "to" or "on", take everything after the event title
            # Find where the event title might end
            for event_title, _, _ in matching_events:
                title_lower = event_title.lower()
                if title_lower in user_input.lower():
                    idx = user_input.lower().find(title_lower)
                    if idx != -1:
                        new_time_text = user_input[idx + len(title_lower):].strip()
                        print(f"  New time from after title: '{new_time_text}'")
                        break
            else:
                new_time_text = ""
        
        if not new_time_text:
            return "Please specify the new time (e.g., 'to 8 dec 8am')"
        
        # If only one match, reschedule it directly
        if len(matching_events) == 1:
            event_title, event_data, score = matching_events[0]
            print(f"  Single match found: '{event_title}' with score {score}")
            
            # Get the original event title (not lowercase)
            original_title = event_data.get('summary') or event_data.get('title') or event_title
            
            print(f"  Original title: '{original_title}'")
            print(f"  New time: '{new_time_text}'")
            
            result = reschedule_event(original_title, new_time_text)
            self.caches['events'] = None
            if result.get('status') == 'success':
                return f" Event '{original_title}' rescheduled to {new_time_text}"
            else:
                return f" Failed to reschedule event: {result.get('message', 'Unknown error')}"
        
        # Multiple matches - show options
        response = [f"Found {len(matching_events)} events matching '{query}':"]
        for i, (event_title, event_data, score) in enumerate(matching_events[:5], 1):
            # Get time info
            start = event_data.get('start', {}).get('dateTime', event_data.get('start', {}).get('date', ''))
            original_title = event_data.get('summary') or event_data.get('title') or event_title
            
            if 'T' in start:
                try:
                    event_time = dt.fromisoformat(start.replace('Z', '+00:00'))
                    time_str = event_time.strftime('%I:%M %p on %b %d')
                except:
                    time_str = start
            else:
                time_str = "All day event"
            
            response.append(f"{i}. {original_title[:40]}... ({time_str}) [match: {score}]")
        
        response.append(f"\nWhich event do you want to reschedule? (1-{min(len(matching_events), 5)} or 'cancel')")
        
        print("\nAssistant: " + "\n".join(response))
        
        try:
            selection = input("\nEnter number: ").strip().lower()
            
            if selection in ['cancel', 'c', 'no']:
                return "Reschedule cancelled"
            
            selection_num = int(selection)
            if 1 <= selection_num <= min(len(matching_events), 5):
                event_title, event_data, score = matching_events[selection_num - 1]
                original_title = event_data.get('summary') or event_data.get('title') or event_title
                
                result = reschedule_event(original_title, new_time_text)
                self.caches['events'] = None
                if result.get('status') == 'success':
                    return f"Event '{original_title}' rescheduled to {new_time_text}"
                else:
                    return f" Failed to reschedule event: {result.get('message', 'Unknown error')}"
            else:
                return f"Invalid selection. Please choose between 1 and {min(len(matching_events), 5)}"
        
        except (ValueError, KeyboardInterrupt):
            return "Reschedule cancelled"   
            
    def _task_statistics(self):
        stats = get_task_statistics()
        if isinstance(stats, dict):
            return f"Tasks: {stats.get('total', 0)} total, {stats.get('completed', 0)} completed, {stats.get('pending', 0)} pending"
        return "Unable to get task statistics"

    def _show_help(self, text=None, user_input=None):
        help_text = """
Available Commands:

Calendar/Events:
• create event [title] on [day/time] - Create new event
• show calendar / show events - View upcoming events
• show events today/tomorrow - View specific day events
• delete event [name] - Delete an event
• reschedule event [name] to [new time] - Move event to new time

Tasks:
• create task [description] - Add new task
• show tasks / show tasks today - View tasks
• complete task [name] - Mark task as done
• delete task [name] - Remove task

Email:
• send email to [address] [subject] [body] - Send email

General:
• stats - Show statistics
• help - Show this help message

Examples:
• "create event team meeting on friday at 3pm"
• "create task finish report"
• "show events today"
• "complete task buy groceries"
"""
        return help_text

    def _show_stats(self, text=None, user_input=None):
        stats = []
        
        if TASKS_AVAILABLE:
            try:
                task_stats = get_task_statistics()
                if isinstance(task_stats, dict):
                    stats.append(f"Tasks: {task_stats.get('total', 0)} total, {task_stats.get('completed', 0)} completed, {task_stats.get('pending', 0)} pending")
            except Exception as e:
                stats.append(f"Tasks: Error - {str(e)}")
        else:
            stats.append("Tasks: Module not available")
        
        if CALENDAR_AVAILABLE:
            try:
                calendar_stats = get_calendar_statistics()
                if isinstance(calendar_stats, dict):
                    stats.append(f"Calendar: {calendar_stats.get('events_today', 0)} today, {calendar_stats.get('events_tomorrow', 0)} tomorrow, {calendar_stats.get('upcoming_week', 0)} this week")
            except Exception as e:
                stats.append(f"Calendar: Error - {str(e)}")
        else:
            stats.append("Calendar: Module not available")
        
        return "\n".join(stats) if stats else "No statistics available"

    def _reschedule_item(self, text, user_input):
        """Handle reschedule for ambiguous cases"""
        return "Please specify what you want to reschedule: 'reschedule event [name]' or 'reschedule task [name]'"

def main():
    chatbot = SmartChatbot()
    print("=" * 50)
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                break
            if not user_input:
                continue
            
            response = chatbot.process_message(user_input)
            print(f"\nAssistant: {response}")
            
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()