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
        personality_traits: Optional[str] = None,
        traits_file: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        output_dir: str = "data/synthetic"
    ):
        """
        Initialize synthetic chat generator
        
        Args:
            personality_traits: Personality traits text (formatted)
            traits_file: Path to personality traits JSON file
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: LLM model to use
            output_dir: Directory to save generated chats
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load personality traits
        self.personality_traits = ""
        if traits_file:
            traits_path = Path(traits_file)
            if traits_path.exists():
                import json
                with open(traits_path, 'r', encoding='utf-8') as f:
                    traits_data = json.load(f)
                    # Format traits
                    self.personality_traits = self._format_traits(traits_data)
        
        if personality_traits:
            self.personality_traits = personality_traits
        
        # Initialize OpenAI client
        api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def _format_traits(self, traits: List[Dict[str, str]]) -> str:
        """Format traits list to context string"""
        formatted = "PERSONALITY TRAITS AND COMMUNICATION STYLE:\n\n"
        
        for i, trait in enumerate(traits, 1):
            formatted += f"{i}. {trait.get('trait', 'Unknown')}\n"
            formatted += f"   {trait.get('description', '')}\n"
            if 'workplace_example' in trait:
                formatted += f"   Example: {trait['workplace_example']}\n"
            formatted += "\n"
        
        return formatted
    
    def _load_persona_context(self) -> str:
        """Build persona context from personality traits"""
        return self.personality_traits
    
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

Based on these personality traits and communication style:
{persona_context}

Generate a realistic workplace conversation that captures BOTH positive and negative aspects:
1. Ryan's emotional responses (enthusiasm, concern, confidence, thoughtfulness, but also frustration, impatience, stress)
2. His communication nuances (level of detail, technical depth, formality) - including when he might be too brief, too verbose, or miss social cues
3. Personality traits in action (how he approaches problems, interacts with colleagues) - including flaws, blind spots, and areas where he struggles
4. Authentic emotional tone in workplace situations (stress, excitement, frustration, satisfaction, but also defensiveness, awkwardness, overconfidence)
5. Subtle personality markers (humor, directness, collaboration style) - including when these might be inappropriate or come across poorly

CRITICAL: Be realistic and balanced. Include negative traits and flaws:
- Areas where Ryan might be too perfectionist, impatient, or overly critical
- Moments of social awkwardness, overthinking, or over-explaining
- Times when confidence becomes overconfidence or assertiveness becomes pushiness
- Situations where his strengths become weaknesses (e.g., attention to detail slowing things down, technical focus missing social context)
- Emotional responses that are less than ideal (defensiveness, anxiety, frustration)
- Communication missteps (too formal when casual is needed, too casual when formal is expected, missing cues)
- Work habits that might be problematic (overworking, difficulty delegating, struggle with boundaries)

The USER sends a message/task/question, and Ryan Lin (ASSISTANT) responds authentically based on his personality traits - including both strengths AND weaknesses.

Scenario: {scenario}
Conversation type: {conversation_type}
Number of exchanges: {num_exchanges}

IMPORTANT: 
- Show a REALISTIC, FLAWED human - not a perfect employee
- Include subtle negative traits and communication flaws naturally
- Don't make him toxic, but do show human imperfections
- Balance positive traits with realistic shortcomings
- Show emotions that aren't always professional (frustration, anxiety, impatience)
- Include moments where his communication style might not be ideal

Generate the conversation in JSON format:
{{
    "scenario": "...",
    "exchanges": [
        {{"role": "USER", "content": "..."}},
        {{"role": "ASSISTANT", "content": "..."}}
    ]
}}

Each exchange should feel authentically human - showing both strengths and realistic flaws in Ryan's personality and communication style."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate a {conversation_type} conversation with {num_exchanges} exchanges about: {scenario}. CRITICALLY IMPORTANT: Even though the personality traits provided are mostly positive, you MUST nitpick and find realistic negative aspects, flaws, and imperfections. Show where strengths become weaknesses, where communication misses the mark, where emotional responses aren't ideal. Include social awkwardness, overthinking, impatience, perfectionism issues, or moments where Ryan's approach isn't perfect. Make him authentically human with flaws."}
                ],
                temperature=0.9,  # Higher temperature for more varied, realistic (including flawed) responses
                max_tokens=2500
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
        """Generate list of workplace scenarios that reveal personality traits and emotions"""
        return [
            "A colleague takes credit for your work in a team meeting. How do you respond?",
            "You discover a major mistake in a project you've been working on for weeks. How do you communicate this?",
            "A team member is struggling with a task and asks for help, but you're already overloaded. What do you say?",
            "You're asked to present your research findings to executives who might not understand the technical details. How do you approach this?",
            "A colleague suggests an approach you strongly disagree with. How do you express your disagreement professionally?",
            "You receive unexpected praise from your manager for exceptional work. How do you respond?",
            "A deadline is moved up significantly, creating stress for the team. How do you handle the situation?",
            "You notice a junior colleague is making errors but seems defensive when corrected. How do you provide feedback?",
            "A meeting runs over time and you have another commitment. How do you handle this diplomatically?",
            "You're asked to help with a project outside your expertise but are interested in learning. How do you respond?",
            "A colleague is frustrated and venting about a project issue. How do you respond empathetically?",
            "You have a conflicting opinion with someone senior to you in a meeting. How do you present your view?",
            "A team member keeps missing deadlines. How do you address this without being confrontational?",
            "You're invited to speak at a conference but feel nervous. How do you handle the invitation?",
            "A project you're passionate about gets deprioritized. How do you express your concerns?",
            "You see an opportunity to improve a process but it might require challenging existing norms. How do you propose this?",
            "A colleague asks for career advice about transitioning to a different role. How do you respond?",
            "You're feeling overwhelmed with multiple high-priority tasks. How do you communicate this to your manager?",
            "You receive critical feedback on your work. How do you respond and incorporate it?",
            "A team celebration is being planned but conflicts with a personal commitment. How do you handle this?",
            "You notice someone is being excluded from important discussions. How do you address this?",
            "You're asked to mentor a new team member. How do you approach establishing this relationship?",
            "A decision is made that you think is a mistake. How do you voice your concerns constructively?",
            "You're running late to a meeting. How do you communicate this professionally?",
            "A colleague shares exciting news about a personal achievement. How do you celebrate with them?"
        ]
    
    def generate_conversations(
        self,
        num_conversations: int = 50,
        conversations_per_scenario: int = 2,
        save_every: int = 10,
        save_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple synthetic conversations
        
        Args:
            num_conversations: Total number of conversations to generate
            conversations_per_scenario: Number of conversations per scenario
            save_every: Save progress every N conversations (0 = only at end)
            save_file: Optional filename for continuous saving
        """
        scenarios = self.generate_scenarios()
        conversations = []
        
        # Load existing conversations if resuming
        if save_file:
            # Handle both full paths and just filenames
            if Path(save_file).is_absolute() or '/' in save_file or '\\' in save_file:
                # It's a full path, use as-is
                existing_path = Path(save_file)
            else:
                # It's just a filename, combine with output_dir
                existing_path = self.output_dir / save_file
            
            if existing_path.exists():
                try:
                    with open(existing_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        conversations = existing_data.get('conversations', [])
                        print(f"📂 Resuming: Loaded {len(conversations)} existing conversations")
                except Exception as e:
                    print(f"⚠️  Could not load existing file: {e}")
        
        print(f"🎭 Generating {num_conversations} synthetic conversations...")
        if save_every > 0:
            print(f"💾 Saving progress every {save_every} conversations")
        
        start_idx = len(conversations)
        target_total = start_idx + num_conversations
        
        for i in range(start_idx, target_total):
            scenario_idx = (i - start_idx) // conversations_per_scenario
            if scenario_idx >= len(scenarios):
                scenario_idx = (i - start_idx) % len(scenarios)
            
            scenario = scenarios[scenario_idx]
            
            # Vary conversation types
            conversation_types = ["workplace", "email", "slack", "meeting", "technical_discussion"]
            conv_type = conversation_types[(i - start_idx) % len(conversation_types)]
            
            # Vary exchange count
            num_exchanges = 3 + ((i - start_idx) % 5)  # 3-7 exchanges
            
            print(f"⏳ Generating conversation {i+1}/{target_total}: {scenario[:50]}...")
            
            conversation = self.generate_conversation(
                scenario=scenario,
                conversation_type=conv_type,
                num_exchanges=num_exchanges
            )
            
            if conversation.get('exchanges'):
                conversation['generated_at'] = datetime.now().isoformat()
                conversation['conversation_type'] = conv_type
                conversations.append(conversation)
                
                # Save periodically (based on successful conversations)
                if save_every > 0 and save_file and len(conversations) % save_every == 0:
                    self._save_conversations_incremental(conversations, save_file)
                    print(f"💾 Progress saved: {len(conversations)} conversations")
            else:
                print(f"⚠️  Failed to generate conversation {i+1}, skipping...")
            
            # Rate limiting - be nice to API
            import time
            time.sleep(1)
        
        print(f"✅ Generated {len(conversations)} conversations")
        return conversations
    
    def _save_conversations_incremental(
        self,
        conversations: List[Dict[str, Any]],
        filename: str
    ) -> None:
        """Save conversations incrementally (overwrites file)"""
        # Handle both full paths and just filenames
        if Path(filename).is_absolute() or '/' in filename or '\\' in filename:
            # It's a full path, use as-is (but ensure parent directory exists)
            filepath = Path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
        else:
            # It's just a filename, combine with output_dir
            filepath = self.output_dir / filename
        
        output = {
            'last_updated': datetime.now().isoformat(),
            'total_conversations': len(conversations),
            'conversations': conversations
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
    
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
        '--traits-file',
        type=str,
        default='personality_traits.json',
        help='Path to personality traits JSON file'
    )
    parser.add_argument(
        '--personality-traits',
        type=str,
        help='Personality traits text (overrides traits-file)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o-mini',
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
    parser.add_argument(
        '--save-every',
        type=int,
        default=10,
        help='Save progress every N conversations (0 = only at end)'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default=None,
        help='Output filename for continuous saving (default: auto-generate with timestamp)'
    )
    
    args = parser.parse_args()
    
    # Load personality traits
    personality_traits = args.personality_traits
    traits_file = args.traits_file if not personality_traits else None
    
    # Create generator
    generator = SyntheticChatGenerator(
        personality_traits=personality_traits,
        traits_file=traits_file,
        api_key=args.api_key,
        model=args.model,
        output_dir=args.output_dir
    )
    
    # Generate filename if not provided
    output_filename = args.output_file
    if output_filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"synthetic_chats_{timestamp}.json"
    
    # Generate conversations (with continuous saving if enabled)
    conversations = generator.generate_conversations(
        num_conversations=args.num_conversations,
        save_every=args.save_every if args.save_every > 0 else 0,
        save_file=output_filename if args.save_every > 0 else None
    )
    
    # Final save (or first save if not saving incrementally)
    if conversations:
        generator.save_conversations(conversations, filename=output_filename)
        print("\n✅ Synthetic chat generation complete!")
        print(f"📊 Generated {len(conversations)} conversations")
        print(f"💾 Saved to: {Path(args.output_dir) / output_filename}")
    else:
        print("⚠️  No conversations generated")


if __name__ == '__main__':
    main()

