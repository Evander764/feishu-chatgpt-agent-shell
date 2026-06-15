from __future__ import annotations

import argparse
import subprocess
import sys

from .browser_runner import ChatGPTWebRunner
from .config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="feishu-chatgpt-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup-chatgpt", help="Open the isolated browser profile for first login.")
    sub.add_parser("run", help="Run the local FastAPI server.")
    sub.add_parser("health", help="Print local settings health.")
    args = parser.parse_args()

    settings = load_settings()
    if args.command == "setup-chatgpt":
        ChatGPTWebRunner(settings).open_for_login()
        print("Opened isolated Chrome profile. Log in to ChatGPT, create/pin a project, then set CHATGPT_PROJECT_URL in .env.")
        return
    if args.command == "health":
        from .service import AgentService

        print(AgentService(settings).health())
        return
    if args.command == "run":
        subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "feishu_chatgpt_agent_shell.main:app",
                "--host",
                settings.app_host,
                "--port",
                str(settings.app_port),
            ]
        )


if __name__ == "__main__":
    main()

