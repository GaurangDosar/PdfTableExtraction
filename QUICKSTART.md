# Quick Start Guide

## Prerequisites
- Python 3.10 or higher
- Git

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd PdfTableExtraction
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   ```

3. **Configure API keys**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your Groq API keys
   # Get free API keys from: https://console.groq.com/keys
   ```

4. **Run the web interface**
   ```bash
   streamlit run app.py
   ```
   
   The app will open at http://localhost:8501

## Usage

### Web Interface (Recommended)
1. Open http://localhost:8501 in your browser
2. Upload a PDF file
3. Click "Extract Tables"
4. View results and download CSV

### Command Line
```bash
python -m pdf_table_extraction.cli your_file.pdf
```

## Features

- 📤 Drag & drop PDF upload
- 🤖 AI-powered table extraction and normalization
- ✅ Automatic data validation
- 📊 Quality metrics and analysis
- ⬇️ CSV export
- 🔄 Automatic API failover (multiple Groq accounts)
- 🔍 OCR support for scanned documents

## API Rate Limits

- Free tier: 100,000 tokens/day per Groq account
- **Tip**: Use multiple Groq accounts (different emails) for automatic failover
- Each PDF uses approximately 4,000-5,000 tokens

## Troubleshooting

### Rate Limit Errors
- Wait for daily limit reset (midnight UTC)
- Add backup API keys (`GROQ_API_KEY_2`, `GROQ_API_KEY_3`)
- Switch to smaller model: `llama-3.1-8b-instant`

### No Tables Found
- Enable OCR option for scanned PDFs
- Verify PDF contains table structures

### Other Issues
- Check `logs/pipeline.log` for detailed errors
- Ensure all dependencies are installed
- Verify API keys in `.env` file

## Documentation

- [Main README](README.md) - Full documentation
- [Web Interface Guide](README_WEB.md) - Streamlit app details
- [Prompts Documentation](PROMPTS_DOCUMENTATION.md) - AI prompt design

## Support

For issues or questions, please open a GitHub issue.
