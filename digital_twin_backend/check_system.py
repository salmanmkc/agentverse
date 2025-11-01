#!/usr/bin/env python3
"""
System Health Check for Digital Twin Backend
Verifies all dependencies and core functionality
"""
import sys
import asyncio
from pathlib import Path
import subprocess

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


class SystemHealthChecker:
    """Check system health and dependencies"""
    
    def __init__(self):
        self.results = {}
        
    def check_python_version(self) -> bool:
        """Check Python version"""
        version = sys.version_info
        
        if version.major == 3 and version.minor >= 8:
            print(f"✅ Python {version.major}.{version.minor} (supported)")
            return True
        else:
            print(f"❌ Python {version.major}.{version.minor} (need 3.8+)")
            return False
    
    def check_core_dependencies(self) -> dict:
        """Check core Python dependencies"""
        core_deps = {
            "asyncio": "Built-in async support",
            "json": "JSON handling", 
            "pathlib": "File system operations",
            "dataclasses": "Data structures"
        }
        
        results = {}
        
        for dep, description in core_deps.items():
            try:
                __import__(dep)
                results[dep] = {"status": "✅", "description": description}
            except ImportError:
                results[dep] = {"status": "❌", "description": f"{description} - MISSING"}
        
        return results
    
    def check_optional_dependencies(self) -> dict:
        """Check optional dependencies"""
        optional_deps = {
            "torch": "PyTorch for AI models",
            "transformers": "Hugging Face transformers",
            "datasets": "Dataset handling",
            "peft": "LoRA fine-tuning",
            "fastapi": "Web API framework",
            "uvicorn": "ASGI server",
            "redis": "Data persistence",
            "selenium": "Web scraping",
            "pandas": "Data processing"
        }
        
        results = {}
        
        for dep, description in optional_deps.items():
            try:
                __import__(dep)
                results[dep] = {"status": "✅", "description": description}
            except ImportError:
                results[dep] = {"status": "❌", "description": f"{description} - Install with pip"}
        
        return results
    
    def check_configuration_files(self) -> dict:
        """Check required configuration files"""
        config_files = {
            ".env": "Environment configuration",
            "agent_training_config.json": "Agent training configuration",
            "requirements.txt": "Python dependencies"
        }
        
        results = {}
        
        for filename, description in config_files.items():
            file_path = Path(filename)
            if file_path.exists():
                results[filename] = {"status": "✅", "description": description, "size": file_path.stat().st_size}
            else:
                results[filename] = {"status": "❌", "description": f"{description} - MISSING"}
        
        return results
    
    async def check_core_imports(self) -> dict:
        """Check core system imports"""
        imports = {
            "digital_twin_backend.config.settings": "Configuration system",
            "digital_twin_backend.communication.shared_knowledge": "Shared knowledge base",
            "digital_twin_backend.communication.protocol": "Communication protocol"
        }
        
        results = {}
        
        for module, description in imports.items():
            try:
                __import__(module)
                results[module] = {"status": "✅", "description": description}
            except ImportError as e:
                results[module] = {"status": "❌", "description": f"{description} - Error: {str(e)}"}
        
        return results
    
    async def check_system_initialization(self) -> dict:
        """Check if core systems can initialize"""
        results = {}
        
        try:
            # Test shared knowledge
            from digital_twin_backend.communication.shared_knowledge import SharedKnowledgeBase
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            results["shared_knowledge"] = {"status": "✅", "description": "Shared knowledge initialization"}
            await shared_knowledge.close()
        except Exception as e:
            results["shared_knowledge"] = {"status": "❌", "description": f"Shared knowledge - Error: {str(e)}"}
        
        try:
            # Test communication protocol
            from digital_twin_backend.communication.shared_knowledge import SharedKnowledgeBase
            from digital_twin_backend.communication.protocol import AgentCommunicationProtocol
            
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            
            protocol = AgentCommunicationProtocol(shared_knowledge)
            await protocol.initialize()
            results["communication"] = {"status": "✅", "description": "Communication protocol initialization"}
            
            await protocol.shutdown()
            await shared_knowledge.close()
        except Exception as e:
            results["communication"] = {"status": "❌", "description": f"Communication protocol - Error: {str(e)}"}
        
        return results
    
    async def run_complete_check(self):
        """Run complete system health check"""
        
        print("🔍 Digital Twin Backend - System Health Check")
        print("=" * 50)
        
        # Python version
        print("\n📋 Python Version:")
        python_ok = self.check_python_version()
        
        # Core dependencies
        print("\n📋 Core Dependencies:")
        core_results = self.check_core_dependencies()
        for dep, result in core_results.items():
            print(f"  {result['status']} {dep}: {result['description']}")
        
        # Optional dependencies
        print("\n📋 Optional Dependencies:")
        optional_results = self.check_optional_dependencies()
        for dep, result in optional_results.items():
            print(f"  {result['status']} {dep}: {result['description']}")
        
        # Configuration files
        print("\n📋 Configuration Files:")
        config_results = self.check_configuration_files()
        for filename, result in config_results.items():
            size_info = f" ({result['size']} bytes)" if result.get('size') else ""
            print(f"  {result['status']} {filename}: {result['description']}{size_info}")
        
        # Core imports
        print("\n📋 Core System Imports:")
        import_results = await self.check_core_imports()
        for module, result in import_results.items():
            print(f"  {result['status']} {module}: {result['description']}")
        
        # System initialization
        print("\n📋 System Initialization:")
        init_results = await self.check_system_initialization()
        for system, result in init_results.items():
            print(f"  {result['status']} {system}: {result['description']}")
        
        # Summary
        print("\n" + "=" * 50)
        print("🎯 SYSTEM HEALTH SUMMARY")
        print("=" * 50)
        
        # Count successes
        all_results = {**core_results, **import_results, **init_results}
        total_checks = len(all_results)
        passed_checks = len([r for r in all_results.values() if r["status"] == "✅"])
        
        print(f"📊 Core System: {passed_checks}/{total_checks} checks passed")
        
        # Check optional dependencies
        optional_total = len(optional_results)
        optional_passed = len([r for r in optional_results.values() if r["status"] == "✅"])
        print(f"📦 Optional Dependencies: {optional_passed}/{optional_total} available")
        
        # Configuration status
        config_total = len(config_results) 
        config_passed = len([r for r in config_results.values() if r["status"] == "✅"])
        print(f"⚙️  Configuration: {config_passed}/{config_total} files present")
        
        # Overall assessment
        if passed_checks == total_checks and config_passed == config_total:
            print("\n🎉 SYSTEM READY! All core components working.")
            
            if optional_passed < optional_total:
                print(f"💡 Install remaining dependencies: pip install -r requirements.txt")
            
            print("🚀 Next steps:")
            print("   1. Configure agent_training_config.json with your team")
            print("   2. Run: python deploy_agents.py run")
            
        elif passed_checks == total_checks:
            print("\n⚠️  SYSTEM PARTIALLY READY - Missing configuration files")
            print("🔧 Fix configuration issues above, then re-run this check")
            
        else:
            print("\n❌ SYSTEM NOT READY - Core component failures")
            print("🔧 Fix the errors above before proceeding")
            
        return {
            "python_version": python_ok,
            "core_system": f"{passed_checks}/{total_checks}",
            "optional_deps": f"{optional_passed}/{optional_total}",
            "configuration": f"{config_passed}/{config_total}",
            "overall_status": "ready" if (passed_checks == total_checks and config_passed == config_total) else "needs_work"
        }


async def main():
    """Main health check function"""
    checker = SystemHealthChecker()
    await checker.run_complete_check()


if __name__ == "__main__":
    asyncio.run(main())
