#!/usr/bin/env python3
"""
Start the Digital Twin MCP Server
Simple wrapper to run the MCP server
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    from digital_twin_backend.mcp_integration.server import create_app
    
    print("🚀 Digital Twin MCP Server")
    print("=" * 60)
    print("Starting FastMCP server with 25 tools...")
    print("=" * 60)
    print("")
    
    app = create_app()
    
    print("✅ Server initialized successfully!")
    print("✅ All 25 MCP tools registered")
    print("")
    print("📡 Available Tool Categories:")
    print("   • System Management (2 tools)")
    print("   • Task Management (5 tools)")
    print("   • Agent Management (4 tools)")
    print("   • Model Management (7 tools)")
    print("   • API Key Management (7 tools)")
    print("")
    print("🔌 Server ready for MCP client connections")
    print("   (Claude Desktop, Cursor, custom clients, etc.)")
    print("")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print("")
    
    # Run the server
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        print("✅ Shutdown complete")

