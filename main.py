import re
from datetime import datetime as dt

from smart_chatbot import SmartChatbot
from integrations import SmartTimeParser, extract_event_title
from integrations import create_event 


def split_into_commands(user_input: str):
    commands = []
    quoted_sections = []

    def protect_quotes(match):
        quoted_sections.append(match.group(0))
        return f"__QUOTE_{len(quoted_sections)-1}__"

    protected_text = re.sub(r'["\'][^"\']*["\']', protect_quotes, user_input)
    split_pattern = r'\s+(?:and|also|then)\s+|\s*;\s*|\s*,\s*|\.\s+(?=[A-Z])'
    parts = re.split(split_pattern, protected_text)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        for idx, q in enumerate(quoted_sections):
            placeholder = f"__QUOTE_{idx}__"
            part = part.replace(placeholder, q)
        commands.append(part)

    if not commands:
        commands = [user_input.strip()]

    return commands


def handle_direct_event(cmd: str):
    """
    Create a calendar event directly, without going through SmartChatbot._create_event,
    so we never call create_event(title=..., ...).
    """
    time_parser = SmartTimeParser()
    clean_title = extract_event_title(cmd)
    event_time = time_parser.extract_datetime(cmd)

    processed_input = (
        f"{clean_title} at {event_time.strftime('%I:%M %p')} "
        f"on {event_time.strftime('%b %d')}"
    )

    result = create_event(processed_input)

    if isinstance(result, dict) and result.get("status") == "success":
        return (
            f"Event created: {clean_title} on "
            f"{event_time.strftime('%A, %b %d')} at {event_time.strftime('%I:%M %p')}"
        )
    return f"Failed to create event: {result}"


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

            commands = split_into_commands(user_input)
            all_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)

            for i, cmd in enumerate(commands):
                original_cmd = cmd
                lower_cmd = cmd.lower()

                # 1) If it looks like an event creation command, bypass SmartChatbot
                if any(kw in lower_cmd for kw in ['create event', 'new event', 'schedule event']):
                    response = handle_direct_event(cmd)

                # 2) If it looks like a reminder email without address, inject email
                elif (
                    'reminder' in lower_cmd
                    and 'email' in lower_cmd
                    and not re.search(r'[\w\.-]+@[\w\.-]+\.\w+', cmd)
                    and all_emails
                ):
                    cmd_for_bot = f"send email to {all_emails[0]} about meeting reminder"
                    response = chatbot.process_message(cmd_for_bot)

                # 3) Otherwise, let SmartChatbot decide
                else:
                    response = chatbot.process_message(cmd)

                if len(commands) > 1:
                    print(f"\n[Command {i+1}/{len(commands)}] {original_cmd}")
                print(f"Assistant: {response}")

    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


if __name__ == "__main__":
    main()
