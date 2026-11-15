"""FORGE AI Local Workspace Agent entry point."""
import asyncio
import sys


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="FORGE AI Local Workspace Agent")
    parser.add_argument("--config", default="forge-agent.toml", help="Config file path")
    parser.add_argument("--server", default=None, help="Override WebSocket server URL")
    parser.add_argument("--api", default=None, help="Backend REST API base, e.g. http://localhost:8000/api")
    parser.add_argument("--pair", default=None, metavar="CODE", help="Pairing code from the web Connect Agent dialog")
    parser.add_argument("--device-id", default=None, help="Device ID from the web Connect Agent dialog (required with --pair)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # One-time pairing: exchange the code for a device token and store it encrypted.
    if args.pair:
        if not args.device_id:
            print("ERROR: --device-id is required with --pair. Both values are shown in the\n"
                  "       web 'Connect Agent' dialog, right under the pairing code.")
            sys.exit(2)
        from app.authentication.pairing import pair_with_backend, derive_api_base
        from app.authentication import token_store
        api_base = derive_api_base(args.server, args.api)
        print(f"Pairing device {args.device_id} via {api_base} ...")
        try:
            creds = pair_with_backend(api_base, args.device_id, args.pair)
        except Exception as exc:
            print(f"Pairing failed: {exc}")
            sys.exit(1)
        token_store.save_token(creds["device_id"], creds["auth_token"])
        print("Paired successfully. Credentials saved. Starting agent...")

    from app.main import ForgeAgent
    agent = ForgeAgent(config_path=args.config, server_url=args.server, debug=args.debug)

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
