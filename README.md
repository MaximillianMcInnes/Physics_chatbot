# Physics RAG Chatbot (AQA)

A Retrieval-Augmented Generation (RAG) based physics chatbot designed to answer AQA A-Level Physics questions using **spec-aligned sources**, including:

- SaveMyExams notes  
- Physics & Maths Tutor (PMT)  
- AQA Specification  
- Textbook extracts  

The system retrieves relevant content and generates grounded answers with references.

---

## 🚀 Features

- Spec-aligned knowledge base (AQA Physics)
- Source-linked answers (SaveMyExams, textbook, etc.)
- Local vector database (FAISS)
- Modular pipeline (data → embeddings → retrieval → LLM)
- CLI-based testing interface
- Docker-ready for deployment

---

## 📦 Requirements

You will need:

- Python **3.10+**
- OpenAI API key → https://platform.openai.com/api-keys
- Git
- (Optional) Docker

---

## ⚙️ Installation

```bash
git clone https://github.com/MaximillianMcInnes/Physics_chatbot.git
cd Physics_chatbot
pip install -r requirements.txt