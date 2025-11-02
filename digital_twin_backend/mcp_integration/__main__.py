"""
MCP Server Entry Point
Run with: python -m digital_twin_backend.mcp_integration
"""
from digital_twin_backend.mcp_integration.server import create_app

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Ensure project root is on path
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    print("🚀 Starting Digital Twin MCP Server...")
    print("=" * 60)
    
    app = create_app()
    
    print("✅ Server initialized with 25 MCP tools")
    print("🔌 Ready for MCP client connections")
    print("=" * 60)
    
    # Run the server
    app.run()

