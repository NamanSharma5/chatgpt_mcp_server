import os
import time
import logging
import io
import contextlib
from dotenv import load_dotenv
from seleniumbase import SB
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ChatGPTMCPServer")

# Initialize FastMCP server
mcp = FastMCP("chatgpt_memory")
# Global ChatGPT server instance (lazily initialized)
_chatgpt = None

load_dotenv()
chrome_path = os.getenv('CHROME_PATH')

class ChatGPTMCPServer:
    def __init__(self, headless: bool = True):
        logger.info("Initializing ChatGPTMCPServer (headless=%s)", headless)
        # Set up credentials
        self.email = os.getenv('OPENAI_EMAIL')
        self.password = os.getenv('OPENAI_PASSWORD')

        if not (self.email and self.password):
            raise ValueError("Please set OPENAI_EMAIL and OPENAI_PASSWORD in your environment")

        # SeleniumBase manager
        self.headed = not headless
        self._sb_mgr = None
        self.sb      = None

    def __enter__(self):
        logger.info("Launching browser wrapped in stdout redirect buffer w/ better error handling")
        # Capture SB’s banner output so it doesn’t hit stdout
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                self._sb_mgr = SB(test=True, headed=self.headed, uc=True, binary_location=chrome_path)
                self.sb      = self._sb_mgr.__enter__()
        except Exception as e:
            # Log the exception (goes to stderr) so Claude sees it in its debug log
            logger.exception("Browser launch failed: %s", e)
            # Re‑raise so the tool call clearly errors out
            raise
        logger.info("Browser launched")
        return self

    def __exit__(self, exc_type, exc, tb):
        logger.info("Closing browser")
        if self._sb_mgr is None:
            logger.error("Browser manager is None, cannot close")
            return

         # Capture SB’s banner output so it doesn’t hit stdout
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                self._sb_mgr.__exit__(exc_type, exc, tb)
        except Exception as e:
            # Log the exception (goes to stderr) so Claude sees it in its debug log
            logger.exception("Browser launch failed: %s", e)
            # Re‑raise so the tool call clearly errors out
            raise
        logger.info("Browser closed")

    def login(self):
        logger.info("Starting login process")
        sb = self.sb
        sb.open("https://chatgpt.com/")
        # If "sign up" is present, we need to authenticate
        if "sign up" in sb.get_page_source().lower():
            sb.click('button[data-testid="login-button"]')
            sb.wait_for_element('input[id=":r1:-email"]', timeout=120)
            sb.type('input[id=":r1:-email"]', self.email)
            sb.click('button[type="submit"]')

            sb.wait_for_element('input[id=":re:-password"]', timeout=120)
            sb.type('input[id=":re:-password"]', self.password)
            sb.click('button:contains("Continue")')

            # give Cloudflare / ChatGPT a moment
            sb.sleep(5)
            logger.info("Login successful")
        else:
            logger.info("Already logged in!")

    def send_prompt(self, prompt: str):
        sb = self.sb
        sb.wait_for_element('#prompt-textarea', timeout=40)
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
                logger.error(f"⚠️ Error processing a response container: {e}")
                continue

        return "\n".join(filter(None, output_lines))

async def _ensure_chatgpt():
    """Lazily initialize and log in to ChatGPT on first tool call."""
    global _chatgpt
    if _chatgpt is None:
        logger.info("First tool invocation: initializing ChatGPT session")
        # Instantiate and enter context
        server = ChatGPTMCPServer(headless=False)
        server.__enter__()
        server.login()
        _chatgpt = server
    return _chatgpt

@mcp.tool()
async def get_chatgpt_memory() -> str:
    """Syncs with ChatGPT to fetch the latest stored memory data in real time"""
    logger.info("Tool call: get_chatgpt_memory")
    server = await _ensure_chatgpt()
    prompt = "What do you remember about me?"
    # Send prompt and fetch response
    server.send_prompt(prompt)
    memory = server.extract_response()
    if not memory:
        memory = "No memory retrieved or empty response."
    return memory

@mcp.tool()
async def shutdown_chatgpt() -> str:
    """Shutdown the ChatGPT server."""
    logger.info("Tool call: shutdown_chatgpt")
    global _chatgpt
    if _chatgpt is not None:
        _chatgpt.__exit__(None, None, None)
        _chatgpt = None
        return "ChatGPT server shut down successfully."
    return "ChatGPT server was not running."


if __name__ == "__main__":
    logger.info("Starting MCP server...")
    mcp.run(transport='stdio')
    logger.info("MCP server stopped")


    # Example usage of just the ChatGPTMCPServer class
    # This is a standalone example, not using the FastMCP server:
    # with ChatGPTMCPServer(headless=False) as server:
    #     server.login()
    #     server.send_prompt("What do you remember about me?")
    #     reply = server.extract_response()
    #     print("\nChatGPT replied:\n")
    #     print(reply)
