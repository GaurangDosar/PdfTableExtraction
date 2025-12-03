"""
Streamlit Web Interface for PDF Table Extraction Pipeline
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.pdf_table_extraction.pipeline import run_pipeline

# Page configuration
st.set_page_config(
    page_title="PDF Table Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'validation_report' not in st.session_state:
    st.session_state.validation_report = None
if 'summary' not in st.session_state:
    st.session_state.summary = None


def reset_state():
    """Reset session state when new file is uploaded"""
    st.session_state.processed = False
    st.session_state.df = None
    st.session_state.validation_report = None
    st.session_state.summary = None


def process_pdf(uploaded_file, use_ocr: bool = False):
    """Process the uploaded PDF file through the pipeline"""
    try:
        # Create temporary files for input and output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Save uploaded file to temporary location
            pdf_path = temp_dir_path / uploaded_file.name
            pdf_path.write_bytes(uploaded_file.read())
            
            # Define output paths
            output_csv_path = temp_dir_path / "output.csv"
            
            # Run the pipeline
            with st.spinner('🔄 Processing PDF... This may take a minute...'):
                summary = run_pipeline(
                    pdf_path,
                    output_csv=output_csv_path,
                    use_ocr=use_ocr
                )
            
            # Check if processing was successful
            if summary.get('status') != 'success':
                reason = summary.get('reason', 'Unknown error')
                
                # Provide user-friendly error messages
                error_msg = f"❌ Processing failed: {reason}"
                help_text = None
                
                if 'normalization_failed' in reason or 'RateLimitError' in reason:
                    error_msg = "❌ Normalization failed"
                    help_text = """
**Possible causes:**
- **API Rate Limit**: Too many requests to Groq API. Wait 30-60 seconds and try again.
- **Network Issues**: Check your internet connection.
- **Invalid API Key**: Verify your `.env` file has a valid `GROQ_API_KEY`.

**What to do:**
1. Wait a minute before retrying
2. Try processing a smaller PDF
3. Check the logs folder for detailed error information
                    """
                elif 'daily token limit' in reason.lower() or 'tokens per day' in reason.lower():
                    error_msg = "❌ Daily API Token Limit Reached"
                    help_text = """
**Both Groq API keys have exhausted their daily token quota (100,000 tokens/day).**

**Solutions:**
1. **Wait**: Token limits reset at midnight UTC (check https://console.groq.com)
2. **Upgrade**: Get higher limits at https://console.groq.com/settings/billing
3. **Add More Keys**: Create a 3rd Groq account and add `GROQ_API_KEY_3` to `.env`
4. **Use Smaller Model**: Switch to `llama-3.1-8b-instant` (uses fewer tokens)

**Tip**: You've processed many PDFs today. The system will work again tomorrow automatically.
                    """
                elif 'no_tables_found' in reason:
                    error_msg = "❌ No tables found in PDF"
                    help_text = """
**Suggestions:**
- Enable OCR if the PDF contains scanned/image-based tables
- Verify the PDF contains actual table structures
- Try a different PDF file
                    """
                
                return None, None, {'status': 'failed', 'error_msg': error_msg, 'help_text': help_text}
            
            # Read the generated CSV
            df = pd.read_csv(output_csv_path)
            
            # Read validation report - check both temp dir and main outputs folder
            validation_report = None
            
            # First try temp dir location
            validation_report_path = temp_dir_path / "output" / "validation_report.json"
            if not validation_report_path.exists():
                # Try the pipeline's default output location
                from src.pdf_table_extraction.config import OUTPUT_DIR
                validation_report_path = OUTPUT_DIR / "validation_report.json"
            
            if validation_report_path.exists():
                validation_report = json.loads(validation_report_path.read_text(encoding='utf-8'))
            
            return df, validation_report, summary
            
    except Exception as e:
        error_details = str(e)
        st.error(f"❌ Unexpected error: {error_details}")
        
        help_text = """
**Debugging steps:**
1. Check the `logs/pipeline.log` file for detailed error messages
2. Verify your `.env` file contains valid API credentials
3. Ensure all dependencies are installed: `pip install -e .`
        """
        
        return None, None, {
            'status': 'failed', 
            'error_msg': f"Unexpected error: {error_details}",
            'help_text': help_text
        }


def display_validation_report(report: dict):
    """Display the validation report in a formatted way"""
    if not report:
        st.warning("⚠️ Validation report not available")
        return
    
    st.subheader("📊 Validation Report")
    
    # Overall Status
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status = report.get('overall_status', 'N/A')
        status_color = {"PASSED": "🟢", "NEEDS_REVIEW": "🟡", "FAILED": "🔴"}.get(status, "⚪")
        st.metric("Overall Status", f"{status_color} {status}")
    with col2:
        st.metric("Critical Issues", report.get('critical_issues', 0))
    with col3:
        st.metric("Major Issues", report.get('major_issues', 0))
    with col4:
        st.metric("Minor Issues", report.get('minor_issues', 0))
    
    # Summary
    if report.get('summary'):
        st.markdown("#### 📝 Summary")
        st.info(report['summary'])
    
    # Detailed Issues
    if report.get('issues'):
        st.markdown("#### 🔍 Detailed Issues")
        
        # Group issues by severity
        critical = [i for i in report['issues'] if i.get('severity') == 'critical']
        major = [i for i in report['issues'] if i.get('severity') == 'major']
        minor = [i for i in report['issues'] if i.get('severity') == 'minor']
        info = [i for i in report['issues'] if i.get('severity') == 'info']
        
        # Display critical issues first (always expanded)
        if critical:
            st.markdown("##### 🔴 Critical Issues")
            for idx, issue in enumerate(critical, 1):
                with st.expander(f"Critical {idx}: {issue.get('field', 'N/A')}", expanded=True):
                    st.write(f"**Issue:** {issue.get('issue', 'N/A')}")
                    st.write(f"**Rows Affected:** {issue.get('rows_affected', 'N/A')}")
                    if issue.get('examples'):
                        st.write("**Examples:**")
                        for example in issue['examples']:
                            st.code(str(example), language=None)
        
        # Display major issues
        if major:
            st.markdown("##### 🟠 Major Issues")
            for idx, issue in enumerate(major, 1):
                with st.expander(f"Major {idx}: {issue.get('field', 'N/A')}"):
                    st.write(f"**Issue:** {issue.get('issue', 'N/A')}")
                    st.write(f"**Rows Affected:** {issue.get('rows_affected', 'N/A')}")
                    if issue.get('examples'):
                        st.write("**Examples:**")
                        for example in issue['examples']:
                            st.code(str(example), language=None)
        
        # Display minor issues
        if minor:
            st.markdown("##### 🟡 Minor Issues")
            for idx, issue in enumerate(minor, 1):
                with st.expander(f"Minor {idx}: {issue.get('field', 'N/A')}"):
                    st.write(f"**Issue:** {issue.get('issue', 'N/A')}")
                    st.write(f"**Rows Affected:** {issue.get('rows_affected', 'N/A')}")
                    if issue.get('examples'):
                        st.write("**Examples:**")
                        for example in issue['examples']:
                            st.code(str(example), language=None)
        
        # Display info messages
        if info:
            st.markdown("##### 🔵 Informational")
            for idx, issue in enumerate(info, 1):
                with st.expander(f"Info {idx}: {issue.get('field', 'N/A')}"):
                    st.write(f"**Issue:** {issue.get('issue', 'N/A')}")
                    st.write(f"**Rows Affected:** {issue.get('rows_affected', 'N/A')}")
                    if issue.get('examples'):
                        st.write("**Examples:**")
                        for example in issue['examples']:
                            st.code(str(example), language=None)
    else:
        st.success("✅ No validation issues detected!")
    
    # Additional Metadata
    st.markdown("---")
    st.markdown("#### 📋 Additional Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Per-Table Alignment
        if report.get('per_table_alignment') is not None:
            alignment_status = "✅ Yes" if report['per_table_alignment'] else "❌ No"
            st.write(f"**All tables properly aligned:** {alignment_status}")
        
        # Total rows validated
        if report.get('total_rows') is not None:
            st.write(f"**Total rows validated:** {report['total_rows']}")
    
    with col2:
        # Low Confidence Rows
        if report.get('low_confidence_rows') is not None:
            low_conf_count = len(report['low_confidence_rows']) if isinstance(report['low_confidence_rows'], list) else 0
            if low_conf_count > 0:
                st.write(f"**Low confidence rows:** ⚠️ {low_conf_count}")
            else:
                st.write(f"**Low confidence rows:** ✅ 0")
        
        # Tables validated
        if report.get('tables_validated') is not None:
            st.write(f"**Tables validated:** {report['tables_validated']}")
    
    # Show low confidence rows if any
    if report.get('low_confidence_rows') and len(report['low_confidence_rows']) > 0:
        with st.expander(f"⚠️ View Low Confidence Rows ({len(report['low_confidence_rows'])})"):
            st.json(report['low_confidence_rows'])
    
    # Download full report as JSON
    st.markdown("---")
    report_json = json.dumps(report, indent=2)
    st.download_button(
        label="📥 Download Full Validation Report (JSON)",
        data=report_json,
        file_name="validation_report.json",
        mime="application/json",
        use_container_width=True
    )


# Main UI
st.markdown('<div class="main-header">📄 PDF Table Extractor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Extract and normalize tables from PDF documents with AI</div>', unsafe_allow_html=True)

# File upload section
st.markdown("### 📤 Upload PDF")
uploaded_file = st.file_uploader(
    "Drop your PDF file here or browse",
    type=['pdf'],
    help="Upload a PDF file containing tables to extract",
    on_change=reset_state
)

# OCR option
use_ocr = st.checkbox(
    "Enable OCR fallback",
    value=False,
    help="Use OCR for complex or image-based tables (slower but more accurate)"
)

# Process button
if uploaded_file is not None and not st.session_state.processed:
    if st.button("🚀 Extract Tables", type="primary", use_container_width=True):
        df, validation_report, summary = process_pdf(uploaded_file, use_ocr)
        
        if summary.get('status') == 'success' and df is not None:
            st.session_state.df = df
            st.session_state.validation_report = validation_report
            st.session_state.summary = summary
            st.session_state.processed = True
            st.rerun()
        else:
            st.markdown('<div class="error-box">', unsafe_allow_html=True)
            st.error(summary.get('error_msg', f"❌ Processing failed: {summary.get('reason', 'Unknown error')}"))
            
            if summary.get('help_text'):
                st.markdown("---")
                st.markdown(summary['help_text'])
            
            st.markdown('</div>', unsafe_allow_html=True)

# Display results if processed
if st.session_state.processed and st.session_state.df is not None:
    st.markdown("---")
    
    # Success message
    st.markdown('<div class="success-box">', unsafe_allow_html=True)
    st.success("✅ PDF processed successfully!")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Summary statistics
    st.markdown("### 📈 Extraction Summary")
    
    # Main metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tables", st.session_state.summary.get('total_tables', 0))
    with col2:
        st.metric("Total Rows", st.session_state.summary.get('total_rows', 0))
    with col3:
        avg_rows = st.session_state.summary.get('total_rows', 0) / max(st.session_state.summary.get('total_tables', 1), 1)
        st.metric("Avg Rows/Table", f"{avg_rows:.1f}")
    
    # Validation summary from report
    if st.session_state.validation_report:
        report = st.session_state.validation_report
        
        st.markdown("#### 📊 Quality Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            alignment_status = "✅" if report.get('column_alignment_ok', False) else "❌"
            st.metric("Column Alignment", alignment_status)
        
        with col2:
            low_conf_count = len(report.get('low_confidence_rows', []))
            st.metric("Low Confidence Rows", low_conf_count)
        
        with col3:
            discrepancy_count = len(report.get('discrepancies', []))
            st.metric("Discrepancies", discrepancy_count)
        
        with col4:
            per_table = report.get('per_table_alignment', {})
            aligned_tables = sum(1 for v in per_table.values() if v)
            st.metric("Aligned Tables", f"{aligned_tables}/{len(per_table)}")
        
        # LLM Notes
        if report.get('llm_notes'):
            st.markdown("#### 💡 AI Analysis")
            st.info(report['llm_notes'])
        
        # Discrepancies detail
        if report.get('discrepancies'):
            with st.expander(f"⚠️ View Discrepancies ({len(report['discrepancies'])})"):
                for idx, disc in enumerate(report['discrepancies'], 1):
                    st.markdown(f"**{idx}.** {disc}")
        
        # Low Confidence Rows detail
        if report.get('low_confidence_rows'):
            with st.expander(f"⚠️ View Low Confidence Rows ({len(report['low_confidence_rows'])})"):
                st.json(report['low_confidence_rows'])
    
    # Rows per table breakdown
    if st.session_state.summary.get('rows_per_table'):
        with st.expander("📊 Rows per Table Breakdown"):
            for table_id, row_count in st.session_state.summary['rows_per_table'].items():
                st.write(f"**{table_id}:** {row_count} rows")
    
    st.markdown("---")
    
    # Display extracted data
    st.markdown("### 📋 Extracted Data")
    st.dataframe(
        st.session_state.df,
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv_data = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_data,
        file_name=f"{Path(uploaded_file.name).stem}_extracted.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True
    )
    
    st.markdown("---")
    
    # Display validation report
    if st.session_state.validation_report:
        display_validation_report(st.session_state.validation_report)
    
    # Process another file button
    if st.button("🔄 Process Another File", use_container_width=True):
        reset_state()
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666; font-size: 0.9rem;">'
    'Powered by LLM-driven extraction pipeline | Built with Streamlit'
    '</div>',
    unsafe_allow_html=True
)
