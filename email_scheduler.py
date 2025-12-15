import time
import threading
from datetime import datetime as dt, timedelta

from email_assistant import send_email
from integrations import SmartTimeParser


class EmailScheduler:
    def __init__(self):
        self.scheduled_emails = []
        self.running = False
        self.time_parser = SmartTimeParser()

    def start_scheduler(self):
        self.running = True
        threading.Thread(target=self._scheduler_loop, daemon=True).start()

    def stop_scheduler(self):
        self.running = False

    def schedule_email(self, to_email, subject, body, scheduled_time, user_input=""):
        """
        Schedule or send email immediately based on keywords in user_input.

        Behavior:
        - If user says 'now', 'immediately', 'asap', etc. -> send immediately.
        - Otherwise:
            - Parse scheduled_time (YYYY-MM-DD HH:MM).
            - If that time is in the past, move to next day at the same time.
            - ALWAYS schedule (no automatic send-when-past).
        """
        # 1) Explicit immediate send based on keywords
        if user_input:
            user_input_lower = user_input.lower()
            immediate_keywords = [
                'now', 'immediately', 'right away', 'asap',
                'straight away', 'instantly'
            ]
            for keyword in immediate_keywords:
                if keyword in user_input_lower:
                    print(f"DEBUG: Immediate sending keyword '{keyword}' detected, sending now")
                    try:
                        success = send_email([to_email], [], [], subject, body)
                        if success:
                            return True, "sent immediately"
                        return False, "failed to send immediately"
                    except Exception as e:
                        return False, f"error sending immediately: {str(e)}"

        # 2) Otherwise always schedule
        try:
            scheduled_dt = dt.strptime(scheduled_time, "%Y-%m-%d %H:%M")

            # If time is in the past, push to next day same time
            if scheduled_dt <= dt.now():
                print(f"DEBUG: Scheduled time {scheduled_dt} is in the past, moving to next day")
                scheduled_dt = scheduled_dt + timedelta(days=1)

            self.scheduled_emails.append({
                'to_email': to_email,
                'subject': subject,
                'body': body,
                'scheduled_time': scheduled_dt,
                'sent': False
            })
            print(f"DEBUG: Email scheduled for {scheduled_dt}")
            return True, f"scheduled for {scheduled_dt.strftime('%Y-%m-%d %H:%M')}"
        except Exception as e:
            return False, f"error: {str(e)}"

    def _scheduler_loop(self):
        while self.running:
            try:
                now = dt.now()
                for email in self.scheduled_emails[:]:
                    if not email['sent'] and email['scheduled_time'] <= now:
                        print(f"DEBUG: Sending scheduled email: {email['subject']}")
                        send_email(
                            [email['to_email']], [], [],
                            email['subject'], email['body']
                        )
                        email['sent'] = True
                        self.scheduled_emails.remove(email)
                time.sleep(30)
            except Exception:
                time.sleep(60)
