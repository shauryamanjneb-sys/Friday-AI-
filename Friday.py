import re
import os
import streamlit as st
import json
import hashlib
from sympy import sympify
from groq import Groq
from ddgs import DDGS
import time

# ---------------- CONFIG ----------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.1-8b-instant"
client = Groq(api_key=GROQ_API_KEY)

# ---------------- USERS FILE ----------------
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- LOGIN / SIGNUP PAGE ----------------
def login_page():
    st.title("Welcome to FRIDAY 🤖")
    st.markdown("### Please Login or Signup to continue")
    tab1, tab2 = st.tabs(["🔑 Login", "✍️ Signup"])
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", type="primary", use_container_width=True):
            users = load_users()
            if username in users and users[username]["password"] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.success(f"Welcome back, {username}!")
                time.sleep(0.8)
                st.rerun()
            else:
                st.error("Wrong username or password")
    with tab2:
        new_username = st.text_input("Choose Username", key="signup_user")
        email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Choose Password", type="password", key="signup_pass")
        if st.button("Create Account", type="primary", use_container_width=True):
            if new_username and email and new_password:
                users = load_users()
                if new_username in users:
                    st.error("Username already exists")
                else:
                    users[new_username] = {
                        "email": email,
                        "password": hash_password(new_password)
                    }
                    save_users(users)
                    st.success("Account created! Please login now.")
            else:
                st.error("Please fill all fields")

# ---------------- CALCULATOR ----------------
def calculate_expression(text):
    pattern = r"[-+]?\d+(?:\.\d+)?(?:\s*[-+*/]\s*[-+]?\d+(?:\.\d+)?)+"
    match = re.search(pattern, text)
    if not match:
        return None
    expr = match.group()
    try:
        result = sympify(expr)
        return f"{result} (≈ {float(result):.4f})"
    except:
        return None

# ---------------- SEARCH ----------------
def needs_search(text):
    text = text.lower()
    keywords = ["latest","current","recent","new","today","yesterday","news","update","suggest recent"
                "trending","search for","look up","who made","who is creator of","in 2026","in 2025","who is"]
    return any(k in text for k in keywords)

def improve_query(query):
    query = query.replace("search for", "").strip()
    if "latest" not in query.lower():
        query += " latest"
    query += " 2026"
    return query.strip()

def web_search(query):
    try:
        with DDGS(timeout=20) as ddgs:
            results = list(ddgs.text(query, max_results=12))
        cleaned = [f"{r.get('title', '')}: {r.get('body', '')}" for r in results
                   if r.get('title') and r.get('body')]
        return "\n".join(cleaned[:8]) if cleaned else "No fresh results found."
    except Exception as e:
        return f"Search failed: {str(e)}"

# ---------------- MEMORY ----------------
def memory_response(key, base_answer):
    if key not in st.session_state.memory:
        st.session_state.memory[key] = 0
    st.session_state.memory[key] += 1
    count = st.session_state.memory[key]
    if count == 1:
        return base_answer
    elif count == 2:
        return f"Sure 😊 {base_answer}"
    elif count == 3:
        return f"Happy to repeat it! {base_answer}"
    return base_answer

# ---------------- LLM ----------------
def ask_llm(user_prompt):
    messages = [{
        "role": "system",
        "content": """
You are FRIDAY, a friendly intelligent AI assistant created by Shaurya Anjney.
- Be natural, polite and helpful.
- Add small emojis sometimes 🙂
- NEVER say the user repeated something unless you see the EXACT same message multiple times in the history above.
- NEVER EVER SAY the user repeated hello, or hi or any sort of greeting twice at all cost
- Do not hallucinate repetitions.
- If the user asks "who is shaurya" or "who is shaurya anjney", just say: "Shaurya Anjney is the brilliant creator behind my existence."
"""
    }]
    messages.extend(st.session_state.history[-8:])
    messages.append({"role": "user", "content": user_prompt})
  
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.3,
        max_tokens=600,
        messages=messages
    )
    return response.choices[0].message.content.strip()

# ---------------- MAIN LOGIC (100% untouched) ----------------
def assistant_reply(user_input):
    text_lower = user_input.lower()
 
    if "your name" in text_lower:
        reply = memory_response("name", "My name is FRIDAY.")
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": reply})
        return reply
    if "who created you" in text_lower or "who made you" in text_lower:
        reply = memory_response("creator", "I was created by Shaurya Anjney.")
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": reply})
        return reply
    if "who is shaurya" in text_lower or "who is shaurya anjney" in text_lower or "who is he" in text_lower:
        reply = memory_response("shaurya", "Shaurya Anjney is the brilliant creator behind my existence.")
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": reply})
        return reply
    if calculate_expression(user_input):
        calc = calculate_expression(user_input)
        reply = f"The result is {calc}. 🧮"
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": reply})
        return reply

    for n in range(1, 8):
        if f"{n}{'st' if n==1 else 'nd' if n==2 else 'rd' if n==3 else 'th'} message" in text_lower or f"what was my {n}{'st' if n==1 else 'nd' if n==2 else 'rd' if n==3 else 'th'} message" in text_lower:
            if st.session_state.conversation_log and len(st.session_state.conversation_log) >= n:
                msg = st.session_state.conversation_log[n-1]
                reply = f"Your {n}{'st' if n==1 else 'nd' if n==2 else 'rd' if n==3 else 'th'} message was: \"{msg}\" 🙂"
            else:
                reply = f"You haven't sent a {n}{'st' if n==1 else 'nd' if n==2 else 'rd' if n==3 else 'th'} message yet."
            st.session_state.history.append({"role": "user", "content": user_input})
            st.session_state.history.append({"role": "assistant", "content": reply})
            return reply

    st.session_state.history.append({"role": "user", "content": user_input})
    st.session_state.conversation_log.append(user_input)
    if needs_search(user_input):
        query = improve_query(user_input)
        results = web_search(query)
        prompt = f"User question: {user_input}\n\nFresh web search results (use the newest info only):\n{results}\nAnswer using only the latest information."
        reply = ask_llm(prompt)
    else:
        reply = ask_llm(user_input)
    st.session_state.history.append({"role": "assistant", "content": reply})
    return reply

# ====================== STREAMLIT UI ======================
st.set_page_config(page_title="FRIDAY", page_icon="🤖", layout="wide")

# AUTH CHECK
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    login_page()
    st.stop()

# --------------------- PER-USER DATA ---------------------
current_user = st.session_state.current_user
for key in [f"chats_{current_user}", f"history_{current_user}", f"conversation_log_{current_user}",
            f"memory_{current_user}", f"current_chat_name_{current_user}", f"name_finalized_{current_user}"]:
    if key not in st.session_state:
        if "chats" in key:
            st.session_state[key] = []
        elif "history" in key or "conversation_log" in key:
            st.session_state[key] = []
        elif "memory" in key:
            st.session_state[key] = {}
        elif "current_chat_name" in key:
            st.session_state[key] = "New Conversation"
        else:
            st.session_state[key] = False

# Shortcuts
st.session_state.chats = st.session_state[f"chats_{current_user}"]
st.session_state.history = st.session_state[f"history_{current_user}"]
st.session_state.conversation_log = st.session_state[f"conversation_log_{current_user}"]
st.session_state.memory = st.session_state[f"memory_{current_user}"]
st.session_state.current_chat_name = st.session_state[f"current_chat_name_{current_user}"]
st.session_state.name_finalized = st.session_state[f"name_finalized_{current_user}"]

# Sidebar - New Chat FIXED
with st.sidebar:
    st.title("💬 My Chats")
    if st.button("➕ New Chat", type="primary", use_container_width=True):
        if st.session_state.history or st.session_state.conversation_log:
            st.session_state.chats.append({
                "name": st.session_state.current_chat_name,
                "history": st.session_state.history.copy(),
                "conversation_log": st.session_state.conversation_log.copy()
            })

        # FIX
        st.session_state[f"history_{current_user}"] = []
        st.session_state[f"conversation_log_{current_user}"] = []
        st.session_state[f"current_chat_name_{current_user}"] = "New Conversation"
        st.session_state[f"name_finalized_{current_user}"] = False

        st.session_state.history = []
        st.session_state.conversation_log = []
        st.session_state.current_chat_name = "New Conversation"
        st.session_state.name_finalized = False

        st.rerun()

    st.divider()
    st.subheader("Previous Chats")
    if st.session_state.chats:
        for i, chat in enumerate(st.session_state.chats):
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(chat["name"], key=f"switch_{i}", use_container_width=True):
                    st.session_state.history = chat["history"].copy()
                    st.session_state.conversation_log = chat["conversation_log"].copy()
                    st.session_state.current_chat_name = chat["name"]
                    st.session_state.name_finalized = True
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"del_{i}"):
                    st.session_state.confirm_delete = i
                    st.rerun()
    if "confirm_delete" in st.session_state:
        st.warning("Delete this chat permanently?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes", type="primary"):
                del st.session_state.chats[st.session_state.confirm_delete]
                del st.session_state.confirm_delete
                st.rerun()
        with c2:
            if st.button("No"):
                del st.session_state.confirm_delete
                st.rerun()

# Main UI
st.title("FRIDAY 🤖")

# Chat name animation (UNCHANGED)
name_placeholder = st.empty()
if st.session_state.current_chat_name != "New Conversation":
    displayed = ""
    for char in st.session_state.current_chat_name:
        displayed += char
        name_placeholder.subheader(f"💬 {displayed}▌")
        time.sleep(0.015)
    name_placeholder.subheader(f"💬 {st.session_state.current_chat_name}")
else:
    name_placeholder.subheader("💬 New Conversation")

st.markdown("Your friendly AI assistant — created by **Shaurya Anjney** 😊")

chat_container = st.container(height=520, border=True)
with chat_container:
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Talk to FRIDAY..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = assistant_reply(prompt)

            # FIXED CHAT NAME LOGIC
            if len(st.session_state.conversation_log) <= 4 and not st.session_state.name_finalized:
                try:
                    context = " ".join(st.session_state.conversation_log[:4])
                    topic_prompt = f"Create a short catchy 3-6 word title for this chat based on this conversation: {context}"
                    name_resp = client.chat.completions.create(
                        model=MODEL, temperature=0.5, max_tokens=25,
                        messages=[{"role": "user", "content": topic_prompt}]
                    )
                    new_name = name_resp.choices[0].message.content.strip().replace('"', '')[:40]
                    if new_name and len(new_name) > 5:
                        st.session_state.current_chat_name = new_name
                    if len(st.session_state.conversation_log) >= 4:
                        st.session_state.name_finalized = True
                except:
                    pass

            placeholder = st.empty()
            full = ""
            for char in reply:
                full += char
                placeholder.markdown(full + "▌")
                time.sleep(0.012)
            placeholder.markdown(full)

    st.rerun()

st.markdown("---")
st.caption("Made with ❤️ by Shaurya Anjney • ")
