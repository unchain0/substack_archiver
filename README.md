# Substack Archiver & RAG Chatbot

Substack Archiver is a powerful Python tool designed to archive posts from your
favorite Substack newsletters and transform them into a personal, queryable
knowledge base.

The project has two main components:

1. **The Archiver**: A robust tool that uses Playwright to reliably download and
   save Substack posts in HTML, JSON, and clean plain text formats.
2. **The RAG Chatbot**: An intelligent assistant, powered by **Agno** and
   **OpenAI**, that allows you to "chat" with your archived content. Ask
   questions, get summaries, and find information across all your newsletters
   using natural language.

![Substack Archiver](README/images/cover.png)

## Features

- **Archive Multiple Substacks**: Configure a list of publications to archive
  in a single run.
- **Incremental Archiving**: Automatically skips already downloaded posts,
  saving time and bandwidth.
- **Multiple Formats**: Saves posts in HTML, JSON, and plain text.
- **Login Support**: Access paywalled or private posts by saving your login
  session.
- **Intelligent Chatbot (RAG)**: Interact with your entire archive through a
  conversational AI.
- **Semantic Search**: Uses vector embeddings (`text-embedding-3-large`) to
  find the most relevant information, even if the keywords don't match
  exactly.
- **Local Knowledge Base**: All your data is stored locally, and the chatbot
  uses it as its single source of truth, ensuring accurate and context-aware
  responses.
- **Powered by Agno**: Leverages the Agno framework for a seamless RAG
  implementation, connecting your data to large language models.

## Architecture

The system is composed of several key technologies working together:

- **Playwright**: For robust browser automation to scrape Substack content.
- **Agno**: A framework that orchestrates the RAG pipeline, managing the
  knowledge base, memory, and interaction with the LLM.
- **PostgreSQL + pgvector**: A local vector database to store and efficiently
  query the text embeddings of your archived posts.
- **OpenAI**: Utilizes `GPT-4o` for generating responses and
  `text-embedding-3-large` for creating vector embeddings.

## Getting Started

### Prerequisites

- [**uv**](https://github.com/astral-sh/uv): For Python package management.
- [**Docker**](https://www.docker.com/): To run the PostgreSQL database with the
  `pgvector` extension.
- [**OpenAI API Key**](https://platform.openai.com/api-keys): Required for the
  chatbot to function.

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/unchain0/substack_archiver.git
   cd substack_archiver
   ```

2. **Start the database:**

   Make sure Docker is running, then start the PostgreSQL database service:

   ```bash
   docker-compose up -d
   ```

3. **Install dependencies:**

   ```bash
   uv sync
   ```

4. **Install Playwright browsers:**

   ```bash
   playwright install
   ```

### Configuration

#### 1. Environment Setup (for the Chatbot)

- Create a file named `.env` in the root of the project.
- Add your OpenAI API key to it:

  ```env
  OPENAI_API_KEY="your-openai-api-key"
  ```

#### 2. Archiver Configuration

- Open the `config.json` file and add the Substack publication URLs you want
  to archive. The script will automatically extract the names.
- **Example `config.json`:**

  ```json
  [
    "https://artificialcorner.com/archive",
    "https://www.cafecomsatoshi.com.br/archive",
    "https://amoedo.substack.com"
  ]
  ```

## Usage

The application runs in two stages: first archiving the content, then running
the chatbot.

### Stage 1: Archiving Content

- To start the process, run the main script:

  ```bash
  uv run main.py
  ```

- The script will first archive the posts from the URLs in your
  `config.json`.
- After archiving, it will automatically process the text files, create
  vector embeddings, and load them into the `pgvector` database.

### (Optional) Saving Your Login Session

To access paywalled posts, you need to save your Substack login session.

1. **Run the `save_session.py` script:**

   ```bash
   uv run scripts/save_session.py
   ```

2. A Chromium browser will open. Log in to your Substack account.
3. Once logged in, close the browser. A `storage_state.json` file will be
   created.
4. The main archiver will now use this session for all future runs.

### Stage 2: Interacting with the Chatbot

- After the archiving and embedding process is complete, the chatbot will
  automatically start in your terminal.
- You can now ask questions about your archived content in natural language.

**Example Interaction:**

```text
Talk to the assistant. Type 'exit' to quit.
User: What do the articles say about Bitcoin adoption in Latin America?
Assistant: The articles mention that...
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
