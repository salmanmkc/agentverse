# 🚀 Cloud GPU Deployment Guide for Fine-tuning Pipeline

Complete step-by-step guide for running the fine-tuning pipeline on cloud GPU instances (Vast.ai, RunPod, Lambda Labs, etc.)

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Setup Cloud GPU Instance](#step-1-setup-cloud-gpu-instance)
3. [Step 2: Initial Server Setup](#step-2-initial-server-setup)
4. [Step 3: Transfer Files to Cloud](#step-3-transfer-files-to-cloud)
5. [Step 4: Install Dependencies](#step-4-install-dependencies)
6. [Step 5: Data Collection (Local)](#step-5-data-collection-local)
7. [Step 6: Upload Data to Cloud](#step-6-upload-data-to-cloud)
8. [Step 7: Generate Training Data](#step-7-generate-training-data)
9. [Step 8: Run Fine-tuning](#step-8-run-fine-tuning)
10. [Step 9: Evaluate Model](#step-9-evaluate-model)
11. [Step 10: Download Results](#step-10-download-results)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Local machine with:
  - Python 3.10+
  - Internet connection
  - SSH client
  - File transfer capability (scp, rsync, or SFTP)

- Cloud GPU account:
  - Vast.ai account (recommended for lowest cost ~$0.20-0.30/hr for RTX 4090)
  - RunPod account (~$0.34/hr for RTX 4090)
  - Lambda Labs account (~$1.85/hr for H100)
  - Or any cloud provider with NVIDIA GPUs (24GB+ VRAM recommended)

- API Keys:
  - Google Cloud credentials (for Gmail API)
  - OpenAI API key (for synthetic chat generation)

---

## Step 1: Setup Cloud GPU Instance

### Option A: Vast.ai (Cheapest)

1. **Sign up**: Go to https://vast.ai/
2. **Rent GPU**:
   - Click "Create" → "GPU Instances"
   - Filter: RTX 4090 (24GB), availability
   - Sort by price (lowest first)
   - Select instance (check reviews/uptime)
   - Choose base image: `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04` or similar
   - Click "Rent"
3. **Get connection info**:
   - Note: IP address, SSH port, username, password
   - Connection format: `ssh -p <port> root@<ip>`

### Option B: RunPod

1. **Sign up**: Go to https://www.runpod.io/
2. **Create Pod**:
   - Click "Deploy" → "Secure Cloud"
   - Select GPU: RTX 4090 or A6000
   - Template: `RunPod PyTorch`
   - Click "Deploy"
3. **Get connection info**:
   - SSH connection details provided in pod details

### Option C: Lambda Labs

1. **Sign up**: Go to https://lambda.ai/
2. **Launch instance**:
   - Select GPU instance (H100 or A100)
   - Choose Ubuntu 22.04 template
   - Launch instance

### General Notes

- **Recommended specs**:
  - GPU: RTX 4090 (24GB) or better
  - RAM: 32GB+
  - Storage: 100GB+ SSD
  - OS: Ubuntu 22.04 LTS

- **Cost estimation**:
  - RTX 4090: ~$0.20-0.50/hr = $4.80-12/day
  - Training time: 2-8 hours (depending on data size)
  - Total cost: ~$10-50 for complete run

---

## Step 2: Initial Server Setup

### Connect to Instance

```bash
# Vast.ai example
ssh -p <port> root@<ip_address>

# RunPod/Lambda Labs
ssh root@<ip_address>
```

### Install System Dependencies

```bash
# Update system
apt-get update
apt-get upgrade -y

# Install Python 3.10+ and essential tools
apt-get install -y python3.10 python3.10-venv python3-pip git curl wget

# Install CUDA (if not pre-installed)
# Check: nvidia-smi
# If missing, install CUDA 11.8+ from NVIDIA

# Install Git LFS (for large model files)
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash
apt-get install -y git-lfs
git lfs install
```

### Verify GPU Access

```bash
# Check GPU
nvidia-smi

# Should show GPU info (RTX 4090, A100, etc.)
# If not visible, contact support or check drivers
```

---

## Step 3: Transfer Files to Cloud

### Create Project Directory on Cloud

```bash
mkdir -p ~/finetuning_pipeline
cd ~/finetuning_pipeline
```

### Transfer Files from Local Machine

**From your local machine**, run:

```bash
# Navigate to project directory
cd /path/to/AgentVerseProject/finetuning

# Transfer all files
scp -P <port> -r * root@<cloud_ip>:~/finetuning_pipeline/

# Or using rsync (more efficient)
rsync -avz -e "ssh -p <port>" \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  . root@<cloud_ip>:~/finetuning_pipeline/
```

**Alternative: Clone from Git** (if you push to repo):

```bash
# On cloud instance
git clone <your-repo-url>
cd finetuning
```

---

## Step 4: Install Dependencies

### Create Virtual Environment

```bash
cd ~/finetuning_pipeline

# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Install Python Packages

```bash
# Install requirements
pip install -r requirements.txt

# Verify key packages
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
python -c "import peft; print(f'PEFT: {peft.__version__}')"
```

**Note**: Installation may take 10-20 minutes. If any package fails, install dependencies individually.

### Install HuggingFace CLI (for model downloads)

```bash
pip install huggingface-hub
```

### Authenticate with HuggingFace (if needed)

```bash
# Set token for private models
huggingface-cli login
# Or: export HF_TOKEN=your_token_here
```

---

## Step 5: Data Collection (Local)

**Note**: These steps run on your **local machine**, not the cloud instance.

### 5.1 Setup Gmail API

1. **Create Google Cloud Project**:
   - Go to https://console.cloud.google.com/
   - Create new project
   - Enable "Gmail API"

2. **Create OAuth Credentials**:
   - APIs & Services → Credentials
   - Create Credentials → OAuth 2.0 Client ID
   - Application type: Desktop app
   - Download JSON → save as `credentials.json`

3. **Extract Gmail Data** (on local machine):

```bash
cd /path/to/AgentVerseProject/finetuning

# Run Gmail extraction
python gmail_extraction.py \
  --credentials credentials.json \
  --token token.pickle \
  --max-results 5000 \
  --output-dir data/gmail
```

This will:
- Open browser for OAuth authentication
- Extract your emails
- Save to `data/gmail/gmail_export_YYYYMMDD_HHMMSS.json`

### 5.2 Process Message Exports

**For iMessage** (if you have CSV export):

```bash
python message_processor.py \
  /path/to/imessage_export.csv \
  --format imessage \
  --output-dir data/processed
```

**For WhatsApp** (if you have .txt export):

```bash
python message_processor.py \
  /path/to/whatsapp_export.txt \
  --format whatsapp \
  --output-dir data/processed
```

### 5.3 Generate Synthetic Conversations

```bash
# Set OpenAI API key
export OPENAI_API_KEY=your_openai_key_here

# Generate synthetic chats
python synthetic_chat_generation.py \
  --cv-path cvRyanLin.txt \
  --num-conversations 50 \
  --output-dir data/synthetic
```

**Note**: Adjust `--num-conversations` based on your needs (50-200 recommended).

---

## Step 6: Upload Data to Cloud

### Upload Collected Data

**From local machine**:

```bash
# Upload all data
rsync -avz -e "ssh -p <port>" \
  data/ \
  root@<cloud_ip>:~/finetuning_pipeline/data/

# Or using scp
scp -P <port> -r data/* root@<cloud_ip>:~/finetuning_pipeline/data/
```

### Verify Data on Cloud

```bash
# On cloud instance
cd ~/finetuning_pipeline
ls -lh data/
# Should see: gmail/, processed/, synthetic/ directories
```

---

## Step 7: Generate Training Data

**On cloud instance**:

```bash
cd ~/finetuning_pipeline
source venv/bin/activate

# Generate training JSONL files
python data_generation.py \
  --gmail-dir data/gmail \
  --message-dir data/processed \
  --synthetic-dir data/synthetic \
  --persona-name "Ryan Lin" \
  --user-name "Ryan Lin" \
  --train-ratio 0.9 \
  --output-dir data/training
```

**Expected output**:
- `data/training/train.jsonl` - Training examples
- `data/training/valid.jsonl` - Validation examples

**Check data**:

```bash
# Count examples
wc -l data/training/train.jsonl
wc -l data/training/valid.jsonl

# Preview first example
head -n 1 data/training/train.jsonl | python -m json.tool
```

---

## Step 8: Run Fine-tuning

### 8.1 Start Training

**On cloud instance**:

```bash
cd ~/finetuning_pipeline
source venv/bin/activate

# Run fine-tuning
python finetuning.py \
  --model-name "unsloth/gpt-oss-20b" \
  --train-file data/training/train.jsonl \
  --validation-file data/training/valid.jsonl \
  --output-dir adapters/ryan_lin \
  --lora-r 16 \
  --lora-alpha 32 \
  --learning-rate 2e-4 \
  --batch-size 1 \
  --gradient-accumulation-steps 8 \
  --num-epochs 1 \
  --max-steps 2000
```

### 8.2 Monitor Training

**In another terminal** (optional, for monitoring):

```bash
# Connect to instance
ssh -p <port> root@<ip_address>

# Watch GPU usage
watch -n 1 nvidia-smi

# Or check training logs
tail -f adapters/ryan_lin/training_logs.txt  # if logging enabled
```

### 8.3 Training Progress

- Training loss should decrease over time
- Validation loss should track training loss
- Checkpoints saved every 500 steps (configurable)
- Final model saved to `adapters/ryan_lin/`

**Expected training time**:
- 1k examples: ~1-2 hours
- 5k examples: ~3-5 hours
- 10k+ examples: ~5-8 hours

---

## Step 9: Evaluate Model

**On cloud instance**:

```bash
cd ~/finetuning_pipeline
source venv/bin/activate

# Run evaluation
python evaluation.py \
  --base-model "unsloth/gpt-oss-20b" \
  --adapter-path adapters/ryan_lin \
  --persona-name "Ryan Lin" \
  --num-prompts 10
```

**Results saved to**: `adapters/ryan_lin/evaluation_results.json`

**Review results**:

```bash
cat adapters/ryan_lin/evaluation_results.json | python -m json.tool | less
```

---

## Step 10: Download Results

### Download Adapters

**From local machine**:

```bash
# Download adapter directory
rsync -avz -e "ssh -p <port>" \
  root@<cloud_ip>:~/finetuning_pipeline/adapters/ \
  ./adapters/

# Or using scp
scp -P <port> -r root@<cloud_ip>:~/finetuning_pipeline/adapters ./adapters
```

### Download Evaluation Results

```bash
scp -P <port> \
  root@<cloud_ip>:~/finetuning_pipeline/adapters/ryan_lin/evaluation_results.json \
  ./evaluation_results.json
```

### Verify Downloads

```bash
# Check adapter files
ls -lh adapters/ryan_lin/

# Should contain:
# - adapter_config.json
# - adapter_model.bin (or adapter_model.safetensors)
# - training_metrics.json
# - evaluation_results.json
```

---

## Troubleshooting

### Issue: CUDA Out of Memory

**Solution**:
```bash
# Reduce batch size or increase gradient accumulation
python finetuning.py \
  --batch-size 1 \
  --gradient-accumulation-steps 16  # Increase this

# Or reduce max sequence length in finetuning.py
# Change max_seq_length from 1024 to 512
```

### Issue: Model Download Fails

**Solution**:
```bash
# Pre-download model on cloud instance
huggingface-cli download unsloth/gpt-oss-20b --local-dir ./models/gpt-oss-20b

# Then use --model-name ./models/gpt-oss-20b in finetuning.py
```

### Issue: Training Too Slow

**Solution**:
- Use 8-bit instead of 4-bit (if have >32GB VRAM):
  ```bash
  python finetuning.py --8bit ...
  ```
- Reduce max_seq_length
- Use smaller LoRA rank (--lora-r 8)

### Issue: Connection Lost During Training

**Solution**:
- Use `screen` or `tmux` for persistent sessions:
  ```bash
  # Install screen
  apt-get install -y screen
  
  # Start screen session
  screen -S training
  
  # Run training
  python finetuning.py ...
  
  # Detach: Ctrl+A, then D
  # Reattach: screen -r training
  ```

### Issue: Data Files Not Found

**Solution**:
```bash
# Verify file paths
ls -lh data/training/

# Check JSONL format
head -n 1 data/training/train.jsonl | python -m json.tool
```

### Issue: Import Errors

**Solution**:
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify installations
python -c "import torch, transformers, peft, bitsandbytes; print('All imports OK')"
```

---

## Quick Reference Commands

### Complete Pipeline (Summary)

**Local (Data Collection)**:
```bash
# 1. Gmail extraction
python gmail_extraction.py --max-results 5000

# 2. Process messages (if available)
python message_processor.py message_export.txt --format whatsapp

# 3. Generate synthetic
python synthetic_chat_generation.py --num-conversations 50

# 4. Upload to cloud
rsync -avz data/ root@cloud_ip:~/finetuning_pipeline/data/
```

**Cloud (Training)**:
```bash
# 1. Setup
git clone <repo> && cd finetuning
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Generate training data
python data_generation.py --gmail-dir data/gmail --synthetic-dir data/synthetic

# 3. Train
python finetuning.py --train-file data/training/train.jsonl

# 4. Evaluate
python evaluation.py --adapter-path adapters/ryan_lin

# 5. Download results
# (from local) scp -r root@cloud_ip:~/finetuning_pipeline/adapters ./
```

---

## Cost Optimization Tips

1. **Use spot/preemptible instances** (save 50-80%)
2. **Monitor GPU usage** - shutdown if idle
3. **Pre-download models** before starting billing
4. **Use smaller models** for testing (before full run)
5. **Optimize hyperparameters** on smaller dataset first
6. **Checkpoint frequently** - resume if interrupted
7. **Use Vast.ai community instances** for lowest rates

---

## Next Steps

After training:

1. **Test locally** with adapter weights
2. **Deploy for inference** (see deployment docs)
3. **Iterate** on training data based on evaluation
4. **Fine-tune hyperparameters** for better results
5. **Generate more synthetic data** to fill gaps

---

## Support

- **Vast.ai support**: https://vast.ai/docs/
- **RunPod docs**: https://docs.runpod.io/
- **HuggingFace forums**: https://discuss.huggingface.co/
- **Project issues**: Open GitHub issue

---

**Estimated Total Time**: 4-12 hours (including data collection, training, evaluation)

**Estimated Total Cost**: $10-50 (depending on GPU choice and training time)

Good luck with your fine-tuning! 🚀

