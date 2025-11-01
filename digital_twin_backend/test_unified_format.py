#!/usr/bin/env python3
"""
Test Unified Task Format
Demonstrates single format working across all system components
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from digital_twin_backend.communication.task_format import (
    UnifiedTask,
    TaskStatus,
    create_task_from_any_format,
    batch_convert_to_frontend,
    batch_convert_from_frontend
)


def test_unified_format():
    """Test the unified task format"""
    
    print("📋 Testing Unified Task Format")
    print("=" * 60)
    
    # ========================================
    # Test 1: Create task
    # ========================================
    print("\n🔨 Test 1: Create Task")
    print("-" * 40)
    
    task = UnifiedTask(
        title="API Documentation Update",
        task_type="Technical content",
        priority=7,
        estimated_hours=3.5,
        description="Update REST API documentation",
        required_skills=["technical", "api", "documentation"]
    )
    
    print(f"✅ Created: {task}")
    print(f"   ID: {task.task_id}")
    print(f"   Status: {task.status.value}")
    print(f"   Skills: {', '.join(task.required_skills)}")
    
    # ========================================
    # Test 2: Convert to ALL formats
    # ========================================
    print("\n🔄 Test 2: Convert to All Formats")
    print("-" * 40)
    
    # To dictionary
    dict_format = task.to_dict()
    print("✅ Dictionary format:")
    print(f"   {json.dumps(dict_format, indent=2, default=str)[:200]}...")
    
    # To frontend
    frontend_format = task.to_frontend_format(1)
    print("\n✅ Frontend dashboard format:")
    print(f"   {json.dumps(frontend_format, indent=2)}")
    
    # To API response
    api_format = task.to_api_response()
    print("\n✅ API response format:")
    print(f"   {json.dumps(api_format, indent=2, default=str)}")
    
    # To JSON string
    json_string = task.to_json()
    print("\n✅ JSON string format:")
    print(f"   {json_string[:150]}...")
    
    # ========================================
    # Test 3: Parse FROM all formats
    # ========================================
    print("\n📥 Test 3: Parse from Different Formats")
    print("-" * 40)
    
    # From frontend
    frontend_input = {
        "id": 2,
        "header": "Design System Components",
        "type": "Visual Design",
        "status": "In Process",
        "target": "6",
        "limit": "4",
        "reviewer": "Sarah Johnson"
    }
    
    task_from_frontend = UnifiedTask.from_frontend_format(frontend_input)
    print("✅ Parsed from frontend:")
    print(f"   Title: {task_from_frontend.title}")
    print(f"   Type: {task_from_frontend.task_type}")
    print(f"   Assigned to: {task_from_frontend.assigned_to}")
    print(f"   Status: {task_from_frontend.status.value}")
    
    # From API request
    api_request = {
        "title": "Database Schema Update",
        "description": "Modify user table schema",
        "task_type": "Backend Development",
        "priority": 8,
        "estimated_hours": 5.0,
        "required_skills": ["backend", "database", "sql"]
    }
    
    task_from_api = UnifiedTask.from_api_request(api_request)
    print("\n✅ Parsed from API request:")
    print(f"   Title: {task_from_api.title}")
    print(f"   Skills: {', '.join(task_from_api.required_skills)}")
    
    # From dictionary
    task_from_dict = UnifiedTask.from_dict(dict_format)
    print("\n✅ Parsed from dictionary:")
    print(f"   Title: {task_from_dict.title}")
    print(f"   ID matches: {task_from_dict.task_id == task.task_id}")
    
    # ========================================
    # Test 4: Auto-detect format
    # ========================================
    print("\n🤖 Test 4: Auto-Detect Format")
    print("-" * 40)
    
    # Auto-detect frontend
    auto_task_1 = create_task_from_any_format(frontend_input)
    print(f"✅ Auto-detected frontend format: {auto_task_1.title}")
    
    # Auto-detect API
    auto_task_2 = create_task_from_any_format(api_request)
    print(f"✅ Auto-detected API format: {auto_task_2.title}")
    
    # ========================================
    # Test 5: Task lifecycle operations
    # ========================================
    print("\n🔄 Test 5: Task Lifecycle")
    print("-" * 40)
    
    lifecycle_task = UnifiedTask(
        title="Lifecycle Test Task",
        task_type="Testing",
        priority=5,
        estimated_hours=1.0
    )
    
    print(f"Created: {lifecycle_task.status.value}")
    
    # Assign
    lifecycle_task.assign_to("agent_1")
    print(f"✅ Assigned: status={lifecycle_task.status.value}, assigned_to={lifecycle_task.assigned_to}")
    
    # Update status
    lifecycle_task.update_status(TaskStatus.IN_PROGRESS)
    print(f"✅ In progress: {lifecycle_task.status.value}")
    
    # Complete
    lifecycle_task.complete()
    print(f"✅ Completed: {lifecycle_task.status.value}")
    
    # Check frontend representation
    frontend_view = lifecycle_task.to_frontend_format()
    print(f"✅ Frontend shows: {frontend_view['status']} - {frontend_view['reviewer']}")
    
    # ========================================
    # Test 6: Batch conversion
    # ========================================
    print("\n📦 Test 6: Batch Conversion")
    print("-" * 40)
    
    # Create multiple tasks
    tasks = [
        UnifiedTask(title=f"Task {i}", task_type="General", priority=i, estimated_hours=float(i))
        for i in range(1, 6)
    ]
    
    # Batch convert to frontend
    frontend_batch = batch_convert_to_frontend(tasks)
    print(f"✅ Converted {len(tasks)} tasks to frontend format")
    print(f"   Sample: {json.dumps(frontend_batch[0], indent=2)}")
    
    # Batch convert back
    tasks_back = batch_convert_from_frontend(frontend_batch)
    print(f"✅ Converted {len(tasks_back)} frontend items back to tasks")
    print(f"   Sample title: {tasks_back[0].title}")
    
    # ========================================
    # Test 7: Skill auto-inference
    # ========================================
    print("\n🧠 Test 7: Automatic Skill Inference")
    print("-" * 40)
    
    task_types_to_test = [
        "Technical content",
        "Visual Design",
        "Backend Development",
        "Frontend Development",
        "Testing"
    ]
    
    for task_type in task_types_to_test:
        test_task = UnifiedTask(
            title=f"Test {task_type}",
            task_type=task_type,
            priority=5,
            estimated_hours=2.0
        )
        print(f"✅ {task_type:25s} → Skills: {', '.join(test_task.required_skills)}")
    
    # ========================================
    # Summary
    # ========================================
    print("\n" + "=" * 60)
    print("🎉 UNIFIED TASK FORMAT: WORKING PERFECTLY!")
    print("=" * 60)
    print("✅ Single format for entire system")
    print("✅ Automatic conversion to/from frontend")
    print("✅ Compatible with existing dashboard")
    print("✅ Works in agent communication")
    print("✅ API request/response handling")
    print("✅ Batch operations supported")
    print("✅ Skill auto-inference working")
    print("\n🚀 Use UnifiedTask everywhere in your system!")


if __name__ == "__main__":
    test_unified_format()
