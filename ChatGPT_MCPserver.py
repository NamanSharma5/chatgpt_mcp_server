import os
import time
from dotenv import load_dotenv
from seleniumbase import SB

class ChatGPTMCPServer:
    def __init__(self, headless: bool = True):
        load_dotenv()
        # Set up credentials
        self.hidden = False
        if self.hidden:
            self.email = os.getenv('CC_EMAIL')
            self.password = os.getenv('CC_PASSWORD')
        else:
            self.email = os.getenv('OPENAI_EMAIL')
            self.password = os.getenv('OPENAI_PASSWORD')

        if not (self.email and self.password):
            raise ValueError("Please set OPENAI_EMAIL and OPENAI_PASSWORD in your environment")

        self.headed = not headless
        self._sb_mgr = None
        self.sb      = None

    def __enter__(self):
        # Launch undetected Chrome via SeleniumBase
        self._sb_mgr = SB(uc=True, test=True, headed=self.headed)
        self.sb      = self._sb_mgr.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._sb_mgr:
            self._sb_mgr.__exit__(exc_type, exc, tb)

    def login(self):
        sb = self.sb
        sb.open("https://chatgpt.com/")
        # If "sign up" is present, we need to authenticate
        if "sign up" in sb.get_page_source().lower():
            sb.click('button[data-testid="login-button"]')
            sb.wait_for_element('input[id=":r1:-email"]')
            sb.type('input[id=":r1:-email"]', self.email)
            sb.click('button[type="submit"]')

            sb.wait_for_element('input[id=":re:-password"]', timeout=15)
            sb.type('input[id=":re:-password"]', self.password)
            sb.click('button:contains("Continue")')

            # give Cloudflare / ChatGPT a moment
            sb.sleep(5)
        else:
            print("✅ Already logged in!")

    def send_prompt(self, prompt: str):
        sb = self.sb
        sb.wait_for_element('#prompt-textarea', timeout=20)
        sb.type('#prompt-textarea', prompt)
        time.sleep(2)  # mimic a brief “thinking” pause
        sb.click('button[data-testid="send-button"]')
        # # wait for the assistant’s reply to render - renders but since streaming can be incomplete
        # sb.wait_for_element('article[data-testid^="conversation-turn-"]', timeout=30)

        # Wait for the "stop streaming" button to appear
        sb.wait_for_element('button[data-testid="stop-button"]', timeout=10)

        # Then wait for it to disappear (streaming complete)
        sb.wait_for_element_absent('button[data-testid="stop-button"]', timeout=180)

    def extract_response(self) -> str:
        sb = self.sb
        articles = sb.find_elements('article[data-testid^="conversation-turn-"]')
        output_lines = []

        for article in articles:
            try:
                if "ChatGPT said:" in article.text:
                    output_lines.append(article.text.split("ChatGPT said:")[-1].strip())

            except Exception as e:
                print(f"⚠️ Error processing a response container: {e}")
                continue

        return "\n".join(output_lines)

# Example usage:
if __name__ == "__main__":
    with ChatGPTMCPServer(headless=False) as server:
        server.login()
        server.send_prompt("What do you remember about me?")
        reply = server.extract_response()
        print("\n💬 ChatGPT replied:\n")
        print(reply)
