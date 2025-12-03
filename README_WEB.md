# PDF Table Extractor - Web Interface

A simple web interface for the PDF Table Extraction pipeline built with Streamlit.

## Features

- 📤 **Drag & Drop Upload**: Easy file upload with drag-and-drop support
- 🚀 **One-Click Processing**: Extract tables with a single click
- 📊 **Live Results**: View extracted data in an interactive table
- ⬇️ **CSV Download**: Download results as CSV file
- 📋 **Validation Report**: Detailed quality assessment with severity levels
- 🔄 **OCR Support**: Optional OCR fallback for complex tables

## Running the Web App

### 1. Install Dependencies (if not already installed)

The web interface requires Streamlit, which is already included in `pyproject.toml`:

```powershell
pip install -e .
```

### 2. Set Up Environment Variables

Make sure your `.env` file contains the required API keys:

```
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Start the Web Server

```powershell
streamlit run app.py
```

The application will open automatically in your default browser at `http://localhost:8501`

### 4. Using the Interface

1. **Upload PDF**: Drag and drop a PDF file or click "Browse files"
2. **Configure Options**: 
   - Enable OCR if needed (for complex/scanned tables)
3. **Extract Tables**: Click "🚀 Extract Tables" button
4. **View Results**:
   - See extraction summary (tables found, rows extracted)
   - Browse extracted data in interactive table
   - Review validation report for quality issues
5. **Download**: Click "⬇️ Download as CSV" to save results
6. **Process Another**: Click "🔄 Process Another File" to upload a new PDF

## Features Explained

### Extraction Summary
- **Total Tables**: Number of tables detected in the PDF
- **Total Rows**: Total data rows extracted and normalized
- **Avg Rows/Table**: Average rows per table
- **Rows per Table Breakdown**: Detailed count for each table

### Validation Report
- **Overall Status**: PASSED/NEEDS_REVIEW/FAILED
- **Issue Severity Levels**: 
  - 🔴 Critical: Must fix
  - 🟠 Major: Should review
  - 🟡 Minor: Optional review
  - 🔵 Info: For awareness
- **Per-Table Alignment**: Check if tables align with expected schema
- **Low Confidence Rows**: Rows that may need manual verification

## Configuration

Streamlit settings are in `.streamlit/config.toml`:
- Max upload size: 50 MB
- Theme: Blue and white
- CORS: Disabled (local use)

## Deployment Options

### Local Network Access

To allow access from other devices on your network:

```powershell
streamlit run app.py --server.address 0.0.0.0
```

### Cloud Deployment

The app can be deployed to:
- **Streamlit Cloud** (Free tier available)
- **Azure App Service**
- **AWS ECS/Fargate**
- **Google Cloud Run**

See the main README for detailed deployment instructions.

## Troubleshooting

### Port Already in Use
```powershell
streamlit run app.py --server.port 8502
```

### Upload Size Limit
Edit `.streamlit/config.toml` and change `maxUploadSize` value.

### API Rate Limits
If you encounter Groq API rate limits, wait a few moments and try again.

## Technical Notes

- The web interface is a thin wrapper around the existing CLI pipeline
- No modifications were made to the core pipeline code
- All processing logic remains in `src/pdf_table_extraction/`
- Temporary files are automatically cleaned up after processing
