import requests
from bs4 import BeautifulSoup
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('website_monitor.log'),
        logging.StreamHandler()
    ]
)

class WebsiteMonitor:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.last_content_hash = None
        self.current_content_hash = None
        self.current_content = None
        
        self.email_server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
        self.email_server.starttls()
        self.email_server.login(self.config['email']['sender_email'], self.config['email']['sender_password'])
        
    def login(self):

        try:
            login_url = "https://adfs.hv.se/adfs/ls/?SAMLRequest=fZFdb4IwFIbv9ytI76GlfKYRjJsxM9kyo7iL3SwFymwCLespZj9%2BCpq5G%2B%2FapOc5b593Nv%2FpWucoDEitMuR7BDlCVbqW6itD%2B2LlpmieP8yAdy3t2WKwB7UV34MA6ywAhLGnuSetYOiE2QlzlJXYb18ydLC2B4YxgPakgl4Y7lW6w2cQFqrutVQW8ysCOcsTUipuxxzXaV434B2OHojxiFvAyFlpU4kxSYYa3oJAznqZoc%2BwDpIy4bFbRg13wzBO3bIOGrfhRMSkChuSnn63BhjEWoHlymaIEhq5JHZJUFDKgoBFqRdH%2FgdyNkZbXen2UapJxmAU0xwkMMU7AcxWbLd4fWHUI6ycHgF7LoqNu3nbFch5v0qlZ6knzQrYpPE%2Bq78sRvlknY2JzS3hPuBPan72eCnBp1FC%2FCSIbuuY4dsV%2BeX6v%2Bf8Fw%3D%3D&SigAlg=http%3A%2F%2Fwww.w3.org%2F2001%2F04%2Fxmldsig-more%23rsa-sha256&Signature=vExEk2io6XhvOuqfhjUKPAGgECko5IVfpsH%2FyoIGIkf9CkMfiipKe08OrBrf8G0DpfflFKmi2OeyR8h1KnJNvusbQbcTPRtLM7dWUcAg5ZqZdc481ZnQC9R7MmWyg4AXAtcnfa6v%2BQZWviRLqVvLnaikSQe954GmHpwGUD4Eg0xuSYF73yhV7AB8oihlZMS5Cs9Pkf9j3wCwVa4kHpfd%2BCvod2COCL250Cui1tn%2BSgNzJQi1o71OGI1TZcU1T0tUYQ%2FmpQ1A4caojZjRDBAW1kzRqsVFpdF5t%2BQN0%2FfdIKehbKzpivY%2FZ%2FIx7Hac4yP5NVrWAZOUKQWdnQJ9OhyrXwi8CjGWbALJNRH6%2BP6YB4RLFMd9BPtnyEeO47%2B0xysRtV4ebTVbNh%2FAyJ83HcSZ25YhhV2rxTtZN24WihqbdCRJSMeMS9%2BqOolwqKx%2BDhhypquQcTIj1%2FbLmfK6nyfquuIwjsSecW9YC3axWXYb9J23nQs76VbissT867aTH9P2GaLa26oVbAkffzBFg%2B4f88pe5%2BxaylIfkfrvGhMoQzU6C9awJQpeAlKiBffk1FYDLMajovL3nfqS6yTqBAx9TKchY3o2lBwRJBRTwhbjN5tJpDF2pqjNqqipJyGKTx4g0mDmu7kf2FiTHThRDzbuOY0VfFmwA4ABQdqkxydHfoQ%3D" #Studentens inlogg på inspera 
            login_data = {
                'username': self.config['website']['username'],
                'password': self.config['website']['password']
            }
            
            response = self.session.post(login_url, data=login_data)
            response.raise_for_status()
            
            if "login" in response.url.lower():
                raise Exception("Login failed - check credentials")
                
            logging.info("Successfully logged in")
            return True
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False
    
    def fetch_content(self):
        try:
            response = self.session.get(self.config['website']['url'])
            response.raise_for_status()
            self.current_content = response.text
            return True
        except Exception as e:
           logging.error(f"Failed to fetch content: {str(e)}")
           return False 


    def check_for_changes(self):
        if not self.fetch_content():
            return False

        soup = BeautifulSoup(self.current_content, 'html.parser')
        grade_element = soup.find('span', class_='grade')
        if grade_element:
            if not getattr(self, 'notified', False):
                logging.info(f"Grade detected: {grade_element.text.strip()}")
                self.notified = True
                return True
            else:
                logging.info("Grade still present, already notified.")
                return False
        else:
            logging.info("No grade found yet.")
            self.notified = False
            return False
    
    def send_notification(self):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['sender_email']
            msg['To'] = self.config['email']['recipient_email']
            msg['Subject'] = f"Change detected on {self.config['website']['url']}"
            
            body = f"""
The website {self.config['website']['url']} has changed.

Check it at: {self.config['website']['url']}

Time detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            msg.attach(MIMEText(body, 'plain'))
            
            self.email_server.send_message(msg)
            logging.info("Notification email sent successfully")
        except Exception as e:
            logging.error(f"Failed to send notification: {str(e)}")
    
    def monitor(self):
        logging.info("Starting website monitor")
        
        if not self.login():
            logging.error("Cannot continue without successful login")
            return
            
        while True:
            try:
                if self.check_for_changes():
                    self.send_notification()
                logging.info(f"Waiting {self.config['monitor']['check_interval']} seconds before next check")
                time.sleep(self.config['monitor']['check_interval'])
            except KeyboardInterrupt:
                logging.info("Monitoring stopped by user")
                break
            except Exception as e:
                logging.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)
    
    def __del__(self):
        try:
            self.email_server.quit()
        except:
            pass

def load_config():
    required_vars = [
        'WEBSITE_URL', 'WEBSITE_USERNAME', 'WEBSITE_PASSWORD',
        'SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'SENDER_PASSWORD', 
        'RECIPIENT_EMAIL', 'CHECK_INTERVAL'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return {
        'website': {
            'url': os.getenv('WEBSITE_URL'),
            'username': os.getenv('WEBSITE_USERNAME'),
            'password': os.getenv('WEBSITE_PASSWORD')
        },
        'email': {
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': int(os.getenv('SMTP_PORT')),
            'sender_email': os.getenv('SENDER_EMAIL'),
            'sender_password': os.getenv('SENDER_PASSWORD'),
            'recipient_email': os.getenv('RECIPIENT_EMAIL')
        },
        'monitor': {
            'check_interval': int(os.getenv('CHECK_INTERVAL'))
        }
    }

if __name__ == "__main__":
    config = load_config()
    WebsiteMonitor(config).monitor()