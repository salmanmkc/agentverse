#!/usr/bin/env python3
"""
OpenAI Fine-tuning Security Validation Script
Checks training data files for compliance with OpenAI's usage policies
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys


class OpenAISecurityValidator:
    """Validate training data for OpenAI fine-tuning security requirements"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        
    def validate_file(self, filepath: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a JSONL file for OpenAI fine-tuning
        
        Returns:
            (is_valid, errors, warnings)
        """
        self.issues = []
        self.warnings = []
        
        jsonl_path = Path(filepath)
        if not jsonl_path.exists():
            self.issues.append(f"File not found: {filepath}")
            return False, self.issues, self.warnings
        
        print(f"🔍 Validating {filepath}...")
        
        total_examples = 0
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                total_examples = line_num
                line = line.strip()
                if not line:
                    continue
                
                try:
                    example = json.loads(line)
                    self._validate_example(example, line_num)
                except json.JSONDecodeError as e:
                    self.issues.append(f"Line {line_num}: Invalid JSON - {e}")
        
        print(f"✅ Validated {total_examples} examples")
        
        # Summary checks
        self._check_overall_issues(total_examples)
        
        is_valid = len(self.issues) == 0
        return is_valid, self.issues, self.warnings
    
    def _validate_example(self, example: Dict[str, Any], line_num: int):
        """Validate a single training example"""
        # Check required structure
        if 'messages' not in example:
            self.issues.append(f"Line {line_num}: Missing 'messages' key")
            return
        
        messages = example['messages']
        if not isinstance(messages, list):
            self.issues.append(f"Line {line_num}: 'messages' must be a list")
            return
        
        if len(messages) < 2:
            self.issues.append(f"Line {line_num}: Need at least 2 messages (has {len(messages)})")
            return
        
        # Check each message
        valid_roles = {'system', 'user', 'assistant'}
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                self.issues.append(f"Line {line_num}, message {i}: Message must be a dict")
                continue
            
            if 'role' not in msg:
                self.issues.append(f"Line {line_num}, message {i}: Missing 'role'")
                continue
            
            if msg['role'] not in valid_roles:
                self.issues.append(f"Line {line_num}, message {i}: Invalid role '{msg['role']}'")
                continue
            
            if 'content' not in msg:
                self.issues.append(f"Line {line_num}, message {i}: Missing 'content'")
                continue
            
            if not isinstance(msg['content'], str):
                self.issues.append(f"Line {line_num}, message {i}: 'content' must be a string")
                continue
        
        # Check first message is system
        if messages[0].get('role') != 'system':
            self.issues.append(f"Line {line_num}: First message must be 'system' (is '{messages[0].get('role')}')")
        
        # Check last message is assistant
        if messages[-1].get('role') != 'assistant':
            self.issues.append(f"Line {line_num}: Last message must be 'assistant' (is '{messages[-1].get('role')}')")
        
        # Security checks
        for i, msg in enumerate(messages):
            content = msg.get('content', '')
            self._check_sensitive_content(content, line_num, i, msg.get('role'))
    
    def _check_sensitive_content(self, content: str, line_num: int, msg_idx: int, role: str):
        """Check for sensitive content that violates OpenAI policies"""
        content_lower = content.lower()
        
        # Check for unredacted passwords
        password_patterns = [
            r'(?<!redact)(?:password|pwd|passwd)\s*[:=]\s*[^\s\n]{4,}',
            r'(?:username|user)\s*[:=]\s*[\w-]+\s*[,:]\s*(?:password|pwd)\s*[:=]\s*[^\s\n]+',
        ]
        for pattern in password_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if '[REDACTED' not in content[max(0, content.lower().find(match)-50):content.lower().find(match)+len(match)+50]:
                    self.issues.append(
                        f"Line {line_num}, message {msg_idx} ({role}): Unredacted password/credential: {match[:30]}..."
                    )
        
        # Check for unredacted SSN
        ssn_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # XXX-XX-XXXX format
        ]
        for pattern in ssn_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if '[REDACTED_SSN]' not in content[max(0, content.find(match)-50):content.find(match)+len(match)+50]:
                    self.issues.append(
                        f"Line {line_num}, message {msg_idx} ({role}): Unredacted SSN: {match}"
                    )
        
        # Check for unredacted phone numbers (but allow in URLs/context)
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        phones = re.findall(phone_pattern, content)
        for phone in phones:
            # Allow if it's part of a URL (like overleaf.com/1234567890)
            context_start = max(0, content.find(phone) - 20)
            context_end = min(len(content), content.find(phone) + len(phone) + 20)
            context = content[context_start:context_end].lower()
            
            # Skip if in URL or already redacted
            if 'http' in context or '.com' in context or '[REDACTED_PHONE]' in content:
                continue
                
            self.warnings.append(
                f"Line {line_num}, message {msg_idx} ({role}): Potential unredacted phone: {phone}"
            )
        
        # Check for Zoom links with passwords
        zoom_with_pwd = re.search(r'zoom\.us/[^\s]*\?pwd=[^\s&\n]+', content, re.IGNORECASE)
        if zoom_with_pwd:
            self.issues.append(
                f"Line {line_num}, message {msg_idx} ({role}): Zoom link with password parameter"
            )
        
        # Check for excessive sensitive content (might indicate need for more redaction)
        redaction_count = content.count('[REDACTED')
        if redaction_count > 10:
            self.warnings.append(
                f"Line {line_num}, message {msg_idx} ({role}): High redaction count ({redaction_count}) - consider reviewing"
            )
    
    def _check_overall_issues(self, total_examples: int):
        """Check for overall dataset issues"""
        if total_examples < 10:
            self.warnings.append(f"Dataset is very small ({total_examples} examples) - may not train well")
        
        if len(self.issues) > total_examples * 0.1:  # More than 10% have issues
            self.warnings.append(
                f"High error rate: {len(self.issues)} issues in {total_examples} examples "
                f"({len(self.issues)/total_examples*100:.1f}%)"
            )
    
    def print_report(self, filepath: str, is_valid: bool, errors: List[str], warnings: List[str]):
        """Print validation report"""
        print("\n" + "="*70)
        print(f"📋 Validation Report: {Path(filepath).name}")
        print("="*70)
        
        if is_valid:
            print("✅ PASSED: File is valid for OpenAI fine-tuning")
        else:
            print(f"❌ FAILED: Found {len(errors)} critical issues")
        
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warning in warnings[:20]:
                print(f"  • {warning}")
            if len(warnings) > 20:
                print(f"  ... and {len(warnings) - 20} more warnings")
        
        if errors:
            print(f"\n❌ Critical Issues ({len(errors)}):")
            for error in errors[:30]:
                print(f"  • {error}")
            if len(errors) > 30:
                print(f"  ... and {len(errors) - 30} more errors")
        
        print("\n" + "="*70 + "\n")
        
        return is_valid and len(warnings) < 50  # Allow some warnings


def main():
    """Main validation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate OpenAI fine-tuning data')
    parser.add_argument('file', type=str, help='JSONL file to validate')
    parser.add_argument('--strict', action='store_true', help='Fail on warnings')
    
    args = parser.parse_args()
    
    validator = OpenAISecurityValidator()
    is_valid, errors, warnings = validator.validate_file(args.file)
    
    validator.print_report(args.file, is_valid, errors, warnings)
    
    # Exit with error code if validation failed
    if not is_valid:
        sys.exit(1)
    
    if args.strict and warnings:
        print("⚠️  Strict mode: Exiting due to warnings")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()

