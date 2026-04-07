"""
Azure AI client wrapper for Cisco CircuIT API.

- Supports env vars from OS, .env files, CI/CD, containers, or Kubernetes
- OAuth2 client-credentials authentication
"""

import base64
import os
import re
import markdown
import requests
from openai import AzureOpenAI
from dotenv import load_dotenv


class AzureAIClient:
    """
    Client for interacting with Azure-hosted OpenAI models via Cisco CircuIT.
    """

    REQUIRED_ENV_VARS = [
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TOKEN_URL",
        "AZURE_APP_KEY",
        "AZURE_ENDPOINT",
        "AZURE_API_VERSION",
        "AZURE_MODEL",
    ]

    def __init__(self, env_path = None):
        """
        Initialize the client.

        Args:
            env_path (str, optional): Path to .env file for loading environment variables.
        """
        self.env_path = env_path
        self.access_token = None
        self.client = None

        self.client_id = None
        self.client_secret = None
        self.token_url = None
        self.app_key = None
        self.endpoint = None
        self.api_version = None
        self.model = None

        self._load_environment()

    def _load_environment(self):
        """
        Load environment variables.

        Priority:
        1. Existing OS environment variables
        2. Optional .env file (if provided)
        """
        if self.env_path and os.path.exists(self.env_path):
            load_dotenv(self.env_path, override=False)

        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.token_url = os.getenv("AZURE_TOKEN_URL")
        self.app_key = os.getenv("AZURE_APP_KEY")
        self.endpoint = os.getenv("AZURE_ENDPOINT")
        self.api_version = os.getenv("AZURE_API_VERSION")
        self.model = os.getenv("AZURE_MODEL")

    def _get_missing_env_vars(self):
        """
        Return list of missing required environment variables.
        """
        return [
            var for var in self.REQUIRED_ENV_VARS
            if not os.getenv(var)
        ]

    def is_ready(self, strict = False):
        """
        Check if the client is properly configured.

        Args:
            strict (bool):
                If True, also verifies OAuth token retrieval.
                If False, only checks configuration variables.

        Returns:
            bool
        """
        missing = self._get_missing_env_vars()
        if missing:
            return False

        if strict:
            try:
                if not self.access_token:
                    self.obtain_oauth_token()
                return True
            except Exception:
                return False

        return True

    def obtain_oauth_token(self):
        """
        Obtain OAuth2 access token using client credentials.
        """
        payload = "grant_type=client_credentials"
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}",
        }

        response = requests.post(self.token_url, headers=headers, data=payload)
        response.raise_for_status()

        self.access_token = response.json().get("access_token")
        return self.access_token

    def _initialize_client(self):
        """
        Initialize AzureOpenAI client if not already initialized.
        """
        missing = self._get_missing_env_vars()
        if missing:
            raise RuntimeError(
                "Client not properly configured. Missing: "
                + ", ".join(missing)
            )

        if not self.access_token:
            self.obtain_oauth_token()

        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.access_token,
            api_version=self.api_version,
        )

    def ask(
            self,
            system_prompt,
            user_prompt,
            format = "raw",
    ):
        """
        Send prompts to CircuIT Chat Completion API.

        Args:
            system_prompt: System instruction
            user_prompt: User input
            format: raw | plain | html | code
        """
        if not self.client:
            self._initialize_client()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            user=f'{{"appkey": "{self.app_key}"}}',
        )

        content = response.choices[0].message.content.strip()

        if format == "html":
            return self._to_html(content)
        if format == "plain":
            return self._to_plaintext(content)
        if format == "code":
            return self._extract_code(content)

        return content

    @staticmethod
    def _to_html(content):
        """ Convert Markdown content to styled HTML. """
        content = re.sub(r'!\[(.*?)\]\((.*?)\)', "", content)
        html_body = markdown.markdown(content, extensions=["tables"])

        styled_html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-weight: 300;
                    padding: 10px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    border-bottom: 1px solid #ccc;
                    padding-bottom: 4px;
                }}
                pre {{
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                code {{
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                blockquote {{
                    border-left: 4px solid #888;
                    padding-left: 10px;
                    margin-left: 0;
                    font-style: italic;
                }}
                a {{
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                ul, ol {{
                    padding-left: 20px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }}
                th, td {{
                    border: 1px solid #d0d7de;
                    padding: 6px 13px;
                    text-align: left;
                }}

                /* Light theme */
                @media (prefers-color-scheme: light) {{
                    body {{ background-color: #ffffff; color: #24292e; }}
                    pre {{ background-color: #f6f8fa; color: #000; }}
                    code {{ background-color: #f6f8fa; color: #000; }}
                    th {{ background-color: #f6f8fa; }}
                    td, th {{ border: 1px solid #d0d7de; }}
                }}

                /* Dark theme */
                @media (prefers-color-scheme: dark) {{
                    body {{ background-color: #1e1e1e; color: #d4d4d4; }}
                    pre {{ background-color: #2d2d2d; color: #ddd; }}
                    code {{ background-color: #2d2d2d; color: #ddd; }}
                    th {{ background-color: #333; }}
                    td, th {{ border: 1px solid #444; }}
                }}
            </style>
        </head>
        <body>{html_body}</body>
        </html>
        """
        return styled_html

    @staticmethod
    def _to_plaintext(content):
        """ Strip Markdown formatting to return plain text. """
        content = re.sub(r"^```[\w]*\n(.*?)\n```$", r"\1", content.strip(), flags=re.DOTALL)
        content = re.sub(r'^.*!\[.*?\]\(.*?\).*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'^(#{1,6})\s+(.*)$', r'\2', content, flags=re.MULTILINE)
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)
        content = re.sub(r'^\s*[-*]\s+', '- ', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\d+\.\s+', lambda m: m.group(), content, flags=re.MULTILINE)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        content = re.sub(r'\n{2,}', '\n\n', content)
        return content.strip()

    @staticmethod
    def _extract_code(markdown_text):
        """ Extract code from Markdown-formatted string. """
        match = re.search(
            r"```(?:\w+)?\n(.*?)\n```",
            markdown_text,
            flags=re.DOTALL,
        )
        return match.group(1) if match else markdown_text