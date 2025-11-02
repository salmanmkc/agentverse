# Fine-tuning Pipeline for GPT-OSS-20B

Complete pipeline for fine-tuning GPT-OSS-20B with LoRA/QLoRA adapters to emulate Ryan Lin's persona in workplace settings.

## 📁 Project Structure

```
finetuning/
├── gmail_extraction.py          # Extract Gmail data via Google API
├── message_processor.py          # Process iMessage/WhatsApp exports
├── synthetic_chat_generation.py  # Generate synthetic conversations
├── data_generation.py            # Normalize data to SFT JSONL format
├── finetuning.py                 # QLoRA fine-tuning script
├── evaluation.py                 # Evaluate model on held-out prompts
├── requirements.txt              # Python dependencies
├── CLOUD_DEPLOYMENT_GUIDE.md     # Complete cloud deployment guide
├── README.md                      # This file
└── cvryanlin.txt                 # CV for persona context
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Collect Data (Local)

```bash
# Extract Gmail data
python gmail_extraction.py --max-results 5000

# Process message exports (optional)
python message_processor.py export.txt --format whatsapp

# Generate synthetic conversations
python synthetic_chat_generation.py --num-conversations 50
```

### 3. Generate Training Data

```bash
python data_generation.py \
  --gmail-dir data/gmail \
  --message-dir data/processed \
  --synthetic-dir data/synthetic \
  --output-dir data/training
```

### 4. Fine-tune (Cloud GPU Recommended)

See [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md) for complete instructions.

```bash
python finetuning.py \
  --train-file data/training/train.jsonl \
  --validation-file data/training/valid.jsonl \
  --output-dir adapters/ryan_lin
```

### 5. Evaluate

```bash
python evaluation.py \
  --adapter-path adapters/ryan_lin
```

## 📖 Detailed Documentation

- **[CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)**: Complete step-by-step guide for cloud GPU deployment
- See individual script files for command-line options and usage

## 🔧 Requirements

- Python 3.10+
- NVIDIA GPU with 24GB+ VRAM (for QLoRA) or 40GB+ (for full precision)
- Google Cloud credentials (for Gmail API)
- OpenAI API key (for synthetic generation, optional)

## 📊 Data Sources

1. **Gmail**: Professional email history
2. **iMessage/WhatsApp**: Text message exports
3. **Synthetic**: LLM-generated conversations based on CV/LinkedIn

## 🎯 Training Format

All training examples use persona framing:

```
SYSTEM: You are Ryan Lin. Respond as Ryan Lin would in a professional workplace context.
USER: <task/message>
ASSISTANT: <Ryan Lin style response>
```

## 💾 Output

- **Adapters**: LoRA adapter weights (small files, ~100MB)
- **Evaluation**: Held-out prompt results and metrics
- **Training metrics**: Loss curves and checkpoints

## 🔗 Related Files

- See `digital_twin_backend/finetune_gpt_oss.ipynb` for alternative Jupyter notebook approach
- See `digital_twin_backend/` for agent deployment

## 📝 License

See main project license.

