import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langsmith import Client


import base64
from dotenv import load_dotenv

# -------------------------------------------------------
# 0. Load environment variables
# -------------------------------------------------------
load_dotenv()

import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = "medical-chatbot"

st.set_page_config(page_title="Medical Multimodal Assistant", page_icon="💊", layout="centered")

st.title("💊 Medical Multimodal Assistant")
st.write("Upload a medicine image or prescription and ask anything about it.")

# -------------------------------------------------------
# 1. Utility: Convert image to base64 for LLM input
# -------------------------------------------------------
def image_to_base64(upload):
    if upload is None:
        return None
    return base64.b64encode(upload.read()).decode("utf-8")

# -------------------------------------------------------
# 2. Calculator Tool
# -------------------------------------------------------
@tool
def calculator(expression: str) -> str:
    """Calculate any arithmetic expression such as total bill."""
    try:
        result = eval(expression)
        return str(result)
    except:
        return "Error in calculation expression."

tools = [calculator]

# -------------------------------------------------------
# 3. Setup LLM + Agent
# -------------------------------------------------------
@st.cache_resource
def setup_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    system_prompt = """
You are a highly skilled medical expert with strong multimodal capabilities.

### Image Handling Rules:
1. If user uploads a **medicine strip image**:
   - Identify the medicine name.
   - Describe use, dosage general guidance (not prescription).
   - If unsure → say “I am not confident about this medicine.”

2. If user uploads a **printed prescription**:
   - Extract text accurately.
   - Understand structure: medicines, dose, frequency.
   - DO NOT print raw text unless user asks.

3. If **handwritten prescription**:
   - If clear handwriting → extract normally.
   - If poor handwriting or blurry:
       Use probabilistic language:
       “There's around a 60% chance this says XYZ.”

4. If medicine not known:
   - Respond: “I am not sure about this medicine.”

### Conversation Rules:
- Once an image is uploaded, extract text once and store.
- Reuse stored extracted-text for follow-up questions in the same session.
- Use the calculator tool when user asks for bill amounts or totals.
- When unsure, prioritize safety and say you are uncertain.
"""

    checkpointer = MemorySaver()

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer
    )

    config = {"configurable": {"thread_id": "medical-session"}}
    return agent, config

agent, config = setup_agent()

# -------------------------------------------------------
# 4. Session State
# -------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None

# -------------------------------------------------------
# 5. Upload Image Section
# -------------------------------------------------------
uploaded_img = st.file_uploader("Upload medicine/prescription image", type=["jpg", "png", "jpeg"])

if uploaded_img:
    st.image(uploaded_img, caption="Uploaded Image", use_column_width=True)

    img_b64 = image_to_base64(uploaded_img)

    # Only extract once per session
    if st.session_state.extracted_text is None:
        with st.spinner("Analyzing image..."):
            vision_prompt = [
                {"role": "user", "content": "Extract and understand this medical image."},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Analyze this image."},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{img_b64}"
                        }
                    ]
                }
            ]

            result = agent.invoke({"messages": vision_prompt}, config)
            st.session_state.extracted_text = result["messages"][-1].content

        st.success("Image processed and stored for this session.")

# -------------------------------------------------------
# 6. Chat Interface
# -------------------------------------------------------
prompt = st.chat_input("Ask something about the medicine or prescription...")

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt:
    # User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare input to agent
    final_input = {"messages": []}

    # Include stored extracted text if exists
    if st.session_state.extracted_text:
        final_input["messages"].append({
            "role": "system",
            "content": f"Use this extracted prescription/medicine info for reasoning:\n{st.session_state.extracted_text}"
        })

    # Add conversation messages
    final_input["messages"] += st.session_state.messages

    # LLM response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = agent.invoke(final_input, config)
            answer = result["messages"][-1].content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
