"""Command-line interface (CLI) entrypoint for Durable Agentic OS."""

import argparse
import asyncio
import sys
from pathlib import Path

from durable_agent.safeguards.hmac_signer import CryptoApprovalSigner


def _ensure_repo_root_in_path() -> None:
    repo_root = str(Path(__file__).resolve().parent.parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def run_demo() -> None:
    """Run the live trading desk demonstration."""
    _ensure_repo_root_in_path()
    from examples.run_trading_desk import main as run_trading_desk_main

    asyncio.run(run_trading_desk_main())


def run_recovery_demo() -> None:
    """Run the crash recovery demonstration."""
    _ensure_repo_root_in_path()
    from examples.crash_recovery_demo import main as run_recovery_main

    asyncio.run(run_recovery_main())


def generate_token_cli(workflow_id: str, action: str, notional: float) -> None:
    """CLI helper to generate HMAC approval token."""
    signer = CryptoApprovalSigner()
    token = signer.generate_token(workflow_id, action, notional)
    print("\n[+] Generated Cryptographic Approval Token:")
    print(token)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="durable-agent",
        description="Durable Agentic OS: The Durable Operating System for Agentic AI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # demo
    demo_parser = subparsers.add_parser("demo", help="Run the Autonomous Trading Desk demo")
    demo_parser.add_argument("--crash-recovery", action="store_true", help="Run crash recovery demo")

    # token
    token_parser = subparsers.add_parser("token", help="Generate cryptographic approval token")
    token_parser.add_argument("--workflow-id", required=True, help="Temporal workflow ID")
    token_parser.add_argument("--action", default="BUY", choices=["BUY", "SELL"], help="Trade action")
    token_parser.add_argument("--notional", type=float, default=15000.0, help="Trade amount in USD")

    args = parser.parse_args()

    if args.command == "demo":
        if args.crash_recovery:
            run_recovery_demo()
        else:
            run_demo()
    elif args.command == "token":
        generate_token_cli(args.workflow_id, args.action, args.notional)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
