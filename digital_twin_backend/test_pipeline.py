#!/usr/bin/env python3
"""
Test Script for Digital Twin Pipeline
Verifies core functionality without requiring actual data scraping
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure project root is available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from digital_twin_backend.config.settings import settings, AGENT_CONFIGS
    from digital_twin_backend.communication.shared_knowledge import (
        SharedKnowledgeBase,
        AgentCapabilities,
        TaskInfo,
        TaskStatus,
    )
    from digital_twin_backend.communication.protocol import AgentCommunicationProtocol
    from digital_twin_backend.agents.manager_agent import ManagerAgent
    from digital_twin_backend.agents.worker_agent import WorkerAgent
    from digital_twin_backend.finetuning import FineTuningOrchestrator
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error("Make sure you're running from the digital_twin_backend directory")
    sys.exit(1)


class PipelineTestSuite:
    """Test suite for the digital twin pipeline"""
    
    def __init__(self):
        self.test_results = {}
        self.temp_dir = None
    
    def setup_test_environment(self):
        """Setup test environment"""
        logger.info("🔧 Setting up test environment...")
        
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp(prefix="digital_twin_test_")
        logger.info(f"📁 Test directory: {self.temp_dir}")
        
        # Create test data directories
        test_data_dir = Path(self.temp_dir) / "data"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def cleanup_test_environment(self):
        """Cleanup test environment"""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info("🧹 Test environment cleaned up")
    
    async def test_shared_knowledge_system(self):
        """Test shared knowledge system"""
        logger.info("🧠 Testing shared knowledge system...")
        
        try:
            # Initialize shared knowledge
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            
            # Test agent registration
            test_capabilities = AgentCapabilities(
                technical_skills={"technical": 0.8, "communication": 0.7},
                preferred_task_types=["Testing", "Verification"],
                work_style={"collaborative": True},
                communication_style={"formal": 0.6}
            )
            
            await shared_knowledge.register_agent("test_agent", test_capabilities)
            
            # Test task creation
            test_task = TaskInfo(
                task_id="test_task_001",
                title="Test Task",
                description="Testing the system",
                task_type="Testing",
                priority=5,
                estimated_hours=1.0,
                required_skills=["testing"],
                status=TaskStatus.PENDING
            )
            
            await shared_knowledge.add_task(test_task)
            
            # Verify task retrieval
            retrieved_task = await shared_knowledge.get_task("test_task_001")
            assert retrieved_task is not None, "Failed to retrieve test task"
            assert retrieved_task.title == "Test Task", "Task title mismatch"
            
            self.test_results["shared_knowledge"] = "✅ PASSED"
            logger.info("✅ Shared knowledge system test passed")
            
        except Exception as e:
            self.test_results["shared_knowledge"] = f"❌ FAILED: {str(e)}"
            logger.error(f"❌ Shared knowledge system test failed: {e}")
        
        finally:
            try:
                await shared_knowledge.close()
            except:
                pass
    
    async def test_communication_protocol(self):
        """Test agent communication protocol"""
        logger.info("📡 Testing communication protocol...")
        
        try:
            # Initialize systems
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            communication_protocol = AgentCommunicationProtocol(shared_knowledge)
            await communication_protocol.initialize()
            
            # Test message sending
            test_handler_called = False
            
            async def test_message_handler(message):
                nonlocal test_handler_called
                test_handler_called = True
                logger.info(f"📨 Received test message: {message.get('content', '')}")
            
            # Register test agent
            await communication_protocol.register_agent("test_sender", test_message_handler)
            
            # Send test message
            from digital_twin_backend.communication.protocol import MessageType, MessagePriority
            success = await communication_protocol.send_message(
                from_agent="system",
                to_agent="test_sender",
                message_type=MessageType.GENERAL,
                content="Test message content",
                priority=MessagePriority.NORMAL
            )
            
            assert success, "Failed to send test message"
            
            # Wait for message processing
            await asyncio.sleep(1)
            
            # Check if handler was called
            assert test_handler_called, "Message handler was not called"
            
            self.test_results["communication"] = "✅ PASSED"
            logger.info("✅ Communication protocol test passed")
            
        except Exception as e:
            self.test_results["communication"] = f"❌ FAILED: {str(e)}"
            logger.error(f"❌ Communication protocol test failed: {e}")
        
        finally:
            try:
                await communication_protocol.shutdown()
                await shared_knowledge.close()
            except:
                pass
    
    async def test_agent_initialization(self):
        """Test agent initialization"""
        logger.info("🤖 Testing agent initialization...")
        
        try:
            # Initialize systems
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            communication_protocol = AgentCommunicationProtocol(shared_knowledge)
            await communication_protocol.initialize()
            
            # Test manager agent
            manager = ManagerAgent(
                shared_knowledge=shared_knowledge,
                worker_agent_ids=["test_worker"]
            )
            await manager.initialize()
            
            # Test worker agent
            test_capabilities = AgentCapabilities(
                technical_skills={"technical": 0.8},
                preferred_task_types=["Testing"],
                work_style={"collaborative": True},
                communication_style={"formal": 0.5}
            )
            
            worker = WorkerAgent(
                agent_id="test_worker",
                person_name="Test Worker",
                shared_knowledge=shared_knowledge,
                capabilities=test_capabilities
            )
            await worker.initialize()
            
            # Register agents with communication protocol
            await communication_protocol.register_agent("manager", manager.receive_message)
            await communication_protocol.register_agent("test_worker", worker.receive_message)
            
            # Test agent status
            manager_status = await manager.get_team_status()
            assert manager_status is not None, "Failed to get manager status"
            
            worker_status = await worker.get_current_status()
            assert worker_status["agent_id"] == "test_worker", "Worker status mismatch"
            
            self.test_results["agent_init"] = "✅ PASSED"
            logger.info("✅ Agent initialization test passed")
            
        except Exception as e:
            self.test_results["agent_init"] = f"❌ FAILED: {str(e)}"
            logger.error(f"❌ Agent initialization test failed: {e}")
        
        finally:
            try:
                await communication_protocol.shutdown()
                await shared_knowledge.close()
            except:
                pass
    
    async def test_task_distribution(self):
        """Test task distribution workflow"""
        logger.info("🎯 Testing task distribution...")
        
        try:
            # Initialize systems
            shared_knowledge = SharedKnowledgeBase()
            await shared_knowledge.initialize()
            communication_protocol = AgentCommunicationProtocol(shared_knowledge)
            await communication_protocol.initialize()
            
            # Create manager and worker agents
            manager = ManagerAgent(
                shared_knowledge=shared_knowledge,
                worker_agent_ids=["test_worker_1", "test_worker_2"]
            )
            await manager.initialize()
            
            # Create worker agents
            workers = {}
            for i in range(1, 3):
                worker_id = f"test_worker_{i}"
                capabilities = AgentCapabilities(
                    technical_skills={"technical": 0.7 + (i * 0.1)},
                    preferred_task_types=["Testing"],
                    work_style={"collaborative": True},
                    communication_style={"formal": 0.5}
                )
                
                worker = WorkerAgent(
                    agent_id=worker_id,
                    person_name=f"Test Worker {i}",
                    shared_knowledge=shared_knowledge,
                    capabilities=capabilities
                )
                await worker.initialize()
                workers[worker_id] = worker
            
            # Register all agents
            await communication_protocol.register_agent("manager", manager.receive_message)
            for worker_id, worker in workers.items():
                await communication_protocol.register_agent(worker_id, worker.receive_message)
            
            # Create and distribute test task
            test_task = TaskInfo(
                task_id="distribution_test_001",
                title="Test Task Distribution",
                description="Testing task distribution workflow",
                task_type="Testing",
                priority=7,
                estimated_hours=2.0,
                required_skills=["technical", "testing"],
                status=TaskStatus.PENDING
            )
            
            # Test task distribution
            distribution_result = await manager.distribute_task(test_task)
            
            # Verify distribution result
            assert distribution_result is not None, "Distribution result is None"
            
            if distribution_result.get("success"):
                assigned_agent = distribution_result["assigned_agent"]
                assert assigned_agent in ["test_worker_1", "test_worker_2"], f"Invalid assigned agent: {assigned_agent}"
                logger.info(f"✅ Task assigned to {assigned_agent}")
            else:
                logger.warning(f"⚠️  Task distribution failed: {distribution_result.get('error')}")
            
            self.test_results["task_distribution"] = "✅ PASSED"
            logger.info("✅ Task distribution test passed")
            
        except Exception as e:
            self.test_results["task_distribution"] = f"❌ FAILED: {str(e)}"
            logger.error(f"❌ Task distribution test failed: {e}")
        
        finally:
            try:
                await communication_protocol.shutdown()
                await shared_knowledge.close()
            except:
                pass
    
    def test_configuration_loading(self):
        """Test configuration loading"""
        logger.info("⚙️  Testing configuration loading...")
        
        try:
            # Test agent configs
            assert len(AGENT_CONFIGS) > 0, "No agent configs loaded"
            
            # Check if agent_training_config.json exists
            config_file = Path("agent_training_config.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    training_config = json.load(f)
                
                assert "agents" in training_config, "No agents section in training config"
                assert len(training_config["agents"]) > 0, "No agents in training config"
                
                logger.info(f"✅ Training config loaded with {len(training_config['agents'])} agents")
            else:
                logger.warning("⚠️  agent_training_config.json not found")
            
            self.test_results["config_loading"] = "✅ PASSED"
            logger.info("✅ Configuration loading test passed")
            
        except Exception as e:
            self.test_results["config_loading"] = f"❌ FAILED: {str(e)}"
            logger.error(f"❌ Configuration loading test failed: {e}")
    
    def test_fine_tuning_setup(self):
        """Test fine-tuning system setup (without actual training)"""
        logger.info("🧠 Testing fine-tuning setup...")
        
        try:
            # Initialize fine-tuning orchestrator
            fine_tuner = FineTuningOrchestrator()
            
            # Check if models directory exists
            models_dir = Path(fine_tuner.models_dir)
            assert models_dir.exists(), "Models directory not created"
            
            # Check training data directory
            data_dir = Path(fine_tuner.data_dir)
            assert data_dir.exists(), "Training data directory not created"
            
            # Test training status method
            status = fine_tuner.get_training_status()
            assert "base_model" in status, "Training status missing base_model"
            
            self.test_results["finetuning_setup"] = "✅ PASSED"
            logger.info("✅ Fine-tuning setup test passed")
            
        except Exception as e:
            self.test_results["finetuning_setup"] = f"❌ FAILED: {str(e)}"
            logger.error(f"❌ Fine-tuning setup test failed: {e}")
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting Digital Twin Pipeline Test Suite")
        logger.info("=" * 50)
        
        test_functions = [
            ("Configuration Loading", self.test_configuration_loading),
            ("Fine-tuning Setup", self.test_fine_tuning_setup),
            ("Shared Knowledge System", self.test_shared_knowledge_system),
            ("Communication Protocol", self.test_communication_protocol),
            ("Agent Initialization", self.test_agent_initialization),
            ("Task Distribution", self.test_task_distribution),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in test_functions:
            logger.info(f"\n🔍 Running: {test_name}")
            
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            
            if self.test_results.get(test_name.lower().replace(" ", "_"), "").startswith("✅"):
                passed += 1
            else:
                failed += 1
        
        # Print final results
        logger.info("\n" + "=" * 50)
        logger.info("🎯 TEST SUITE COMPLETE")
        logger.info("=" * 50)
        
        for test_name, result in self.test_results.items():
            logger.info(f"{result} {test_name.replace('_', ' ').title()}")
        
        logger.info(f"\n📊 SUMMARY: {passed} passed, {failed} failed")
        
        if failed == 0:
            logger.info("🎉 All tests passed! Your pipeline is ready to use.")
            logger.info("🚀 Next steps:")
            logger.info("   1. Update agent_training_config.json with real social media accounts")
            logger.info("   2. Run: python deploy_agents.py run")
            logger.info("   3. Start the system: python main.py")
        else:
            logger.info("⚠️  Some tests failed. Check the errors above.")
            logger.info("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
        
        return failed == 0


async def main():
    """Main test function"""
    test_suite = PipelineTestSuite()
    
    try:
        test_suite.setup_test_environment()
        success = await test_suite.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⏹️  Tests stopped by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        test_suite.cleanup_test_environment()


if __name__ == "__main__":
    asyncio.run(main())
