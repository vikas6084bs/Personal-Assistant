## PERSONAL ASSISTANT

## Overview

Smart Productivity Assistant is a console‑based assistant that lets you manage Google Tasks, Google Calendar events, and email actions using natural language.[1]
You can type free‑form text like “create meeting tomorrow at 5pm and send reminder email” and the assistant will create tasks, schedule calendar events (with Meet links), and send or schedule emails accordingly.[1]

## Features

- Google Tasks  
  - Create, view, search, complete, delete tasks, and view task statistics (today, tomorrow, pending, completed, all).[1]

- Google Calendar  
  - Create events (including online meetings), view upcoming events, search, delete, reschedule, and get calendar statistics.[1]

- Email Assistant  
  - Extract recipients from text, build subjects and bodies, send emails immediately or schedule them for later.[1]

- Natural Language Handling  
  - Detects whether you mean a task, event, or email.  
  - Parses dates/times (today, tomorrow, weekdays, explicit dates, “next week”, etc.).  
  - Splits multi‑step commands like “create meeting and send reminder email” into separate operations.[1]

## Architecture

- Core Assistant  
  - Routes user input to methods such as `_create_item`, `_view_tasks`, `_view_calendar`, `_process_email`, `_search_items`, `_delete_item`, and `_reschedule_event`.[1]

- Time Parsing  
  - `SmartTimeParser` extracts dates and times from natural language for tasks, events, and email scheduling.[1]

- Service Modules (typical structure)  
  - `google_tasks.py`: wraps the Google Tasks API (CRUD operations, search, statistics).[1]
  - `google_calendar.py`: wraps the Google Calendar API (create, view, search, delete, reschedule events, generate Meet links).[1]
  - `email_assistant.py`: handles email composition and sending/scheduling.[1]

The assistant degrades gracefully when a service is not available, returning clear error messages instead of crashing.[1]

## Prerequisites

- Python 3.9 or higher.[2]
- A Google Cloud project with:
  - Google Tasks API enabled.[2]
  - Google Calendar API enabled.[2]
- Google OAuth client or service account credentials (JSON).[2]
- An OpenAI API key for any model‑based features (e.g., smarter email/text generation).[2]
- SMTP or email provider credentials for sending emails.[1]

## Installation

1. Clone the repository:

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

3. Install dependencies directly with pip (no requirements.txt):

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib openai python-dotenv
```


If you add extra libraries (for example, for logging or richer CLI), list them here as well.

## Google Cloud Setup

1. Create or select a project  
   - Go to Google Cloud Console and either create a new project or select an existing one.[2]

2. Enable APIs  
   - In “APIs & Services → Library”, enable:
     - Google Tasks API  
     - Google Calendar API[2]

3. Create credentials  
   - Open “APIs & Services → Credentials”.[2]
   - Click “Create Credentials” and choose:
     - OAuth client ID (Desktop application) if you want user consent flow, or  
     - Service account if you prefer server‑to‑server access.[2]
   - Download the JSON credentials file.[2]

4. Store credentials  
   - Save the JSON file in a secure location within your project, for example:

     ```text
     <project-root>/credentials/credentials.json
     ```

   - Update `google_tasks.py` and `google_calendar.py` to point to this path when building the clients.[1]

5. Set the Google credentials environment variable (see next section):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/credentials/credentials.json
```


## Environment Variables

Use a `.env` file loaded via `python-dotenv` or export variables in your shell. Example `.env`:

```env
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/credentials/credentials.json
OPENAI_API_KEY=your-openai-api-key
```

- `GOOGLE_APPLICATION_CREDENTIALS`  
  Points to the Google JSON credentials file for the Tasks and Calendar APIs.[2]

- `OPENAI_API_KEY`  
  Used to call OpenAI models (for generating email content, summaries, or other smart behaviors inside the assistant).[2]

- Email variables  
  Configure how `email_assistant.py` connects to your SMTP server or email provider.[1]


## Usage

1. Run the assistant:

```bash
python main.py
```

2. Enter natural language commands in the terminal. Examples:[1]

- Tasks  
  - `create task finish ML assignment tomorrow`  
  - `show my tasks for today`  
  - `complete task finish ML assignment`  
  - `delete task pay electricity bill`  

- Calendar  
  - `create meeting tomorrow at 5pm with participant user@example.com`  
  - `show my meetings for the next 7 days`  
  - `reschedule meeting project sync to next monday at 3pm`  
  - `delete event project sync`  

- Email  
  - `send email to user@example.com about project status`  
  - `schedule email to user@example.com on 20 dec at 9:00 am about demo`  

The assistant responds with confirmations like “Task created”, “Event created”, “Event rescheduled”, or “Email scheduled”, including key details such as titles and times.[1]

## Natural Language Behavior

- Intent Detection  
  - Uses keywords such as `task`, `event`, `meeting`, `appointment`, `email`, `send` to decide whether to operate on tasks, calendar, or email.[1]

- Title Extraction  
  - For tasks: strips leading command words like `create`, `add`, `make`, `new`, `task`, `todo`, `reminder`, and uses the remainder as the task title.[1]
  - For events: similar cleaning to build a readable event title, while still including important context such as participant emails when possible.[1]

- Date and Time Parsing  
  - Handles phrases like `today`, `tomorrow`, `day after tomorrow`, `next week`, specific dates (`20 dec`, `dec 20`), times (`5pm`, `17:30`, `10:15 am`), and weekdays (`next monday`).[1]

- Multi‑command Inputs  
  - Can split and process combined commands such as  
    `create schedule meeting today at 5pm with participant user@example.com and send reminder email to user@example.com at 12:50 pm`.[1]

## Error Handling

- Missing services (Tasks/Calendar/Email) are reported with clear messages instead of causing crashes.[1]
- If no matching task or event is found for complete/delete/reschedule, the assistant replies with a descriptive “not found” message.[1]
- Exceptions in viewing tasks or events are caught and surfaced as `"Error: <message>"`.[1]

## Testing

- Parsing  
  - Test `SmartTimeParser` with multiple input formats (different date/time phrases and weekdays) to ensure correct `datetime` extraction.[1]

- Intents  
  - Verify that `_create_item`, `_delete_item`, `_search_items`, `_view_tasks`, `_view_calendar`, and `_process_email` route correctly for various natural language commands.[1]

- Integration  
  - Confirm that tasks appear in Google Tasks, events in Google Calendar, and emails actually reach the intended recipients and respect scheduled times.[1]





