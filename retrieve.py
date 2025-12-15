# retrieve.py
from google_tasks import list_tasks
from dateparser import parse
from datetime import datetime
import re
import spacy

# -----------------------------
# Load spaCy model
# -----------------------------
nlp = spacy.load("en_core_web_sm")

# -----------------------------
# Simple intent detection using NLP
# -----------------------------
def detect_intent_and_entities(user_input):
    """
    Simple intent detection using spaCy's linguistic features.
    """
    doc = nlp(user_input.lower())
    
    # Extract entities
    persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    
    # Simple intent detection using lemma matching
    intent = "all"
    meeting_lemmas = {"meeting", "meet", "appointment", "call", "discussion"}
    exam_lemmas = {"exam", "test", "quiz", "study", "prepare"}
    
    for token in doc:
        if token.lemma_ in meeting_lemmas:
            intent = "meeting"
            break
        elif token.lemma_ in exam_lemmas:
            intent = "exam"
            break
    
    return intent, persons, dates

# -----------------------------
# Improved date parsing using spaCy entities
# -----------------------------
def parse_user_date(user_input):
    """Parse date from user input using multiple strategies"""
    # First try using spaCy to extract dates
    doc = nlp(user_input)
    for ent in doc.ents:
        if ent.label_ == "DATE":
            parsed_date = parse(ent.text, settings={
                'PREFER_DATES_FROM': 'future', 
                'RELATIVE_BASE': datetime.now()
            })
            if parsed_date:
                return parsed_date
    
    # If spaCy doesn't find dates, try the original approach
    parsed_date = parse(user_input, settings={
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': datetime.now(),
    })
    
    return parsed_date

# -----------------------------
# Simple task matching
# -----------------------------
def is_related_task(task_title, intent, entities):
    """
    Simple and reliable task matching.
    """
    task_lower = task_title.lower()
    
    # If specific persons mentioned, check if task contains them
    if entities:
        for person in entities:
            if person.lower() in task_lower:
                return True
        return False
    
    # Otherwise, use simple keyword matching for intent
    if intent == "meeting":
        return any(word in task_lower for word in ["meeting", "meet", "appointment", "call"])
    elif intent == "exam":
        return any(word in task_lower for word in ["exam", "test", "quiz", "study"])
    else:
        return True  # "all" intent matches everything

# -----------------------------
# Extract date from due string
# -----------------------------
def extract_date_from_due(due_str):
    """Extract just the date part from due string"""
    if due_str == "No date" or not due_str:
        return None
    
    date_match = re.search(r'\d{4}-\d{2}-\d{2}', due_str)
    if date_match:
        return date_match.group()
    return None

# -----------------------------
# Main retrieve function
# -----------------------------
def retrieve_tasks(user_input):
    """
    Retrieve tasks using simple and reliable NLP.
    """
    # Detect intent and entities
    intent, persons, date_entities = detect_intent_and_entities(user_input)
    
    # Parse date from user input
    parsed_input_date = parse_user_date(user_input)
    input_date_str = parsed_input_date.strftime("%Y-%m-%d") if parsed_input_date else None

    # Get all tasks
    all_tasks_output = list_tasks()
    if "No tasks found" in all_tasks_output:
        return "No tasks found."

    # Parse tasks
    tasks = []
    for line in all_tasks_output.split("\n"):
        if line.startswith("  - "):
            try:
                parts = line[4:].split("(Due:")
                title = parts[0].strip()
                if len(parts) > 1:
                    due_parts = parts[1].split(", List:")
                    due = due_parts[0].strip().rstrip(')')
                    list_name = due_parts[1].strip().rstrip(')') if len(due_parts) > 1 else "Tasks"
                else:
                    due = "No date"
                    list_name = "Tasks"
                
                task_date_str = extract_date_from_due(due)
                
                tasks.append({
                    "title": title, 
                    "due": due, 
                    "due_date": task_date_str,
                    "list": list_name
                })
            except Exception:
                continue

    # Filter by date
    if input_date_str:
        tasks = [t for t in tasks if t["due_date"] and t["due_date"] == input_date_str]

    # Filter by intent and entities
    filtered_tasks = []
    for task in tasks:
        if is_related_task(task["title"], intent, persons):
            filtered_tasks.append(task)

    if not filtered_tasks:
        date_info = f" on {input_date_str}" if input_date_str else ""
        entity_info = f" with {', '.join(persons)}" if persons else ""
        return f"No {intent if intent != 'all' else ''} tasks found{entity_info}{date_info}."

    # Format output
    date_info = f" on {input_date_str}" if input_date_str else ""
    entity_info = f" with {', '.join(persons)}" if persons else ""
    intent_info = f"{intent}-related " if intent != "all" else ""
    
    output = f"Found {intent_info}tasks{entity_info}{date_info}:\n"
    for t in filtered_tasks:
        output += f"  - {t['title']} (Due: {t['due']}, List: {t['list']})\n"

    return output