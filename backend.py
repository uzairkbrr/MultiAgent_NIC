from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from prompts import doctor_prompt, language_safety_prompt, ner_prompt
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict, Literal, Annotated
from pydantic import Field, BaseModel
from dotenv import load_dotenv
import operator
import json
import sqlite3
from datetime import datetime
import os
import re

load_dotenv()

NER_DATA_DIR = "ner_data"
USERS_DATA_FILE = "users_data.json"

model = ChatOpenAI(model="gpt-4o-mini",temperature=0.5, max_tokens=1000)

# Custom Message classes with timestamps
class TimestampedHumanMessage(HumanMessage):
    timestamp: datetime = Field(default_factory=datetime.now)

class TimestampedAIMessage(AIMessage):
    timestamp: datetime = Field(default_factory=datetime.now)

class State(TypedDict):
    messages:Annotated[list[BaseMessage], add_messages]
    session_id:str
    time_stamps: Annotated[list[datetime], operator.add]
    ner_entities: Annotated[list[str], operator.add]
    chat_response: str  #Temporary string
    current_user: str

class PersonEntity(BaseModel):
    """Named person in the client's narrative"""
    name: str = Field(description="Name of the person mentioned")
    relationship: str = Field(description="Relationship to the client (e.g., 'mother', 'ex-partner', 'friend', 'self')")
    significance: str = Field(description="Why this person is significant in the therapeutic context", default="")
    emotional_charge: Literal["positive", "negative", "neutral"] = Field(description="Emotional association the client has with this person", default="neutral")

class PlaceEntity(BaseModel):
    """Named place in the client's narrative"""
    location: str = Field(description="Name or description of the place")
    context: str = Field(description="Context in which this place was mentioned")
    emotional_association: str = Field(description="Emotional significance of this place to the client")

class EventEntity(BaseModel):
    """Significant event in the client's narrative"""
    event: str = Field(description="Description of the event")
    timeframe: str = Field(description="When this event occurred (e.g., 'childhood', 'last year', 'recently')")
    trauma_relevance: Literal["high", "medium", "low"] = Field(description="How relevant this event is to trauma processing")
    description: str = Field(description="Additional therapeutic context about this event")

class SubstanceEntity(BaseModel):
    """Substance use mentioned by client"""
    substance: str = Field(description="Type of substance (alcohol, drugs, medication, etc.)")
    usage_pattern: str = Field(description="How the substance is being used")
    context: str = Field(description="Context around substance use - coping mechanism, medical, social, etc.")

class NamedEntity(BaseModel):
    people: list[PersonEntity] = Field(default_factory=list, description="People mentioned by the client")
    places: list[PlaceEntity] = Field(default_factory=list, description="Places mentioned by the client")
    events: list[EventEntity] = Field(default_factory=list, description="Significant events mentioned by the client")
    substances: list[SubstanceEntity] = Field(default_factory=list, description="Substances mentioned by the client")

os.makedirs(NER_DATA_DIR, exist_ok=True)
def load_users_data():
    """Load all users data"""
    if os.path.exists(USERS_DATA_FILE):
        with open(USERS_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users_data(users_data):
    """Save all users data"""
    with open(USERS_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=4, ensure_ascii=False, default=str)

def validate_cnic(cnic: str) -> bool:
    """Validate CNIC format (13 digits)"""
    cnic_cleaned = re.sub(r'[-\s]', '', cnic)
    return len(cnic_cleaned) == 13 and cnic_cleaned.isdigit()

def format_cnic(cnic: str) -> str:
    """Format CNIC as XXXXX-XXXXXXX-X"""
    cnic_cleaned = re.sub(r'[-\s]', '', cnic)
    if len(cnic_cleaned) == 13:
        return f"{cnic_cleaned[:5]}-{cnic_cleaned[5:12]}-{cnic_cleaned[12]}"
    return cnic

def add_user(name: str, cnic: str) -> dict:
    """Add a new user"""
    if not validate_cnic(cnic):
        return {"success": False, "message": "Invalid CNIC format. Must be 13 digits."}
    
    formatted_cnic = format_cnic(cnic)
    users_data = load_users_data()
    
    # Check if CNIC already exists
    for user_id, user_info in users_data.items():
        if user_info.get("cnic") == formatted_cnic:
            return {"success": False, "message": "User with this CNIC already exists."}
    
    # Create new user ID
    user_id = f"user_{len(users_data) + 1:04d}"
    
    users_data[user_id] = {
        "name": name.strip().title(),
        "cnic": formatted_cnic,
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat()
    }
    
    save_users_data(users_data)
    
    # Initialize NER data for new user
    user_ner_data = {
        "user_id": user_id,
        "name": name.strip().title(),
        "cnic": formatted_cnic,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "sessions": {},
        "summary": {
            "total_people": 0,
            "total_places": 0,
            "total_events": 0,
            "total_substances": 0,
            "unique_people": [],
            "unique_places": [],
            "unique_events": [],
            "unique_substances": []
        }
    }
    save_user_ner_data(user_ner_data, user_id)
    
    return {"success": True, "message": f"User {name} added successfully.", "user_id": user_id}

def get_user_info(user_id: str) -> dict:
    """Get user information"""
    users_data = load_users_data()
    return users_data.get(user_id, {})

def get_all_users() -> dict:
    """Get all users"""
    return load_users_data()

def update_user_last_active(user_id: str):
    """Update user's last active timestamp"""
    users_data = load_users_data()
    if user_id in users_data:
        users_data[user_id]["last_active"] = datetime.now().isoformat()
        save_users_data(users_data)

def search_user_by_cnic(cnic: str) -> str:
    """Search user by CNIC and return user_id"""
    if not validate_cnic(cnic):
        return None
    
    formatted_cnic = format_cnic(cnic)
    users_data = load_users_data()
    
    for user_id, user_info in users_data.items():
        if user_info.get("cnic") == formatted_cnic:
            return user_id
    return None

def get_user_ner_file(user_id: str = "default_user"):
    """Get the NER file path for a specific user"""
    return os.path.join(NER_DATA_DIR, f"{user_id}_ner.json")

def load_user_ner_data(user_id: str = "default_user"):
    """Load NER data for a specific user"""
    file_path = get_user_ner_file(user_id)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Add user info if available
            user_info = get_user_info(user_id)
            if user_info:
                data["name"] = user_info.get("name", "Unknown")
                data["cnic"] = user_info.get("cnic", "Unknown")
            return data
    
    # Create default structure
    user_info = get_user_info(user_id)
    return {
        "user_id": user_id,
        "name": user_info.get("name", "Default User"),
        "cnic": user_info.get("cnic", "Unknown"),
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "sessions": {},
        "summary": {
            "total_people": 0,
            "total_places": 0,
            "total_events": 0,
            "total_substances": 0,
            "unique_people": [],
            "unique_places": [],
            "unique_events": [],
            "unique_substances": []
        }
    }

def save_user_ner_data(user_data, user_id: str = "default_user"):
    """Save NER data for a specific user"""
    file_path = get_user_ner_file(user_id)
    user_data["last_updated"] = datetime.now().isoformat()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=4, ensure_ascii=False, default=str)

def update_user_ner_summary(user_data):
    """Update the summary statistics for the user"""
    total_people = set()
    total_places = set()
    total_events = set()
    total_substances = set()
    
    for session_data in user_data["sessions"].values():
        for person in session_data.get("people", []):
            total_people.add(person.get("name", ""))
        for place in session_data.get("places", []):
            total_places.add(place.get("location", ""))
        for event in session_data.get("events", []):
            total_events.add(event.get("event", ""))
        for substance in session_data.get("substances", []):
            total_substances.add(substance.get("substance", ""))
    
    user_data["summary"] = {
        "total_people": len(total_people),
        "total_places": len(total_places),
        "total_events": len(total_events),
        "total_substances": len(total_substances),
        "unique_people": list(total_people),
        "unique_places": list(total_places),
        "unique_events": list(total_events),
        "unique_substances": list(total_substances)
    }

def add_ner_to_user_session(ner_result, session_id: str, timestamp: datetime, user_id: str = "default_user"):
    """Add NER results to a specific user's session with timestamp"""
    user_data = load_user_ner_data(user_id)
    
    if session_id not in user_data["sessions"]:
        user_data["sessions"][session_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "people": [],
            "places": [],
            "events": [],
            "substances": [],
            "messages": []
        }
    
    session_data = user_data["sessions"][session_id]
    session_data["last_updated"] = datetime.now().isoformat()
    
    if hasattr(ner_result, 'dict'):
        ner_dict = ner_result.dict()
    else:
        ner_dict = ner_result
    
    timestamp_str = timestamp.isoformat()
    
    # Add entities with timestamps
    for category in ["people", "places", "events", "substances"]:
        existing_items = {json.dumps({k: v for k, v in item.items() if k != 'timestamp'}, sort_keys=True) 
                         for item in session_data[category]}
        
        for item in ner_dict.get(category, []):
            item_with_timestamp = dict(item)
            item_with_timestamp['timestamp'] = timestamp_str
            
            item_str = json.dumps({k: v for k, v in item.items() if k != 'timestamp'}, sort_keys=True, default=str)
            if item_str not in existing_items:
                session_data[category].append(item_with_timestamp)
                existing_items.add(item_str)

    update_user_ner_summary(user_data)
    save_user_ner_data(user_data, user_id)
    
    return user_data

def add_message_to_session(session_id: str, message_content: str, message_type: str, timestamp: datetime, user_id: str = "default_user"):
    """Add a message to the session conversation history"""
    user_data = load_user_ner_data(user_id)
    
    if session_id not in user_data["sessions"]:
        user_data["sessions"][session_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "people": [],
            "places": [],
            "events": [],
            "substances": [],
            "messages": []
        }
    
    # Add message to session
    user_data["sessions"][session_id]["messages"].append({
        "content": message_content,
        "type": message_type,
        "timestamp": timestamp.isoformat()
    })
    
    user_data["sessions"][session_id]["last_updated"] = datetime.now().isoformat()
    save_user_ner_data(user_data, user_id)
    
    # Update user's last active time
    update_user_last_active(user_id)
    
    return user_data

def get_session_conversation(session_id: str, user_id: str = "default_user"):
    """Get conversation messages for a specific session"""
    user_data = load_user_ner_data(user_id)
    
    if session_id in user_data["sessions"]:
        return user_data["sessions"][session_id].get("messages", [])
    return []

def get_user_ner_insights(user_id: str = "default_user"):
    """Get insights about a user's NER data"""
    user_data = load_user_ner_data(user_id)
    return {
        "user_id": user_id,
        "summary": user_data.get("summary", {}),
        "total_sessions": len(user_data.get("sessions", {})),
        "created_at": user_data.get("created_at"),
        "last_updated": user_data.get("last_updated")
    }

def get_messages_with_timestamps_from_state(thread_id: str):
    """Extract messages with timestamps from SQLite state"""
    try:
        # Get the state from checkpointer
        state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
        messages = state.values.get('messages', [])
        timestamps = state.values.get('time_stamps', [])
        
        processed_messages = []
        timestamp_index = 0
        
        for msg in messages:
            # Get corresponding timestamp
            if timestamp_index < len(timestamps):
                timestamp = timestamps[timestamp_index]
                timestamp_index += 1
            else:
                timestamp = datetime.now()
            
            if isinstance(msg, HumanMessage):
                processed_messages.append({
                    "role": "user",
                    "content": msg.content,
                    "timestamp": timestamp.isoformat()
                })
            elif isinstance(msg, AIMessage):
                processed_messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "timestamp": timestamp.isoformat()
                })
        
        return processed_messages
    except Exception as e:
        print(f"Error extracting messages with timestamps: {e}")
        return []

def ner_node(state: State):
    """Extract NER entities with structured output"""
    msg = state['messages'][-1].content
    session_id = state.get('session_id', 'default_session')
    timestamp = state.get('time_stamps', [datetime.now()])[-1]
    current_user = state.get('current_user', 'default_user')
    
    structured_model = model.with_structured_output(NamedEntity)
    msg_prompt = f"""Extract all named entities from this Message: {msg}"""
    
    ner_result = structured_model.invoke([
        SystemMessage(content=ner_prompt),
        HumanMessage(content=msg_prompt)
    ])
    
    try:
        add_ner_to_user_session(ner_result, session_id, timestamp, current_user)
        add_message_to_session(session_id, msg, "user", timestamp, current_user)
        print(f"NER data saved for user {current_user}, session {session_id}")
    except Exception as e:
        print(f"Error saving NER data: {e}")
    
    return {"ner_entities": [ner_result]}

def chat_node(state: State):
    """A therapeutic chat node"""
    response = model.invoke([SystemMessage(content=doctor_prompt)] + state["messages"])
    return {"chat_response": response.content}  #Temporary storing

def language_safety_node(state: State):
    """Apply language safety and add final response to messages"""
    chat_response = state.get('chat_response', state['messages'][-1].content if state['messages'] else "")
    current_user = state.get('current_user', 'default_user')
    
    msg_prompt = f"Message: {chat_response}"
    safe_response = model.invoke([SystemMessage(content=language_safety_prompt), HumanMessage(content=msg_prompt)])
    ai_timestamp = datetime.now()
    session_id = state.get('session_id', 'default_session')
    
    try:
        add_message_to_session(session_id, safe_response.content, "assistant", ai_timestamp, current_user)
    except Exception as e:
        print(f"Error saving AI response: {e}")
    
    return {
        "messages": [AIMessage(content=safe_response.content)],
        "time_stamps": [ai_timestamp]
    }

conn= sqlite3.connect("history.db", check_same_thread=False)
checkpointer= SqliteSaver(conn=conn)

def retrieve_all_threads():
    """Get all threads from checkpointer"""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)

def retrieve_user_threads(user_id: str = "default_user"):
    """Get threads for a specific user based on NER data"""
    user_data = load_user_ner_data(user_id)
    sessions = user_data.get("sessions", {})
    return list(sessions.keys())

def delete_session(session_id: str, user_id: str = "default_user"):
    """Delete a session from user's NER data and optionally from checkpointer"""
    try:
        # Remove from user's NER data
        user_data = load_user_ner_data(user_id)
        if session_id in user_data["sessions"]:
            del user_data["sessions"][session_id]
            
            # Update summary after deletion
            update_user_ner_summary(user_data)
            save_user_ner_data(user_data, user_id)
            
            # Try to delete from checkpointer (optional, as it might be shared across users)
            try:
                # Note: LangGraph checkpointer doesn't have a direct delete method
                # So we'll just remove it from our NER data
                pass
            except:
                pass
                
            return {"success": True, "message": f"Session {session_id} deleted successfully."}
        else:
            return {"success": False, "message": "Session not found."}
    except Exception as e:
        return {"success": False, "message": f"Error deleting session: {str(e)}"}

def check_user_has_data(user_id: str) -> bool:
    """Check if user actually has any session data"""
    try:
        user_data = load_user_ner_data(user_id)
        sessions = user_data.get("sessions", {})
        
        # Check if there are any sessions with actual messages or entities
        for session_data in sessions.values():
            messages = session_data.get("messages", [])
            people = session_data.get("people", [])
            places = session_data.get("places", [])
            events = session_data.get("events", [])
            substances = session_data.get("substances", [])
            
            # If any session has messages or entities, user has data
            if messages or people or places or events or substances:
                return True
                
        return False
    except:
        return False

graph=StateGraph(State)
graph.add_node("chat_node",chat_node)
graph.add_node("ner_node", ner_node)
graph.add_node("language_safety_node", language_safety_node)

graph.add_edge(START,"chat_node")
graph.add_edge(START,"ner_node")
graph.add_edge("chat_node","language_safety_node")
graph.add_edge("ner_node",END)
graph.add_edge("language_safety_node",END)

chatbot=graph.compile(checkpointer=checkpointer)