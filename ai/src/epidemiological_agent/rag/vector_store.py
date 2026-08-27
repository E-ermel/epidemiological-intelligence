from pathlib import Path
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

AI_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_PATH = AI_ROOT / "src" / "knowledge" / "modeling_methodology.md"
CHROMA_PATH = AI_ROOT / "chroma_db"

def load_knowledge() -> str:
    return KNOWLEDGE_PATH.read_text(
        encoding="utf-8"
    )

def split_knowledge(
    text: str,
):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
    )

    return splitter.create_documents(
        [text]
    )


def build_vector_store():
    text = load_knowledge()

    documents = split_knowledge(
        text
    )

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(
            CHROMA_PATH
        ),
        collection_name="epidemiological_knowledge",
    )

    return vector_store
def get_vector_store():

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    return Chroma(
        persist_directory=str(
            CHROMA_PATH
        ),
        embedding_function=embeddings,
        collection_name="epidemiological_knowledge",
    )


def search_knowledge(
    query: str,
    k: int = 2,
):

    vector_store = (
        get_vector_store()
    )

    return (
        vector_store
        .similarity_search(
            query,
            k=k,
        )
    )