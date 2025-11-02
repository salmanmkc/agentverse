#!/usr/bin/env python3
"""
Test Fine-Tuned OpenAI Model
Tests the fine-tuned assistant model with various prompts
"""
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI package not installed. Run: pip install openai")
    sys.exit(1)

# Load environment variables
load_dotenv()

class FineTunedModelTester:
    """Test fine-tuned OpenAI assistant model"""
    
    def __init__(self, assistant_id: str):
        """
        Initialize tester
        
        Args:
            assistant_id: OpenAI assistant ID (starts with 'asst_')
        """
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        
    def _get_assistant_model(self) -> str:
        """
        Get the model from the assistant configuration
        
        Returns:
            Model ID (fine-tuned model or base model)
        """
        try:
            # Try to retrieve assistant to get its model
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            return assistant.model
        except Exception as e:
            # If assistant retrieval fails, assume assistant_id is actually a model ID
            # Check if it looks like a fine-tuned model ID
            if self.assistant_id.startswith('ft:'):
                return self.assistant_id
            # Otherwise, try using it as a model name
            return self.assistant_id
    
    def test_single_prompt(
        self,
        user_message: str,
        system_message: str = "You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context.",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Test model with a single prompt using Chat Completions API
        
        Args:
            user_message: User prompt to test
            system_message: System message context
            conversation_history: Optional conversation history for context
            
        Returns:
            Dict with response and metadata
        """
        try:
            # Get the model ID (either from assistant or use directly)
            try:
                model = self._get_assistant_model()
            except:
                # If we can't get model from assistant, try using Chat Completions directly
                # For fine-tuned models, the ID format is like: ft:gpt-4o-mini-2024-08-06:org:model-id
                # For assistants, we need to retrieve the model
                # For now, try using the assistant_id as model (in case it's actually a model ID)
                model = self.assistant_id
            
            # Build messages list
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call Chat Completions API
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract response
            assistant_response = response.choices[0].message.content
            
            return {
                'success': True,
                'user_message': user_message,
                'assistant_response': assistant_response,
                'model': model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            # Try alternative: use Assistants API if Chat Completions doesn't work
            if "model" in error_msg.lower() or "invalid" in error_msg.lower():
                try:
                    return self._test_with_assistants_api(user_message, system_message)
                except Exception as e2:
                    return {
                        'success': False,
                        'error': f"Chat Completions error: {error_msg}. Assistants API error: {str(e2)}"
                    }
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def _test_with_assistants_api(
        self,
        user_message: str,
        system_message: str
    ) -> Dict[str, Any]:
        """Fallback: Test using Assistants API (deprecated but might still work)"""
        try:
            # Create thread
            thread = self.client.beta.threads.create()
            thread_id = thread.id
            
            # Add user message to thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            # Wait for completion
            import time
            max_wait = 30
            waited = 0
            while run.status in ['queued', 'in_progress']:
                if waited >= max_wait:
                    return {
                        'success': False,
                        'error': f"Run timed out after {max_wait} seconds. Status: {run.status}"
                    }
                time.sleep(1)
                waited += 1
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
            
            if run.status != 'completed':
                error_details = getattr(run, 'last_error', None)
                error_msg = f"Run failed with status: {run.status}"
                if error_details:
                    error_msg += f". Error: {error_details}"
                return {
                    'success': False,
                    'error': error_msg,
                    'thread_id': thread_id
                }
            
            # Retrieve messages
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order='asc'
            )
            
            # Get assistant's response
            assistant_messages = [
                msg for msg in messages.data 
                if msg.role == 'assistant'
            ]
            
            if not assistant_messages:
                return {
                    'success': False,
                    'error': "No assistant response found",
                    'thread_id': thread_id
                }
            
            latest_response = assistant_messages[-1]
            response_text = latest_response.content[0].text.value
            
            return {
                'success': True,
                'user_message': user_message,
                'assistant_response': response_text,
                'thread_id': thread_id,
                'run_id': run.id,
                'method': 'assistants_api'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Assistants API error: {str(e)}"
            }
    
    def test_from_file(self, prompts_file: str = "evaluation_prompts.json") -> List[Dict[str, Any]]:
        """
        Test model with prompts from evaluation file
        
        Args:
            prompts_file: Path to JSON file with evaluation prompts
            
        Returns:
            List of test results
        """
        prompts_path = Path(prompts_file)
        if not prompts_path.exists():
            print(f"⚠️  Evaluation prompts file not found: {prompts_file}")
            return []
        
        with open(prompts_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both dict format {"prompts": [...]} and list format [...]
        if isinstance(data, dict):
            prompts = data.get('prompts', [])
        elif isinstance(data, list):
            prompts = data
        else:
            prompts = []
        
        print(f"🧪 Testing with {len(prompts)} evaluation prompts...")
        print("="*70)
        
        results = []
        conversation_history = []  # Maintain conversation history for context
        
        for i, prompt in enumerate(prompts, 1):
            if isinstance(prompt, dict):
                user_msg = prompt.get('prompt', prompt.get('user', prompt.get('message', '')))
                scenario = prompt.get('scenario', prompt.get('category', 'General'))
            else:
                user_msg = str(prompt)
                scenario = 'General'
            
            if not user_msg:
                continue
            
            print(f"\n[{i}/{len(prompts)}] Testing: {scenario}")
            print(f"Prompt: {user_msg[:100]}...")
            
            result = self.test_single_prompt(user_msg, conversation_history=conversation_history)
            
            if result['success']:
                # Update conversation history
                conversation_history.append({"role": "user", "content": user_msg})
                conversation_history.append({"role": "assistant", "content": result['assistant_response']})
                # Keep only last 10 exchanges to avoid context getting too long
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                
                print(f"✅ Response: {result['assistant_response'][:150]}...")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
            results.append({
                'prompt': user_msg,
                'scenario': scenario,
                **result
            })
            
            # Small delay between requests
            import time
            time.sleep(1)
        
        return results
    
    def test_custom_prompts(self, prompts: List[str]) -> List[Dict[str, Any]]:
        """
        Test model with custom prompts
        
        Args:
            prompts: List of user prompts to test
            
        Returns:
            List of test results
        """
        print(f"🧪 Testing with {len(prompts)} custom prompts...")
        print("="*70)
        
        results = []
        conversation_history = []
        
        for i, prompt in enumerate(prompts, 1):
            print(f"\n[{i}/{len(prompts)}] Prompt: {prompt[:100]}...")
            
            result = self.test_single_prompt(prompt, conversation_history=conversation_history)
            
            if result['success']:
                # Update conversation history
                conversation_history.append({"role": "user", "content": prompt})
                conversation_history.append({"role": "assistant", "content": result['assistant_response']})
                # Keep only last 10 exchanges
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                
                print(f"✅ Response: {result['assistant_response'][:150]}...")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
            
            results.append(result)
            
            import time
            time.sleep(1)
        
        return results
    
    def print_results_summary(self, results: List[Dict[str, Any]]):
        """Print summary of test results"""
        print("\n" + "="*70)
        print("📊 TEST RESULTS SUMMARY")
        print("="*70)
        
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        
        print(f"✅ Successful: {len(successful)}/{len(results)}")
        print(f"❌ Failed: {len(failed)}/{len(results)}")
        
        if failed:
            print("\n❌ Failed Tests:")
            for i, result in enumerate(failed, 1):
                print(f"  {i}. {result.get('error', 'Unknown error')}")
        
        print("\n✅ Successful Responses (sample):")
        for i, result in enumerate(successful[:5], 1):
            print(f"\n  {i}. Prompt: {result.get('user_message', result.get('prompt', ''))[:80]}...")
            print(f"     Response: {result.get('assistant_response', '')[:120]}...")
        
        # Save detailed results
        output_file = Path("test_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {output_file}")


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test fine-tuned OpenAI assistant model')
    parser.add_argument(
        '--assistant-id',
        type=str,
        default='asst_Z0iNwOpGtqooVPFMutWfz15G',
        help='OpenAI assistant ID (default: asst_Z0iNwOpGtqooVPFMutWfz15G)'
    )
    parser.add_argument(
        '--prompts-file',
        type=str,
        default='evaluation_prompts.json',
        help='Path to evaluation prompts JSON file'
    )
    parser.add_argument(
        '--custom-prompt',
        type=str,
        action='append',
        help='Custom prompt to test (can be used multiple times)'
    )
    parser.add_argument(
        '--quick-test',
        action='store_true',
        help='Run quick test with a few sample prompts'
    )
    
    args = parser.parse_args()
    
    # Initialize tester
    try:
        tester = FineTunedModelTester(args.assistant_id)
        print(f"✅ Initialized tester for assistant: {args.assistant_id}")
    except Exception as e:
        print(f"❌ Failed to initialize tester: {e}")
        sys.exit(1)
    
    results = []
    
    # Quick test with sample prompts
    if args.quick_test:
        print("\n🚀 Running quick test...")
        sample_prompts = [
            "Hi Ryan, can you help me with the quarterly report?",
            "I noticed an issue with the data analysis. Can you review it?",
            "What's your availability for a meeting next week?"
        ]
        results.extend(tester.test_custom_prompts(sample_prompts))
    
    # Custom prompts
    if args.custom_prompt:
        results.extend(tester.test_custom_prompts(args.custom_prompt))
    
    # Evaluation prompts file
    if not args.quick_test and not args.custom_prompt:
        results.extend(tester.test_from_file(args.prompts_file))
    
    # Print summary
    if results:
        tester.print_results_summary(results)
    else:
        print("⚠️  No tests were run. Use --quick-test, --custom-prompt, or provide --prompts-file")


if __name__ == '__main__':
    main()

