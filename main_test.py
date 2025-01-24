pip install -r requirements.txt

from kiwipiepy import Kiwi
from kiwipiepy.utils import Stopwords
import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain.retrievers import BM25Retriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import gridfs
import os
import tempfile
import pickle
import streamlit as st
from dotenv import load_dotenv
import os
from langchain_teddynote import logging
import asyncio
import uuid

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
uri = "mongodb+srv://yiji:yiji1214@cluster0.v1ig9.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))
embeddings_model = OpenAIEmbeddings(model = 'text-embedding-3-small', api_key = api_key)

logging.langsmith(project_name="Hongdae_restaurants")
# logging.langsmith("Hongdae_restaurants", set_enable=False) # Disable logging

db = FAISS(
    embedding_function=embeddings_model,
    index=faiss.IndexFlatL2(1536),
    docstore=InMemoryDocstore(),
    index_to_docstore_id={},
)

db_m = client["Hongdae"]
faiss = gridfs.GridFS(db_m)

def create_virtual_folder_with_files():
    # 임시 폴더 생성
    temp_folder = tempfile.TemporaryDirectory()
    folder_path = temp_folder.name  # 임시 폴더 경로

    # MongoDB에서 파일 다운로드
    def download_file_from_mongodb(filename, output_path):
        file = faiss.find_one({"filename": filename})
        if file:
            with open(output_path, "wb") as f:
                f.write(file.read())

    # 필요한 파일 다운로드
    download_file_from_mongodb("index.faiss", os.path.join(folder_path, "index.faiss"))
    download_file_from_mongodb("index.pkl", os.path.join(folder_path, "index.pkl"))

    # 임시 폴더 경로 반환 (폴더는 프로그램 종료 시 삭제됨)
    return folder_path, temp_folder

# 임시 폴더 생성 및 파일 저장
folder_path, temp_folder = create_virtual_folder_with_files()

db = db.load_local(folder_path, embeddings=embeddings_model, allow_dangerous_deserialization=True)
docs = db.docstore._dict.values()

kiwi = Kiwi(typos="basic", model_type='sbg')
stopwords = Stopwords()
stopwords.remove(('사람', 'NNG'))

def kiwi_tokenize(text):
    split_s = kiwi.tokenize(text, stopwords=stopwords, normalize_coda=True)
    split_list = [i.form for i in split_s]
    split_f = ','.join(split_list).replace(",", " ")
    return split_f

def kiwi_word(text):
    split_s = kiwi.tokenize(text, stopwords=stopwords, normalize_coda=True)
    N_list = [i.form for i in split_s if i.tag == "NNG" or i.tag == "NNP"]
    return N_list

with open("bm25_retriever.pkl", "rb") as f:
    bm25_retriever = pickle.load(f)

with open("bm25_word.pkl", "rb") as f:
    bm25_word = pickle.load(f)

faiss_retriever = db.as_retriever(search_kwargs={"k": 5})


prompt_text = """
Your role is to recommend a place to eat something to the user.
Follow the instructions below to achieve your role.

1) Read the user's message and rephrase it in a standard language to understand the user's intention deeply.
2) Choose one that is most relevant to the user's intention from the list of restaurants.
Each of the restaurants consists of the 0. 가게명, 1. 메뉴목록, 2. 리뷰목록. Carefully read the information. 
list of restaurants:
{context}
4) Answer the name of the chosen restaurant and the reason for the recommendation.
4-1) If you cannot find a suitable restaurant, you must choose a place not in the list of restaurants, but from the chat history.
Please try to match a correct menu.
4-2) If you can never find a suitable restaurant, encourage the user to ask in other ways.
4-3) If the user's message is not related to the place to eat, encourage the user to get a recommendation or rather, you suggest a menu to the user first.
5) Answer in Korean.
"""

bm25_retriever.invoke('.')
bm25_word.invoke('.')

def simplify_list(list, max_length):
    for i, store_data in enumerate(list):
        reviews_start = store_data.find("2. 리뷰목록:") 
        if reviews_start != -1:
            reviews = eval(store_data[reviews_start + len("2. 리뷰목록:"):])
            truncated_reviews = [review[:max_length] + "..." if len(review) > max_length else review for review in reviews]
            list[i] = (
                store_data[:reviews_start + len("2. 리뷰목록:")] + str(truncated_reviews)
            )
    return list

# Streamlit UI 설정
st.title("🍴 홍대 근처 음식점 추천 챗봇")
st.write("음식점 추천이 필요하면 질문해보세요!")


def RAG_lists(text):
    bm_r = bm25_retriever.invoke(text)
    bm_w = bm25_word.invoke(text)
    faiss_r = faiss_retriever.invoke(text)

    def add_to_list(source, RAG_list, max_length, n=0):
        while len(RAG_list) < max_length and n < len(source):
            if source[n] not in RAG_list:
                RAG_list.append(source[n])
            n += 1
        return n

    RAG_list = []
    n = add_to_list(faiss_r, RAG_list, 4)  # faiss_r에서 최대 4개 추가
    if len(RAG_list) < 7:
        n = add_to_list(bm_r, RAG_list, 7, n)  # bm_r에서 추가하여 최대 7개 채움
    if len(RAG_list) < 7:
        add_to_list(bm_w, RAG_list, 7)  # bm_w에서 추가하여 최대 7개 채움

    result = [doc.page_content for doc in RAG_list]
    if "context_memory" not in st.session_state:
        st.session_state["context_memory"] = []
    st.session_state["context_memory"].append(result)
    if len(st.session_state["context_memory"]) > 3:
        st.session_state["context_memory"].pop(0)
    return result


llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)
rag_runnable = RunnableLambda(lambda inputs: RAG_lists(inputs))


def get_or_create_user_id():
    if "user_id" not in st.session_state:
        # 랜덤 ID 생성
        st.session_state["user_id"] = str(uuid.uuid4())  # 고유 UUID 생성
    return st.session_state["user_id"]

if "user_memories" not in st.session_state:
    st.session_state["user_memories"] = {}

def get_user_memory():
    user_id = get_or_create_user_id()
    if user_id not in st.session_state["user_memories"]:
        # 사용자별 ConversationBufferWindowMemory 생성
        st.session_state["user_memories"][user_id] = ConversationBufferWindowMemory(
            memory_key="history",
            return_messages=True,
            k=3  # 최근 3개의 대화만 유지
        )
    return st.session_state["user_memories"][user_id]

prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ]
    )

user_memory = get_user_memory()
def load_memory(x):
    return user_memory.load_memory_variables({})["history"]


chain = (
    {"context": rag_runnable, "question": RunnablePassthrough()}
    | RunnablePassthrough.assign(history=load_memory)
    | prompt_template
    | llm
    | StrOutputParser()
)

def invoke_chain(question):
    result = chain.invoke(question)
    user_memory.save_context(
        inputs={"question": question},
        outputs={
            "response": result
            + "▧ This was responsed by following RAG results: "
            + ", ".join(map(str, simplify_list(st.session_state["context_memory"][-1][:3], 40)))
        },
    )
    return result

# 비동기 함수 (사용자별 context_memory 관리)
async def invoke_chain_async(question):
    # 예시로 비동기적으로 처리
    result = await asyncio.to_thread(invoke_chain, question)
    # 사용자 context_memory 업데이트
    # st.session_state["context_memory"].append(
    #     {"question": question, "response": result}
    # )
    return result

# 사용자 입력 받기
user_input = st.text_input("질문을 입력하세요", key="user_input")

# Streamlit의 비동기 지원 활용
if user_input:
    # 비동기 작업 처리
    response = asyncio.run(invoke_chain_async(user_input))

    # UI 업데이트
    st.text_area("🤖 챗봇의 응답", value=response, height=200)
    print(load_memory(""))

    # 대화 기록 표시
    st.write("### 대화 기록")
    st.write(load_memory("")[0].content)
    split_a = load_memory("")[1].content.find("▧")
    st.write(load_memory("")[1].content[:split_a])
    try:
        st.write(load_memory("")[2].content)
        split_b = load_memory("")[3].content.find("▧")
        st.write(load_memory("")[3].content[:split_b])
    except IndexError:
        pass
    try:
        st.write(load_memory("")[4].content)
        split_c = load_memory("")[5].content.find("▧")
        st.write(load_memory("")[5].content[:split_c])
    except IndexError:
        pass

# streamlit run main_test.py

# 가상환경:
# C:\Users\nodap\OneDrive\Desktop\bigdata\study\.venv\Scripts\Activate.ps1