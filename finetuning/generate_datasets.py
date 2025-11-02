#!/usr/bin/env python3
"""
Master Script to Generate High-Quality Fine-tuning Datasets
Generates both synthetic and Gmail datasets in OpenAI JSONL format
"""
import sys
from pathlib import Path
from typing import Optional, Tuple
import json
import os

# Import our modules
from personality_extractor import PersonalityExtractor
from synthetic_chat_generation import SyntheticChatGenerator
from openai_formatter import OpenAIFormatter


def generate_complete_datasets(
    cv_path: str = "cvryanlin.txt",
    linkedin_csv: str = "result.csv",
    gmail_file: str = "data/gmail/gmail_export_20251101_235831.json",
    num_synthetic: int = 100,
    synthetic_output: str = "data/openai_format/synthetic.jsonl",
    gmail_output: str = "data/openai_format/gmail.jsonl",
    num_traits: int = 15
) -> Tuple[bool, bool]:
    """
    Generate both synthetic and Gmail datasets in OpenAI format
    
    Returns:
        (synthetic_success, gmail_success)
    """
    print("🚀 Starting Complete Dataset Generation Pipeline\n")
    print("=" * 70)
    
    # Step 1: Extract Personality Traits
    print("\n📋 Step 1: Extracting Personality Traits...")
    print("-" * 70)
    
    extractor = PersonalityExtractor()
    cv_text = extractor.load_cv_data(cv_path)
    linkedin_text = extractor.load_linkedin_data(linkedin_csv)
    
    if not cv_text and not linkedin_text:
        print("❌ No data loaded. Check file paths.")
        return False, False
    
    print(f"✅ Loaded CV ({len(cv_text)} chars) and LinkedIn ({len(linkedin_text)} chars)")
    print(f"🔍 Extracting {num_traits} personality traits...")
    
    traits = extractor.extract_traits(cv_text, linkedin_text, num_traits)
    
    if not traits:
        print("❌ Failed to extract personality traits")
        return False, False
    
    traits_file = "personality_traits.json"
    with open(traits_file, 'w', encoding='utf-8') as f:
        json.dump(traits, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extracted {len(traits)} traits")
    print(f"💾 Saved to {traits_file}")
    
    # Step 2: Generate Synthetic Conversations
    print("\n🎭 Step 2: Generating Synthetic Conversations...")
    print("-" * 70)
    
    synthetic_raw_file = "synthetic_chats_for_training.json"  # Just filename, not full path
    generator = SyntheticChatGenerator(
        traits_file=traits_file,
        model="gpt-4o-mini",
        output_dir="data/synthetic"
    )
    
    print(f"📝 Generating {num_synthetic} conversations with personality traits...")
    conversations = generator.generate_conversations(
        num_conversations=num_synthetic,
        save_every=10,
        save_file=synthetic_raw_file
    )
    
    if not conversations:
        print("❌ Failed to generate synthetic conversations")
        return False, False
    
    generator.save_conversations(conversations, filename=synthetic_raw_file)
    print(f"✅ Generated {len(conversations)} conversations")
    
    # Step 3: Format Synthetic Data to OpenAI JSONL
    print("\n📦 Step 3: Formatting Synthetic Data to OpenAI JSONL...")
    print("-" * 70)
    
    # Full path to the synthetic file that was saved (output_dir + filename)
    synthetic_file_full_path = str(Path("data/synthetic") / synthetic_raw_file)
    if not Path(synthetic_file_full_path).exists():
        # Try alternative path format
        synthetic_file_full_path = str(generator.output_dir / synthetic_raw_file)
    
    formatter = OpenAIFormatter()
    synthetic_count = formatter.format_synthetic_to_openai(
        synthetic_file_full_path,
        synthetic_output,
        system_message="You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context."
    )
    
    synthetic_success = synthetic_count > 0
    
    # Step 4: Format Gmail Data to OpenAI JSONL
    print("\n📧 Step 4: Formatting Gmail Data to OpenAI JSONL...")
    print("-" * 70)
    
    gmail_file_path = Path(gmail_file)
    if not gmail_file_path.exists():
        print(f"⚠️  Gmail file not found: {gmail_file}")
        print("   Skipping Gmail formatting...")
        gmail_success = False
    else:
        gmail_count = formatter.format_gmail_to_openai(
            gmail_file,
            gmail_output,
            system_message="You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context."
        )
        gmail_success = gmail_count > 0
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 GENERATION SUMMARY")
    print("=" * 70)
    print(f"✅ Synthetic Dataset: {synthetic_count} examples -> {synthetic_output}")
    if gmail_success:
        print(f"✅ Gmail Dataset: {gmail_count} examples -> {gmail_output}")
    else:
        print(f"⚠️  Gmail Dataset: Not generated")
    
    print("\n💡 Next Steps:")
    print(f"   1. Review datasets: {synthetic_output} and {gmail_output}")
    print("   2. Upload to OpenAI Fine-tuning Platform")
    print("   3. Create fine-tuning job using these JSONL files")
    
    return synthetic_success, gmail_success


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate complete fine-tuning datasets')
    parser.add_argument('--cv-path', type=str, default='cvryanlin.txt')
    parser.add_argument('--linkedin-csv', type=str, default='result.csv')
    parser.add_argument('--gmail-file', type=str, 
                       default='data/gmail/gmail_export_20251101_235831.json')
    parser.add_argument('--num-synthetic', type=int, default=100)
    parser.add_argument('--synthetic-output', type=str,
                       default='data/openai_format/synthetic.jsonl')
    parser.add_argument('--gmail-output', type=str,
                       default='data/openai_format/gmail.jsonl')
    parser.add_argument('--num-traits', type=int, default=15)
    
    args = parser.parse_args()
    
    # Generate datasets
    synthetic_ok, gmail_ok = generate_complete_datasets(
        cv_path=args.cv_path,
        linkedin_csv=args.linkedin_csv,
        gmail_file=args.gmail_file,
        num_synthetic=args.num_synthetic,
        synthetic_output=args.synthetic_output,
        gmail_output=args.gmail_output,
        num_traits=args.num_traits
    )
    
    if synthetic_ok and gmail_ok:
        print("\n🎉 SUCCESS: Both datasets generated!")
        sys.exit(0)
    elif synthetic_ok:
        print("\n✅ SUCCESS: Synthetic dataset generated (Gmail skipped)")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Dataset generation incomplete")
        sys.exit(1)


if __name__ == '__main__':
    main()

