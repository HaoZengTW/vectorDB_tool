from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
from langchain.schema.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')

llm = ChatGroq(
    model="llama-3.2-90b-vision-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

def summarize_image(encoded_image):
    prompt = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": "你是一個善於分圖像的專家.請用繁體中文詳細解釋這圖片的內容."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                },
            },
        ])
    ]
    response = llm.invoke(prompt)
    return response.content

summary_prompt = """
請用繁體中文幫我總結下列markdown表格內容.
markdown:
{element}
"""

table_llm = ChatGroq(
    model="llama-3.1-70b-versatile",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

table_prompt=ChatPromptTemplate.from_template(summary_prompt)

summary_chain = table_prompt | table_llm | StrOutputParser()

def summarize_table(context):
    return summary_chain.invoke(context)
