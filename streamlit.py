import streamlit as st
from fpdf import FPDF
import fitz  # PyMuPDF for PDF text extraction
import os

def extract_text_from_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "\n".join([page.get_text("text") for page in doc])
    return text

def generate_pdf(text):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Use a Unicode-supporting font
    pdf.add_font("Arial", "", "arial.ttf", uni=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text.encode("utf-8").decode("utf-8"))
    
    pdf_path = "generated_document.pdf"
    pdf.output(pdf_path, "F")
    return pdf_path

# Sidebar components
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Enter API Key", type="password")
uploaded_file = st.sidebar.file_uploader("Upload a document", type=["txt", "md", "pdf"])

# Main content
st.title("Markdown/PDF Viewer and PDF Generator")

if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1]
    
    if file_extension == "pdf":
        file_content = extract_text_from_pdf(uploaded_file)
    else:
        file_content = uploaded_file.read().decode("utf-8")
    
    st.markdown(file_content)
    
    pdf_path = generate_pdf(file_content)
    
    with open(pdf_path, "rb") as pdf_file:
        st.download_button(
            label="Download PDF",
            data=pdf_file,
            file_name="document.pdf",
            mime="application/pdf"
        )
    
    # Cleanup
    os.remove(pdf_path)
else:
    st.info("Please upload a document (TXT, MD, or PDF) to display and download.")
