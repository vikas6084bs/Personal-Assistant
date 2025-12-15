import re
import time
from datetime import datetime as dt

from rapidfuzz import process, fuzz

from integrations import (
    SmartTimeParser, extract_event_title,
    TASKS_AVAILABLE, EMAIL_AVAILABLE, CALENDAR_AVAILABLE,
    create_task, get_pending_tasks, get_completed_tasks, get_all_tasks,
    get_tasks_due_today, get_tasks_due_tomorrow, get_upcoming_tasks,
    get_overdue_tasks, search_tasks, get_task_statistics,
    complete_task, delete_task, update_task,
    create_event, get_formatted_events_today,
    get_formatted_events_tomorrow, get_formatted_upcoming_events,
    search_events, delete_event, get_calendar_statistics,
    reschedule_event, parse_datetime_for_event,
    send_email, log_email, generate_email_content, extract_subject,
)
from email_scheduler import EmailScheduler


class SmartChatbot:
    def __init__(self):
        self.time_parser = SmartTimeParser()
        self.email_scheduler = EmailScheduler()
        self.email_scheduler.start_scheduler()
        self.caches = {'tasks': None, 'events': None}
        self.cache_times = {'tasks': 0, 'events': 0}

        print("\nPersonal Assistant - Module Status:")
        print(f"  Tasks: {'Available' if TASKS_AVAILABLE else 'NOT Available'}")
        print(f"  Email: {'Available' if EMAIL_AVAILABLE else 'NOT Available'}")
        print(f"  Calendar: {'Available' if CALENDAR_AVAILABLE else 'NOT Available'}")
        print("\nType 'help' for available commands\n")

    def __del__(self):
        self.email_scheduler.stop_scheduler()

    def _get_cached(self, cache_type, fetch_func):
        if (self.caches[cache_type] and
            time.time() - self.cache_times[cache_type] < 5):
            return self.caches[cache_type]
        self.caches[cache_type] = fetch_func()
        self.cache_times[cache_type] = time.time()
        return self.caches[cache_type]

    def split_multiple_commands(self, user_input):
        commands = []
        quoted_sections = []

        def protect_quotes(match):
            quoted_sections.append(match.group(0))
            return f"__QUOTE_{len(quoted_sections)-1}__"

        protected_text = re.sub(r'["\'][^"\']*["\']', protect_quotes, user_input)
        split_pattern = (
            r'\s+(?:and|also|then)\s+|\s*,\s*|\s*;\s*|\.\s+(?=[A-Z])'
        )
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

    def _find_match(self, query, items, threshold=70):
        if not items:
            return None, 0
        titles = []
        for item in items:
            if isinstance(item, dict):
                title = (
                    item.get('title') or item.get('summary') or
                    item.get('name') or ''
                )
                titles.append(title if title else 'No title')
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

        best_match, score, _ = process.extractOne(
            query, titles, scorer=fuzz.partial_ratio
        )
        return best_match if score >= threshold else None, score

    # ---- Tasks ----

    def _view_tasks(self, text):
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

    def _create_task(self, user_input):
        task_title = user_input
        command_patterns = [
            r'^create\s+', r'^add\s+', r'^make\s+',
            r'^new\s+', r'\btask\s+', r'\btodo\s+',
            r'\breminder\s+',
        ]
        for pattern in command_patterns:
            task_title = re.sub(pattern, '', task_title, flags=re.IGNORECASE)
        task_title = re.sub(r'\s+', ' ', task_title).strip()
        if not task_title:
            task_title = re.sub(
                r'^(create|add|make|new)\s+', '',
                user_input, flags=re.IGNORECASE
            )
            task_title = re.sub(r'\s+', ' ', task_title).strip()

        result = create_task(task_title)
        self.caches['tasks'] = None
        if result.get('status') == 'success':
            return f"Task created: {result.get('title', 'task')}"
        return f"Failed to create task: {result.get('message', 'Unknown error')}"

    def _complete_item(self, text, user_input):
        query = re.sub(r'\b(complete|finish|done|task)\b', '', text).strip()
        if not query:
            return "Please specify task to complete"
        tasks = self._get_cached('tasks', get_all_tasks)
        best_match, score = self._find_match(query, tasks)
        if best_match:
            complete_task(best_match)
            self.caches['tasks'] = None
            return f"Completed: {best_match}"
        return f"Task '{query}' not found"

    def _delete_task(self, text):
        query = re.sub(r'\b(delete|remove|cancel|task)\b', '', text).strip()
        if not query:
            return "Please specify task to delete"
        tasks = self._get_cached('tasks', get_all_tasks)
        best_match, score = self._find_match(query, tasks)
        if best_match:
            delete_task(best_match)
            self.caches['tasks'] = None
            return f"Deleted: {best_match}"
        return f"Task '{query}' not found"

    def _task_statistics(self):
        stats = get_task_statistics()
        if isinstance(stats, dict):
            return (
                f"Tasks: {stats.get('total', 0)} total, "
                f"{stats.get('completed', 0)} completed, "
                f"{stats.get('pending', 0)} pending"
            )
        return "Unable to get task statistics"

    # ---- Calendar ----

    def _view_calendar(self, text):
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
        stats = get_calendar_statistics()
        if isinstance(stats, dict):
            return (
                f"Calendar Stats: {stats.get('events_today', 0)} today, "
                f"{stats.get('events_tomorrow', 0)} tomorrow, "
                f"{stats.get('upcoming_week', 0)} this week"
            )
        return "Unable to get calendar statistics"

    def _delete_event(self, text):
        query = re.sub(
            r'\b(delete|remove|cancel|event|meeting|appointment)\b',
            '', text, flags=re.IGNORECASE
        ).strip()
        if not query:
            return "Please specify which event to delete"
        events = self._get_cached('events', lambda: get_upcoming_events(30))
        if not events:
            return "No events found to delete"
        best_match, score = self._find_match(query, events)
        if best_match:
            result = delete_event(best_match)
            self.caches['events'] = None
            if result.get('status') == 'success':
                return f"Event deleted: {best_match}"
            return (
                f"Failed to delete event: "
                f"{result.get('message', 'Unknown error')}"
            )
        return f"Event '{query}' not found"

    def _create_event(self, user_input):
        try:
            clean_title = extract_event_title(user_input)
            event_time = self.time_parser.extract_datetime(user_input)
            start_time = event_time.strftime("%Y-%m-%d %H:%M")
            # NOTE: you may still want to adapt this to your calendar API
            result = create_event(title=clean_title, start_time=start_time)
            if result.get('status') == 'success':
                self.caches['events'] = None
                response = f"Event created: {clean_title}"
                if result.get('start_time'):
                    try:
                        event_time = dt.strptime(
                            result['start_time'], "%Y-%m-%d %H:%M"
                        )
                        display_time = result.get(
                            'display_time',
                            event_time.strftime('%I:%M %p')
                        )
                        response += (
                            f" on {event_time.strftime('%A, %b %d')} "
                            f"at {display_time}"
                        )
                    except ValueError:
                        response += f" at {result['start_time']}"
                return response
            error_msg = result.get('message', 'Unknown error')
            return f"Failed to create event: {error_msg}"
        except Exception as e:
            return f"Error creating event: {str(e)}"

    # ---- Email ----

    def _extract_email_subject(self, text):
        text = re.sub(
            r'[\w\.-]+@[\w\.-]+\.\w+', '', text, flags=re.IGNORECASE
        )

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
            r'^send\s+', r'^email\s+', r'^mail\s+',
            r'\bto\s+', r'\bfor\s+', r'\bcc\b', r'\bbcc\b',
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
            stop_words = {
                'a', 'an', 'the', 'and', 'or', 'but',
                'on', 'at', 'in', 'to', 'of', 'bring',
                'his', 'her', 'their'
            }
            for word in words:
                if word.lower() not in stop_words and len(word) > 2:
                    meaningful_words.append(word)
                if len(meaningful_words) >= 6:
                    break
            subject = (
                ' '.join(meaningful_words) if meaningful_words
                else "Important Message"
            )

        subject = re.sub(r'\s+', ' ', subject).strip()
        if subject:
            subject = subject[0].upper() + subject[1:]
        return subject if subject else "Email"

    def _process_email(self, user_input):
        """Process email: schedule when time is mentioned, otherwise send now."""
        if not EMAIL_AVAILABLE:
            return "Email functionality not available"

        # 1) Extract email addresses
        email_addresses = re.findall(
            r'[\w\.-]+@[\w\.-]+\.\w+', user_input
        )
        if not email_addresses:
            return "Please specify a valid email address"

        to_email = email_addresses[0]

        # CC handling
        cc_emails = []
        if 'cc' in user_input.lower() or 'in cc' in user_input.lower():
            cc_text = user_input.lower()
            cc_index = cc_text.find('cc')
            if cc_index != -1:
                cc_part = user_input[cc_index + 2:]
                cc_emails = re.findall(
                    r'[\w\.-]+@[\w\.-]+\.\w+', cc_part
                )
        for email in email_addresses[1:]:
            if email not in cc_emails:
                cc_emails.append(email)

        email_text_lower = user_input.lower()
        print(f"DEBUG: Checking for scheduling in: '{email_text_lower}'")

        # 2) Detect explicit "at HH:MM[/am/pm]" first (force scheduling)
        force_time_match = re.search(
            r'\bat\s+(\d{1,2}):(\d{2})(\s*(am|pm))?\b',
            email_text_lower
        )

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
                break

        if not date_time_text:
            all_matches = []
            for pattern in date_time_patterns:
                matches = list(
                    re.finditer(pattern, email_text_lower, re.IGNORECASE)
                )
                all_matches.extend(matches)
            if all_matches:
                all_matches.sort(key=lambda m: m.end())
                last_match = all_matches[-1]
                date_time_text = last_match.group(1)

        if not date_time_text:
            for pattern in scheduling_keywords:
                matches = list(
                    re.finditer(pattern, email_text_lower, re.IGNORECASE)
                )
                if matches:
                    last_match = matches[-1]
                    date_time_text = last_match.group(1)
                    break

        scheduled_time = None

        # 3) If explicit "at HH:MM" -> use that directly for scheduling
        if force_time_match:
            from datetime import datetime as _dt, timedelta as _td
            hour = int(force_time_match.group(1))
            minute = int(force_time_match.group(2))
            period = (force_time_match.group(4) or '').lower()

            if period == 'pm' and hour < 12:
                hour += 12
            if period == 'am' and hour == 12:
                hour = 0

            now = _dt.now()
            scheduled_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled_dt <= now:
                scheduled_dt = scheduled_dt + _td(days=1)

            scheduled_time = scheduled_dt.strftime("%Y-%m-%d %H:%M")

        # 4) Otherwise, fall back to SmartTimeParser for natural language
        elif date_time_text:
            try:
                clean_date_text = date_time_text
                if clean_date_text.lower().startswith('on '):
                    clean_date_text = clean_date_text[3:]
                elif clean_date_text.lower().startswith('at '):
                    clean_date_text = clean_date_text[3:]
                clean_date_text = clean_date_text.strip()

                if re.match(
                    r'^\d{1,2}[:]?\d{0,2}\s*(?:am|pm)?$', clean_date_text,
                    re.IGNORECASE
                ):
                    date_patterns_for_full = [
                        r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)',
                        r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})',
                        r'(\d{1,2}[/-]\d{1,2}[/-]?\d{2,4}?)',
                    ]
                    full_date_text = None
                    for pattern in date_patterns_for_full:
                        match = re.search(pattern, email_text_lower, re.IGNORECASE)
                        if match:
                            full_date_text = match.group(1)
                            break
                    if full_date_text:
                        clean_date_text = f"{full_date_text} {clean_date_text}"

                event_time = self.time_parser.extract_datetime_for_email(clean_date_text)
                if event_time:
                    scheduled_time = event_time.strftime("%Y-%m-%d %H:%M")
            except Exception:
                scheduled_time = None

        subject = self._extract_email_subject(user_input)
        try:
            body = generate_email_content(user_input)
        except Exception:
            body = (
                "This is an automated reminder email.\n\n"
                f"Original command:\n{user_input}"
            )

        confirm = input("\nSend this email? (y/n): ").lower()
        if confirm in ['y', 'yes']:
            # If time was detected -> ALWAYS schedule, using EmailScheduler
            if scheduled_time:
                success, status = self.email_scheduler.schedule_email(
                    to_email, subject, body, scheduled_time, user_input=user_input
                )
                if success:
                    return f"Email {status} (CC: {', '.join(cc_emails) if cc_emails else 'none'})"
                return f"Failed: {status}"
            # No time -> send immediately
            else:
                success = send_email([to_email], cc_emails, [], subject, body)
                if success:
                    return (
                        "Email sent successfully! "
                        f"(CC: {', '.join(cc_emails) if cc_emails else 'none'})"
                    )
                return "Failed to send email"

        return "Email cancelled"

# ---- High-level router ----

    def _create_item(self, text, user_input):
        text_lower = text.lower()
        user_input_lower = user_input.lower()
        if 'task' in text_lower:
            return self._create_task(user_input)
        if any(kw in text_lower for kw in ['event', 'meeting', 'appointment']):
            return self._create_event(user_input)
        if (any(t in user_input_lower for t in [
            'at', ':', 'am', 'pm', 'jan', 'feb', 'mar', 'apr', 'may',
            'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
        ]) or (
            'on' in user_input_lower and any(
                day in user_input_lower for day in [
                    'monday', 'tuesday', 'wednesday', 'thursday',
                    'friday', 'saturday', 'sunday'
                ]
            )
        )):
            return self._create_event(user_input)
        return self._create_task(user_input)

    def _delete_item(self, text, user_input):
        if any(kw in text for kw in ['event', 'meeting', 'appointment']):
            return self._delete_event(text)
        return self._delete_task(text)

    def _search_items(self, text, user_input):
        if any(kw in text for kw in ['event', 'meeting']):
            return self._search_events(text)
        return self._search_tasks(text)

    def _search_tasks(self, text):
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

    def _process_calendar(self, text, user_input):
        try:
            if any(kw in text for kw in ['show', 'list', 'view']):
                return self._view_calendar(text)
            if any(kw in text for kw in ['create', 'add', 'make', 'schedule']):
                return self._create_event(user_input)
            if any(kw in text for kw in ['delete', 'remove', 'cancel']):
                return self._delete_event(text)
            if any(kw in text for kw in ['reschedule', 'move', 'change']):
                return self._reschedule_event(text, user_input)
            if any(kw in text for kw in ['search', 'find']):
                return self._search_events(text)
            if any(kw in text for kw in ['stats', 'statistics']):
                return self._calendar_statistics()
            return "Try: 'show calendar', 'create event', or 'delete event'"
        except Exception as e:
            return f"Calendar error: {str(e)}"

    def _reschedule_task(self, text, user_input):
        query = re.sub(
            r'\b(reschedule|move|change|task|todo)\b',
            '', text, flags=re.IGNORECASE
        ).strip()
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
                    return (
                        f"Task '{best_match}' due date updated to "
                        f"{new_date.strftime('%b %d, %Y')}"
                    )
                return "Failed to update task"
            except ValueError as e:
                return f"Task not found: {str(e)}"
            except Exception as e:
                return f"Error updating task: {str(e)}"
        return f"Task '{query}' not found"

    def _reschedule_item(self, text, user_input):
        return (
            "Please specify what you want to reschedule: "
            "'reschedule event [name]' or 'reschedule task [name]'"
        )

    def _show_help(self, text=None, user_input=None):
        return (
            "Available Commands:\n\n"
            "Calendar/Events:\n"
            "• create event [title] on [day/time] - Create new event\n"
            "• show calendar / show events - View upcoming events\n"
            "• show events today/tomorrow - View specific day events\n"
            "• delete event [name] - Delete an event\n"
            "• reschedule event [name] to [new time] - Move event to new time\n\n"
            "Tasks:\n"
            "• create task [description] - Add new task\n"
            "• show tasks / show tasks today - View tasks\n"
            "• complete task [name] - Mark task as done\n"
            "• delete task [name] - Remove task\n\n"
            "Email:\n"
            "• send email to [address] [subject/body description]\n\n"
            "General:\n"
            "• stats - Show statistics\n"
            "• help - Show this help message\n"
        )

    def _show_stats(self, text=None, user_input=None):
        stats = []
        if TASKS_AVAILABLE:
            try:
                task_stats = get_task_statistics()
                if isinstance(task_stats, dict):
                    stats.append(
                        f"Tasks: {task_stats.get('total', 0)} total, "
                        f"{task_stats.get('completed', 0)} completed, "
                        f"{task_stats.get('pending', 0)} pending"
                    )
            except Exception as e:
                stats.append(f"Tasks: Error - {str(e)}")
        else:
            stats.append("Tasks: Module not available")

        if CALENDAR_AVAILABLE:
            try:
                calendar_stats = get_calendar_statistics()
                if isinstance(calendar_stats, dict):
                    stats.append(
                        f"Calendar: {calendar_stats.get('events_today', 0)} today, "
                        f"{calendar_stats.get('events_tomorrow', 0)} tomorrow, "
                        f"{calendar_stats.get('upcoming_week', 0)} this week"
                    )
            except Exception as e:
                stats.append(f"Calendar: Error - {str(e)}")
        else:
            stats.append("Calendar: Module not available")

        return "\n".join(stats) if stats else "No statistics available"

    def process_message(self, user_input):
        text = user_input.lower().strip()
        if 'reschedule task' in text or 'update task' in text:
            return self._reschedule_task(text, user_input)
        if 'reschedule event' in text or 'update event' in text:
            return self._reschedule_event(text, user_input)
        if any(kw in text for kw in ['reschedule', 'move', 'change', 'update']):
            if 'task' in text:
                return self._reschedule_task(text, user_input)
            if any(kw in text for kw in ['event', 'meeting', 'appointment']):
                return self._reschedule_event(text, user_input)
            return self._reschedule_item(text, user_input)

        if re.search(r'@[\w\.-]+\.\w+', text) and any(
            kw in text for kw in ['send', 'email']
        ):
            return self._process_email(user_input)

        if any(keyword in text for keyword in ['task', 'todo', 'reminder']):
            if any(kw in text for kw in ['create', 'add', 'make', 'new']):
                return self._create_task(user_input)
            if any(kw in text for kw in ['show', 'list', 'view']):
                return self._view_tasks(text)
            if any(kw in text for kw in ['complete', 'finish', 'done']):
                return self._complete_item(text, user_input)
            if any(kw in text for kw in ['delete', 'remove']):
                return self._delete_task(text)

        if any(keyword in text for keyword in ['event', 'meeting', 'appointment', 'calendar']):
            if any(kw in text for kw in ['create', 'add', 'make', 'new', 'schedule']):
                return self._create_event(user_input)
            if any(kw in text for kw in ['show', 'list', 'view']):
                return self._view_calendar(text)
            if any(kw in text for kw in ['delete', 'remove', 'cancel']):
                return self._delete_event(text)
            if any(kw in text for kw in ['reschedule', 'move', 'change']):
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
            'help': self._show_help,
        }
        for keyword, handler in command_handlers.items():
            if keyword in text:
                return handler(text, user_input)

        if 'create' in text:
            return (
                "Please specify what you want to create: "
                "'create task' or 'create event'"
            )
        return "I'm not sure what you want to do. Type 'help' for available commands."

    def _view_items(self, text, user_input):
        if any(kw in text for kw in ['event', 'meeting', 'appointment', 'calendar']):
            return self._view_calendar(text)
        return self._view_tasks(text)
