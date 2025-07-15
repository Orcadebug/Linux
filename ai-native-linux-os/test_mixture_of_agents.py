#!/usr/bin/env python3
"""
Test Script for AI-Native Linux OS - Mixture of Agents System
Tests all specialized agents with tiny LLMs and dormant behavior
"""

import asyncio
import sys
import os
import time
import json
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from ai_orchestrator.main_ai_controller import MainAIController
    CONTROLLER_AVAILABLE = True
except ImportError as e:
    print(f"❌ Could not import MainAIController: {e}")
    CONTROLLER_AVAILABLE = False

class MixtureOfAgentsTest:
    def __init__(self):
        self.controller = None
        self.test_results = []
        
    def log_test(self, test_name, success, message="", details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": time.time()
        })
    
    async def test_controller_initialization(self):
        """Test main controller initialization"""
        print("\n🔧 Testing Controller Initialization...")
        
        try:
            if not CONTROLLER_AVAILABLE:
                self.log_test("Controller Import", False, "MainAIController not available")
                return False
            
            self.controller = MainAIController()
            self.log_test("Controller Creation", True, "MainAIController created successfully")
            
            # Test welcome message
            welcome = self.controller.get_welcome_message()
            self.log_test("Welcome Message", len(welcome) > 0, f"Welcome message length: {len(welcome)}")
            
            # Test agent registry
            registry_count = len(self.controller.agent_registry)
            self.log_test("Agent Registry", registry_count >= 5, f"Found {registry_count} agents in registry")
            
            return True
            
        except Exception as e:
            self.log_test("Controller Initialization", False, f"Exception: {str(e)}")
            return False
    
    async def test_agent_status(self):
        """Test agent status monitoring"""
        print("\n📊 Testing Agent Status...")
        
        try:
            status = self.controller.get_agent_status()
            
            # Check status structure
            required_keys = ['loaded_agents', 'dormant_agents', 'total_agents', 'memory_usage']
            for key in required_keys:
                self.log_test(f"Status Key: {key}", key in status, f"Key present: {key in status}")
            
            # Initially all agents should be dormant
            self.log_test("Initial Dormant State", len(status['loaded_agents']) == 0, 
                         f"Loaded: {len(status['loaded_agents'])}, Dormant: {len(status['dormant_agents'])}")
            
            return True
            
        except Exception as e:
            self.log_test("Agent Status", False, f"Exception: {str(e)}")
            return False
    
    async def test_agent_loading(self):
        """Test lazy loading of agents"""
        print("\n🔄 Testing Agent Lazy Loading...")
        
        test_queries = [
            ("system_management", "install docker"),
            ("file_storage", "organize my files"),
            ("media", "play music"),
            ("communication", "check my email"),
            ("personal_assistant", "set a reminder"),
            ("troubleshooting", "fix network issues"),
            ("shell", "run ls command"),
            ("activity", "show my usage patterns")
        ]
        
        for expected_agent, query in test_queries:
            try:
                print(f"  Testing query: '{query}'")
                
                # Get initial status
                initial_status = self.controller.get_agent_status()
                initial_loaded = len(initial_status['loaded_agents'])
                
                # Process query (should trigger agent loading)
                response = await self.controller.classify_and_route(query)
                
                # Check if agent was loaded
                final_status = self.controller.get_agent_status()
                final_loaded = len(final_status['loaded_agents'])
                
                agent_loaded = final_loaded > initial_loaded
                response_received = len(response) > 0
                
                self.log_test(f"Agent Loading: {expected_agent}", agent_loaded, 
                             f"Loaded agents: {initial_loaded} -> {final_loaded}")
                self.log_test(f"Response: {expected_agent}", response_received, 
                             f"Response length: {len(response)}")
                
                # Small delay between tests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.log_test(f"Agent Loading: {expected_agent}", False, f"Exception: {str(e)}")
    
    async def test_multi_agent_queries(self):
        """Test queries that should trigger multiple agents"""
        print("\n🔀 Testing Multi-Agent Queries...")
        
        multi_agent_queries = [
            "organize my files and set a reminder",
            "install docker and play music",
            "check system info and send an email",
            "cleanup files and update the system"
        ]
        
        for query in multi_agent_queries:
            try:
                print(f"  Testing multi-agent query: '{query}'")
                
                initial_status = self.controller.get_agent_status()
                initial_loaded = len(initial_status['loaded_agents'])
                
                response = await self.controller.classify_and_route(query)
                
                final_status = self.controller.get_agent_status()
                final_loaded = len(final_status['loaded_agents'])
                
                # Should load multiple agents
                multiple_agents = final_loaded > initial_loaded
                response_sections = response.count('[') >= 2  # Multiple agent responses
                
                self.log_test(f"Multi-Agent: {query[:30]}...", multiple_agents, 
                             f"Agents loaded: {initial_loaded} -> {final_loaded}")
                self.log_test(f"Multi-Response: {query[:30]}...", response_sections, 
                             f"Response sections: {response.count('[')}")
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.log_test(f"Multi-Agent Query", False, f"Exception: {str(e)}")
    
    async def test_agent_unloading(self):
        """Test agent unloading functionality"""
        print("\n🗑️ Testing Agent Unloading...")
        
        try:
            # Load some agents first
            await self.controller.classify_and_route("install docker")
            await self.controller.classify_and_route("organize files")
            
            status_before = self.controller.get_agent_status()
            loaded_before = len(status_before['loaded_agents'])
            
            # Unload all agents
            await self.controller.unload_all_agents()
            
            status_after = self.controller.get_agent_status()
            loaded_after = len(status_after['loaded_agents'])
            
            self.log_test("Agent Unloading", loaded_after == 0, 
                         f"Loaded agents: {loaded_before} -> {loaded_after}")
            
            return True
            
        except Exception as e:
            self.log_test("Agent Unloading", False, f"Exception: {str(e)}")
            return False
    
    async def test_fallback_classification(self):
        """Test fallback classification without LLM"""
        print("\n🔄 Testing Fallback Classification...")
        
        # Test the fallback classify method directly
        test_cases = [
            ("install docker", "system_management"),
            ("organize my files", "file_storage"),
            ("play music", "media"),
            ("send email", "communication"),
            ("set reminder", "personal_assistant"),
            ("fix error", "troubleshooting"),
            ("run command", "shell"),
            ("show usage", "activity")
        ]
        
        for query, expected_category in test_cases:
            try:
                result = self.controller._fallback_classify(query)
                success = result == expected_category
                
                self.log_test(f"Fallback: {query}", success, 
                             f"Expected: {expected_category}, Got: {result}")
                
            except Exception as e:
                self.log_test(f"Fallback: {query}", False, f"Exception: {str(e)}")
    
    async def test_chat_history(self):
        """Test chat history functionality"""
        print("\n💬 Testing Chat History...")
        
        try:
            # Clear history
            self.controller.chat_history.clear()
            
            # Add some queries
            queries = ["hello", "install docker", "organize files"]
            for query in queries:
                await self.controller.classify_and_route(query)
            
            history_length = len(self.controller.chat_history)
            self.log_test("Chat History", history_length > 0, 
                         f"History entries: {history_length}")
            
            # Test history limit (should be 10)
            for i in range(15):
                await self.controller.classify_and_route(f"test query {i}")
            
            final_length = len(self.controller.chat_history)
            self.log_test("History Limit", final_length <= 10, 
                         f"Final history length: {final_length}")
            
            return True
            
        except Exception as e:
            self.log_test("Chat History", False, f"Exception: {str(e)}")
            return False
    
    async def test_error_handling(self):
        """Test error handling"""
        print("\n❌ Testing Error Handling...")
        
        try:
            # Test with invalid agent
            self.controller.agent_registry['invalid_agent'] = 'nonexistent.module'
            
            # This should handle the error gracefully
            response = await self.controller.classify_and_route("test invalid agent")
            
            error_handled = "Error" in response or "not recognized" in response
            self.log_test("Error Handling", error_handled, 
                         f"Error handled gracefully: {error_handled}")
            
            # Clean up
            del self.controller.agent_registry['invalid_agent']
            
            return True
            
        except Exception as e:
            self.log_test("Error Handling", False, f"Exception: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🤖 Starting AI-Native Linux OS - Mixture of Agents Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run tests in sequence
        tests = [
            self.test_controller_initialization,
            self.test_agent_status,
            self.test_fallback_classification,
            self.test_agent_loading,
            self.test_multi_agent_queries,
            self.test_agent_unloading,
            self.test_chat_history,
            self.test_error_handling
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"❌ Test suite error: {e}")
        
        # Generate summary
        self.generate_test_summary(start_time)
    
    def generate_test_summary(self, start_time):
        """Generate test summary"""
        end_time = time.time()
        duration = end_time - start_time
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️ Duration: {duration:.2f} seconds")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
        
        # Save results to file
        self.save_test_results()
        
        print(f"\n📄 Detailed results saved to: test_results.json")
        print("=" * 60)
    
    def save_test_results(self):
        """Save test results to file"""
        try:
            with open('test_results.json', 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'summary': {
                        'total': len(self.test_results),
                        'passed': sum(1 for r in self.test_results if r['success']),
                        'failed': sum(1 for r in self.test_results if not r['success'])
                    },
                    'results': self.test_results
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save test results: {e}")

async def main():
    """Main test runner"""
    test_suite = MixtureOfAgentsTest()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 