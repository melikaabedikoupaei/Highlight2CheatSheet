from langgraph.graph import StateGraph, START, END
from typing import Annotated, List
from typing_extensions import TypedDict
from operator import add
import fitz  # PyMuPDF
from collections import Counter
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate

# Load .env variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(api_key=GROQ_API_KEY, model="gemma2-9b-it")

# Define State Structure
class State(TypedDict):
    highlights: Annotated[List[dict], add]  # Store highlights with context
    summary: str  # Store final summary

# Function to extract highlights with context
def extract_highlights(state: State) -> State:
    pdf_path = "uploaded.pdf"  
    doc = fitz.open(pdf_path)

    highlights = []
    text_blocks = []

    # Extract text with font size details for all pages
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text_instances = page.get_text("dict")["blocks"]

        page_texts = [
            {"text": span["text"], "size": span["size"], "bbox": span["bbox"], "page": page_num + 1}
            for block in text_instances if block["type"] == 0
            for line in block["lines"]
            for span in line["spans"]
        ]

        # Determine dynamic header threshold
        font_sizes = [block["size"] for block in page_texts]
        header_threshold = Counter(font_sizes).most_common(1)[0][0] * 1.2 if font_sizes else 12

        text_blocks.append((page_texts, header_threshold))

    # Extract highlights
    for page in doc:
        page_num = page.number + 1
        annotations = page.annots() or []

        for annot in annotations:
            if annot.type[0] == 8:  # Highlight annotation type
                highlight_text = page.get_text("text", clip=annot.rect).strip()
                highlight_rect = annot.rect

                page_texts, header_threshold = text_blocks[page_num - 1]

                # Identify headers dynamically
                headers_above = [block for block in page_texts if block["size"] > header_threshold and block["bbox"][1] < highlight_rect.y0]
                headers_below = [block for block in page_texts if block["size"] > header_threshold and block["bbox"][1] > highlight_rect.y1]

                header_above_text = headers_above[-1]["text"] if headers_above else None
                header_below_text = headers_below[0]["text"] if headers_below else None

                # Extract context text between headers
                if header_above_text and header_below_text:
                    context = [block["text"] for block in page_texts if headers_above[-1]["bbox"][3] <= block["bbox"][1] <= headers_below[0]["bbox"][1]]
                elif header_above_text:
                    context = [block["text"] for block in page_texts if headers_above[-1]["bbox"][3] <= block["bbox"][1]]
                else:
                    context = [block["text"] for block in page_texts]

                highlights.append({
                    "highlight": highlight_text,
                    "page": page_num,
                    "header_above": header_above_text,
                    "header_below": header_below_text,
                    "context": " ".join(context)
                })

    state["highlights"].extend(highlights)
    return state

# Summarization Prompts
chunks_prompt = """
Please summarize based on what user highlight in the context for cheat sheet `{text}`
Summary:
"""
map_prompt_template = PromptTemplate(input_variables=['text'], template=chunks_prompt)

final_combine_prompt = """
Provide a final summary of the entire highlights in a way that is easy to read `{text}`
"""
final_combine_prompt_template = PromptTemplate(input_variables=['text'], template=final_combine_prompt)

# Function to summarize highlights in batches
def summarize_highlights(state: State) -> State:
    highlights = state["highlights"]
    
    batch_size = 5  # Process in chunks
    summaries = []

    for i in range(0, len(highlights), batch_size):
        batch = highlights[i:i + batch_size]
        
        # Convert each highlight + context into a Document
        documents = [
            Document(
                page_content=f"User highlight:\n{h['highlight']}\n\nContext:\n{h['context']}",
                metadata={"page": h["page"], "header_above": h["header_above"], "header_below": h["header_below"]}
            )
            for h in batch
        ]

        # Summarize the batch
        summary_chain = load_summarize_chain(
            llm=llm,
            chain_type='map_reduce',
            map_prompt=map_prompt_template,
            combine_prompt=final_combine_prompt_template,
            verbose=False
        )
        
        summary = summary_chain.invoke(documents)
        summaries.append(summary)

    # Combine all batch summaries
    state["summary"] = "\n\n".join(summaries)
    
    return state

# Define LangGraph Workflow
workflow = StateGraph(State)

# Add nodes
workflow.add_node("extract_highlights", extract_highlights)
workflow.add_node("summarize_highlights", summarize_highlights)

# Define execution flow
workflow.add_edge(START, "extract_highlights")
workflow.add_edge("extract_highlights", "summarize_highlights")
workflow.add_edge("summarize_highlights", END)

# Compile the application
app = workflow.compile()


