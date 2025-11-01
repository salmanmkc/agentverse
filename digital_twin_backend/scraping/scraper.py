"""
Social Media Scraping System for Fine-tuning Data Collection
Scrapes WhatsApp, LinkedIn, and X (Twitter) messages with user consent
"""
import asyncio
import json
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config.settings import settings


@dataclass
class ScrapedMessage:
    """Container for scraped message data"""
    platform: str
    sender: str
    content: str
    timestamp: datetime
    message_type: str  # text, image, file, etc.
    conversation_id: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapedMessage':
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ConsentRecord:
    """Record of user consent for data scraping"""
    person_name: str
    email: str
    platforms: List[str]
    consent_date: datetime
    consent_token: str
    expires_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if consent is still valid"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['consent_date'] = self.consent_date.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsentRecord':
        """Create from dictionary"""
        data = data.copy()
        data['consent_date'] = datetime.fromisoformat(data['consent_date'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class SocialMediaScraper:
    """Main scraper class for collecting fine-tuning data"""
    
    def __init__(self, person_name: str, consent_token: str):
        self.person_name = person_name
        self.consent_token = consent_token
        self.driver: Optional[webdriver.Chrome] = None
        self.scraped_messages: List[ScrapedMessage] = []
        
        # Data storage
        self.data_dir = Path("data/scraped")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Scraping settings
        self.max_messages_per_platform = 1000
        self.scraping_delay = 2  # seconds between requests
        
        # Platform handlers
        self.platform_handlers = {
            "whatsapp": self._scrape_whatsapp_web,
            "linkedin": self._scrape_linkedin_messages,
            "twitter": self._scrape_twitter_dms
        }
        
    async def initialize_driver(self) -> None:
        """Initialize Selenium WebDriver"""
        
        try:
            chrome_options = Options()
            
            if settings.SELENIUM_HEADLESS:
                chrome_options.add_argument("--headless")
                
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User data directory for persistent sessions
            user_data_dir = Path(f"data/browser_profiles/{self.person_name}")
            user_data_dir.mkdir(parents=True, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"✅ Selenium WebDriver initialized for {self.person_name}")
            
        except Exception as e:
            print(f"❌ Failed to initialize WebDriver: {e}")
            raise
    
    async def scrape_platform(self, platform: str) -> List[ScrapedMessage]:
        """Scrape messages from a specific platform"""
        
        if platform not in self.platform_handlers:
            raise ValueError(f"Unsupported platform: {platform}")
        
        print(f"🔍 Starting {platform} scrape for {self.person_name}")
        
        # Verify consent
        if not await self._verify_consent(platform):
            raise PermissionError(f"No valid consent for {platform} scraping")
        
        # Initialize driver if not already done
        if not self.driver:
            await self.initialize_driver()
        
        try:
            # Call platform-specific handler
            handler = self.platform_handlers[platform]
            messages = await handler()
            
            print(f"✅ Scraped {len(messages)} messages from {platform}")
            return messages
            
        except Exception as e:
            print(f"❌ {platform} scraping failed: {e}")
            return []
    
    async def scrape_all_platforms(self, platforms: List[str] = None) -> Dict[str, List[ScrapedMessage]]:
        """Scrape messages from all specified platforms"""
        
        if platforms is None:
            platforms = ["whatsapp", "linkedin", "twitter"]
        
        results = {}
        
        for platform in platforms:
            try:
                messages = await self.scrape_platform(platform)
                results[platform] = messages
                self.scraped_messages.extend(messages)
                
                # Save platform data immediately
                await self._save_platform_data(platform, messages)
                
                # Delay between platforms
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"⚠️  Skipping {platform} due to error: {e}")
                results[platform] = []
        
        return results
    
    async def _scrape_whatsapp_web(self) -> List[ScrapedMessage]:
        """Scrape WhatsApp Web messages"""
        
        messages = []
        
        try:
            # Navigate to WhatsApp Web
            self.driver.get("https://web.whatsapp.com")
            print("📱 Please scan QR code to login to WhatsApp Web...")
            
            # Wait for login (user scans QR code)
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']"))
            )
            print("✅ WhatsApp Web logged in successfully")
            
            # Get chat list
            chat_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']"))
            )
            
            chats = chat_list.find_elements(By.CSS_SELECTOR, "[data-testid='cell-frame-container']")
            print(f"📋 Found {len(chats)} chats")
            
            # Process each chat (limit to prevent overwhelming)
            for i, chat in enumerate(chats[:10]):  # Limit to 10 chats
                try:
                    # Click on chat
                    chat.click()
                    await asyncio.sleep(2)
                    
                    # Get chat name
                    try:
                        chat_name_element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='conversation-header'] span"))
                        )
                        chat_name = chat_name_element.text
                    except:
                        chat_name = f"Chat_{i}"
                    
                    print(f"💬 Scraping chat: {chat_name}")
                    
                    # Scroll up to load more messages
                    message_container = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='conversation-panel-messages']")
                    
                    # Load more messages by scrolling
                    for _ in range(5):  # Scroll 5 times
                        self.driver.execute_script("arguments[0].scrollTop = 0", message_container)
                        await asyncio.sleep(1)
                    
                    # Get messages
                    message_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='msg-container']")
                    
                    for msg_elem in message_elements:
                        try:
                            # Determine if message is sent or received
                            is_sent = "message-out" in msg_elem.get_attribute("class")
                            sender = self.person_name if is_sent else chat_name
                            
                            # Get message text
                            try:
                                text_elem = msg_elem.find_element(By.CSS_SELECTOR, ".selectable-text")
                                content = text_elem.text
                            except:
                                content = "[Non-text message]"
                            
                            if not content or len(content.strip()) == 0:
                                continue
                            
                            # Get timestamp (approximate)
                            try:
                                time_elem = msg_elem.find_element(By.CSS_SELECTOR, "[data-testid='msg-meta'] span")
                                timestamp_str = time_elem.text
                                # Parse timestamp (this is simplified - real parsing would be more robust)
                                timestamp = datetime.now()  # Placeholder
                            except:
                                timestamp = datetime.now()
                            
                            # Create message object
                            message = ScrapedMessage(
                                platform="whatsapp",
                                sender=sender,
                                content=content,
                                timestamp=timestamp,
                                message_type="text",
                                conversation_id=f"whatsapp_{chat_name}",
                                metadata={
                                    "chat_name": chat_name,
                                    "is_sent": is_sent,
                                    "raw_timestamp": timestamp_str if 'timestamp_str' in locals() else ""
                                }
                            )
                            
                            messages.append(message)
                            
                            # Limit messages per chat
                            if len(messages) >= self.max_messages_per_platform:
                                break
                                
                        except Exception as e:
                            print(f"⚠️  Error processing message: {e}")
                            continue
                    
                    if len(messages) >= self.max_messages_per_platform:
                        break
                        
                except Exception as e:
                    print(f"⚠️  Error processing chat {i}: {e}")
                    continue
            
        except TimeoutException:
            print("❌ WhatsApp Web login timeout")
        except Exception as e:
            print(f"❌ WhatsApp scraping error: {e}")
        
        return messages
    
    async def _scrape_linkedin_messages(self) -> List[ScrapedMessage]:
        """Scrape LinkedIn direct messages"""
        
        messages = []
        
        try:
            # Navigate to LinkedIn
            self.driver.get("https://www.linkedin.com/login")
            print("💼 Please login to LinkedIn...")
            
            # Wait for user to login manually
            WebDriverWait(self.driver, 120).until(
                EC.url_contains("linkedin.com/feed")
            )
            print("✅ LinkedIn logged in successfully")
            
            # Navigate to messaging
            self.driver.get("https://www.linkedin.com/messaging/")
            await asyncio.sleep(3)
            
            # Get conversation list
            try:
                conversations = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".msg-conversation-listitem"))
                )
                print(f"📋 Found {len(conversations)} LinkedIn conversations")
                
                # Process each conversation (limit to prevent overwhelming)
                for i, conv in enumerate(conversations[:10]):
                    try:
                        # Click on conversation
                        conv.click()
                        await asyncio.sleep(2)
                        
                        # Get conversation name
                        try:
                            name_elem = conv.find_element(By.CSS_SELECTOR, ".msg-conversation-listitem__participant-names")
                            conv_name = name_elem.text
                        except:
                            conv_name = f"LinkedIn_Conv_{i}"
                        
                        print(f"💬 Scraping LinkedIn conversation: {conv_name}")
                        
                        # Get messages from this conversation
                        message_elements = self.driver.find_elements(By.CSS_SELECTOR, ".msg-s-event-listitem")
                        
                        for msg_elem in message_elements:
                            try:
                                # Check if message is sent by user
                                is_sent = "msg-s-event-listitem--other" not in msg_elem.get_attribute("class")
                                sender = self.person_name if is_sent else conv_name
                                
                                # Get message content
                                try:
                                    text_elem = msg_elem.find_element(By.CSS_SELECTOR, ".msg-s-event-listitem__message-bubble p")
                                    content = text_elem.text
                                except:
                                    content = "[Non-text message]"
                                
                                if not content or len(content.strip()) == 0:
                                    continue
                                
                                # Create message object
                                message = ScrapedMessage(
                                    platform="linkedin",
                                    sender=sender,
                                    content=content,
                                    timestamp=datetime.now(),  # LinkedIn doesn't easily expose timestamps
                                    message_type="text",
                                    conversation_id=f"linkedin_{conv_name}",
                                    metadata={
                                        "conversation_name": conv_name,
                                        "is_sent": is_sent
                                    }
                                )
                                
                                messages.append(message)
                                
                                if len(messages) >= self.max_messages_per_platform:
                                    break
                                    
                            except Exception as e:
                                print(f"⚠️  Error processing LinkedIn message: {e}")
                                continue
                        
                        if len(messages) >= self.max_messages_per_platform:
                            break
                            
                    except Exception as e:
                        print(f"⚠️  Error processing LinkedIn conversation {i}: {e}")
                        continue
                
            except TimeoutException:
                print("❌ LinkedIn messaging page not loaded")
                
        except Exception as e:
            print(f"❌ LinkedIn scraping error: {e}")
        
        return messages
    
    async def _scrape_twitter_dms(self) -> List[ScrapedMessage]:
        """Scrape Twitter/X direct messages"""
        
        messages = []
        
        try:
            # Navigate to Twitter
            self.driver.get("https://twitter.com/login")
            print("🐦 Please login to Twitter/X...")
            
            # Wait for user to login manually
            WebDriverWait(self.driver, 120).until(
                EC.url_contains("twitter.com/home")
            )
            print("✅ Twitter/X logged in successfully")
            
            # Navigate to messages
            self.driver.get("https://twitter.com/messages")
            await asyncio.sleep(3)
            
            # Get conversation list
            try:
                conversations = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='conversation']"))
                )
                print(f"📋 Found {len(conversations)} Twitter conversations")
                
                # Process conversations (limit to prevent overwhelming)
                for i, conv in enumerate(conversations[:10]):
                    try:
                        # Click on conversation
                        conv.click()
                        await asyncio.sleep(2)
                        
                        # Get conversation info
                        conv_name = f"Twitter_Conv_{i}"
                        
                        print(f"💬 Scraping Twitter conversation: {conv_name}")
                        
                        # Get messages
                        message_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='messageEntry']")
                        
                        for msg_elem in message_elements:
                            try:
                                # Determine sender (simplified)
                                # In a real implementation, you'd need better logic to identify sent vs received
                                sender = self.person_name  # Placeholder
                                
                                # Get message text
                                try:
                                    text_elem = msg_elem.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
                                    content = text_elem.text
                                except:
                                    try:
                                        text_elem = msg_elem.find_element(By.CSS_SELECTOR, "span")
                                        content = text_elem.text
                                    except:
                                        content = "[Non-text message]"
                                
                                if not content or len(content.strip()) == 0:
                                    continue
                                
                                # Create message object
                                message = ScrapedMessage(
                                    platform="twitter",
                                    sender=sender,
                                    content=content,
                                    timestamp=datetime.now(),
                                    message_type="text",
                                    conversation_id=f"twitter_{conv_name}",
                                    metadata={
                                        "conversation_name": conv_name
                                    }
                                )
                                
                                messages.append(message)
                                
                                if len(messages) >= self.max_messages_per_platform:
                                    break
                                    
                            except Exception as e:
                                print(f"⚠️  Error processing Twitter message: {e}")
                                continue
                        
                        if len(messages) >= self.max_messages_per_platform:
                            break
                            
                    except Exception as e:
                        print(f"⚠️  Error processing Twitter conversation {i}: {e}")
                        continue
                
            except TimeoutException:
                print("❌ Twitter messages page not loaded")
                
        except Exception as e:
            print(f"❌ Twitter scraping error: {e}")
        
        return messages
    
    async def _verify_consent(self, platform: str) -> bool:
        """Verify user consent for platform scraping"""
        
        # In a real implementation, this would check a consent database
        # For now, we'll use the consent token as verification
        
        consent_file = self.data_dir / f"{self.person_name}_consent.json"
        
        if consent_file.exists():
            try:
                with open(consent_file, 'r') as f:
                    consent_data = json.load(f)
                
                consent = ConsentRecord.from_dict(consent_data)
                
                # Check if consent is valid and covers this platform
                if consent.consent_token == self.consent_token and platform in consent.platforms:
                    if consent.is_valid():
                        return True
                    
            except Exception as e:
                print(f"⚠️  Error reading consent file: {e}")
        
        print(f"❌ No valid consent found for {platform} scraping")
        return False
    
    async def _save_platform_data(self, platform: str, messages: List[ScrapedMessage]) -> None:
        """Save scraped data for a platform"""
        
        if not messages:
            return
        
        # Create platform-specific file
        filename = f"{self.person_name}_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.data_dir / filename
        
        # Convert messages to dict format
        data = {
            "person_name": self.person_name,
            "platform": platform,
            "scraped_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": [msg.to_dict() for msg in messages]
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(messages)} {platform} messages to {filename}")
    
    async def save_all_data(self) -> str:
        """Save all scraped data to a consolidated file"""
        
        if not self.scraped_messages:
            print("⚠️  No messages to save")
            return ""
        
        # Create consolidated file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.person_name}_all_platforms_{timestamp}.json"
        filepath = self.data_dir / filename
        
        # Organize data by platform
        platform_data = {}
        for msg in self.scraped_messages:
            if msg.platform not in platform_data:
                platform_data[msg.platform] = []
            platform_data[msg.platform].append(msg.to_dict())
        
        # Create consolidated data structure
        consolidated_data = {
            "person_name": self.person_name,
            "scraped_at": datetime.now().isoformat(),
            "total_messages": len(self.scraped_messages),
            "platforms": list(platform_data.keys()),
            "platform_counts": {platform: len(messages) for platform, messages in platform_data.items()},
            "data": platform_data
        }
        
        # Save consolidated file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved consolidated data to {filename}")
        return str(filepath)
    
    async def close(self) -> None:
        """Clean up resources"""
        
        if self.driver:
            self.driver.quit()
            print(f"🧹 WebDriver closed for {self.person_name}")


class ConsentManager:
    """Manage user consent records"""
    
    def __init__(self):
        self.consent_dir = Path("data/consent")
        self.consent_dir.mkdir(parents=True, exist_ok=True)
    
    def create_consent_record(
        self,
        person_name: str,
        email: str,
        platforms: List[str],
        duration_days: int = 30
    ) -> str:
        """Create a new consent record"""
        
        # Generate consent token
        consent_data = f"{person_name}{email}{datetime.now().isoformat()}"
        consent_token = hashlib.sha256(consent_data.encode()).hexdigest()[:16]
        
        # Create consent record
        consent_record = ConsentRecord(
            person_name=person_name,
            email=email,
            platforms=platforms,
            consent_date=datetime.now(),
            consent_token=consent_token,
            expires_at=datetime.now() + timedelta(days=duration_days)
        )
        
        # Save consent record
        consent_file = self.consent_dir / f"{person_name}_consent.json"
        with open(consent_file, 'w') as f:
            json.dump(consent_record.to_dict(), f, indent=2)
        
        print(f"✅ Consent record created for {person_name}")
        print(f"🔑 Consent token: {consent_token}")
        
        return consent_token
    
    def verify_consent(self, person_name: str, consent_token: str) -> bool:
        """Verify consent token"""
        
        consent_file = self.consent_dir / f"{person_name}_consent.json"
        
        if not consent_file.exists():
            return False
        
        try:
            with open(consent_file, 'r') as f:
                consent_data = json.load(f)
            
            consent = ConsentRecord.from_dict(consent_data)
            
            if consent.consent_token == consent_token:
                return consent.is_valid()
                
        except Exception as e:
            print(f"❌ Error verifying consent: {e}")
        
        return False


# Usage example functions
async def scrape_person_data(person_name: str, consent_token: str, platforms: List[str] = None) -> str:
    """Main function to scrape data for a person"""
    
    scraper = SocialMediaScraper(person_name, consent_token)
    
    try:
        # Scrape all platforms
        results = await scraper.scrape_all_platforms(platforms)
        
        # Save consolidated data
        output_file = await scraper.save_all_data()
        
        # Print summary
        total_messages = sum(len(messages) for messages in results.values())
        print(f"\n📊 Scraping Summary for {person_name}:")
        print(f"  Total messages: {total_messages}")
        for platform, messages in results.items():
            print(f"  {platform}: {len(messages)} messages")
        print(f"  Output file: {output_file}")
        
        return output_file
        
    finally:
        await scraper.close()


def create_consent(person_name: str, email: str, platforms: List[str] = None) -> str:
    """Create consent record for a person"""
    
    if platforms is None:
        platforms = ["whatsapp", "linkedin", "twitter"]
    
    consent_manager = ConsentManager()
    consent_token = consent_manager.create_consent_record(person_name, email, platforms)
    
    return consent_token
