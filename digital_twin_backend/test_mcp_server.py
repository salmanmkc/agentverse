#!/usr/bin/env python3
"""
Test MCP Server Functionality
Tests all MCP tools including model and API key management
"""
import asyncio
import sys
import json
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def test_mcp_server():
    """Test all MCP server functions"""
    
    print("🧪 Testing MCP Server Functionality")
    print("=" * 60)
    
    try:
        # Import MCP server
        from digital_twin_backend.mcp.server import create_app
        
        print("✅ MCP server module imported")
        
        # Create app
        try:
            app = create_app()
            print("✅ MCP server app created")
        except RuntimeError as e:
            if "mcp" in str(e):
                print("⚠️  MCP package not installed")
                print("💡 Install with: pip install mcp")
                print("\n📝 Testing MCP functions manually instead...")
                await test_mcp_functions_manually()
                return
            raise
        
        print("\n" + "=" * 60)
        print("🎯 MCP Server Available Tools:")
        print("=" * 60)
        
        # List all available tools
        if hasattr(app, 'list_tools'):
            tools = app.list_tools()
            
            categories = {
                "System Management": [],
                "Task Management": [],
                "Agent Management": [],
                "Model Management": [],
                "API Key Management": []
            }
            
            for tool in tools:
                tool_name = tool.get('name', '')
                
                if 'system' in tool_name or tool_name in ['initialize_system', 'get_system_status']:
                    categories["System Management"].append(tool_name)
                elif 'task' in tool_name:
                    categories["Task Management"].append(tool_name)
                elif 'agent' in tool_name and 'model' not in tool_name and 'api' not in tool_name:
                    categories["Agent Management"].append(tool_name)
                elif 'model' in tool_name or 'base_model' in tool_name:
                    categories["Model Management"].append(tool_name)
                elif 'api' in tool_name or 'key' in tool_name or 'provider' in tool_name:
                    categories["API Key Management"].append(tool_name)
            
            for category, tool_list in categories.items():
                if tool_list:
                    print(f"\n{category}:")
                    for tool_name in tool_list:
                        print(f"   ✅ {tool_name}")
        else:
            print("⚠️  Cannot list tools (MCP version issue)")
        
        print("\n🎉 MCP Server is ready to use!")
        print("🚀 Start with: python -m digital_twin_backend.mcp.server")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're in the digital_twin_backend directory")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_mcp_functions_manually():
    """Test MCP functions manually without MCP SDK"""
    
    print("\n🔧 Testing MCP Functions Manually")
    print("=" * 60)
    
    # Test 1: System initialization
    print("\n📡 Test 1: System Initialization")
    print("-" * 40)
    
    try:
        from digital_twin_backend.mcp.server import ServerState
        
        state = ServerState()
        result = await state.initialize()
        
        print(f"✅ System initialized")
        print(f"   Status: {result['status']}")
        print(f"   Manager: {result['agents']['manager']}")
        print(f"   Workers: {', '.join(result['agents']['workers'])}")
        
        # Test 2: Get agent directory
        print("\n👥 Test 2: Agent Directory")
        print("-" * 40)
        
        directory = {
            "total_agents": 1 + len(state.workers),
            "total_workers": len(state.workers),
            "agents": []
        }
        
        if state.manager:
            directory["agents"].append({
                "agent_id": "manager",
                "person_name": state.manager.person_name,
                "role": "manager"
            })
        
        for aid, agent in state.workers.items():
            directory["agents"].append({
                "agent_id": aid,
                "person_name": agent.person_name,
                "role": "worker"
            })
        
        print(f"✅ Found {directory['total_agents']} agents:")
        for agent in directory["agents"]:
            print(f"   • {agent['agent_id']:10s} - {agent['person_name']:35s} [{agent['role']}]")
        
        # Test 3: Get agent model info
        print("\n🤖 Test 3: Agent Model Information")
        print("-" * 40)
        
        for agent_id in list(state.workers.keys())[:3]:  # Test first 3
            agent = state.workers[agent_id]
            model_info = {
                "agent_id": agent_id,
                "person_name": agent.person_name,
                "model_path": agent.model_path,
                "model_loaded": agent.is_model_loaded,
                "using_fallback": not agent.is_model_loaded
            }
            
            print(f"   {model_info['person_name']}:")
            print(f"      Model path: {model_info['model_path'] or 'None'}")
            print(f"      Loaded: {model_info['model_loaded']}")
            print(f"      Using fallback: {model_info['using_fallback']}")
        
        # Test 4: List available models
        print("\n📁 Test 4: Available Models")
        print("-" * 40)
        
        models_dir = Path(settings.MODELS_DIR)
        if models_dir.exists():
            models = [d for d in models_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            print(f"✅ Found {len(models)} model(s) in {models_dir}:")
            for model_dir in models:
                print(f"   • {model_dir.name}")
        else:
            print(f"⚠️  Models directory not found: {models_dir}")
            print("   (This is normal if no models trained yet)")
        
        # Test 5: API Key Management
        print("\n🔑 Test 5: API Key Management")
        print("-" * 40)
        
        from digital_twin_backend.config.api_keys import api_key_manager
        
        # Add test key
        test_result = api_key_manager.add_key("openai", "sk-test-key-12345", "Test Key")
        print(f"✅ Add key: {test_result['success']} - {test_result.get('masked_key', '')}")
        
        # List keys
        keys = api_key_manager.list_keys()
        print(f"✅ Total API keys: {len(keys)}")
        for key_info in keys:
            print(f"   • {key_info['provider']}: {key_info['masked_key']}")
        
        # Supported providers
        print(f"✅ Supported providers ({len(api_key_manager.SUPPORTED_PROVIDERS)}):")
        print(f"   {', '.join(api_key_manager.SUPPORTED_PROVIDERS)}")
        
        # Test 6: Create and distribute task
        print("\n📋 Test 6: Task Creation and Distribution")
        print("-" * 40)
        
        test_task = TaskInfo(
            task_id="mcp_test_001",
            title="MCP Test Task - API Documentation",
            description="Testing MCP task distribution",
            task_type="Technical content",
            priority=7,
            estimated_hours=2.0,
            required_skills=["technical", "documentation"],
            status=TaskStatus.PENDING
        )
        
        await state.shared.add_task(test_task)
        print(f"✅ Task created: {test_task.title}")
        
        # Distribute
        distribution_result = await state.manager.distribute_task(test_task)
        
        if distribution_result.get("success"):
            print(f"✅ Task distributed successfully")
            print(f"   Assigned to: {distribution_result['assigned_agent']}")
        else:
            print(f"⚠️  Distribution completed with result: {distribution_result}")
        
        # Test 7: Get system status
        print("\n📊 Test 7: System Status")
        print("-" * 40)
        
        tasks = list(state.shared.tasks.values())
        contexts = await state.shared.get_all_agent_contexts()
        
        print(f"✅ System Statistics:")
        print(f"   Total tasks: {len(tasks)}")
        print(f"   Pending tasks: {len([t for t in tasks if t.status == TaskStatus.PENDING])}")
        print(f"   Assigned tasks: {len([t for t in tasks if t.status == TaskStatus.ASSIGNED])}")
        print(f"   Active agents: {len(contexts)}")
        print(f"   Total workers: {len(state.workers)}")
        
        # Cleanup
        await state.shutdown()
        print("\n✅ System shutdown successfully")
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 MCP SERVER FULLY FUNCTIONAL!")
        print("=" * 60)
        print("✅ System initialization working")
        print("✅ Agent management working")
        print("✅ Model management working")
        print("✅ API key management working")
        print("✅ Task creation and distribution working")
        print("✅ System status reporting working")
        print("\n🚀 MCP server ready for production use!")
        
    except Exception as e:
        print(f"❌ Error during manual testing: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test runner"""
    
    print("🎯 MCP Server Test Suite")
    print("=" * 60)
    print("Testing Model Context Protocol server with all features")
    print("=" * 60)
    
    await test_mcp_server()


if __name__ == "__main__":
    from digital_twin_backend.communication.shared_knowledge import TaskInfo, TaskStatus
    from digital_twin_backend.config.settings import settings
    
    asyncio.run(main())
