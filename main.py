"""News Curator - Main entry point (Web UI)."""
import sys
import os
import argparse

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import run_web_app


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="News Curator - Web UI")
    parser.add_argument(
        "--host", 
        default="127.0.0.1", 
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=5000, 
        help="Port to bind to (default: 5000)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("News Curator App - Web Interface")
    print("=" * 50)
    print(f"\nConfiguration:")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Debug: {args.debug}")
    
    # Run the web application
    run_web_app(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
