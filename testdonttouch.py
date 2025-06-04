import time
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables from .env
load_dotenv()

USERNAME = r"wad.hv.se\saky0001"
PASSWORD = "Sargonkeio2001!"

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

def send_email(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://hv.inspera.com/student")

        page.click('[data-reactid=".1.1.1.1.1.0:$login-item-0.0.0"]')

        page.wait_for_selector("#userNameInput")
        page.wait_for_selector("#passwordInput")

        page.fill("#userNameInput", USERNAME)
        page.fill("#passwordInput", PASSWORD)

        page.press("#passwordInput", "Enter")

        page.click("#finished")

        page.wait_for_selector('li.test-card-wrapper')

        test_li = page.query_selector(
            'li.test-card-wrapper:has(h1.exam-title:text("CYS201"))'
        )

        if test_li:
            button = test_li.query_selector('button.see-test-details')
            if button:
                button.click()
                print('Clicked "Se fler detaljer" for Digital tentamen - CYS201')
            else:
                print('Could not find "Se fler detaljer" button inside the test card.')
        else:
            print('Could not find test titled "Digital tentamen - CYS201".')

        while True:
            page.wait_for_load_state("networkidle")

            grades = page.query_selector_all(".grade")
            if grades:
                print(f"Found {len(grades)} elements with class 'grade':")

                grades_text = []
                for i, grade in enumerate(grades, start=1):
                    text = grade.inner_text()
                    print(f"Grade: {text}")
                    grades_text.append(f"Grade: {text}")

                # Send email with grades
                subject = "Grades Found for Digital tentamen - CYS201"
                body = "The following grades have been found:\n\n" + "\n".join(grades_text)
                send_email(subject, body)
                print("Email sent with grades information.")
                break
            else:
                print("No elements with class 'grade' found. Retrying in 5 minutes...")
                time.sleep(300)
                page.reload()

        browser.close()

if __name__ == "__main__":
    run()
