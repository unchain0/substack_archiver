"""
Optimized FAISS-based RAG system with the following performance improvements:

1. Vector Store Persistence: Saves and loads vector store from disk to avoid recomputation
2. Incremental Updates: Only recreates vector store when new documents are added
3. Batch Processing: Processes documents in batches to reduce memory usage
4. Optimized Chunk Size: Uses larger chunks (1000 chars) with overlap for better context
5. Limited Retrieval: Retrieves only top 5 most relevant documents
6. Fast Text Splitting: Uses RecursiveCharacterTextSplitter for efficient chunking
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from typing import Any, Optional, cast


class Rag:
    def __init__(self, temperature: float) -> None:
        """Initialize the RAG system.

        Args:
            temperature: The temperature for the LLM (0-1)
        """
        load_dotenv()

        self.temperature = temperature
        self.archive_path = Path(__file__).parents[1] / "archive"
        self.vector_store_path = self.archive_path / "vector_store"
        self.vector_store: Optional[FAISS] = None
        self.chat_history: list[Any] = []
        self.convo_qa_chain: Any = None

        # Initialize models
        self._init_models()
        self._load_docs()
        self._setup_chains()

    def _init_models(self) -> None:
        """Initialize the LLM and embeddings."""
        self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=self.temperature)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    def _load_docs(self) -> None:
        if self.vector_store_path.exists() and not self._is_vector_store_outdated():
            print("Loading existing vector store...")
            self.vector_store = FAISS.load_local(
                str(self.vector_store_path), self.embeddings, allow_dangerous_deserialization=True
            )
            print("Vector store loaded from disk.")
            return

        print("Vector store is outdated or doesn't exist. Recreating...")

        # Load documents from the specified archive path
        print("Loading documents from archive...")
        loader = DirectoryLoader(
            str(self.archive_path),
            glob="**/*.txt",
            loader_cls=TextLoader,
            use_multithreading=True,
            show_progress=True,
        )
        data = loader.load()

        if not data:
            print("No documents found in archive.")
            return

        # Split documents into manageable chunks
        print("Splitting documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
        )
        all_splits = text_splitter.split_documents(data)

        # Store splits in the vector store with batch processing
        print("Creating vector store...")
        batch_size = 100
        total_batches = (len(all_splits) + batch_size - 1) // batch_size

        with Progress(
            TextColumn("[bold blue]Processing batches..."),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[bold green]{task.completed}/{task.total} batches"),
            TimeRemainingColumn(),
            transient=False,
        ) as progress:
            batch_task = progress.add_task("Creating vector store", total=total_batches)

            for i in range(0, len(all_splits), batch_size):
                batch = all_splits[i : i + batch_size]
                batch_num = i // batch_size + 1

                progress.update(batch_task, description=f"Processing batch {batch_num}/{total_batches}")

                if i == 0:
                    self.vector_store = FAISS.from_documents(batch, embedding=self.embeddings)
                else:
                    if self.vector_store:  # Ensure vector_store is not None
                        batch_store = FAISS.from_documents(batch, embedding=self.embeddings)
                        self.vector_store.merge_from(batch_store)

                progress.advance(batch_task)

        print("Saving vector store to disk...")
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        if self.vector_store:  # Ensure vector_store is not None
            self.vector_store.save_local(str(self.vector_store_path))
        print("Vector store created and saved.")

    def _setup_chains(self) -> None:
        condense_question_system_template = (
            "Given a chat history and the user's last question"
            "which may refer to the context in the chat history, "
            "formulate an autonomous question that can be understood "
            "without the chat history. Do NOT answer the question, "
            "only rephrase it if necessary and otherwise return it as it is."
        )

        condense_question_prompt = ChatPromptTemplate.from_messages([
            ("system", condense_question_system_template),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ])
        history_aware_retriever = create_history_aware_retriever(
            self.llm,
            self.vector_store.as_retriever(search_kwargs={"k": 5}) if self.vector_store else None,
            condense_question_prompt,
        )

        system_prompt = (
            "You are an assistant for question-answering tasks. "
            "Use the following parts of the retrieved context to answer"
            "the question. If you don't know the answer, say that "
            "you don't know. Use a maximum of three sentences and keep the "
            "answer concise."
            "\n\n"
            "{context}"
        )

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ])
        qa_chain = create_stuff_documents_chain(self.llm, qa_prompt)

        self.convo_qa_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    def ask(self, user_input: str) -> str:
        if not self.convo_qa_chain:
            return "The conversation chain has not been initialized."

        response = self.convo_qa_chain.invoke({
            "input": user_input,
            "chat_history": self.chat_history,
        })

        self.chat_history.extend([
            HumanMessage(content=user_input),
            AIMessage(content=response["answer"]),
        ])

        return cast(str, response["answer"])

    def _is_vector_store_outdated(self) -> bool:
        """Check if vector store needs to be recreated based on archive modification time."""
        if not self.vector_store_path.exists():
            return True

        vector_store_files = list(self.vector_store_path.glob("*"))
        if not vector_store_files:
            return True

        vector_store_time = max(f.stat().st_mtime for f in vector_store_files)

        archive_files = list(self.archive_path.rglob("*.txt"))
        if not archive_files:
            return False

        most_recent_archive_time = max(f.stat().st_mtime for f in archive_files)

        buffer_time = 5

        return most_recent_archive_time > (vector_store_time + buffer_time)

    @staticmethod
    def initialize(temperature: float = 0) -> None:
        """Initialize the RAG system and start a conversation loop.

        Args:
            temperature: The temperature for the LLM (0-1)
        """
        rag_service = Rag(temperature=temperature)
        print("Talk to the assistant. Type 'exit' to quit.")
        while True:
            user_input = input("User: ")
            if user_input.lower() == "exit":
                break
            answer = rag_service.ask(user_input)
            print(f"Assistant: {answer}")
