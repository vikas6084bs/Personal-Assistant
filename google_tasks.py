import os
import pickle
import re
from datetime import datetime, timedelta, timezone
import dateparser

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/tasks"]
CRED_FOLDER = "google_credentials"
CLIENT_SECRET_FILE = os.path.join(CRED_FOLDER, "credentials.json")
TOKEN_FILE = os.path.join(CRED_FOLDER, "token.pickle")

os.makedirs(CRED_FOLDER, exist_ok=True)

def get_tasks_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None

    if not creds or not getattr(creds, "valid", False):
        if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(f"Missing OAuth client secret: {CLIENT_SECRET_FILE}")

            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("tasks", "v1", credentials=creds)


def to_rfc3339(dt: datetime) -> str:
    """Return RFC3339 timestamp (UTC) with Z."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6
}

def next_weekday_option_b(target_wd: int) -> datetime:
    today = datetime.now().date()
    today_wd = today.weekday()
    days_ahead = (target_wd - today_wd) % 7
    if days_ahead == 0:
        days_ahead = 7
    target_date = today + timedelta(days=days_ahead)
    return datetime.combine(target_date, datetime.min.time())

def parse_datetime_from_text(text: str):
    """
    Parse many natural expressions into (YYYY-MM-DD, HH:MM).
    Returns (date_str, time_str) or (fallback_date, fallback_time).
    """
    if not isinstance(text, str):
        return None, None

    t = text.lower().strip()
    now = datetime.now()
    default_hour, default_minute = 9, 0

    if "today" in t:
        dt = now.replace(hour=default_hour, minute=default_minute, second=0, microsecond=0)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    if "tomorrow" in t and "day after" not in t:
        dt = now + timedelta(days=1)
        dt = dt.replace(hour=default_hour, minute=default_minute, second=0, microsecond=0)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    if "day after tomorrow" in t:
        dt = now + timedelta(days=2)
        dt = dt.replace(hour=default_hour, minute=default_minute, second=0, microsecond=0)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    if "yesterday" in t:
        dt = now - timedelta(days=1)
        dt = dt.replace(hour=default_hour, minute=default_minute, second=0, microsecond=0)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

    vague = {
        "morning": "09:00",
        "afternoon": "15:00",
        "evening": "18:00",
        "tonight": "20:00",
        "night": "20:00",
        "noon": "12:00"
    }
    t_for_parse = t
    for w, rep in vague.items():
        t_for_parse = re.sub(rf"\b{w}\b", rep, t_for_parse)

    date_match = re.search(
        r"\bon\s+(\d{1,2}\s*[A-Za-z]+|\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?|[A-Za-z]+\s*\d{1,2})",
        t,
        flags=re.IGNORECASE,
    )
    if date_match:
        raw = date_match.group(1)
        parsed = dateparser.parse(raw, settings={"PREFER_DATES_FROM": "future"})
        if parsed:
            tm = re.search(r"\b(at\s*)?(\d{1,2}(:\d{2})?\s*(am|pm)?)\b", t)
            if tm:
                p2 = dateparser.parse(tm.group(2))
                if p2:
                    parsed = parsed.replace(hour=p2.hour, minute=p2.minute)
            else:
                parsed = parsed.replace(hour=default_hour, minute=default_minute)
            return parsed.strftime("%Y-%m-%d"), parsed.strftime("%H:%M")

    wd_match = re.search(
        r"\b(this|next|coming)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b",
        t,
        flags=re.IGNORECASE,
    )
    if wd_match:
        wd = wd_match.group(2).lower()
        if wd in WEEKDAYS:
            final_dt = next_weekday_option_b(WEEKDAYS[wd])
            tm = re.search(r"\b(at\s*)?(\d{1,2}(:\d{2})?\s*(am|pm)?)\b", t)
            if tm:
                p2 = dateparser.parse(tm.group(2))
                if p2:
                    final_dt = final_dt.replace(hour=p2.hour, minute=p2.minute)
            else:
                final_dt = final_dt.replace(hour=default_hour, minute=default_minute)
            return final_dt.strftime("%Y-%m-%d"), final_dt.strftime("%H:%M")

    hh = re.search(r"\bin\s+(\d+)\s+hours?\b", t)
    if hh:
        dt = now + timedelta(hours=int(hh.group(1)))
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    mm = re.search(r"\bin\s+(\d+)\s+minutes?\b", t)
    if mm:
        dt = now + timedelta(minutes=int(mm.group(1)))
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

    dt = dateparser.parse(
        t_for_parse, settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": now}
    )
    if dt:
        if dt.hour == 0 and dt.minute == 0:
            dt = dt.replace(hour=default_hour, minute=default_minute)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

    fallback = now.replace(hour=default_hour, minute=default_minute)
    return fallback.strftime("%Y-%m-%d"), fallback.strftime("%H:%M")


def extract_list_name_from_text(text: str) -> str:
    m = re.search(r"\b(under|in|into|to)\s+([A-Za-z0-9\s&_-]+)", text, flags=re.IGNORECASE)
    if not m:
        return "My Tasks"
    raw = m.group(2).strip()
    # remove stray date words etc.
    raw = re.sub(r"\bon\s+[A-Za-z0-9\s\/-]+\b", "", raw)
    raw = re.sub(r"\b(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", "", raw)
    raw = re.sub(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b", "", raw)
    raw = re.sub(r"\d{1,2}([/-]\d{1,2}([/-]\d{2,4})?)?", "", raw)
    raw = re.sub(r"[^\w\s&_-]", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw.title() if raw else "My Tasks"


def extract_task_title_from_natural_language(text: str) -> str:
    t = text
    # remove common verbs / date phrases
    t = re.sub(r"\b(create|cretae|add|make|set|please|task|todo|to-do|task:|remind|remind me|remind me to|schedule)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(in|under|into)\s+[A-Za-z0-9\s\/-]+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bon\s+[A-Za-z0-9\s\/-]+\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\d{1,2}([/-]\d{1,2}([/-]\d{2,4})?)?", "", t)
    t = re.sub(r"(at\s*)?\d{1,2}(:\d{2})?\s*(am|pm)?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"[^\w\s&_-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return "Untitled Task"
    # Capitalize each word
    return " ".join(word.capitalize() for word in t.split())


def create_task(user_input: str):
    """
    user_input: natural sentence. returns dict with status,title,date,time,list
    """
    date_str, time_str = parse_datetime_from_text(user_input)
    title = extract_task_title_from_natural_language(user_input)
    list_name = extract_list_name_from_text(user_input)

    service = get_tasks_service()

    lists = service.tasklists().list().execute().get("items", [])
    list_id = None
    for lst in lists:
        if lst["title"].strip().lower() == list_name.strip().lower():
            list_id = lst["id"]
            break

    if not list_id:
        created = service.tasklists().insert(body={"title": list_name}).execute()
        list_id = created["id"]

    task_body = {"title": title}
    if date_str:
        try:
            hour_min = time_str if time_str else "09:00"
            dt = datetime.strptime(f"{date_str} {hour_min}", "%Y-%m-%d %H:%M")
            task_body["due"] = to_rfc3339(dt)
        except Exception:
            task_body["due"] = f"{date_str}T{time_str}:00.000Z" if time_str else f"{date_str}T09:00:00.000Z"

    created_task = service.tasks().insert(tasklist=list_id, body=task_body).execute()
    return {"status": "success", "title": title, "date": date_str, "time": time_str, "list": list_name, "id": created_task.get("id")}

def get_task_lists():
    service = get_tasks_service()
    return service.tasklists().list().execute().get("items", [])



def get_all_tasks():
    service = get_tasks_service()
    all_tasks = []
    try:
        tasklists = service.tasklists().list().execute().get("items", [])
    except Exception:
        return []

    for tlist in tasklists:
        tasks = service.tasks().list(tasklist=tlist["id"], showCompleted=True).execute().get("items", [])
        for task in tasks:
            all_tasks.append({
                "id": task.get("id"),
                "title": task.get("title"),
                "due": task.get("due"),
                "status": task.get("status"),
                "list": tlist.get("title")
            })
    return all_tasks


# -----------------------------
# GET PENDING TASKS (exported)
# -----------------------------
def get_pending_tasks():
    return [t for t in get_all_tasks() if t.get("status") != "completed"]


# -----------------------------
# GET COMPLETED TASKS (exported)
# -----------------------------
def get_completed_tasks():
    return [t for t in get_all_tasks() if t.get("status") == "completed"]

def _parse_due_date_string(due_str):
    """Return date string YYYY-MM-DD for comparing. If None -> None"""
    if not due_str:
        return None
    # due_str is RFC3339 usually, take first 10 chars
    return due_str[:10]

def get_tasks_due_today():
    today = datetime.now().strftime("%Y-%m-%d")
    return [t for t in get_pending_tasks() if _parse_due_date_string(t.get("due")) == today]

def get_tasks_due_tomorrow():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return [t for t in get_pending_tasks() if _parse_due_date_string(t.get("due")) == tomorrow]

def get_upcoming_tasks(days: int = 7):
    start = datetime.now().date()
    end = start + timedelta(days=days)
    out = []
    for t in get_pending_tasks():
        d = _parse_due_date_string(t.get("due"))
        if not d:
            continue
        try:
            ddate = datetime.strptime(d, "%Y-%m-%d").date()
            if start <= ddate <= end:
                out.append(t)
        except Exception:
            continue
    return out

def get_overdue_tasks():
    today = datetime.now().date()
    out = []
    for t in get_pending_tasks():
        d = _parse_due_date_string(t.get("due"))
        if not d:
            continue
        try:
            ddate = datetime.strptime(d, "%Y-%m-%d").date()
            if ddate < today:
                out.append(t)
        except Exception:
            continue
    return out


# -----------------------------
# SEARCH TASKS (exported)
# -----------------------------
def search_tasks(query: str):
    q = (query or "").strip().lower()
    if not q:
        return []
    return [t for t in get_all_tasks() if q in (t.get("title") or "").lower() or q in (t.get("list") or "").lower()]


# -----------------------------
# TASK STATISTICS (exported)
# -----------------------------
def get_task_statistics():
    all_tasks = get_all_tasks()
    total = len(all_tasks)
    completed = len([t for t in all_tasks if t.get("status") == "completed"])
    pending = total - completed
    overdue = len(get_overdue_tasks())
    due_today = len(get_tasks_due_today())
    due_tomorrow = len(get_tasks_due_tomorrow())
    upcoming_7 = len(get_upcoming_tasks(7))
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "due_today": due_today,
        "due_tomorrow": due_tomorrow,
        "upcoming_7_days": upcoming_7
    }


# -----------------------------
# Helpers: find task by exact title (case-insensitive) across lists
# -----------------------------
def _find_task_by_title_exact(title: str):
    if not title:
        return None, None  # (task_dict, tasklist_id)
    title_norm = title.strip().lower()
    service = get_tasks_service()
    for lst in get_task_lists():
        tasks = service.tasks().list(tasklist=lst["id"], showCompleted=True).execute().get("items", [])
        for t in tasks:
            if (t.get("title") or "").strip().lower() == title_norm:
                return t, lst["id"]
    return None, None


# -----------------------------
# COMPLETE TASK (exported)
# -----------------------------
def complete_task(task_title: str):
    """
    Mark task with exact title as completed (first match).
    Returns updated task dict or raises.
    """
    task, list_id = _find_task_by_title_exact(task_title)
    if not task:
        raise ValueError("Task not found")
    # Mark completed
    task["status"] = "completed"
    task["completed"] = to_rfc3339(datetime.now())
    service = get_tasks_service()
    updated = service.tasks().update(tasklist=list_id, task=task["id"], body=task).execute()
    return updated


# -----------------------------
# DELETE TASK (exported)
# -----------------------------
def delete_task(task_title: str):
    task, list_id = _find_task_by_title_exact(task_title)
    if not task:
        raise ValueError("Task not found")
    service = get_tasks_service()
    service.tasks().delete(tasklist=list_id, task=task["id"]).execute()
    return {"status": "deleted", "title": task_title}


def update_task(task_title: str, new_title: str = None, new_due_raw: str = None):
    """
    Update a task's title and/or due date.
    new_due_raw may be a natural-language string or a tuple (date_str,time_str).
    """
    task, list_id = _find_task_by_title_exact(task_title)
    if not task:
        raise ValueError("Task not found")

    # Update title
    if new_title:
        task["title"] = new_title

    # Update due
    if new_due_raw:
        if isinstance(new_due_raw, tuple):
            date_str, time_str = new_due_raw
        else:
            date_str, time_str = parse_datetime_from_text(new_due_raw)
        if date_str:
            try:
                hour_min = time_str or "09:00"
                dt = datetime.strptime(f"{date_str} {hour_min}", "%Y-%m-%d %H:%M")
                task["due"] = to_rfc3339(dt)
            except Exception:
                task["due"] = f"{date_str}T{time_str}:00.000Z" if time_str else f"{date_str}T09:00:00.000Z"

    service = get_tasks_service()
    updated = service.tasks().update(tasklist=list_id, task=task["id"], body=task).execute()
    return updated


def reschedule_task(task_title: str, new_due_raw: str):
    """
    Reschedule a task by title to new due date string.
    """
    return update_task(task_title, new_due_raw=new_due_raw)


def create_task_list(name: str):
    service = get_tasks_service()
    created = service.tasklists().insert(body={"title": name}).execute()
    return {"status": "created", "id": created.get("id"), "title": created.get("title")}

def delete_task_list(name: str):
    # find list by exact name
    for lst in get_task_lists():
        if lst["title"].strip().lower() == name.strip().lower():
            service = get_tasks_service()
            service.tasklists().delete(tasklist=lst["id"]).execute()
            return {"status": "deleted", "title": name}
    raise ValueError("Task list not found")

def get_task_lists():
    service = get_tasks_service()
    return service.tasklists().list().execute().get("items", [])

# In google_tasks.py - ADD THESE FUNCTIONS

def parse_recurrence_pattern(user_input):
    """
    Parse recurrence patterns from user input
    Returns: (pattern_type, pattern_details)
    """
    import re
    
    input_lower = user_input.lower()
    
    # Daily pattern
    if 'daily' in input_lower or 'every day' in input_lower:
        return 'daily', {'interval': 1}
    
    # Weekly pattern - single day
    weekly_match = re.search(r'weekly\s+(\w+)', input_lower)
    if weekly_match:
        day = weekly_match.group(1)
        days_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6
        }
        if day in days_map:
            return 'weekly', {'weekday': days_map[day]}
    
    # Monthly pattern
    monthly_match = re.search(r'monthly\s+(\d+)(?:st|nd|rd|th)?', input_lower)
    if monthly_match:
        day_of_month = int(monthly_match.group(1))
        if 1 <= day_of_month <= 31:
            return 'monthly', {'day': day_of_month}
    
    # Multiple weekdays
    if 'every' in input_lower and ('and' in input_lower or ',' in input_lower):
        days = re.findall(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', input_lower)
        if days:
            days_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            weekdays = [days_map[d] for d in days if d in days_map]
            if weekdays:
                return 'weekly_multiple', {'weekdays': weekdays}
    
    return None, None

def generate_recurring_dates(start_date, recurrence_type, recurrence_details, count=5):
    """
    Generate recurring dates based on pattern
    """
    from datetime import datetime, timedelta
    import calendar
    
    dates = [start_date]
    
    if recurrence_type == 'daily':
        for i in range(1, count):
            dates.append(start_date + timedelta(days=i))
    
    elif recurrence_type == 'weekly':
        weekday = recurrence_details['weekday']
        current = start_date
        for i in range(1, count):
            current = current + timedelta(days=1)
            while current.weekday() != weekday:
                current = current + timedelta(days=1)
            dates.append(current)
    
    elif recurrence_type == 'weekly_multiple':
        weekdays = recurrence_details['weekdays']
        current = start_date
        days_generated = 0
        
        while days_generated < count - 1:
            current = current + timedelta(days=1)
            if current.weekday() in weekdays:
                dates.append(current)
                days_generated += 1
    
    elif recurrence_type == 'monthly':
        day_of_month = recurrence_details['day']
        current = start_date
        for i in range(1, count):
            # Move to next month
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1)
            else:
                next_month = current.replace(month=current.month + 1)
            
            # Adjust if day doesn't exist in month
            try:
                current = next_month.replace(day=day_of_month)
            except ValueError:
                # If day doesn't exist (e.g., Feb 30), use last day of month
                last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                current = next_month.replace(day=min(day_of_month, last_day))
            
            dates.append(current)
    
    return dates
# -----------------------------
# MOVE TASK BETWEEN LISTS (exported)
# -----------------------------
def move_task_between_lists(task_title: str, dest_list_name: str):
    """
    Copy task to dest list and delete original (API has no atomic move).
    Identifies task by exact title.
    """
    task, src_list_id = _find_task_by_title_exact(task_title)
    if not task:
        raise ValueError("Task not found")

    service = get_tasks_service()

    # find or create dest list
    dest_id = None
    for lst in get_task_lists():
        if lst["title"].strip().lower() == dest_list_name.strip().lower():
            dest_id = lst["id"]
            break
    if not dest_id:
        created = service.tasklists().insert(body={"title": dest_list_name}).execute()
        dest_id = created.get("id")

    # build copy body
    copy_body = {
        "title": task.get("title"),
        "notes": task.get("notes"),
    }
    if task.get("due"):
        copy_body["due"] = task.get("due")
    if task.get("status") == "completed":
        copy_body["status"] = "completed"
        copy_body["completed"] = task.get("completed")

    new_task = service.tasks().insert(tasklist=dest_id, body=copy_body).execute()
    # delete original
    service.tasks().delete(tasklist=src_list_id, task=task["id"]).execute()
    return {"status": "moved", "old_list": src_list_id, "new_list": dest_id, "title": task.get("title"), "new_id": new_task.get("id")}


# -----------------------------
# Export compatibility names (some callers expect these names)
# -----------------------------
# parse_datetime_from_text already exported above
# extract_task_title_from_natural_language already exported above
# extract_list_name_from_text already exported above

# The module exports are the functions defined above.
__all__ = [
    "get_tasks_service",
    "parse_datetime_from_text",
    "extract_task_title_from_natural_language",
    "extract_list_name_from_text",
    "create_task",
    "get_task_lists",
    "create_task_list",
    "delete_task_list",
    "get_all_tasks",
    "get_pending_tasks",
    "get_completed_tasks",
    "get_tasks_due_today",
    "get_tasks_due_tomorrow",
    "get_upcoming_tasks",
    "get_overdue_tasks",
    "search_tasks",
    "get_task_statistics",
    "complete_task",
    "delete_task",
    "update_task",
    "reschedule_task",
    "move_task_between_lists",
]
