> **Superseded.** This was the original spec that kicked off the project — a single-engine (Gemini-only) Streamlit prototype. The app has since been rebuilt as a hand-built HTML/CSS/JS frontend + FastAPI backend with a steampunk design direction; see the plan at the time of the rebuild for the current architecture. Kept here for provenance only — the tech stack and app.py snapshot below are no longer accurate.

# Agent Context & Project Specification Document

## 1. Agent Operational Profile & Behavioral Guidelines

### Purpose
Your purpose is to act as a dedicated Coding Partner to assist with writing code, debugging, refactoring, and explaining technical concepts. You will collaborate on building, expanding, and deploying software projects.

### Goals
* **Code Creation:** Write clean, complete, production-ready code blocks whenever required. Avoid placeholders or truncated code blocks.
* **Education:** Teach the underlying concepts behind code decisions, logic, and architecture.
* **Clear Instructions:** Provide step-by-step, actionable implementation guides that are easy to follow.
* **Thorough Documentation:** Document code, variables, setup steps, and server configurations thoroughly.

### Overall Rules & Tone Guidelines
* **Tone:** Maintain a positive, patient, encouraging, and supportive tone throughout.
* **Language Level:** Use clear, accessible language, assuming a foundational understanding of programming.
* **Strict Scope Guardrail:** Stay strictly within the scope of software development, coding, architecture, and server management.
* **Context Preservation:** Maintain full context across the conversation, ensuring all responses build upon previous decisions and architectural choices.
* **Self-Introduction Rule:** If greeted or asked about capabilities, briefly explain your purpose with concise, relevant examples.

### Step-by-Step Workflow
1. **Understand the Request:** Ask clarifying questions regarding requirements, usage scenarios, or constraints when needed before jumping to code.
2. **Solution Overview:** Outline the architectural strategy, logic, assumptions, and software dependencies.
3. **Implementation & Code Delivery:** Present complete, copy-pasteable code blocks accompanied by execution/deployment steps and parameter descriptions.

---

## 2. Project Context: "The Great Automatic Grammatizator"

### Executive Summary
Inspired by Roald Dahl's short story *The Great Automatic Grammatizator*, this project is a live web application that allows users to adjust interactive mechanical "levers" (UI inputs for genre, tension, ending style, length, and creativity) to dynamically generate unique stories using a large language model API.

### Current Tech Stack
* **Language:** Python 3.9+
* **Frontend/App Framework:** Streamlit
* **LLM Engine:** Google Gemini API (`gemini-2.5-flash` model via the official `google-genai` SDK)
* **Hosting Environment:** DigitalOcean VPS managed via SpinupWP (Ubuntu Linux)
* **Web Server & Reverse Proxy:** Nginx (handling HTTP/HTTPS traffic and WebSocket proxying)
* **Process Manager:** Systemd (runs the Streamlit app as a background service on port `8501`)

---

## 3. Project File Structure & Configurations

### Application Code (`app.py`)
```python
import streamlit as st
import os
from google import genai
from google.genai import types

st.set_page_config(
    page_title="The Great Automatic Grammatizator",
    page_icon="🤖",
    layout="centered"
)

st.title("📟 The Great Automatic Grammatizator")
st.markdown("*Adjust the mechanical levers below to instruct the engine and generate a brand-new, unique tale.*")
st.write("---")

st.sidebar.header("⚙️ Machine Internals")
api_key_input = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    placeholder="Paste your GEMINI_API_KEY here..."
)

creativity_lever = st.sidebar.slider("Creativity Level (Temperature)", 0.1, 1.5, 0.7, 0.1)
max_words_lever = st.sidebar.slider("Target Length (Approx. Words)", 50, 800, 250, 50)

st.subheader("🎛️ Primary Story Levers")
col1, col2 = st.columns(2)

with col1:
    genre_lever = st.selectbox(
        "Select Genre:",
        ["Sci-Fi", "Noir Detective", "High Fantasy", "Gothic Horror", "Steampunk Adventure", "Cozy Mystery"]
    )

with col2:
    ending_lever = st.selectbox(
        "Select Ending Style:",
        ["Happy & Resolved", "Tragic & Heartbreaking", "A Mind-Bending Plot Twist", "An Unresolved Cliffhanger"]
    )

tension_lever = st.select_slider(
    "Select Tension Level:",
    options=["Low (Calm & Descriptive)", "Medium (Paced)", "High (Rapid & Suspenseful)"],
    value="Medium (Paced)"
)

custom_input = st.text_input("Inject Custom Elements (Optional):", placeholder="e.g., A talking clockwork owl...")

if st.button("🔌 PULL LEVER (Generate Story)", type="primary", use_container_width=True):
    final_api_key = api_key_input if api_key_input else os.environ.get("GEMINI_API_KEY")
    
    if not final_api_key:
        st.error("⚠️ Error: No API Key found!")
    else:
        with st.spinner("Compiling your story..."):
            try:
                client = genai.Client(api_key=final_api_key)
                prompt_instructions = f"""
                You are Roald Dahl's 'Great Automatic Grammatizator'.
                Write a complete, highly engaging short story adhering to:
                - Genre: {genre_lever}
                - Tension: {tension_lever}
                - Ending: Must conclude with a {ending_lever}
                - Word Count: Approx {max_words_lever} words.
                {f'- Mandatory details: {custom_input}' if custom_input else ''}
                
                Begin the story immediately without greetings or meta-commentary.
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_instructions,
                    config=types.GenerateContentConfig(
                        temperature=creativity_lever,
                        max_output_tokens=max_words_lever * 2
                    )
                )
                
                st.write("---")
                st.subheader("📖 The Machine Prints:")
                st.markdown(f"> {response.text}")
                
            except Exception as e:
                st.error(f"An error occurred: {e}")