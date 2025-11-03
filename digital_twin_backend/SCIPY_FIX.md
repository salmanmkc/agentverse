# 🔧 Scipy/LAPACK Fix Documentation

## Problem
When running `test_pipeline.py` (or any script importing transformers), you may see:
```
ImportError: dlopen(...): Library not loaded: @rpath/liblapack.3.dylib
```

This occurs when using the **base conda Python** which has a broken scipy installation.

## Solution

### ✅ Always Use the Virtual Environment

The project has a virtual environment (`venv/`) with properly installed dependencies.

**Option 1: Activate venv manually**
```bash
cd digital_twin_backend
source venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
python test_pipeline.py
```

**Option 2: Use the convenience scripts**
```bash
# For running tests
./run_test.sh

# For starting the server
./start.sh
```

### What Was Fixed

1. **Enhanced error handling in `base_agent.py`**
   - Now catches `RuntimeError` in addition to `ImportError`
   - Provides helpful message when scipy issues occur
   - Gracefully falls back to API models

2. **Added venv detection in `test_pipeline.py`**
   - Warns if not using venv Python
   - Helps identify the issue early

3. **Updated `start.sh`**
   - Better venv verification
   - Shows which Python is being used

4. **Created `run_test.sh`**
   - Convenient script to run tests with venv

## Verification

To verify everything works:
```bash
cd digital_twin_backend
source venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
python -c "import transformers; print('✅ Transformers OK')"
python -c "import scipy; print('✅ Scipy OK')"
python test_pipeline.py
```

## Important Notes

- **Always activate venv before running scripts**
- The venv has `scipy` properly installed
- The base conda environment has broken scipy - avoid using it
- When using OpenAI API models (like for Ryan Lin), ML libraries aren't required anyway

## For API-Only Usage

If you're only using OpenAI API models (not local fine-tuning), the scipy issue doesn't matter. The system will:
1. Detect that ML libraries are unavailable
2. Set `ML_AVAILABLE = False`
3. Use API models automatically (which is what you want for OpenAI assistants)

