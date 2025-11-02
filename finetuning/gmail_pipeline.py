#!/usr/bin/env python3
"""
Complete Gmail Data Pipeline
Extracts all Gmail data, formats it, validates security, and generates training files
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gmail_extraction import GmailExtractor
from openai_formatter import OpenAIFormatter
from validate_openai_security import OpenAISecurityValidator


def run_full_pipeline(
    credentials_file: str = "credentials.json",
    token_file: str = "token.pickle",
    max_emails: int = None,
    output_dir: str = "data/gmail",
    formatted_output: str = "data/openai_format/gmail.jsonl",
    use_existing: bool = True
):
    """
    Run the complete Gmail data pipeline
    
    Steps:
    1. Authenticate with Gmail API
    2. Extract all emails (sent + received) - or use existing export
    3. Format to OpenAI JSONL format
    4. Validate security compliance
    5. Report results
    """
    print("="*70)
    print("📧 GMAIL DATA PIPELINE")
    print("="*70)
    print()
    
    # Step 1: Extract emails or use existing
    print("🔐 Step 1: Authenticating and Extracting Gmail Data...")
    print("-"*70)
    
    raw_file = None
    messages = []
    
    # Check for existing export files
    if use_existing:
        output_path = Path(output_dir)
        if output_path.exists():
            export_files = sorted(output_path.glob("gmail_export_*.json"), reverse=True)
            if export_files:
                raw_file = str(export_files[0])
                print(f"📂 Found existing export: {export_files[0].name}")
                
                # Load existing data
                try:
                    with open(raw_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    messages = data.get('messages', [])
                    print(f"✅ Loaded {len(messages)} emails from existing export")
                    
                    # Count sent vs received
                    sent_count = sum(1 for m in messages if m.get('is_sent', False))
                    received_count = len(messages) - sent_count
                    print(f"   📤 Sent: {sent_count}")
                    print(f"   📥 Received: {received_count}")
                    
                    if max_emails and len(messages) < max_emails:
                        print(f"⚠️  Existing export has {len(messages)} emails, but limit is {max_emails}")
                        print("   Re-extracting to get more emails...")
                        raw_file = None  # Force re-extraction
                        messages = []
                except Exception as e:
                    print(f"⚠️  Error loading existing file: {e}")
                    print("   Will re-extract...")
                    raw_file = None
    
    # Extract if no existing file or need more emails
    if not messages:
        extractor = GmailExtractor(
            credentials_file=credentials_file,
            token_file=token_file,
            output_dir=output_dir
        )
        
        if not extractor.authenticate():
            print("❌ Authentication failed")
            return False
        
        messages = extractor.extract_emails(
            max_results=max_emails,
            include_sent=True,
            include_received=True
        )
        
        if not messages:
            print("❌ No emails extracted")
            return False
        
        print(f"✅ Extracted {len(messages)} emails")
        
        # Count sent vs received
        sent_count = sum(1 for m in messages if m.get('is_sent', False))
        received_count = len(messages) - sent_count
        print(f"   📤 Sent: {sent_count}")
        print(f"   📥 Received: {received_count}")
        
        # Save raw data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        raw_file = extractor.save_emails(messages, f"gmail_export_{timestamp}.json")
        print(f"💾 Saved raw data to: {raw_file}")
        print()
    
    # Step 2: Format to OpenAI JSONL
    print("📦 Step 2: Formatting to OpenAI JSONL...")
    print("-"*70)
    
    formatter = OpenAIFormatter()
    example_count = formatter.format_gmail_to_openai(
        gmail_file=raw_file,
        output_file=formatted_output,
        system_message="You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context."
    )
    
    if example_count == 0:
        print("❌ No training examples generated")
        return False
    
    print(f"✅ Generated {example_count} training examples")
    print()
    
    # Step 3: Validate security
    print("🔒 Step 3: Validating Security Compliance...")
    print("-"*70)
    
    validator = OpenAISecurityValidator()
    is_valid, errors, warnings = validator.validate_file(formatted_output)
    
    validator.print_report(formatted_output, is_valid, errors, warnings)
    
    if not is_valid:
        print("❌ Security validation FAILED")
        print("⚠️  Fix the issues above before uploading to OpenAI")
        return False
    
    # Final summary
    print("="*70)
    print("✅ PIPELINE COMPLETE")
    print("="*70)
    print(f"📊 Summary:")
    print(f"   • Raw emails extracted: {len(messages)}")
    print(f"   • Training examples: {example_count}")
    print(f"   • Security validation: PASSED")
    print(f"   • Output file: {formatted_output}")
    print()
    print(f"📤 Ready to upload to OpenAI fine-tuning!")
    print()
    
    return True


def main():
    """Main pipeline function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete Gmail data pipeline')
    parser.add_argument(
        '--credentials',
        type=str,
        default='credentials.json',
        help='Path to Google OAuth2 credentials file'
    )
    parser.add_argument(
        '--token',
        type=str,
        default='token.pickle',
        help='Path to authentication token file'
    )
    parser.add_argument(
        '--max-emails',
        type=int,
        default=None,
        help='Maximum emails to extract (None = all)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/gmail',
        help='Directory for raw email exports'
    )
    parser.add_argument(
        '--formatted-output',
        type=str,
        default='data/openai_format/gmail.jsonl',
        help='Output path for formatted JSONL file'
    )
    parser.add_argument(
        '--force-re-extract',
        action='store_true',
        help='Force re-extraction even if existing export found'
    )
    
    args = parser.parse_args()
    
    success = run_full_pipeline(
        credentials_file=args.credentials,
        token_file=args.token,
        max_emails=args.max_emails,
        output_dir=args.output_dir,
        formatted_output=args.formatted_output,
        use_existing=not args.force_re_extract
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

