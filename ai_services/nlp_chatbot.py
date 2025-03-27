from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import OpenAI
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

class TravelChatbot:
    def __init__(self):
        self.llm = OpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = self._initialize_knowledge_base()

    def _initialize_knowledge_base(self):
        # Sample travel knowledge (replace with your data)
        texts = [
            "Manali is best visited between March to June",
            "Pune to Manali flights cost around ₹5000-8000",
            "Popular activities: Rohtang Pass, Solang Valley"
        ]
        return FAISS.from_texts(texts, self.embeddings)

    def respond(self, query: str):
        qa_chain = ConversationalRetrievalChain.from_llm(
            self.llm,
            self.vectorstore.as_retriever(),
            memory=self.memory
        )
        return qa_chain({"question": query})["answer"]