"""
Main application entry point for Digital Twin Backend System
"""
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from communication.shared_knowledge import SharedKnowledgeBase
from communication.protocol import AgentCommunicationProtocol
from integration.frontend_api import create_frontend_api
from config.settings import settings


# Global references
app_instance = None
shared_knowledge = None
communication_protocol = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    print("🚀 Starting Digital Twin Backend System...")
    
    global shared_knowledge, communication_protocol
    
    try:
        # Initialize core systems
        shared_knowledge = SharedKnowledgeBase()
        await shared_knowledge.initialize()
        
        # Initialize communication protocol with shared knowledge
        communication_protocol = AgentCommunicationProtocol(shared_knowledge)
        await communication_protocol.initialize()
        
        print("✅ Core systems initialized successfully")
        
        yield
        
    finally:
        print("🔄 Shutting down Digital Twin Backend System...")
        
        # Cleanup - check if instances exist before shutdown
        if communication_protocol:
            await communication_protocol.shutdown()
        if shared_knowledge:
            await shared_knowledge.close()
        
        print("✅ Shutdown complete")


async def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    # Create the frontend API
    frontend_api = await create_frontend_api(shared_knowledge, communication_protocol)
    
    # Use the FastAPI app from frontend_api
    app = frontend_api.app
    
    # Set lifespan
    app.router.lifespan_context = lifespan
    
    return app


async def main():
    """Main entry point"""
    
    print(f"🎯 Digital Twin Backend - {settings.APP_NAME}")
    print(f"🌐 Starting server on {settings.API_HOST}:{settings.API_PORT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    
    # Create application
    global app_instance
    app_instance = await create_app()
    
    # Configure uvicorn
    config = uvicorn.Config(
        app=app_instance,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG
    )
    
    # Run server
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Application failed to start: {e}")
        raise
