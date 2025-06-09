import time
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import requests
from datetime import datetime
import logging
import sys
load_dotenv()


USERNAME = os.getenv("WEBSITE_USERNAME")
PASSWORD = os.getenv("WEBSITE_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('website_monitor.log', mode='a')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


def get_trollhattan_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=58.282&longitude=12.288&current_weather=true"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        weather = data.get("current_weather", {})
        temp = weather.get("temperature")
        windspeed = weather.get("windspeed")
        return f"Temperatur: {temp}°C, Vindhastighet: {windspeed} km/h"
    except Exception:
        return "Väderdata ej tillgängligt"

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
    course_code = input("Enter the course code to monitor (e.g., CYS201, OGL202): ").upper()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://hv.inspera.com/student")

        page.click('[data-reactid=".1.1.1.1.1.0:$login-item-0.0.0"]')
        page.wait_for_selector("#userNameInput")
        page.wait_for_selector("#passwordInput")
        page.fill("#userNameInput", USERNAME)
        page.fill("#passwordInput", PASSWORD)
        page.press("#passwordInput", "Enter")

        try:
            page.wait_for_selector("#finished", timeout=15000)
            page.click("#finished") 
            print("Clicked on 'Arkiv' tab.")
            logging.info("Clicked on 'Arkiv' tab.")
        except Exception as e:
            print("Could not find or click #finished (Arkiv tab).")
            logging.info(f"Could not find or click #finished (Arkiv tab). Exception: {e}")
            return  

        page.wait_for_selector('li.test-card-wrapper')

        test_li = page.query_selector(
            f'li.test-card-wrapper:has(h1.exam-title:text("{course_code}"))'
        )

        if not test_li:
            print(f'Could not find test titled "Digital tentamen - {course_code}".')
            logging.info(f'Could not find test titled "Digital tentamen - {course_code}".')
            return

        button = test_li.query_selector('button.see-test-details')
        if not button:
            print(f'Could not find "Se fler detaljer" button for {course_code}.')
            logging.info(f'Could not find "Se fler detaljer" button for {course_code}.')
            return

        button.click()
        print(f'Clicked "Se fler detaljer" for Digital tentamen - {course_code}')
        logging.info(f'Clicked "Se fler detaljer" for Digital tentamen - {course_code}')

        try:
            while True:
                page.wait_for_load_state("networkidle")
                

                container_html = page.evaluate('''() => {
                    const container = document.querySelector('div.StudentReport__flexContainer___2hCCt') || document.querySelector('button.download-delivery[aria-label^="Granska resultatöversikt"]') || document.body;
                    return container.outerHTML.slice(0, 1000);  // Limit size for readability
                }''')
                print(f"DEBUG: Snippet of relevant container HTML:\n{container_html}\n")

                grades = page.query_selector_all('span.StudentReport__rightWrapper___321fW')
                if grades:
                    grades_text = [g.inner_text().strip() for g in grades]
                    print(f"DEBUG: Found grades on main page: {grades_text}")

                else:
                    print("DEBUG: No grades found on main page.")

                review_btn = page.query_selector('button.download-delivery[aria-label^="Granska resultatöversikt"]')
                if review_btn:
                    print("DEBUG: Found 'Granska resultatöversikt' button on main page.")
                    
                else:
                    print("DEBUG: No 'Granska resultatöversikt' button found on main page.")


                grades = page.query_selector_all(".grade")
                if grades:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    weather_info = get_trollhattan_weather()

                    grades_text = []
                    for grade in grades:
                        text = grade.inner_text().strip()
                        print(f"Found grade: {text}")
                        logging.info(f"Found grade: {text}")
                        grades_text.append(text)

                    subject = f"Betyg hittades för {course_code}"
                    body = (
                        f"Hej,\n\n"
                        f"Betygen för tentan i {course_code} har nu publicerats på Inspera.\n\n"
                        f"\n\nResultaten hittades den: {now}\n"
                        f"Vädret i Trollhättan just nu: {weather_info}\n\n"
                        "Logga in på Inspera för att se fullständiga resultat.\n\n"
                        "Vänliga hälsningar,\nInspera Grade Monitor Bot"
                    )

                    send_email(subject, body)
                    print("E-post skickad med betygsinformation.")
                    logging.info("E-post skickad med betygsinformation.")
                    break

                review_btn = page.query_selector('button.download-delivery[aria-label^="Granska resultatöversikt"]')
                if review_btn:
                    print("Granska resultatöversikt button found, clicking to open grade review popup...")
                    logging.info("Granska resultatöversikt button found, clicking to open grade review popup...")

                    with page.expect_popup() as popup_info:
                        review_btn.click()
                    new_page = popup_info.value
                    new_page.wait_for_load_state("networkidle")

                    grade_span = new_page.query_selector('div[class*="flexContainer"] span[class*="rightWrapper"]')
                    if grade_span:
                        grade_text = grade_span.inner_text().strip()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        weather_info = get_trollhattan_weather()

                        print(f"Found grade in review popup: {grade_text}")
                        logging.info(f"Found grade in review popup: {grade_text}")

                        subject = f"Betyg hittades för {course_code}"
                        body = (
                            f"Hej,\n\n"
                            f"Betygen för tentan i {course_code} har nu publicerats på Inspera.\n\n"
                            f"Upptäckt betyg: {grade_text}\n"
                            f"Resultatet hittades den: {now}\n"
                            f"Vädret i Trollhättan just nu: {weather_info}\n\n"
                            "Logga in på Inspera för att se fullständiga resultat.\n\n"
                            "Vänliga hälsningar,\nInspera Grade Monitor Bot"
                        )

                        send_email(subject, body)
                        print("E-post skickad med betygsinformation.")
                        logging.info("E-post skickad med betygsinformation.")
                        new_page.close()
                        break 
                    else:
                        print(" Kunde inte hitta betyg i granskningsvyn, men knappen fanns. Detta bör inte hända.")
                        logging.error("Kunde inte hitta betyg i granskningsvyn, men knappen fanns. Detta bör inte hända.")
                        new_page.close()
                        break 

                print(f"Inga betyg hittades för {course_code}. Försöker igen om 5 minuter...")
                logging.info(f"Inga betyg hittades för {course_code}. Försöker igen om 5 minuter...")
                time.sleep(300)
                page.reload()

        except KeyboardInterrupt:
            print("Övervakning avbruten av användaren.")
            logging.info("Overvakning av anvandaren avbruten.")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
