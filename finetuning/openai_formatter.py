#!/usr/bin/env python3
"""
OpenAI Fine-tuning JSONL Formatter
Formats data in OpenAI's fine-tuning format (messages with roles)
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


class OpenAIFormatter:
    """Format data for OpenAI fine-tuning"""
    
    def format_synthetic_to_openai(
        self,
        synthetic_file: str,
        output_file: str,
        system_message: str = "You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context."
    ) -> int:
        """
        Convert synthetic conversations to OpenAI format
        
        Deterministic conversion - splits each USER->ASSISTANT pair into separate training examples.
        
        OpenAI format (one example per line):
        {
          "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
          ]
        }
        """
        synthetic_path = Path(synthetic_file)
        if not synthetic_path.exists():
            raise FileNotFoundError(f"Synthetic file not found: {synthetic_file}")
        
        with open(synthetic_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conversations = data.get('conversations', [])
        formatted_examples = []
        
        print(f"📝 Formatting {len(conversations)} synthetic conversations...")
        
        for conv in conversations:
            exchanges = conv.get('exchanges', [])
            if not exchanges:
                continue
            
            # Process each USER->ASSISTANT pair as a separate training example
            # CRITICAL: Each example must end with an assistant message for OpenAI fine-tuning
            i = 0
            while i < len(exchanges):
                if exchanges[i].get('role') == 'USER':
                    user_content = exchanges[i].get('content', '').strip()
                    
                    # Look for the next ASSISTANT response
                    if i + 1 < len(exchanges) and exchanges[i + 1].get('role') == 'ASSISTANT':
                        assistant_content = exchanges[i + 1].get('content', '').strip()
                        
                        # Only create example if both have content and assistant content is not empty
                        if user_content and assistant_content:
                            # Create a separate training example for this pair
                            messages = [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_content},
                                {"role": "assistant", "content": assistant_content}
                            ]
                            formatted_examples.append({"messages": messages})
                        
                        i += 2  # Skip both USER and ASSISTANT
                    else:
                        # USER without matching ASSISTANT - skip (can't end with user message)
                        i += 1
                else:
                    i += 1  # Skip non-USER exchanges
        
        # Validate all examples end with assistant message (OpenAI requirement)
        validated_examples = []
        skipped_count = 0
        for example in formatted_examples:
            messages = example.get('messages', [])
            if messages and messages[-1].get('role') == 'assistant':
                validated_examples.append(example)
            else:
                # Skip examples that don't end with assistant message
                skipped_count += 1
                continue
        
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} examples that didn't end with assistant message")
        
        formatted_examples = validated_examples
        
        # Write to JSONL
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in formatted_examples:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"✅ Formatted {len(formatted_examples)} user/assistant pairs to {output_file}")
        return len(formatted_examples)
    
    def format_gmail_to_openai(
        self,
        gmail_file: str,
        output_file: str,
        system_message: str = "You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context.",
        min_body_length: int = 20
    ) -> int:
        """
        Convert Gmail emails to OpenAI format as prompt-reply pairs
        
        Deterministic conversion - extracts each received email -> Ryan's reply as a separate training example.
        
        For email threads:
        - Original email (from someone else) -> user message
        - Ryan's reply -> assistant message
        
        Each pair becomes one training example.
        """
        gmail_path = Path(gmail_file)
        if not gmail_path.exists():
            raise FileNotFoundError(f"Gmail file not found: {gmail_file}")
        
        with open(gmail_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        emails = data.get('messages', [])
        formatted_examples = []
        
        print(f"📧 Processing {len(emails)} emails...")
        
        # Group emails by thread
        threads = {}
        for email in emails:
            thread_id = email.get('thread_id', email.get('id'))
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(email)
        
        # Process each thread - find ALL sent emails with their corresponding received emails
        processed_pairs = set()  # Track (received_id, sent_id) to avoid duplicates
        
        for thread_id, thread_emails in threads.items():
            # Sort by date
            thread_emails.sort(key=lambda x: x.get('date', ''))
            
            # Strategy: For each sent email, find the most recent received email before it
            # Also: For each received email, find the next sent email that replies to it
            
            # Match sent emails to their corresponding received emails
            # CRITICAL: Only pair when received email came BEFORE sent email chronologically
            for i, email in enumerate(thread_emails):
                if not email.get('is_sent', False):
                    continue
                
                # This is a sent email - find what it's replying to
                sent_email = email
                sent_id = sent_email.get('id')
                sent_subject = sent_email.get('subject', '')
                sent_date = sent_email.get('date', '')
                
                # Look backwards for a received email this might be replying to
                # Only consider received emails that came BEFORE this sent email
                best_match = None
                best_match_j = None
                
                for j in range(i - 1, -1, -1):
                    received_email = thread_emails[j]
                    if received_email.get('is_sent', False):
                        continue  # Skip other sent emails
                    
                    received_id = received_email.get('id')
                    received_subject = received_email.get('subject', '')
                    received_from = received_email.get('from', '')
                    received_date = received_email.get('date', '')
                    
                    # CRITICAL: Verify received email came BEFORE sent email
                    if received_date >= sent_date:
                        continue  # Received email came after sent email - skip
                    
                    # Check if this pair was already processed
                    pair_key = (received_id, sent_id)
                    if pair_key in processed_pairs:
                        break
                    
                    # Skip automated emails
                    if self._is_automated_email(received_from, received_subject, received_email.get('body', '')):
                        continue
                    
                    # Check if received email is itself a reply to a previous sent email
                    # If so, don't pair it - we want original received emails, not replies to Ryan
                    is_received_a_reply = False
                    
                    # CRITICAL: If received email has "Re:" in subject, check if ANY sent email in the thread
                    # has a matching subject (without "Re:"). If so, this received email is replying to Ryan
                    if received_subject.lower().startswith(('re:', 'fwd:', 'fw:')):
                        # Normalize the received subject (remove Re:/Fwd:)
                        received_normalized = received_subject.lower().replace('re:', '').replace('fwd:', '').replace('fw:', '').strip()
                        
                        # Check ALL sent emails in the thread (not just before this one)
                        # If any sent email has a subject that matches this received email's normalized subject,
                        # then the received email is replying to Ryan
                        for k in range(len(thread_emails)):
                            other_email = thread_emails[k]
                            if other_email.get('is_sent', False):
                                other_subject = other_email.get('subject', '')
                                other_normalized = other_subject.lower().replace('re:', '').replace('fwd:', '').replace('fw:', '').strip()
                                
                                # If subjects match (normalized), this received email is replying to Ryan's sent email
                                if received_normalized == other_normalized or other_normalized in received_normalized or received_normalized in other_normalized:
                                    is_received_a_reply = True
                                    break
                        
                        # Also check: If received email came first chronologically but has "Re:",
                        # it's almost certainly replying to an email sent before this thread
                        if not is_received_a_reply and j == 0:
                            # First email in thread with "Re:" - very likely a reply to earlier email
                            is_received_a_reply = True
                    
                    # Second check: Also check if received email explicitly quotes or references a previous sent email
                    if not is_received_a_reply:
                        received_body_lower = received_email.get('body', '').lower()
                        # Look for indicators that this is a reply to Ryan
                        reply_indicators = [
                            'thank you for your email',
                            'thanks for your email',
                            'in response to',
                            'regarding your email',
                            'as requested',
                            'as you asked',
                            'on .* wrote',  # Email quote pattern
                        ]
                        if any(indicator in received_body_lower[:500] for indicator in reply_indicators):
                            # Check if there's any sent email in the thread
                            for k in range(len(thread_emails)):
                                if thread_emails[k].get('is_sent', False):
                                    is_received_a_reply = True
                                    break
                    
                    if is_received_a_reply:
                        continue  # This received email is a reply to Ryan's earlier email - skip
                    
                    # Check if sent email is a reply to this received email
                    is_reply = self._is_reply_to(sent_subject, received_subject)
                    
                    if is_reply:
                        # Found a candidate - take the most recent one before the sent email
                        if best_match is None or received_date > best_match.get('date', ''):
                            best_match = received_email
                            best_match_j = j
                
                # Process the best match if found
                if best_match is not None:
                    received_email = best_match
                    received_id = received_email.get('id')
                    received_subject = received_email.get('subject', '')
                    received_from = received_email.get('from', '')
                    
                    pair_key = (received_id, sent_id)
                    if pair_key not in processed_pairs:
                        # Found a reply pair - process it
                        received_body = self._clean_email_body(received_email.get('body', ''))
                        reply_body = self._clean_email_body(sent_email.get('body', ''))
                        
                        # Redact sensitive content
                        received_subject_clean = self._redact_sensitive_content(received_subject)
                        received_from_clean = self._redact_sensitive_content(received_from)
                        
                        # Skip if too short
                        if len(received_body) < min_body_length or len(reply_body) < min_body_length:
                            continue
                        
                        # Build user content
                        user_content_parts = []
                        if received_subject_clean:
                            user_content_parts.append(f"Subject: {received_subject_clean}")
                        if received_from_clean:
                            user_content_parts.append(f"From: {received_from_clean}")
                        user_content_parts.append("")
                        user_content_parts.append(received_body)
                        user_content = "\n".join(user_content_parts)
                        
                        # Safety check for excessive redaction
                        redaction_count = user_content.count('[REDACTED') + reply_body.count('[REDACTED')
                        if redaction_count > 5:
                            continue
                        
                        # Create training example
                        messages = [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_content},
                            {"role": "assistant", "content": reply_body}
                        ]
                        
                        formatted_examples.append({"messages": messages})
                        processed_pairs.add(pair_key)
        
        # Write to JSONL
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in formatted_examples:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"✅ Formatted {len(formatted_examples)} email reply pairs to {output_file}")
        return len(formatted_examples)
    
    def _is_automated_email(self, from_addr: str, subject: str, body: str) -> bool:
        """Check if email is automated/notification that shouldn't be replied to"""
        if not from_addr:
            return True
        
        # Automated email indicators
        automated_patterns = [
            r'no-reply@',
            r'noreply@',
            r'notifications@',
            r'@amazon\.',
            r'@.*\.amazon\.',
            r'epicgames\.com',
            r'mail\.epicgames\.com',
            r'pinterest\.com',
            r'tello\.com',
            r'@.*\.com.*noreply',
            r'@.*\.com.*notification',
        ]
        
        from_lower = from_addr.lower()
        for pattern in automated_patterns:
            if re.search(pattern, from_lower):
                return True
        
        # Check subject for notification patterns
        subject_lower = subject.lower()
        notification_subjects = [
            'order', 'delivery', 'dispatched', 'out for delivery', 'refund',
            'confirmation', 'invoice', 'receipt', 'terms of service',
            'privacy policy', 'update', 'newsletter', 'canceled',
            'thank you for', 'you canceled', 'subscription'
        ]
        
        for pattern in notification_subjects:
            if pattern in subject_lower:
                # Additional check: if body contains typical notification content
                body_lower = body.lower()
                if any(phrase in body_lower for phrase in ['track package', 'order #', 'invoice', 'unsubscribe', 'click here']):
                    return True
        
        return False
    
    def _is_reply_to(self, reply_subject: str, original_subject: str) -> bool:
        """Check if reply_subject indicates it's a reply to original_subject"""
        if not reply_subject or not original_subject:
            return False
        
        # Normalize subjects (remove "Re:", "Fwd:", whitespace)
        def normalize_subject(subj):
            subj = subj.strip()
            subj = re.sub(r'^(Re:|Fwd:|RE:|FWD:)\s*', '', subj, flags=re.IGNORECASE)
            return subj.strip()
        
        normalized_reply = normalize_subject(reply_subject)
        normalized_original = normalize_subject(original_subject)
        
        # Check if reply subject starts with "Re:" or matches original
        if reply_subject.lower().startswith(('re:', 'fwd:')):
            return True
        
        # Check if normalized subjects match
        if normalized_reply.lower() == normalized_original.lower():
            return True
        
        # Check if normalized reply contains normalized original (common for long subjects)
        if len(normalized_original) > 10 and normalized_original.lower() in normalized_reply.lower():
            return True
        
        return False
    
    def _redact_sensitive_content(self, text: str) -> str:
        """
        Redact sensitive information that might violate OpenAI usage policies
        
        Removes:
        - Passwords, API keys, tokens
        - SSN mentions
        - Phone numbers
        - Zoom links with passwords
        - Physical addresses (optional - can be kept if needed)
        """
        if not text:
            return text
        
        result = text
        
        # Redact passwords in various formats
        # Pattern: password: xxxx or password=xxxx or password is xxxx
        result = re.sub(
            r'(?:password|pwd|passwd|api[_-]?key|secret[_-]?key|token|credential).*?:[=\s]*([^\s\n]{4,})',
            r'[REDACTED_CREDENTIAL]',
            result,
            flags=re.IGNORECASE
        )
        
        # Redact username:password patterns
        result = re.sub(
            r'(?:username|user)[\s:]+[\w-]+[\s:,]+(?:password|pwd)[\s:]+[^\s\n]+',
            r'[REDACTED_CREDENTIAL]',
            result,
            flags=re.IGNORECASE
        )
        
        # Redact SSN mentions (Social Security Number)
        # Match various formats: SSN, social security, SSN number, etc.
        # More comprehensive pattern to catch "social security" even without "number"
        result = re.sub(
            r'\bSSN\s*(?:appointment|number|card|update)?\b|\bsocial\s+security\s*(?:number|card|appointment|appointment)?\b|\b\d{3}-\d{2}-\d{4}\b',
            r'[REDACTED_SSN]',
            result,
            flags=re.IGNORECASE
        )
        
        # Also redact common phrases around SSN
        result = re.sub(
            r'(?:in-person\s+)?(?:SSN|social\s+security)\s+(?:appointment|office\s+visit|application)',
            r'[REDACTED_SSN_APPOINTMENT]',
            result,
            flags=re.IGNORECASE
        )
        
        # Catch phrases like "my social security appointment" 
        result = re.sub(
            r'\b(?:my|your|his|her|their)\s+social\s+security\s+(?:appointment|card|number)',
            r'[REDACTED_SSN_APPOINTMENT]',
            result,
            flags=re.IGNORECASE
        )
        
        # Redact phone numbers (various formats)
        # More comprehensive pattern to catch all phone formats
        result = re.sub(
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\(\d{3}\)\s*\d{3}[-.\s]?\d{4}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            r'[REDACTED_PHONE]',
            result
        )
        
        # Redact Zoom links with passwords (keep link structure but remove pwd parameter)
        result = re.sub(
            r'(https?://[^\s]*zoom\.us/[^\s]*)\?pwd=[^\s&\n]+',
            r'\1',
            result,
            flags=re.IGNORECASE
        )
        
        # Redact other meeting links with passwords
        result = re.sub(
            r'(https?://[^\s]*(?:zoom|meet|teams|webex|gotomeeting)[^\s]*)\?[^\s]*pwd=[^\s&\n]+',
            r'\1',
            result,
            flags=re.IGNORECASE
        )
        
        # Redact long alphanumeric tokens that might be credentials
        # (but be careful not to redact legitimate IDs like order numbers)
        result = re.sub(
            r'\b(?:token|key|secret|credential)[\s:=]+([A-Za-z0-9]{20,})\b',
            r'[REDACTED_TOKEN]',
            result,
            flags=re.IGNORECASE
        )
        
        # Redact standalone "token" mentions in suspicious contexts
        # (but keep it if it's clearly about something else)
        if re.search(r'\btoken\b', result, re.IGNORECASE):
            # If "token" appears near credential-related words, redact
            result = re.sub(
                r'\b(?:access\s+)?token\b(?![^\s]*[:=])',
                r'[REDACTED_TOKEN]',
                result,
                flags=re.IGNORECASE
            )
        
        return result
    
    def _clean_email_body(self, body: str) -> str:
        """Clean email body text and redact sensitive content"""
        if not body:
            return ""
        
        # First, redact sensitive content
        body = self._redact_sensitive_content(body)
        
        # Remove email headers/quoted replies
        # Look for common email quote markers
        quote_patterns = [
            r'On .* wrote:.*',
            r'From:.*',
            r'To:.*',
            r'Sent:.*',
            r'Subject:.*',
            r'-----Original Message-----.*',
            r'________________________________.*',
        ]
        
        for pattern in quote_patterns:
            body = re.sub(pattern, '', body, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove excessive whitespace
        body = re.sub(r'\n{3,}', '\n\n', body)
        body = re.sub(r' {2,}', ' ', body)
        
        return body.strip()


def main():
    """Main formatter function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Format data for OpenAI fine-tuning')
    parser.add_argument('--synthetic-file', type=str, help='Synthetic conversations JSON file')
    parser.add_argument('--gmail-file', type=str, help='Gmail export JSON file')
    parser.add_argument('--output-file', type=str, required=True, help='Output JSONL file')
    parser.add_argument('--system-message', type=str, 
                       default="You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context.")
    
    args = parser.parse_args()
    
    formatter = OpenAIFormatter()
    
    if args.synthetic_file:
        formatter.format_synthetic_to_openai(
            args.synthetic_file,
            args.output_file,
            args.system_message
        )
    
    if args.gmail_file:
        formatter.format_gmail_to_openai(
            args.gmail_file,
            args.output_file,
            args.system_message
        )


if __name__ == '__main__':
    main()

