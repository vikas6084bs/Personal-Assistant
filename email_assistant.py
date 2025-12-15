# email_assistant.py
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime
import time
import re

# -------------------- Configure Gemini API --------------------
genai.configure(api_key="AIzaSyBLPj0owSg9IyNPxJaDicnbKZlXyjfzoiU")  # Replace with your key

# -------------------- Generate Email Content --------------------
def generate_email_content(prompt):
    """Generate professional email content using Gemini API."""
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(
            f"Write exactly ONE clear, polite, professional email about: {prompt}. "
            "Do not include multiple options or alternatives."
        )
        return response.text.strip() if hasattr(response, "text") else str(response)
    except Exception as e:
        print("Error generating content:", e)
        # Fallback template
        return f"Dear [Recipient],\n\n{prompt}\n\nBest regards,\n[Your Name]"

# -------------------- Extract Subject --------------------
def extract_subject(user_input):
    # Look for phrases like "subject: XYZ" or infer from main topic
    match = re.search(r"subject[:\-]\s*(.*?)(?:\.|$)", user_input, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: take first 5-7 words as subject
    words = re.findall(r'\w+', user_input)
    return " ".join(words[:7]).capitalize()

# -------------------- Send Email --------------------
def send_email(to_list, cc_list, bcc_list, subject, body, send_time=None):
    sender_email = "vikasbalasubramaniambs@gmail.com"
    sender_password = "vjyb eycv vuby fzkh"  # 16-char App password

    # Schedule sending if time given
    if send_time:
        try:
            send_dt = datetime.datetime.strptime(send_time, "%Y-%m-%d %H:%M")
            now = datetime.datetime.now()
            delay = (send_dt - now).total_seconds()
            if delay > 0:
                print(f"Waiting until {send_time} to send email...")
                time.sleep(delay)
        except Exception:
            print("Invalid time format, sending immediately.")

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        all_recipients = to_list + cc_list + bcc_list

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg, from_addr=sender_email, to_addrs=all_recipients)

        print(f"Email sent successfully to {', '.join(to_list)}!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# -------------------- Log Email --------------------
def log_email(to_list, cc_list, bcc_list, subject, body, status):
    os.makedirs("email_logs", exist_ok=True)
    log_file = f"email_logs/{datetime.date.today()}.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n----- {datetime.datetime.now()} -----\n")
        f.write(f"Status: {status}\n")
        f.write(f"To: {', '.join(to_list)}\n")
        if cc_list:
            f.write(f"Cc: {', '.join(cc_list)}\n")
        if bcc_list:
            f.write(f"Bcc: {', '.join(bcc_list)}\n")
        f.write(f"Subject: {subject}\n\n{body}\n")
    print(f"Email logged to {log_file}")
