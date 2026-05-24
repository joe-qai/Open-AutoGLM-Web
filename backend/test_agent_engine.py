#!/usr/bin/env python3
"""Test script to verify AgentEngine functionality."""

import sys
import os

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Add project root
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    try:
        from app.core.agent.engine import AgentEngine, ExecutionStep
        from app.core.layers.decision import DecisionLayer, DecisionMode, ActionPlan
        from app.core.layers.action import ActionLayer
        from app.core.layers.perception import PerceptionLayer
        from app.core.adapters.base import Platform
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_decision_layer():
    """Test DecisionLayer initialization."""
    print("\nTesting DecisionLayer...")
    try:
        from app.core.layers.decision import DecisionLayer, DecisionMode
        
        # Create with LLM mode (default)
        layer = DecisionLayer(mode=DecisionMode.LLM)
        print(f"✓ DecisionLayer created with mode: {layer.mode}")
        
        # Test modes
        assert layer.SYSTEM_PROMPT_LLM is not None
        assert layer.SYSTEM_PROMPT_VLM is not None
        print("✓ Both system prompts available")
        
        # Test _format_ui_elements
        test_elements = [
            {"text": "Button 1", "resource_id": "btn1", "clickable": True, "bbox_normalized": {"x": 100, "y": 200, "w": 200, "h": 50}},
            {"text": "Input", "resource_id": "input1", "clickable": True, "bbox_normalized": {"x": 100, "y": 300, "w": 300, "h": 60}},
        ]
        formatted = layer._format_ui_elements(test_elements)
        print(f"✓ UI elements formatting works: {len(formatted)} chars")
        
        return True
    except Exception as e:
        print(f"✗ DecisionLayer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_engine():
    """Test AgentEngine initialization (without real device)."""
    print("\nTesting AgentEngine initialization...")
    try:
        from app.core.agent.engine import AgentEngine
        from app.core.layers.decision import DecisionMode
        
        engine = AgentEngine(mode=DecisionMode.LLM)
        print(f"✓ AgentEngine initialized in {DecisionMode.LLM} mode")
        print(f"  - DecisionLayer available: {engine.decision is not None}")
        print(f"  - MemoryLayer available: {engine.memory is not None}")
        print(f"  - ReplayLayer available: {engine.replay is not None}")
        
        return True
    except Exception as e:
        print(f"✗ AgentEngine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_action_plan():
    """Test ActionPlan."""
    print("\nTesting ActionPlan...")
    try:
        from app.core.layers.decision import ActionPlan
        
        plan = ActionPlan(
            action="tap_element",
            target="login-button",
            parameters={"element_index": 0},
            confidence=0.95,
            reasoning="Tap the login button at index 0"
        )
        
        assert plan.action == "tap_element"
        assert plan.parameters.get("element_index") == 0
        assert plan.confidence == 0.95
        print("✓ ActionPlan works correctly")
        
        return True
    except Exception as e:
        print(f"✗ ActionPlan test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_decision_mode_enum():
    """Test DecisionMode enum."""
    print("\nTesting DecisionMode enum...")
    try:
        from app.core.layers.decision import DecisionMode
        
        # Test values
        assert DecisionMode.LLM == "llm"
        assert DecisionMode.VLM == "vlm"
        assert DecisionMode.AUTO == "auto"
        
        # Test from string
        mode_llm = DecisionMode("llm")
        mode_vlm = DecisionMode("vlm")
        assert mode_llm == DecisionMode.LLM
        assert mode_vlm == DecisionMode.VLM
        
        print("✓ DecisionMode enum works correctly")
        return True
    except Exception as e:
        print(f"✗ DecisionMode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Open-AutoGLM AgentEngine Components")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("DecisionMode Enum", test_decision_mode_enum()))
    results.append(("ActionPlan", test_action_plan()))
    results.append(("DecisionLayer", test_decision_layer()))
    results.append(("AgentEngine", test_agent_engine()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:25s}: {status}")
    
    all_passed = all(result for _, result in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
