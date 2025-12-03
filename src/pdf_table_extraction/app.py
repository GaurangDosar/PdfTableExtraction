import streamlit as st
import pandas as pd
import tempfile
import os
from pathlib import Path
import json
import sys

# Add the src directory to python path so we can import modules if running directly
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from pdf_table_extraction.pipeline import run_pipeline

st.set_page_config(
    page_title="PDF Table Extractor",
    page_icon="📊",
    layout="wide"
)

st.title("📊 PDF Table Extraction Pipeline")
st.markdown("""
Upload a PDF file to extract tables, normalize data, and validate the results using LLM.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    use_ocr = st.checkbox("Use OCR (for scanned docs)", value=False, help="Enable this if the PDF contains scanned images of tables.")
    
    st.divider()
    st.info("This tool uses Groq (Llama 3) for intelligent table normalization.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.success(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Run Extraction", type="primary"):
        # Create a temporary directory to store the file and output
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            tmp_pdf_path = tmp_dir_path / uploaded_file.name
            output_csv_path = tmp_dir_path / "extracted_tables.csv"
            
            # Write uploaded file to temp path
            with open(tmp_pdf_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Run pipeline with a spinner
            with st.spinner("Running extraction pipeline... This may take a minute."):
                try:
                    # Redirect stdout/stderr to capture logs if needed, or just let them go to console
                    result = run_pipeline(
                        pdf_path=tmp_pdf_path,
                        output_csv=output_csv_path,
                        use_ocr=use_ocr
                    )
                    
                    if result["status"] == "success":
                        st.balloons()
                        
                        # Layout: 2 columns
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.subheader("Extracted Data")
                            if output_csv_path.exists():
                                df = pd.read_csv(output_csv_path)
                                st.dataframe(df, use_container_width=True)
                                
                                # Download button
                                with open(output_csv_path, "rb") as f:
                                    st.download_button(
                                        label="Download CSV",
                                        data=f,
                                        file_name=f"{Path(uploaded_file.name).stem}_extracted.csv",
                                        mime="text/csv"
                                    )
                            else:
                                st.error("CSV file was not generated.")

                        with col2:
                            st.subheader("Validation Report")
                            validation = result.get("validation", {})
                            
                            # Metrics
                            m1, m2 = st.columns(2)
                            m1.metric("Total Tables", validation.get("total_tables", 0))
                            m2.metric("Total Rows", validation.get("total_rows", 0))
                            
                            # Alignment check
                            if validation.get("column_alignment_ok"):
                                st.success("✅ Column Alignment: OK")
                            else:
                                st.error("❌ Column Alignment: Issues Found")
                                
                            # Detailed JSON
                            with st.expander("Full Validation Details", expanded=True):
                                st.json(validation)
                                
                    else:
                        st.error(f"Extraction failed: {result.get('reason')}")
                        if "error" in result:
                            st.code(result["error"])
                            
                except Exception as e:
                    st.error(f"An error occurred during execution: {str(e)}")
                    st.exception(e)
