import streamlit as st
from fpdf import FPDF
import fitz  # PyMuPDF for PDF text extraction
import os
from summarizing_highlights import app  # Import the compiled LangGraph app

# Function to generate PDF from text
def generate_pdf(text):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)
    pdf_path = "summary_document.pdf"
    pdf.output(pdf_path, "F")
    return pdf_path

# Streamlit UI
st.title("PDF Highlights Summarizer ")

uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])

if uploaded_file is not None:
    with open("uploaded.pdf", "wb") as f:
        f.write(uploaded_file.read())
    
    st.info("Processing file and extracting highlights...")
    state = {"highlights": [], "summary": ""}
    result = app.invoke(state)
    summary_text = result["summary"]
    
    st.subheader("Summary:")
    st.markdown(summary_text)
    
    pdf_path = generate_pdf(summary_text)
    with open(pdf_path, "rb") as pdf_file:
        st.download_button(
            label="Download Summary as PDF",
            data=pdf_file,
            file_name="summary.pdf",
            mime="application/pdf"
        )
    os.remove("uploaded.pdf")
    os.remove(pdf_path)
else:
    st.info("Please upload a PDF to summarize.")
