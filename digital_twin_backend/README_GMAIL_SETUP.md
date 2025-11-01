# Gmail Dataset Creation Setup Guide

This guide will help you set up the Gmail API to scrape your sent emails and create a dataset for fine-tuning with unsloth.

## Step 1: Set Up Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

## Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace)
   - Fill in the required fields (App name, User support email, etc.)
   - Add your email to test users
   - Save and continue through the scopes (no need to add additional scopes)
   - Save and continue through the summary
4. For Application type, select "Desktop app"
5. Give it a name (e.g., "Gmail Dataset Creator")
6. Click "Create"
7. Download the credentials JSON file
8. Rename it to `credentials.json` and place it in the `digital_twin_backend/` directory

## Step 3: Install Dependencies

Activate your virtual environment and install the required packages:

```bash
source agentverse/bin/activate
pip install -r digital_twin_backend/requirements.txt
```

## Step 4: Run the Script

```bash
cd digital_twin_backend
python gmail_dataset_creation.py
```

On first run:
- A browser window will open for Google OAuth authentication
- Sign in with your Gmail account
- Grant the necessary permissions
- The script will save a `token.pickle` file for future runs

## Step 5: Dataset Output

The script will create:
- `gmail_dataset/` - Hugging Face Dataset directory (suitable for unsloth)
- `gmail_dataset_json.json` - Sample JSON file with first 100 examples for inspection

## Dataset Format

The dataset is formatted for unsloth fine-tuning with chat format:

```json
{
  "messages": [
    {"role": "system", "content": "Context about the email..."},
    {"role": "user", "content": "Prompt about writing the email..."},
    {"role": "assistant", "content": "Your actual email content..."}
  ],
  "metadata": {
    "subject": "Email subject",
    "recipient": "recipient@example.com",
    "date": "2024-01-01T12:00:00",
    "email_id": "gmail_message_id"
  }
}
```

## Notes

- The script fetches up to 10,000 sent emails by default (configurable via `MAX_EMAILS`)
- Only sent emails are included (not received)
- HTML emails are converted to plain text
- The dataset is ready to use with unsloth for fine-tuning

## Troubleshooting

**"credentials.json not found"**
- Make sure you've downloaded the OAuth credentials from Google Cloud Console
- Place the file in the `digital_twin_backend/` directory

**"Access denied" or OAuth errors**
- Make sure you've added your email as a test user in the OAuth consent screen
- For production use, you'll need to verify your app

**Rate limiting**
- Gmail API has rate limits. The script handles this by batching requests
- If you hit limits, wait a few minutes and rerun

**Memory issues with large datasets**
- Reduce `MAX_EMAILS` in the script if you have many emails
- Process emails in batches if needed

