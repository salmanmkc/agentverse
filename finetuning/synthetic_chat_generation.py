#!/usr/bin/env python3
"""
Synthetic Chat Generation Script
Generates synthetic workplace chat conversations using LLM API
Based on CV and LinkedIn profile to emulate Ryan Lin's communication style
"""
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from the script's directory or current working directory
    script_dir = Path(__file__).parent
    env_path = script_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from {env_path}")
    else:
        # Fallback to current directory
        load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Continuing without .env file support...")
except Exception as e:
    print(f"⚠️  Warning loading .env: {e}")
    print("   Continuing without .env file...")

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("⚠️  Installing openai package...")
    print("Run: pip install openai")
    raise


class SyntheticChatGenerator:
    """Generate synthetic workplace chat conversations"""
    
    def __init__(
        self,
        cv_path: Optional[str] = None,
        linkedin_info: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        output_dir: str = "data/synthetic"
    ):
        """
        Initialize synthetic chat generator
        
        Args:
            cv_path: Path to CV/resume text file
            linkedin_info: LinkedIn profile information (text)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: LLM model to use
            output_dir: Directory to save generated chats
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load CV
        self.cv_content = ""
        if cv_path:
            cv_file = Path(cv_path)
            if cv_file.exists():
                with open(cv_file, 'r', encoding='utf-8') as f:
                    self.cv_content = f.read()
        
        # LinkedIn info
        self.linkedin_info = linkedin_info or ""
        
        # Initialize OpenAI client
        api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def _load_persona_context(self) -> str:
        """Build persona context from CV and LinkedIn"""
        context_parts = []
        
        if self.cv_content:
            context_parts.append("=== CV/RESUME ===\n" + self.cv_content)
        
        if self.linkedin_info:
            context_parts.append("=== LINKEDIN PROFILE ===\n" + self.linkedin_info)
        
        return "\n\n".join(context_parts)
    
    def generate_conversation(
        self,
        scenario: str,
        conversation_type: str = "workplace",
        num_exchanges: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a single synthetic conversation
        
        Args:
            scenario: Description of the conversation scenario
            conversation_type: Type of conversation (workplace, email, meeting, etc.)
            num_exchanges: Number of message exchanges
        """
        persona_context = self._load_persona_context()
        
        system_prompt = f"""You are generating synthetic workplace chat conversations where the assistant responds as Ryan Lin.

Based on this context about Ryan Lin:
{persona_context}

Generate a realistic workplace conversation where:
1. The USER sends a message/task/question
2. Ryan Lin (ASSISTANT) responds in his natural communication style
3. The conversation should feel authentic and match Ryan's professional tone, expertise, and communication patterns
4. Include workplace-appropriate language, technical depth when relevant, and typical professional interactions

Scenario: {scenario}
Conversation type: {conversation_type}
Number of exchanges: {num_exchanges}

Generate the conversation in JSON format:
{{
    "scenario": "...",
    "exchanges": [
        {{"role": "USER", "content": "..."}},
        {{"role": "ASSISTANT", "content": "..."}}
    ]
}}

Each exchange should be natural and realistic."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate a {conversation_type} conversation with {num_exchanges} exchanges about: {scenario}"}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                conversation = json.loads(json_match.group())
            else:
                # Fallback: parse manually
                conversation = self._parse_conversation_fallback(content, scenario)
            
            return conversation
            
        except Exception as e:
            print(f"⚠️  Error generating conversation: {e}")
            return {"scenario": scenario, "exchanges": []}
    
    def _parse_conversation_fallback(self, content: str, scenario: str) -> Dict[str, Any]:
        """Fallback parser if JSON extraction fails"""
        exchanges = []
        
        # Try to extract USER and ASSISTANT messages
        user_pattern = r'USER[:\s]+(.+?)(?=ASSISTANT|$)'
        assistant_pattern = r'ASSISTANT[:\s]+(.+?)(?=USER|$)'
        
        user_messages = re.findall(user_pattern, content, re.DOTALL | re.IGNORECASE)
        assistant_messages = re.findall(assistant_pattern, content, re.DOTALL | re.IGNORECASE)
        
        # Pair them up
        max_len = max(len(user_messages), len(assistant_messages))
        for i in range(max_len):
            if i < len(user_messages):
                exchanges.append({
                    "role": "USER",
                    "content": user_messages[i].strip()
                })
            if i < len(assistant_messages):
                exchanges.append({
                    "role": "ASSISTANT",
                    "content": assistant_messages[i].strip()
                })
        
        return {
            "scenario": scenario,
            "exchanges": exchanges
        }
    
    def generate_scenarios(self) -> List[str]:
        """Generate list of workplace scenarios"""
        return [
            "Requesting status update on Q3 metrics dashboard",
            "Asking for code review feedback on ML model implementation",
            "Scheduling a meeting to discuss project timeline",
            "Requesting clarification on API endpoint specifications",
            "Sharing findings from research on transformer architectures",
            "Responding to question about deployment strategy",
            "Negotiating deadline extension for feature delivery",
            "Providing update on bug fix progress",
            "Asking for approval on architecture design decision",
            "Responding to urgent request for data analysis",
            "Discussing team member performance feedback",
            "Coordinating with team on conference presentation",
            "Responding to technical question about PyTorch implementation",
            "Requesting resources for upcoming project",
            "Providing feedback on colleague's proposal",
            "Explaining quantum computing concept to team member",
            "Responding to request for documentation",
            "Coordinating sprint planning meeting",
            "Providing technical guidance on model optimization",
            "Responding to inquiry about hackathon project"
        ]
    
    def generate_conversations(
        self,
        num_conversations: int = 50,
        conversations_per_scenario: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple synthetic conversations
        
        Args:
            num_conversations: Total number of conversations to generate
            conversations_per_scenario: Number of conversations per scenario
        """
        scenarios = self.generate_scenarios()
        conversations = []
        
        print(f"🎭 Generating {num_conversations} synthetic conversations...")
        
        for i in range(num_conversations):
            scenario_idx = i // conversations_per_scenario
            if scenario_idx >= len(scenarios):
                scenario_idx = i % len(scenarios)
            
            scenario = scenarios[scenario_idx]
            
            # Vary conversation types
            conversation_types = ["workplace", "email", "slack", "meeting", "technical_discussion"]
            conv_type = conversation_types[i % len(conversation_types)]
            
            # Vary exchange count
            num_exchanges = 3 + (i % 5)  # 3-7 exchanges
            
            print(f"⏳ Generating conversation {i+1}/{num_conversations}: {scenario[:50]}...")
            
            conversation = self.generate_conversation(
                scenario=scenario,
                conversation_type=conv_type,
                num_exchanges=num_exchanges
            )
            
            if conversation.get('exchanges'):
                conversation['generated_at'] = datetime.now().isoformat()
                conversation['conversation_type'] = conv_type
                conversations.append(conversation)
            
            # Rate limiting - be nice to API
            import time
            time.sleep(1)
        
        print(f"✅ Generated {len(conversations)} conversations")
        return conversations
    
    def save_conversations(
        self,
        conversations: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> str:
        """Save generated conversations to JSON"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"synthetic_chats_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        output = {
            'generated_at': datetime.now().isoformat(),
            'total_conversations': len(conversations),
            'conversations': conversations
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(conversations)} conversations to {filepath}")
        return str(filepath)


def main():
    """Main generation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate synthetic chat conversations')
    parser.add_argument(
        '--cv-path',
        type=str,
        default='cvryanlin.txt',
        help='Path to CV/resume file'
    )
    parser.add_argument(
        '--linkedin-info',
        type=str,
        help='LinkedIn profile information (text or path to file)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4',
        help='LLM model to use'
    )
    parser.add_argument(
        '--num-conversations',
        type=int,
        default=50,
        help='Number of conversations to generate'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/synthetic',
        help='Output directory'
    )
    
    args = parser.parse_args()
    
    # Load LinkedIn info if provided as file path
    linkedin_info = args.linkedin_info
    if linkedin_info and Path(linkedin_info).exists():
        with open(linkedin_info, 'r', encoding='utf-8') as f:
            linkedin_info = f.read()
    
    # Create generator
    generator = SyntheticChatGenerator(
        cv_path=args.cv_path,
        linkedin_info=linkedin_info,
        api_key=args.api_key,
        model=args.model,
        output_dir=args.output_dir
    )
    
    # Generate conversations
    conversations = generator.generate_conversations(
        num_conversations=args.num_conversations
    )
    
    # Save results
    if conversations:
        generator.save_conversations(conversations)
        print("\n✅ Synthetic chat generation complete!")
        print(f"📊 Generated {len(conversations)} conversations")
    else:
        print("⚠️  No conversations generated")


if __name__ == '__main__':
    main()

