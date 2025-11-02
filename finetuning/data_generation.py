#!/usr/bin/env python3
"""
Data Generation and Normalization Script
Combines Gmail, message, and synthetic data into SFT JSONL format
Applies persona framing: "You are Ryan Lin" to all training examples
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import random


class DataNormalizer:
    """Normalize and convert data to SFT JSONL format"""
    
    def __init__(
        self,
        persona_name: str = "Ryan Lin",
        output_dir: str = "data/training"
    ):
        """
        Initialize data normalizer
        
        Args:
            persona_name: Name of the persona to emulate
            output_dir: Output directory for training data
        """
        self.persona_name = persona_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Placeholder patterns for redaction (optional)
        self.pii_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),  # SSN
            (r'\b\d{16}\b', '[CARD]'),  # Credit card
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # Email
        ]
    
    def redact_pii(self, text: str, aggressive: bool = False) -> str:
        """
        Redact personally identifiable information
        
        Args:
            text: Text to redact
            aggressive: If True, replace names/emails more aggressively
        """
        result = text
        
        # Apply PII patterns
        for pattern, replacement in self.pii_patterns:
            result = re.sub(pattern, replacement, result)
        
        # Optionally replace other emails (but keep structure for persona learning)
        if aggressive:
            # Replace email addresses (but keep domain structure)
            result = re.sub(
                r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
                f'[EMAIL]@\\1',
                result
            )
        
        return result
    
    def create_sft_example(
        self,
        instruction: str,
        output: str,
        input_text: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a single SFT training example
        
        Args:
            instruction: System + user instruction (with persona framing)
            output: Assistant response (Ryan Lin's style)
            input_text: Optional input context
            metadata: Optional metadata
        """
        example = {
            "instruction": instruction,
            "input": input_text,
            "output": output
        }
        
        if metadata:
            example["metadata"] = metadata
        
        return example
    
    def normalize_gmail_email(
        self,
        email: Dict[str, Any],
        redact: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Normalize Gmail email to SFT format
        
        Args:
            email: Gmail email dictionary
            redact: Whether to redact PII
        """
        examples = []
        
        if not email.get('body') or not email['body'].strip():
            return examples
        
        body = email['body']
        if redact:
            body = self.redact_pii(body)
        
        is_sent = email.get('is_sent', False)
        subject = email.get('subject', '')
        to_addr = email.get('to', '')
        from_addr = email.get('from', '')
        
        if is_sent:
            # This is Ryan's sent email - use as ASSISTANT output
            # Create instruction from context
            if subject:
                instruction = f"SYSTEM: You are {self.persona_name}. Respond as {self.persona_name} would in a professional workplace context.\nUSER: Write an email"
                if to_addr:
                    instruction += f" to {to_addr}"
                if subject:
                    instruction += f" with subject: {subject}"
                instruction += "."
            else:
                instruction = f"SYSTEM: You are {self.persona_name}. Respond as {self.persona_name} would in a professional workplace context.\nUSER: Write a professional email."
            
            example = self.create_sft_example(
                instruction=instruction,
                output=body,
                metadata={
                    "source": "gmail",
                    "date": email.get('date', ''),
                    "subject": subject,
                    "is_sent": True
                }
            )
            examples.append(example)
        else:
            # Received email - could create a reply scenario
            # For now, we'll use it as context for synthetic replies
            pass
        
        return examples
    
    def normalize_message(
        self,
        message: Dict[str, Any],
        user_name: str = "Ryan Lin",
        redact: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Normalize message (iMessage, WhatsApp, etc.) to SFT format
        
        Args:
            message: Message dictionary
            user_name: Name of the user (to identify sent messages)
            redact: Whether to redact PII
        """
        examples = []
        
        content = message.get('content', '')
        if not content or not content.strip():
            return examples
        
        if redact:
            content = self.redact_pii(content)
        
        sender = message.get('sender', '')
        platform = message.get('platform', 'unknown')
        
        # Determine if this is a sent message (Ryan's message)
        is_sent = user_name.lower() in sender.lower() if sender else False
        
        if is_sent:
            # This is Ryan's message - use as ASSISTANT output
            # Infer context from conversation
            instruction = f"SYSTEM: You are {self.persona_name}. Respond as {self.persona_name} would in a professional workplace context.\nUSER: Respond to a {platform} message."
            
            example = self.create_sft_example(
                instruction=instruction,
                output=content,
                metadata={
                    "source": platform,
                    "date": message.get('timestamp', ''),
                    "is_sent": True
                }
            )
            examples.append(example)
        
        return examples
    
    def normalize_synthetic_conversation(
        self,
        conversation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Normalize synthetic conversation to SFT format
        
        Args:
            conversation: Synthetic conversation dictionary
        """
        examples = []
        
        exchanges = conversation.get('exchanges', [])
        if not exchanges:
            return examples
        
        # Process exchanges in pairs (USER -> ASSISTANT)
        for i in range(len(exchanges) - 1):
            if exchanges[i].get('role') == 'USER' and exchanges[i+1].get('role') == 'ASSISTANT':
                user_message = exchanges[i].get('content', '')
                assistant_message = exchanges[i+1].get('content', '')
                
                if user_message and assistant_message:
                    instruction = f"SYSTEM: You are {self.persona_name}. Respond as {self.persona_name} would in a professional workplace context.\nUSER: {user_message}"
                    
                    example = self.create_sft_example(
                        instruction=instruction,
                        output=assistant_message,
                        metadata={
                            "source": "synthetic",
                            "scenario": conversation.get('scenario', ''),
                            "conversation_type": conversation.get('conversation_type', ''),
                            "generated_at": conversation.get('generated_at', '')
                        }
                    )
                    examples.append(example)
        
        return examples
    
    def load_gmail_data(self, filepath: str) -> List[Dict[str, Any]]:
        """Load Gmail export JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('messages', [])
    
    def load_message_data(self, filepath: str) -> List[Dict[str, Any]]:
        """Load processed message JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('messages', [])
    
    def load_synthetic_data(self, filepath: str) -> List[Dict[str, Any]]:
        """Load synthetic conversation JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('conversations', [])
    
    def combine_and_normalize(
        self,
        gmail_files: List[str] = None,
        message_files: List[str] = None,
        synthetic_files: List[str] = None,
        redact_pii: bool = True,
        user_name: str = "Ryan Lin"
    ) -> List[Dict[str, Any]]:
        """
        Combine all data sources and normalize to SFT format
        
        Args:
            gmail_files: List of Gmail export JSON files
            message_files: List of processed message JSON files
            synthetic_files: List of synthetic conversation JSON files
            redact_pii: Whether to redact PII
            user_name: Name to identify sent messages
        """
        all_examples = []
        
        # Process Gmail data
        if gmail_files:
            print(f"📧 Processing {len(gmail_files)} Gmail export(s)...")
            for filepath in gmail_files:
                try:
                    emails = self.load_gmail_data(filepath)
                    for email in emails:
                        examples = self.normalize_gmail_email(email, redact=redact_pii)
                        all_examples.extend(examples)
                    print(f"   ✅ Processed {len(emails)} emails from {Path(filepath).name}")
                except Exception as e:
                    print(f"   ⚠️  Error processing {filepath}: {e}")
        
        # Process message data
        if message_files:
            print(f"💬 Processing {len(message_files)} message export(s)...")
            for filepath in message_files:
                try:
                    messages = self.load_message_data(filepath)
                    for message in messages:
                        examples = self.normalize_message(message, user_name=user_name, redact=redact_pii)
                        all_examples.extend(examples)
                    print(f"   ✅ Processed {len(messages)} messages from {Path(filepath).name}")
                except Exception as e:
                    print(f"   ⚠️  Error processing {filepath}: {e}")
        
        # Process synthetic data
        if synthetic_files:
            print(f"🎭 Processing {len(synthetic_files)} synthetic conversation file(s)...")
            for filepath in synthetic_files:
                try:
                    conversations = self.load_synthetic_data(filepath)
                    for conversation in conversations:
                        examples = self.normalize_synthetic_conversation(conversation)
                        all_examples.extend(examples)
                    print(f"   ✅ Processed {len(conversations)} conversations from {Path(filepath).name}")
                except Exception as e:
                    print(f"   ⚠️  Error processing {filepath}: {e}")
        
        print(f"\n📊 Total examples: {len(all_examples)}")
        return all_examples
    
    def split_train_valid(
        self,
        examples: List[Dict[str, Any]],
        train_ratio: float = 0.9,
        shuffle: bool = True
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split examples into train and validation sets
        
        Args:
            examples: List of SFT examples
            train_ratio: Ratio for training set
            shuffle: Whether to shuffle before splitting
        """
        if shuffle:
            random.shuffle(examples)
        
        split_idx = int(len(examples) * train_ratio)
        train_examples = examples[:split_idx]
        valid_examples = examples[split_idx:]
        
        return train_examples, valid_examples
    
    def save_jsonl(
        self,
        examples: List[Dict[str, Any]],
        filepath: str
    ) -> None:
        """Save examples to JSONL file"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for example in examples:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"💾 Saved {len(examples)} examples to {filepath}")


def main():
    """Main data generation function"""
    import argparse
    import glob
    
    parser = argparse.ArgumentParser(description='Generate training data in SFT JSONL format')
    parser.add_argument(
        '--gmail-dir',
        type=str,
        help='Directory containing Gmail export JSON files'
    )
    parser.add_argument(
        '--message-dir',
        type=str,
        help='Directory containing processed message JSON files'
    )
    parser.add_argument(
        '--synthetic-dir',
        type=str,
        help='Directory containing synthetic conversation JSON files'
    )
    parser.add_argument(
        '--gmail-files',
        type=str,
        nargs='+',
        help='Specific Gmail export JSON files'
    )
    parser.add_argument(
        '--message-files',
        type=str,
        nargs='+',
        help='Specific message export JSON files'
    )
    parser.add_argument(
        '--synthetic-files',
        type=str,
        nargs='+',
        help='Specific synthetic conversation JSON files'
    )
    parser.add_argument(
        '--persona-name',
        type=str,
        default='Ryan Lin',
        help='Persona name for framing'
    )
    parser.add_argument(
        '--user-name',
        type=str,
        default='Ryan Lin',
        help='User name to identify sent messages'
    )
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.9,
        help='Training set ratio'
    )
    parser.add_argument(
        '--no-redact',
        action='store_true',
        help='Disable PII redaction'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/training',
        help='Output directory for training data'
    )
    
    args = parser.parse_args()
    
    # Collect files
    gmail_files = []
    message_files = []
    synthetic_files = []
    
    if args.gmail_dir:
        gmail_files.extend(glob.glob(str(Path(args.gmail_dir) / "*.json")))
    
    if args.gmail_files:
        gmail_files.extend(args.gmail_files)
    
    if args.message_dir:
        message_files.extend(glob.glob(str(Path(args.message_dir) / "*.json")))
    
    if args.message_files:
        message_files.extend(args.message_files)
    
    if args.synthetic_dir:
        synthetic_files.extend(glob.glob(str(Path(args.synthetic_dir) / "*.json")))
    
    if args.synthetic_files:
        synthetic_files.extend(args.synthetic_files)
    
    if not gmail_files and not message_files and not synthetic_files:
        print("❌ No input files found. Specify --gmail-dir, --message-dir, --synthetic-dir, or specific files.")
        return
    
    # Create normalizer
    normalizer = DataNormalizer(
        persona_name=args.persona_name,
        output_dir=args.output_dir
    )
    
    # Combine and normalize
    examples = normalizer.combine_and_normalize(
        gmail_files=gmail_files if gmail_files else None,
        message_files=message_files if message_files else None,
        synthetic_files=synthetic_files if synthetic_files else None,
        redact_pii=not args.no_redact,
        user_name=args.user_name
    )
    
    if not examples:
        print("❌ No examples generated")
        return
    
    # Split train/valid
    train_examples, valid_examples = normalizer.split_train_valid(
        examples,
        train_ratio=args.train_ratio
    )
    
    # Save JSONL files
    train_path = Path(args.output_dir) / "train.jsonl"
    valid_path = Path(args.output_dir) / "valid.jsonl"
    
    normalizer.save_jsonl(train_examples, train_path)
    normalizer.save_jsonl(valid_examples, valid_path)
    
    print(f"\n✅ Data generation complete!")
    print(f"📊 Training examples: {len(train_examples)}")
    print(f"📊 Validation examples: {len(valid_examples)}")
    print(f"💾 Saved to:")
    print(f"   Train: {train_path}")
    print(f"   Valid: {valid_path}")


if __name__ == '__main__':
    main()

