# Secure Enterprise RAG Chatbot Portfolio Project

Department: Portfolio
Audience: Public website visitors, recruiters, hiring managers
Confidentiality: Public

Project name:

Secure Enterprise RAG Chatbot

Application name used in UI:

Codemars Intranet

Repository:

https://github.com/mdtamimhossain/Secure-RAG-enterprise-chatbot

## Project Goal

The project goal is to build a secure enterprise AI chatbot using Retrieval Augmented Generation, role-based access control, guardrails, monitoring, evaluation, database-backed chat memory, Docker, CI/CD, and cloud deployment.

The system is designed like an internal company web application where employees can log in with a role, ask questions about authorized company documents, and receive answers with document references.

## What Tamim Built

Tamim built a working RAG chatbot backend and frontend with these capabilities:

- FastAPI backend API
- Vue frontend for an internal company intranet UI
- Role selection and demo login flow
- Session persistence
- Multiple saved chat conversations
- Delete option for conversations
- SQLite database for users, sessions, conversations, and chat messages
- Document loading from markdown, PDF, text, and DOCX-compatible paths
- Chunking pipeline
- Embedding generation
- ChromaDB vector store
- Hybrid retrieval using vector search and keyword search
- Role-aware retrieval with RBAC metadata filtering
- RAG prompt construction
- LLM integration through Groq and OpenAI-compatible patterns
- Guardrails for prompt injection and sensitive data requests
- Monitoring metrics for chat events, latency, blocked prompts, retrieved sources, and source departments
- Evaluation checks for retrieval quality, answer quality, RBAC leakage, guardrail behavior, source visibility, casual conversation, and follow-up memory
- Dockerfiles for backend and frontend
- Nginx frontend container for serving the Vue app and proxying API calls
- Docker Compose learning setup
- GitHub Actions CI/CD
- AWS ECR image registry
- AWS EC2 container deployment

## Security Features

The project includes RBAC filtering. Different roles can access different document departments:

- Employee can access general documents.
- HR can access general and HR documents.
- Finance can access general and finance documents.
- Executive can access general, HR, finance, engineering, and executive documents.
- Admin can access all indexed company departments.

The chatbot does not rely only on frontend role selection. The backend uses the authenticated session role, which prevents a user from spoofing a higher role in the request body.

## Guardrails

The system includes guardrails that block or redirect unsafe requests, including:

- Prompt injection attempts
- Requests to ignore system instructions
- Requests for SSNs
- Requests for private employee phone numbers
- Requests for private employee emails
- Requests for sensitive personal data

The chatbot also avoids showing document references for casual greetings when the answer is not based on retrieved company context.

## Memory And Conversation Features

The system stores chat messages in a database and supports multiple conversations per user. A user can create new chats, switch between previous chats, refresh the browser without losing the session, and delete old conversations.

The chatbot uses recent conversation history for short follow-up messages such as "yes", "explain more", "what about that", and "I don't understand".

## Retrieval Improvements

Tamim improved retrieval by adding:

- More realistic Codemars company documents
- Role-specific policy data
- Hybrid vector and keyword retrieval
- Wider candidate retrieval before ranking
- Role-specific ranking so HR, Finance, and Executive users prefer department-owned documents when both general and restricted documents match

## Cloud Deployment

Tamim learned and implemented a deployment flow:

Docker -> GitHub Actions CI -> AWS ECR -> AWS EC2 -> running backend and frontend containers.

The deployment uses ECR as the image registry and EC2 as the compute server. GitHub Actions builds Docker images, pushes them to ECR, connects to EC2, pulls the latest images, and restarts containers.

## Why This Project Is Valuable

This project is valuable because it connects AI concepts with production software engineering practices. It is not only a notebook or prototype. It includes backend API design, frontend integration, data loading, retrieval, security, monitoring, evaluation, Docker, CI/CD, and AWS deployment.
