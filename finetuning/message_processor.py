#!/usr/bin/env python3
"""
Message Processing Script
Processes exported iMessage, WhatsApp, and other message data
Supports CSV, JSON, XML, and text exports
"""
import json
import csv
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class MessageProcessor:
    """Process exported message data from various platforms"""
    
    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_imessage_export(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Process iMessage export (typically CSV format from iPhone backup tools)
        
        Expected CSV format:
        - Columns: date, sender, message, chat_id, etc.
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"iMessage export not found: {filepath}")
        
        messages = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row in reader:
                    # Map common column names
                    date_str = row.get('date') or row.get('Date') or row.get('timestamp') or row.get('Timestamp')
                    sender = row.get('sender') or row.get('Sender') or row.get('from') or row.get('From')
                    content = row.get('message') or row.get('Message') or row.get('text') or row.get('Text') or row.get('body') or row.get('Body')
                    
                    if not content or not content.strip():
                        continue
                    
                    # Parse date
                    try:
                        date = self._parse_date(date_str)
                    except:
                        date = datetime.now()
                    
                    messages.append({
                        'platform': 'imessage',
                        'sender': sender or 'Unknown',
                        'content': content.strip(),
                        'timestamp': date.isoformat(),
                        'message_type': 'text',
                        'metadata': row
                    })
            
            print(f"✅ Processed {len(messages)} iMessage messages")
            return messages
            
        except Exception as e:
            print(f"❌ Error processing iMessage export: {e}")
            return []
    
    def process_whatsapp_export(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Process WhatsApp export (typically .txt format)
        
        Expected format:
        [DD/MM/YYYY, HH:MM:SS] Sender: Message text
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"WhatsApp export not found: {filepath}")
        
        messages = []
        
        # WhatsApp export regex pattern
        # Format: [DD/MM/YYYY, HH:MM:SS] Sender: Message
        pattern = re.compile(
            r'\[(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2}:\d{2}:\d{2})\]\s*(.+?):\s*(.+)',
            re.MULTILINE
        )
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by date pattern to handle multi-line messages
            lines = content.split('\n')
            current_message = None
            current_sender = None
            current_date = None
            current_time = None
            message_text = []
            
            for line in lines:
                match = pattern.match(line)
                
                if match:
                    # Save previous message if exists
                    if current_message and message_text:
                        messages.append({
                            'platform': 'whatsapp',
                            'sender': current_sender or 'Unknown',
                            'content': '\n'.join(message_text).strip(),
                            'timestamp': self._parse_whatsapp_datetime(current_date, current_time),
                            'message_type': 'text',
                            'metadata': {}
                        })
                        message_text = []
                    
                    # Start new message
                    current_date = match.group(1)
                    current_time = match.group(2)
                    current_sender = match.group(3)
                    message_text = [match.group(4)]
                    current_message = match.group(0)
                else:
                    # Continuation of previous message (multi-line)
                    if message_text:
                        message_text.append(line.strip())
            
            # Save last message
            if current_message and message_text:
                messages.append({
                    'platform': 'whatsapp',
                    'sender': current_sender or 'Unknown',
                    'content': '\n'.join(message_text).strip(),
                    'timestamp': self._parse_whatsapp_datetime(current_date, current_time),
                    'message_type': 'text',
                    'metadata': {}
                })
            
            print(f"✅ Processed {len(messages)} WhatsApp messages")
            return messages
            
        except Exception as e:
            print(f"❌ Error processing WhatsApp export: {e}")
            return []
    
    def process_json_export(self, filepath: str) -> List[Dict[str, Any]]:
        """Process generic JSON export"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"JSON export not found: {filepath}")
        
        messages = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle various JSON structures
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common keys
                items = data.get('messages', data.get('data', data.get('items', [data])))
            else:
                items = [data]
            
            for item in items:
                if isinstance(item, dict):
                    # Try to extract common fields
                    sender = item.get('sender') or item.get('from') or item.get('author') or 'Unknown'
                    content = item.get('content') or item.get('message') or item.get('text') or item.get('body') or ''
                    
                    if not content or not str(content).strip():
                        continue
                    
                    # Parse date
                    date_str = item.get('date') or item.get('timestamp') or item.get('time')
                    try:
                        date = self._parse_date(date_str) if date_str else datetime.now()
                    except:
                        date = datetime.now()
                    
                    messages.append({
                        'platform': item.get('platform', 'unknown'),
                        'sender': str(sender),
                        'content': str(content).strip(),
                        'timestamp': date.isoformat(),
                        'message_type': item.get('message_type', 'text'),
                        'metadata': item
                    })
            
            print(f"✅ Processed {len(messages)} messages from JSON")
            return messages
            
        except Exception as e:
            print(f"❌ Error processing JSON export: {e}")
            return []
    
    def process_xml_export(self, filepath: str) -> List[Dict[str, Any]]:
        """Process XML export (e.g., SMS backup)"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"XML export not found: {filepath}")
        
        messages = []
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Common XML structures for SMS/message backups
            # Try different possible structures
            message_elements = root.findall('.//sms') or root.findall('.//message') or root.findall('.//Message')
            
            for elem in message_elements:
                sender = elem.get('address') or elem.get('sender') or elem.get('from') or 'Unknown'
                content = elem.text or elem.get('body') or elem.get('text') or ''
                
                if not content or not content.strip():
                    continue
                
                date_str = elem.get('date') or elem.get('timestamp') or elem.get('time')
                try:
                    # XML dates are often in milliseconds
                    if date_str:
                        try:
                            date = datetime.fromtimestamp(int(date_str) / 1000)
                        except:
                            date = self._parse_date(date_str)
                    else:
                        date = datetime.now()
                except:
                    date = datetime.now()
                
                messages.append({
                    'platform': 'sms',
                    'sender': sender,
                    'content': content.strip(),
                    'timestamp': date.isoformat(),
                    'message_type': 'text',
                    'metadata': {k: v for k, v in elem.attrib.items()}
                })
            
            print(f"✅ Processed {len(messages)} messages from XML")
            return messages
            
        except Exception as e:
            print(f"❌ Error processing XML export: {e}")
            return []
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date string in various formats"""
        if not date_str:
            return datetime.now()
        
        date_str = str(date_str).strip()
        
        # Common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y/%m/%d %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # Try timestamp
        try:
            timestamp = float(date_str)
            if timestamp > 1e10:  # Milliseconds
                return datetime.fromtimestamp(timestamp / 1000)
            else:  # Seconds
                return datetime.fromtimestamp(timestamp)
        except:
            pass
        
        # Fallback
        return datetime.now()
    
    def _parse_whatsapp_datetime(self, date_str: Optional[str], time_str: Optional[str]) -> str:
        """Parse WhatsApp date/time format"""
        if not date_str or not time_str:
            return datetime.now().isoformat()
        
        try:
            # WhatsApp format: DD/MM/YYYY, HH:MM:SS
            dt_str = f"{date_str} {time_str}"
            dt = datetime.strptime(dt_str, '%d/%m/%Y %H:%M:%S')
            return dt.isoformat()
        except:
            return datetime.now().isoformat()
    
    def save_processed(self, messages: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """Save processed messages to JSON"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"processed_messages_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        output = {
            'processed_at': datetime.now().isoformat(),
            'total_messages': len(messages),
            'messages': messages
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(messages)} processed messages to {filepath}")
        return str(filepath)


def main():
    """Main processing function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process exported message data')
    parser.add_argument(
        'input_file',
        type=str,
        help='Path to exported message file'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['auto', 'imessage', 'whatsapp', 'json', 'xml'],
        default='auto',
        help='Input file format (auto-detect if not specified)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/processed',
        help='Output directory'
    )
    
    args = parser.parse_args()
    
    processor = MessageProcessor(output_dir=args.output_dir)
    
    # Auto-detect format
    if args.format == 'auto':
        filepath = Path(args.input_file)
        ext = filepath.suffix.lower()
        
        if ext == '.csv':
            args.format = 'imessage'
        elif ext == '.txt':
            args.format = 'whatsapp'
        elif ext == '.json':
            args.format = 'json'
        elif ext == '.xml':
            args.format = 'xml'
        else:
            print(f"⚠️  Unknown file extension: {ext}")
            print("   Trying JSON format...")
            args.format = 'json'
    
    # Process based on format
    messages = []
    try:
        if args.format == 'imessage':
            messages = processor.process_imessage_export(args.input_file)
        elif args.format == 'whatsapp':
            messages = processor.process_whatsapp_export(args.input_file)
        elif args.format == 'json':
            messages = processor.process_json_export(args.input_file)
        elif args.format == 'xml':
            messages = processor.process_xml_export(args.input_file)
        
        # Save processed messages
        if messages:
            processor.save_processed(messages)
            print("\n✅ Message processing complete!")
            print(f"📊 Processed {len(messages)} messages")
        else:
            print("⚠️  No messages processed")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()

