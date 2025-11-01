"""
Gmail Dataset Creation Script
Scrapes Gmail sent emails and formats them into a Hugging Face Dataset for fine-tuning with unsloth.
"""

import os
import base64
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from email.utils import parsedate_to_datetime

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pickle
except ImportError:
    print("Please install required packages: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

from datasets import Dataset
import html2text

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configuration
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
MAX_EMAILS = 10000  # Limit to prevent memory issues
OUTPUT_DATASET_PATH = 'gmail_dataset'


def authenticate_gmail():
    """
    Authenticate and return Gmail service object.
    Requires credentials.json file from Google Cloud Console.
    """
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials, prompt user to authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. Please download it from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/\n"
                    "2. Create a new project or select existing one\n"
                    "3. Enable Gmail API\n"
                    "4. Create OAuth 2.0 credentials\n"
                    "5. Download credentials.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)


def decode_message_body(message_body: Dict) -> str:
    """Decode email message body from base64."""
    if 'data' in message_body:
        data = message_body['data']
    else:
        return ""
    
    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')


def extract_text_from_html(html_content: str) -> str:
    """Convert HTML email content to plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html_content).strip()


def get_email_content(message: Dict) -> Dict[str, str]:
    """
    Extract email content from message.
    Returns a dictionary with text and html content.
    """
    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    
    text_content = ""
    html_content = ""
    
    # Check if message has a body directly
    if 'body' in payload:
        if payload['body'].get('size', 0) > 0:
            if payload['mimeType'] == 'text/plain':
                text_content = decode_message_body(payload['body'])
            elif payload['mimeType'] == 'text/html':
                html_content = decode_message_body(payload['body'])
    
    # If multipart, extract from parts
    for part in parts:
        mime_type = part.get('mimeType', '')
        body = part.get('body', {})
        
        if mime_type == 'text/plain' and body.get('size', 0) > 0:
            text_content = decode_message_body(body)
        elif mime_type == 'text/html' and body.get('size', 0) > 0:
            html_content = decode_message_body(body)
        
        # Handle nested parts
        if 'parts' in part:
            for nested_part in part['parts']:
                nested_mime = nested_part.get('mimeType', '')
                nested_body = nested_part.get('body', {})
                
                if nested_mime == 'text/plain' and nested_body.get('size', 0) > 0:
                    text_content = decode_message_body(nested_body)
                elif nested_mime == 'text/html' and nested_body.get('size', 0) > 0:
                    html_content = decode_message_body(nested_body)
    
    # Prefer text, fallback to HTML converted to text
    final_text = text_content if text_content else extract_text_from_html(html_content) if html_content else ""
    
    return {
        'text': final_text,
        'html': html_content
    }


def extract_headers(message: Dict) -> Dict[str, str]:
    """Extract email headers."""
    headers = message.get('payload', {}).get('headers', [])
    header_dict = {}
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        header_dict[name] = value
    return header_dict


def get_replied_to_email(service, message: Dict) -> Optional[Dict]:
    """
    Check if this email is a reply and fetch the original email it's replying to.
    Uses thread information to find the original email in the conversation.
    Returns the original email data or None if not a reply.
    """
    headers = extract_headers(message)
    
    # Check if this is a reply using In-Reply-To or References header
    in_reply_to = headers.get('in-reply-to', '')
    references = headers.get('references', '')
    
    if not in_reply_to and not references:
        return None
    
    thread_id = message.get('threadId', '')
    if not thread_id:
        return None
    
    try:
        # Get all messages in the thread
        thread = service.users().threads().get(userId='me', id=thread_id, format='full').execute()
        thread_messages = thread.get('messages', [])
        
        if len(thread_messages) < 2:
            # Single message in thread, not a reply
            return None
        
        # Find the current message index
        current_msg_id = message.get('id', '')
        current_index = -1
        for i, msg in enumerate(thread_messages):
            if msg['id'] == current_msg_id:
                current_index = i
                break
        
        if current_index <= 0:
            # First message or not found, not a reply
            return None
        
        # Get the previous message in the thread (the one we're replying to)
        # We need to find the most recent received (non-sent) message before this one
        original_msg = None
        
        # Look backwards through thread to find the email we're replying to
        for i in range(current_index - 1, -1, -1):
            prev_msg = thread_messages[i]
            prev_msg_full = service.users().messages().get(
                userId='me', 
                id=prev_msg['id'], 
                format='full'
            ).execute()
            
            # Check if this message is a received email (not sent by us)
            # Messages we sent have "SENT" label, received ones don't
            labels = prev_msg_full.get('labelIds', [])
            if 'SENT' not in labels:
                # This is a received email - the one we're replying to
                original_msg = prev_msg_full
                break
        
        if not original_msg:
            return None
        
        # Extract content from original message
        original_headers = extract_headers(original_msg)
        original_content = get_email_content(original_msg)
        
        # Get date
        date_str = original_headers.get('date', '')
        if date_str:
            try:
                date_obj = parsedate_to_datetime(date_str)
                date_str = date_obj.isoformat()
            except:
                pass
        
        return {
            'id': original_msg['id'],
            'headers': original_headers,
            'content': original_content,
            'date': date_str,
            'subject': original_headers.get('subject', 'No Subject'),
            'from': original_headers.get('from', 'Unknown Sender')
        }
    except HttpError as error:
        # If we can't find the original email, return None silently
        return None
    except Exception as e:
        # Silently fail if we can't fetch the original email
        return None


def format_for_unsloth(email_data: Dict, original_email: Optional[Dict] = None) -> Dict:
    """
    Format email data into a format suitable for unsloth fine-tuning.
    Uses chat format with system/user/assistant messages.
    If original_email is provided, includes it in the context.
    """
    headers = email_data['headers']
    content = email_data['content']
    date = email_data.get('date', '')
    subject = headers.get('subject', 'No Subject')
    to = headers.get('to', 'Unknown Recipient')
    
    # Extract recipient name if possible
    recipient = to
    if '<' in to and '>' in to:
        # Extract email address
        recipient = re.search(r'<(.+?)>', to).group(1) if re.search(r'<(.+?)>', to) else to
    else:
        # Just the email address
        recipient = to.split(',')[0].strip()
    
    # Build context with original email if available
    context_parts = [f"Recipient: {recipient}", f"Subject: {subject}", f"Date: {date}"]
    
    if original_email:
        # Include original email in context
        original_sender = original_email.get('from', 'Unknown')
        original_subject = original_email.get('subject', 'No Subject')
        original_content = original_email.get('content', {}).get('text', '')
        original_date = original_email.get('date', '')
        
        # Extract sender name/email
        sender = original_sender
        if '<' in original_sender and '>' in original_sender:
            sender = re.search(r'<(.+?)>', original_sender).group(1) if re.search(r'<(.+?)>', original_sender) else original_sender
        else:
            sender = original_sender.split(',')[0].strip()
        
        # Add original email context
        context_parts.append(f"\n\nThis is a reply to an email from {sender} dated {original_date} with subject '{original_subject}':")
        context_parts.append(f"\n--- Original Email ---")
        context_parts.append(f"From: {sender}")
        context_parts.append(f"Subject: {original_subject}")
        context_parts.append(f"Date: {original_date}")
        context_parts.append(f"\nContent:\n{original_content[:10000]}")  # Limit to 2000 chars to avoid overly long contexts
        context_parts.append(f"\n--- End Original Email ---")
    
    # Get the actual email content
    email_content = content['text']
    
    # Clean up the email content - remove common reply markers/quoted text if present
    email_content = email_content.strip()
    
    # Try to remove quoted/replied content (common patterns like "On [date] wrote:")
    lines = email_content.split('\n')
    cleaned_lines = []
    skip_quoted = False
    for line in lines:
        # Common reply patterns
        if re.match(r'^On .+ wrote:', line, re.IGNORECASE):
            skip_quoted = True
        elif re.match(r'^From:.*$', line, re.IGNORECASE) and skip_quoted:
            continue
        elif re.match(r'^Sent:.*$', line, re.IGNORECASE) and skip_quoted:
            continue
        elif re.match(r'^To:.*$', line, re.IGNORECASE) and skip_quoted:
            continue
        elif re.match(r'^Subject:.*$', line, re.IGNORECASE) and skip_quoted:
            continue
        elif line.strip().startswith('>') or line.strip().startswith('|'):
            # Skip quoted lines
            continue
        else:
            if skip_quoted and line.strip() == '':
                # Empty line after quoted content - stop skipping
                skip_quoted = False
            if not skip_quoted:
                cleaned_lines.append(line)
    
    email_content = '\n'.join(cleaned_lines).strip()
    
    if not email_content:
        return None
    
    # Build the complete system message with all context and the email content
    system_message = f"You are writing an email. Context: {'; '.join(context_parts[:3])}"
    if original_email:
        system_message += ''.join(context_parts[3:])  # Include original email in system message
    
    # Append the actual email content to the system message
    system_message += f"\n\n--- Email to Write ---\n{email_content}"
    
    return {
        "messages": [
            {"role": "system", "content": system_message}
        ],
        # Additional metadata for filtering/analysis
        "metadata": {
            "subject": subject,
            "recipient": recipient,
            "date": date,
            "email_id": email_data.get('id', ''),
            "is_reply": original_email is not None,
            "original_email_id": original_email.get('id') if original_email else None
        }
    }


def fetch_all_sent_emails(service, max_results: int = MAX_EMAILS) -> List[Dict]:
    """
    Fetch all sent emails from Gmail.
    """
    print("Fetching sent emails from Gmail...")
    all_messages = []
    
    try:
        # Search for sent emails
        query = 'in:sent'
        results = service.users().messages().list(userId='me', q=query, maxResults=500).execute()
        messages = results.get('messages', [])
        
        page_token = results.get('nextPageToken')
        total_fetched = 0
        
        while messages and total_fetched < max_results:
            for msg in messages:
                if total_fetched >= max_results:
                    break
                
                try:
                    # Get full message
                    message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    
                    # Extract email data
                    headers = extract_headers(message)
                    content = get_email_content(message)
                    
                    # Get date
                    date_str = headers.get('date', '')
                    date_obj = None
                    if date_str:
                        try:
                            date_obj = parsedate_to_datetime(date_str)
                            date_str = date_obj.isoformat()
                        except:
                            pass
                    
                    email_data = {
                        'id': msg['id'],
                        'headers': headers,
                        'content': content,
                        'date': date_str,
                        'thread_id': message.get('threadId', '')
                    }
                    
                    # Check if this is a reply and fetch the original email
                    original_email = get_replied_to_email(service, message)
                    if original_email:
                        email_data['original_email'] = original_email
                    
                    all_messages.append(email_data)
                    total_fetched += 1
                    
                    if total_fetched % 50 == 0:
                        replies_count = sum(1 for e in all_messages if 'original_email' in e)
                        print(f"Fetched {total_fetched} emails... ({replies_count} replies found)")
                    
                except HttpError as error:
                    print(f"An error occurred fetching message {msg['id']}: {error}")
                    continue
            
            # Fetch next page if available
            if page_token and total_fetched < max_results:
                results = service.users().messages().list(
                    userId='me', 
                    q=query, 
                    maxResults=500,
                    pageToken=page_token
                ).execute()
                messages = results.get('messages', [])
                page_token = results.get('nextPageToken')
            else:
                break
        
        replies_count = sum(1 for e in all_messages if 'original_email' in e)
        print(f"Total emails fetched: {total_fetched}")
        print(f"Emails with replies found: {replies_count} ({replies_count/total_fetched*100:.1f}%)" if total_fetched > 0 else "")
        return all_messages
        
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def create_dataset(emails: List[Dict], output_path: str = OUTPUT_DATASET_PATH) -> Dataset:
    """
    Create Hugging Face Dataset from email data.
    """
    print("Formatting emails for unsloth fine-tuning...")
    formatted_data = []
    
    for email in emails:
        # Get original email if this is a reply
        original_email = email.get('original_email')
        formatted = format_for_unsloth(email, original_email=original_email)
        if formatted and formatted['messages'][0]['content']:  # Ensure system message content exists
            formatted_data.append(formatted)
    
    print(f"Formatted {len(formatted_data)} emails into training examples")
    
    # Create dataset
    dataset = Dataset.from_list(formatted_data)
    
    # Save dataset
    dataset.save_to_disk(output_path)
    print(f"Dataset saved to {output_path}/")
    
    # Also save as JSON for easy inspection
    json_path = f"{output_path}_json.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data[:100], f, indent=2, ensure_ascii=False)  # Save first 100 as sample
    print(f"Sample dataset (first 100 examples) saved to {json_path}")
    
    return dataset


def main():
    """Main function to scrape Gmail and create dataset."""
    print("=" * 60)
    print("Gmail Dataset Creation for Unsloth Fine-tuning")
    print("=" * 60)
    
    try:
        # Authenticate Gmail
        print("\nStep 1: Authenticating Gmail API...")
        service = authenticate_gmail()
        print("✓ Authentication successful")
        
        # Fetch emails
        print("\nStep 2: Fetching sent emails...")
        emails = fetch_all_sent_emails(service, max_results=MAX_EMAILS)
        
        if not emails:
            print("No emails found or error occurred.")
            return
        
        # Create dataset
        print("\nStep 3: Creating Hugging Face Dataset...")
        dataset = create_dataset(emails, OUTPUT_DATASET_PATH)
        
        # Print dataset info
        print("\n" + "=" * 60)
        print("Dataset Creation Complete!")
        print("=" * 60)
        print(f"Total examples: {len(dataset)}")
        print(f"Dataset saved to: {OUTPUT_DATASET_PATH}/")
        print("\nTo load the dataset:")
        print(f"  from datasets import load_from_disk")
        print(f"  dataset = load_from_disk('{OUTPUT_DATASET_PATH}')")
        print("\nDataset format (suitable for unsloth):")
        print("  - Each example has 'messages' field with only system role")
        print("  - System message contains all context including original email (if reply) and email content")
        print("  - Ready for fine-tuning with unsloth library")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

