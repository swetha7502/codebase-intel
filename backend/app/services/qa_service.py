"""
RAG-based Q&A over an indexed codebase using LangChain + ChromaDB.
"""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from app.core.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an expert software engineer helping a new developer understand a codebase.

Use the following code snippets retrieved from the repository to answer the question.
Be specific — mention file paths, function names, and line numbers when relevant.
If the code snippets don't contain enough info, say so clearly.

Retrieved code context:
{context}

Question: {question}

Answer:"""
)


def get_qa_chain(repository_id: str) -> RetrievalQA:
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )
    vectorstore = Chroma(
        persist_directory=settings.chroma_persist_dir,
        embedding_function=embeddings,
        collection_name="code_symbols",
    )
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": 8,
            "filter": {"repository_id": repository_id},
        }
    )
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": SYSTEM_PROMPT},
        return_source_documents=True,
    )


def answer_question(repository_id: str, question: str) -> dict:
    chain = get_qa_chain(repository_id)
    result = chain.invoke({"query": question})

    sources = []
    for doc in result.get("source_documents", []):
        meta = doc.metadata
        sources.append({
            "file_path": meta.get("file_path"),
            "qualified_name": meta.get("qualified_name"),
            "kind": meta.get("kind"),
            "line_start": meta.get("line_start"),
        })

    return {
        "answer": result["result"],
        "sources": sources,
    }
