# Gmail Data Pipeline - Complete Guide

## Overview

This pipeline extracts ALL your Gmail emails, pairs sent emails with their received counterparts, formats them for OpenAI fine-tuning, and validates security compliance.

## Quick Start

### Run the Complete Pipeline

```bash
cd finetuning
python gmail_pipeline.py
```

This will:
1. ✅ Authenticate with Gmail API
2. ✅ Extract ALL your emails (no limit by default)
3. ✅ Format to OpenAI JSONL format
4. ✅ Validate security compliance
5. ✅ Generate ready-to-upload training file

### Options

```bash
# Limit number of emails (useful for testing)
python gmail_pipeline.py --max-emails 5000

# Custom output location
python gmail_pipeline.py --formatted-output data/openai_format/my_gmail.jsonl
```

## Components

### 1. Gmail Extraction (`gmail_extraction.py`)

- **Full pagination**: Extracts ALL emails (no 5000 limit)
- **Smart detection**: Automatically identifies sent vs received emails
- **Thread grouping**: Organizes emails by conversation thread

### 2. OpenAI Formatting (`openai_formatter.py`)

- **Comprehensive pairing**: Matches ALL sent emails with their corresponding received emails
- **Bidirectional matching**: 
  - For each sent email, finds the most recent received email it's replying to
  - For each received email, finds the next sent email that replies
- **Automatic redaction**: Removes passwords, SSN, phone numbers, Zoom passwords
- **Quality filtering**: Skips automated emails, too-short emails, overly sensitive content

### 3. Security Validation (`validate_openai_security.py`)

Validates compliance with OpenAI's requirements:
- ✅ All examples end with assistant message
- ✅ All examples start with system message
- ✅ No unredacted passwords/credentials
- ✅ No unredacted SSN or phone numbers
- ✅ No Zoom links with passwords
- ✅ Proper message structure

**Usage:**
```bash
python validate_openai_security.py data/openai_format/gmail.jsonl
```

## Output

The pipeline generates:
- **Raw export**: `data/gmail/gmail_export_YYYYMMDD_HHMMSS.json` - All extracted emails
- **Training file**: `data/openai_format/gmail.jsonl` - Ready for OpenAI upload

## Requirements

- Google OAuth2 credentials (`credentials.json`)
- Authenticated Gmail API access (`token.pickle`)
- Python packages: `google-auth-oauthlib`, `google-api-python-client`

## Troubleshooting

### Authentication Issues
If authentication fails, delete `token.pickle` and re-authenticate:
```bash
rm token.pickle
python gmail_pipeline.py
```

### Small Dataset
If you're getting fewer examples than expected:
1. Check the raw export file to see total emails extracted
2. The formatter only creates pairs where:
   - Sent email is a reply to a received email
   - Subject matches or starts with "Re:"
   - Both emails have sufficient content (>20 chars)
   - Not an automated/notification email

### Security Validation Failures
If validation fails:
1. Check the error messages
2. The formatter should automatically redact most issues
3. Manually review flagged examples if needed

## Manual Steps

### Extract Only
```bash
python gmail_extraction.py --max-results 10000
```

### Format Only
```bash
python -c "from openai_formatter import OpenAIFormatter; OpenAIFormatter().format_gmail_to_openai('data/gmail/export.json', 'output.jsonl')"
```

### Validate Only
```bash
python validate_openai_security.py output.jsonl
```

