#!/usr/bin/env python3
"""
Gmail Data Extraction Script
Extracts emails using Google Gmail API and converts to structured format
"""
import os
import json
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from email.utils import parsedate_to_datetime
import html2text

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("⚠️  Installing google-auth-oauthlib and google-api-python-client...")
    print("Run: pip install google-auth-oauthlib google-api-python-client")
    raise

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailExtractor:
    """Extract and process Gmail messages using Gmail API"""
    
    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.pickle",
        output_dir: str = "data/gmail"
    ):
        """
        Initialize Gmail extractor
        
        Args:
            credentials_file: Path to Google OAuth2 credentials JSON file
            token_file: Path to store authentication token
            output_dir: Directory to save extracted emails
        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.service = None
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            try:
                import pickle
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"⚠️  Could not load token: {e}")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing access token...")
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    print(f"❌ Credentials file not found: {self.credentials_file}")
                    print("📝 Please download credentials.json from Google Cloud Console:")
                    print("   1. Go to https://console.cloud.google.com/")
                    print("   2. Create a project and enable Gmail API")
                    print("   3. Create OAuth 2.0 credentials (Desktop app)")
                    print("   4. Download and save as 'credentials.json'")
                    return False
                
                print("🔐 Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save token for future use
            try:
                import pickle
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
                print("✅ Authentication token saved")
            except Exception as e:
                print(f"⚠️  Could not save token: {e}")
        
        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            print("✅ Gmail API authenticated successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to build Gmail service: {e}")
            return False
    
    def extract_message_data(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and parse message data"""
        try:
            msg_id = message['id']
            
            # Get full message
            full_message = self.service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()
            
            headers = full_message['payload'].get('headers', [])
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_addr = next((h['value'] for h in headers if h['name'] == 'From'), '')
            to_addr = next((h['value'] for h in headers if h['name'] == 'To'), '')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Parse date
            try:
                date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except:
                date = datetime.now()
            
            # Extract body
            body = self._extract_body(full_message['payload'])
            
            # Determine if sent or received
            # Simple heuristic: if 'me' email is in From, it's sent
            # You may need to adjust this based on your email
            is_sent = 'me' in from_addr.lower() or self._is_sent_message(full_message)
            
            return {
                'id': msg_id,
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'date': date.isoformat(),
                'body': body,
                'is_sent': is_sent,
                'thread_id': full_message.get('threadId', ''),
                'snippet': full_message.get('snippet', ''),
            }
            
        except Exception as e:
            print(f"⚠️  Error extracting message {message.get('id', 'unknown')}: {e}")
            return None
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload"""
        body = ""
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    data = part['body'].get('data', '')
                    if data:
                        html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        body += self.html_converter.handle(html)
                elif 'parts' in part:
                    # Nested parts
                    body += self._extract_body(part)
        else:
            # Simple message
            mime_type = payload.get('mimeType', '')
            data = payload['body'].get('data', '')
            
            if data:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                if mime_type == 'text/html':
                    body = self.html_converter.handle(decoded)
                else:
                    body = decoded
        
        # Clean up body
        body = self._clean_body(body)
        return body
    
    def _clean_body(self, body: str) -> str:
        """Clean and normalize message body"""
        # Remove excessive whitespace
        body = re.sub(r'\n{3,}', '\n\n', body)
        
        # Remove email signatures (simple heuristic)
        # Look for common signature patterns
        signature_patterns = [
            r'--\s*\n.*',
            r'Best regards,.*',
            r'Regards,.*',
            r'Sent from.*',
        ]
        
        for pattern in signature_patterns:
            body = re.sub(pattern, '', body, flags=re.DOTALL | re.IGNORECASE)
        
        return body.strip()
    
    def _is_sent_message(self, message: Dict[str, Any]) -> bool:
        """Determine if message was sent by user"""
        label_ids = message.get('labelIds', [])
        return 'SENT' in label_ids
    
    def extract_emails(
        self,
        max_results: int = 5000,
        query: str = '',
        include_sent: bool = True,
        include_received: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract emails from Gmail
        
        Args:
            max_results: Maximum number of emails to extract
            query: Gmail search query (e.g., 'is:unread', 'after:2024/1/1')
            include_sent: Include sent emails
            include_received: Include received emails
        """
        if not self.service:
            print("❌ Not authenticated. Call authenticate() first.")
            return []
        
        all_messages = []
        
        try:
            # Build query
            queries = []
            if include_sent:
                queries.append('in:sent')
            if include_received:
                queries.append('-in:sent')
            
            base_query = ' OR '.join(queries) if len(queries) > 1 else queries[0] if queries else ''
            full_query = f"{base_query} {query}".strip()
            
            print(f"🔍 Searching Gmail with query: '{full_query}'")
            
            # List messages
            results = self.service.users().messages().list(
                userId='me',
                q=full_query,
                maxResults=min(max_results, 500)  # Gmail API limit
            ).execute()
            
            messages = results.get('messages', [])
            total_found = len(messages)
            
            # Get all pages if needed
            while 'nextPageToken' in results and len(all_messages) < max_results:
                results = self.service.users().messages().list(
                    userId='me',
                    q=full_query,
                    maxResults=min(max_results - len(all_messages), 500),
                    pageToken=results['nextPageToken']
                ).execute()
                messages.extend(results.get('messages', []))
            
            print(f"📧 Found {len(messages)} messages")
            
            # Extract message data
            for i, message in enumerate(messages[:max_results]):
                if (i + 1) % 100 == 0:
                    print(f"⏳ Processing message {i + 1}/{len(messages[:max_results])}...")
                
                message_data = self.extract_message_data(message)
                if message_data:
                    all_messages.append(message_data)
            
            print(f"✅ Extracted {len(all_messages)} emails")
            return all_messages
            
        except HttpError as error:
            print(f"❌ Gmail API error: {error}")
            return []
    
    def save_emails(
        self,
        messages: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> str:
        """Save extracted emails to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"gmail_export_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        output = {
            'extracted_at': datetime.now().isoformat(),
            'total_messages': len(messages),
            'messages': messages
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(messages)} emails to {filepath}")
        return str(filepath)


def main():
    """Main extraction function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract Gmail data')
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
        help='Path to save/load authentication token'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/gmail',
        help='Output directory for extracted emails'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        default=5000,
        help='Maximum number of emails to extract'
    )
    parser.add_argument(
        '--query',
        type=str,
        default='',
        help='Gmail search query (e.g., "after:2024/1/1")'
    )
    parser.add_argument(
        '--no-sent',
        action='store_true',
        help='Exclude sent emails'
    )
    parser.add_argument(
        '--no-received',
        action='store_true',
        help='Exclude received emails'
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = GmailExtractor(
        credentials_file=args.credentials,
        token_file=args.token,
        output_dir=args.output_dir
    )
    
    # Authenticate
    if not extractor.authenticate():
        print("❌ Authentication failed")
        return
    
    # Extract emails
    messages = extractor.extract_emails(
        max_results=args.max_results,
        query=args.query,
        include_sent=not args.no_sent,
        include_received=not args.no_received
    )
    
    # Save results
    if messages:
        extractor.save_emails(messages)
        print("\n✅ Gmail extraction complete!")
        print(f"📊 Statistics:")
        sent_count = sum(1 for m in messages if m.get('is_sent', False))
        received_count = len(messages) - sent_count
        print(f"   Sent: {sent_count}")
        print(f"   Received: {received_count}")
    else:
        print("⚠️  No messages extracted")


if __name__ == '__main__':
    main()

