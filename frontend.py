import streamlit as st
from backend import (chatbot, State, retrieve_all_threads, get_user_ner_insights, 
                    load_user_ner_data, NER_DATA_DIR, get_session_conversation, 
                    get_messages_with_timestamps_from_state, add_user, get_all_users, 
                    get_user_info, search_user_by_cnic, validate_cnic, retrieve_user_threads,
                    delete_session, check_user_has_data)
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
import datetime
import json
import os
import glob
import html

def generate_thread_id():
    current_time = datetime.datetime.now()
    return f"chat_{current_time.strftime('%Y-%m-%d_%H:%M:%S')}"

def reset_chat():
    """Reset chat without generating new thread ID on user switch"""
    # Only generate new thread ID if not switching users
    if not getattr(st.session_state, 'switching_user', False):
        thread_id = generate_thread_id()
        st.session_state.thread_id = thread_id
        add_thread(st.session_state.thread_id)
    
    st.session_state.message_history = []
    
    # Reset switching flag
    if hasattr(st.session_state, 'switching_user'):
        st.session_state.switching_user = False

def switch_user_to(user_id: str):
    """Switch to a specific user without creating new thread"""
    st.session_state.switching_user = True  # Flag to prevent new thread creation
    st.session_state.current_user = user_id
    st.session_state.message_history = []
    
    # Get existing threads for this user
    user_threads = retrieve_user_threads(user_id)
    
    if user_threads:
        # Use the most recent thread
        st.session_state.thread_id = user_threads[-1]
    else:
        # Create new thread only if user has no existing threads
        st.session_state.thread_id = generate_thread_id()
        # Don't add thread here - let it be added when first message is sent
    
    # Update chat threads to show only current user's threads
    st.session_state.chat_threads = user_threads
    st.session_state.switching_user = False

def add_thread(thread_id):
    """Add thread to current user's thread list"""
    current_user = st.session_state.get('current_user', 'default_user')
    
    # Update the session state chat_threads immediately
    if thread_id not in st.session_state.chat_threads:
        st.session_state.chat_threads.append(thread_id)
        # Also update the threads from backend to ensure consistency
        user_threads = retrieve_user_threads(current_user)
        if thread_id not in user_threads:
            st.session_state.chat_threads = user_threads + [thread_id]

def update_user_threads():
    """Update the chat threads for current user"""
    current_user = st.session_state.get('current_user', 'default_user')
    user_threads = retrieve_user_threads(current_user)
    
    # Ensure current thread is included if it has messages
    current_thread = st.session_state.get('thread_id')
    if current_thread and len(st.session_state.message_history) > 0:
        if current_thread not in user_threads:
            user_threads.append(current_thread)
    
    st.session_state.chat_threads = user_threads

def load_conversation(thread_id):
    """Load conversation from the backend state with timestamps"""
    try:
        # Try to get messages with timestamps from our custom function
        processed_messages = get_messages_with_timestamps_from_state(thread_id)
        if processed_messages:
            return processed_messages
        
        # Fallback to regular state loading
        state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
        messages = state.values.get('messages', [])
        timestamps = state.values.get('time_stamps', [])
        
        processed_messages = []
        user_timestamp_index = 0
        ai_timestamp_index = 0
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                # Use user timestamps
                if user_timestamp_index < len(timestamps):
                    timestamp = timestamps[user_timestamp_index]
                    user_timestamp_index += 1
                else:
                    timestamp = datetime.datetime.now()
                    
                processed_messages.append({
                    "role": "user", 
                    "content": msg.content,
                    "timestamp": timestamp.isoformat()
                })
                
            elif isinstance(msg, AIMessage):
                # Use AI timestamps (should be separate from user timestamps)
                if ai_timestamp_index < len(timestamps):
                    timestamp = timestamps[len(timestamps)//2 + ai_timestamp_index] if len(timestamps) > 1 else timestamps[0]
                    ai_timestamp_index += 1
                else:
                    timestamp = datetime.datetime.now()
                    
                processed_messages.append({
                    "role": "assistant", 
                    "content": msg.content,
                    "timestamp": timestamp.isoformat()
                })
        
        return processed_messages
    except Exception as e:
        st.error(f"Error loading conversation: {e}")
        return []
    
def get_final_response(thread_id, user_input, current_user):
    """Get the final response from the chatbot after all nodes complete"""
    try:
        current_time = datetime.datetime.now()
        state_input: State = {
            "messages": [HumanMessage(content=user_input)],
            "session_id": thread_id,
            "time_stamps": [current_time],
            "ner_entities": [],
            "chat_response": "",
            "current_user": current_user  # Add current user to state
        }
        
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        final_result = chatbot.invoke(state_input, config=config)
    
        if 'messages' in final_result:
            messages = final_result['messages']
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    return msg.content
        
        return "I'm sorry, I couldn't process your message properly."
        
    except Exception as e:
        st.error(f"Error getting response: {str(e)}")
        return "I apologize, but I'm experiencing technical difficulties. Please try again."
    
def show_user_management():
    """Show user management interface"""
    st.subheader("👤 User Management")
    
    tab1, tab2 = st.tabs(["Switch User", "Add New User"])
    
    with tab1:
        st.markdown("### Switch to Existing User")
        
        # Method selection
        method = st.radio("Select Method:", ["By Name", "By CNIC"], horizontal=True)
        
        if method == "By Name":
            users_data = get_all_users()
            if users_data:
                # Create display options
                user_options = []
                user_mapping = {}
                
                for user_id, user_info in users_data.items():
                    display_name = f"{user_info['name']} ({user_info['cnic']})"
                    user_options.append(display_name)
                    user_mapping[display_name] = user_id
                
                selected_display = st.selectbox("Select User:", user_options)
                
                if st.button("Switch to User", use_container_width=True):
                    selected_user_id = user_mapping[selected_display]
                    switch_user_to(selected_user_id)
                    st.success(f"Switched to user: {users_data[selected_user_id]['name']}")
                    st.rerun()
            else:
                st.info("No users found. Please add a user first.")
        
        else:  # By CNIC
            cnic_input = st.text_input(
                "Enter CNIC (13 digits):", 
                placeholder="XXXXX-XXXXXXX-X or 13 digits",
                help="Enter 13-digit CNIC with or without dashes"
            )
            
            if st.button("Search by CNIC", use_container_width=True):
                if cnic_input.strip():
                    user_id = search_user_by_cnic(cnic_input.strip())
                    if user_id:
                        user_info = get_user_info(user_id)
                        switch_user_to(user_id)
                        st.success(f"Switched to user: {user_info['name']} ({user_info['cnic']})")
                        st.rerun()
                    else:
                        st.error("User with this CNIC not found.")
                else:
                    st.warning("Please enter a CNIC.")
    
    with tab2:
        st.markdown("### Add New User")
        
        with st.form("add_user_form"):
            name = st.text_input("Full Name:", placeholder="Enter full name")
            cnic = st.text_input("CNIC (13 digits):", placeholder="XXXXX-XXXXXXX-X or 13 digits")
            
            submitted = st.form_submit_button("Add User", use_container_width=True)
            
            if submitted:
                if name.strip() and cnic.strip():
                    if validate_cnic(cnic.strip()):
                        result = add_user(name.strip(), cnic.strip())
                        
                        if result["success"]:
                            st.success(result["message"])
                            # Auto-switch to new user
                            switch_user_to(result["user_id"])
                            st.rerun()
                        else:
                            st.error(result["message"])
                    else:
                        st.error("Invalid CNIC format. Must be exactly 13 digits.")
                else:
                    st.warning("Please fill in all fields.")

def display_current_user_info():
    """Display current user information"""
    current_user = st.session_state.get('current_user', 'default_user')
    user_info = get_user_info(current_user)
    
    if user_info:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Current User")
        st.sidebar.write(f"**Name:** {user_info['name']}")
        st.sidebar.write(f"**CNIC:** {user_info['cnic']}")
        
        # Compact user switch button
        if st.sidebar.button("Switch User", key="sidebar_switch", use_container_width=True):
            st.session_state.show_user_management = True
            st.rerun()
    else:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Current User")
        st.sidebar.write("**Default User**")
        if st.sidebar.button("Add/Switch User", key="sidebar_add", use_container_width=True):
            st.session_state.show_user_management = True
            st.rerun()

def get_available_users():
    """Get list of all users with actual NER data (not just empty files)"""
    if not os.path.exists(NER_DATA_DIR):
        return []
    
    ner_files = glob.glob(os.path.join(NER_DATA_DIR, "*_ner.json"))
    users_with_data = []
    
    for file_path in ner_files:
        filename = os.path.basename(file_path)
        user_id = filename.replace("_ner.json", "")
        
        # Check if user actually has data
        if check_user_has_data(user_id):
            users_with_data.append(user_id)
    
    return users_with_data

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

def display_professional_conversation(session_id, user_id):
    """Professional transcript display with better formatting using Streamlit components"""
    messages = get_session_conversation(session_id, user_id)
    
    if not messages:
        st.info("No conversation found for this session.")
        return
    
    # Header information
    st.markdown("**📋 THERAPY SESSION TRANSCRIPT**")
    st.markdown(f"**Session ID:** {session_id}")
    st.markdown(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # Create a container with better styling - Remove problematic CSS
    with st.container():
        # Create a simple text area for scrollable display
        transcript_text = ""
        transcript_text += f"THERAPY SESSION TRANSCRIPT\n"
        transcript_text += f"Session ID: {session_id}\n"
        transcript_text += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n"
        transcript_text += "=" * 60 + "\n\n"
        
        for i, msg in enumerate(messages, 1):
            timestamp = format_timestamp(msg.get('timestamp', ''))
            
            transcript_text += f"[Entry {i:02d}] {timestamp}\n"
            
            if msg['type'] == 'user':
                transcript_text += f"CLIENT:\n"
                # Indent the message content
                content_lines = msg['content'].split('\n')
                for line in content_lines:
                    transcript_text += f"    {line}\n"
                transcript_text += "\n" + "-" * 50 + "\n\n"
            else:
                transcript_text += f"THERAPIST:\n"
                # Indent the message content
                content_lines = msg['content'].split('\n')
                for line in content_lines:
                    transcript_text += f"    {line}\n"
                transcript_text += "\n" + "=" * 50 + "\n\n"
        
        transcript_text += f"\nEnd of Session Transcript\n"
        transcript_text += f"Total Exchanges: {len(messages)}"
        
        # Display in a text area with fixed height - this works reliably
        st.text_area(
            "Session Transcript",
            value=transcript_text,
            height=350,
            disabled=True,
            key=f"transcript_{session_id}",
            help="Complete therapy session transcript"
        )

def display_conversation_alternative(session_id, user_id):
    """Alternative professional view using expanders for better organization"""
    messages = get_session_conversation(session_id, user_id)
    
    if not messages:
        st.info("No conversation found for this session.")
        return
    
    # Header
    st.markdown("### 📋 Professional Session Transcript")
    st.markdown(f"**Session:** {session_id} | **Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # Use a container with limited height
    with st.container():
        # Limit number of messages to prevent overwhelming display
        max_display = 10
        display_messages = messages[-max_display:] if len(messages) > max_display else messages
        
        if len(messages) > max_display:
            st.info(f"Showing last {max_display} messages out of {len(messages)} total.")
        
        for i, msg in enumerate(display_messages, 1):
            timestamp = format_timestamp(msg.get('timestamp', ''))
            
            if msg['type'] == 'user':
                with st.expander(f"[{i:02d}] CLIENT - {timestamp}", expanded=False):
                    st.write("**Message:**")
                    st.write(msg['content'])
            else:
                with st.expander(f"[{i:02d}] THERAPIST - {timestamp}", expanded=False):
                    st.write("**Response:**")
                    st.write(msg['content'])
    
    st.markdown(f"**Total Exchanges:** {len(messages)}")

def display_ner_data(user_data, user_id):
    """Display NER data in a well-organized format with conversation sidebar"""
    st.title(f"🔍 Admin Dashboard - User: {user_id}")
    
    # User Overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sessions", len(user_data.get("sessions", {})))
    with col2:
        st.metric("Total People", user_data.get("summary", {}).get("total_people", 0))
    with col3:
        st.metric("Total Places", user_data.get("summary", {}).get("total_places", 0))
    with col4:
        st.metric("Total Events", user_data.get("summary", {}).get("total_events", 0))
    
    # User Info
    st.subheader("📊 User Information")
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.write(f"**Name:** {user_data.get('name', 'N/A')}")
        st.write(f"**CNIC:** {user_data.get('cnic', 'N/A')}")
    with info_col2:
        st.write(f"**Created:** {format_timestamp(user_data.get('created_at', 'N/A'))}")
        st.write(f"**Last Updated:** {format_timestamp(user_data.get('last_updated', 'N/A'))}")
    
    # Summary Section
    st.subheader("📈 Summary Overview")
    summary = user_data.get("summary", {})
    
    # Display unique entities in expandable sections
    with st.expander("👥 Unique People"):
        people = summary.get("unique_people", [])
        if people:
            for person in people:
                if person.strip():
                    st.write(f"• {person}")
        else:
            st.write("No people mentioned yet.")
    
    with st.expander("🏢 Unique Places"):
        places = summary.get("unique_places", [])
        if places:
            for place in places:
                if place.strip():
                    st.write(f"• {place}")
        else:
            st.write("No places mentioned yet.")
    
    with st.expander("📅 Unique Events"):
        events = summary.get("unique_events", [])
        if events:
            for event in events:
                if event.strip():
                    st.write(f"• {event}")
        else:
            st.write("No events mentioned yet.")
    
    with st.expander("💊 Substances"):
        substances = summary.get("unique_substances", [])
        if substances:
            for substance in substances:
                if substance.strip():
                    st.write(f"• {substance}")
        else:
            st.write("No substances mentioned yet.")
    
    # Sessions Details
    st.subheader("💬 Session Details")
    sessions = user_data.get("sessions", {})
    
    if sessions:
        for session_id, session_data in sessions.items():
            # Check if this session is being viewed
            is_viewing_conversation = hasattr(st.session_state, 'view_conversation_session') and st.session_state.view_conversation_session == session_id
            
            # Initialize expander state in session state if not exists
            expander_key = f"expander_{session_id}"
            if expander_key not in st.session_state:
                st.session_state[expander_key] = is_viewing_conversation
            
            # Update expander state based on conversation viewing
            if is_viewing_conversation:
                st.session_state[expander_key] = True
            
            # Create header with delete button
            header_col1, header_col2 = st.columns([5, 1])
            with header_col1:
                expander_label = f"Session: {session_id}"
            with header_col2:
                if st.button("🗑️", key=f"delete_{session_id}", help="Delete Session", 
                           use_container_width=True):
                    # Confirm deletion
                    if st.session_state.get(f"confirm_delete_{session_id}", False):
                        result = delete_session(session_id, user_id)
                        if result["success"]:
                            st.success(result["message"])
                            # Clear conversation view if deleting current session
                            if hasattr(st.session_state, 'view_conversation_session') and st.session_state.view_conversation_session == session_id:
                                delattr(st.session_state, 'view_conversation_session')
                            # Refresh data
                            st.session_state.current_user_data = load_user_ner_data(user_id)
                            st.rerun()
                        else:
                            st.error(result["message"])
                    else:
                        st.session_state[f"confirm_delete_{session_id}"] = True
                        st.warning("Click again to confirm deletion")
                        st.rerun()
            
            with st.expander(expander_label, expanded=st.session_state[expander_key]):
                # Check if expander is collapsed and conversation is being viewed
                if not st.session_state[expander_key] and is_viewing_conversation:
                    # Close conversation if expander is collapsed
                    if hasattr(st.session_state, 'view_conversation_session'):
                        delattr(st.session_state, 'view_conversation_session')
                    st.rerun()
                
                if is_viewing_conversation:
                    # Split into main content and sidebar when viewing conversation
                    main_col, sidebar_col = st.columns([2, 1])
                    
                    with sidebar_col:
                        st.markdown("### 💬 Session Transcript")
                        
                        # Close button
                        if st.button("Close Conversation", key=f"close_conv_{session_id}"):
                            delattr(st.session_state, 'view_conversation_session')
                            st.rerun()
                        
                        st.markdown("---")
                        
                        # Display conversation directly without format options
                        display_professional_conversation(session_id, user_id)
                    
                    with main_col:
                        st.markdown("### 📊 Session Information & Entities")
                        
                        # Session info in a clean layout
                        st.markdown("#### Session Details")
                        info_col1, info_col2 = st.columns(2)
                        with info_col1:
                            st.write(f"**Created:** {format_timestamp(session_data.get('created_at', 'N/A'))}")
                            st.write(f"**Messages:** {len(session_data.get('messages', []))}")
                        with info_col2:
                            st.write(f"**Last Updated:** {format_timestamp(session_data.get('last_updated', 'N/A'))}")
                        
                        st.markdown("---")
                        
                        # Display entities for this session
                        st.markdown("#### Extracted Entities")
                        display_session_entities(session_data)
                
                else:
                    # Normal layout when not viewing conversation
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Created:** {format_timestamp(session_data.get('created_at', 'N/A'))}")
                        st.write(f"**Last Updated:** {format_timestamp(session_data.get('last_updated', 'N/A'))}")
                        st.write(f"**Messages:** {len(session_data.get('messages', []))}")
                    
                    with col2:
                        if st.button(f"View Conversation", key=f"conv_{session_id}", use_container_width=True):
                            st.session_state.view_conversation_session = session_id
                            st.session_state[expander_key] = True  # Keep expander open
                            st.rerun()
                    
                    # Display entities in full width when not viewing conversation
                    st.markdown("---")
                    display_session_entities(session_data)
    
    else:
        st.write("No sessions found for this user.")

def display_session_entities(session_data):
    """Display entities for a session with compact view that expands to show details"""
    if not any([session_data.get("people", []), session_data.get("places", []), 
               session_data.get("events", []), session_data.get("substances", [])]):
        st.info("No entities extracted for this session yet.")
        return
    
    # Create tabs for different entity types
    tab1, tab2, tab3, tab4 = st.tabs(["👥 People", "🏢 Places", "📅 Events", "💊 Substances"])
    
    with tab1:
        people = session_data.get("people", [])
        if people:
            st.markdown(f"**Found {len(people)} people mentioned:**")
            for i, person in enumerate(people):
                # Create unique keys for each entity
                person_key = f"person_{hash(str(person))}"
                
                # Compact display with expand button
                col1, col2 = st.columns([4, 1])
                with col1:
                    # Show compact info: name and relationship
                    name = person.get('name', 'N/A')
                    relationship = person.get('relationship', 'Unknown')
                    emotional_charge = person.get('emotional_charge', 'neutral')
                    
                    # Color coding for emotional charge
                    color = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(emotional_charge, "⚪")
                    
                    st.markdown(f"{color} **{name}** ({relationship})")
                
                with col2:
                    if st.button("Details", key=f"btn_{person_key}", use_container_width=True):
                        # Toggle the expanded state
                        expanded_key = f"expanded_{person_key}"
                        if expanded_key not in st.session_state:
                            st.session_state[expanded_key] = False
                        st.session_state[expanded_key] = not st.session_state[expanded_key]
                
                # Show expanded details if toggled
                expanded_key = f"expanded_{person_key}"
                if st.session_state.get(expanded_key, False):
                    with st.container():
                        st.markdown("**📋 Detailed Information:**")
                        detail_col1, detail_col2 = st.columns(2)
                        
                        with detail_col1:
                            st.write(f"**Name:** {person.get('name', 'N/A')}")
                            st.write(f"**Relationship:** {person.get('relationship', 'Unknown')}")
                            st.write(f"**Emotional Charge:** {person.get('emotional_charge', 'neutral')}")
                        
                        with detail_col2:
                            if person.get('significance'):
                                st.write(f"**Significance:** {person.get('significance')}")
                            if person.get('timestamp'):
                                st.write(f"**Mentioned At:** {format_timestamp(person.get('timestamp'))}")
                        
                        # Close button for details
                        if st.button("Hide Details", key=f"hide_{person_key}"):
                            st.session_state[expanded_key] = False
                            st.rerun()
                        
                        st.markdown("---")
                
                if i < len(people) - 1:
                    st.markdown("---")
        else:
            st.info("No people mentioned in this session.")
    
    with tab2:
        places = session_data.get("places", [])
        if places:
            st.markdown(f"**Found {len(places)} places mentioned:**")
            for i, place in enumerate(places):
                place_key = f"place_{hash(str(place))}"
                
                # Compact display
                col1, col2 = st.columns([4, 1])
                with col1:
                    location = place.get('location', 'N/A')
                    context = place.get('context', 'N/A')
                    
                    st.markdown(f"🏢 **{location}**")
                    st.caption(f"Context: {context[:50]}..." if len(context) > 50 else f"Context: {context}")
                
                with col2:
                    if st.button("Details", key=f"btn_{place_key}", use_container_width=True):
                        expanded_key = f"expanded_{place_key}"
                        if expanded_key not in st.session_state:
                            st.session_state[expanded_key] = False
                        st.session_state[expanded_key] = not st.session_state[expanded_key]
                
                # Show expanded details
                expanded_key = f"expanded_{place_key}"
                if st.session_state.get(expanded_key, False):
                    with st.container():
                        st.markdown("**📋 Detailed Information:**")
                        st.write(f"**Location:** {place.get('location', 'N/A')}")
                        st.write(f"**Context:** {place.get('context', 'N/A')}")
                        if place.get('emotional_association'):
                            st.write(f"**Emotional Association:** {place.get('emotional_association')}")
                        if place.get('timestamp'):
                            st.write(f"**Mentioned At:** {format_timestamp(place.get('timestamp'))}")
                        
                        if st.button("Hide Details", key=f"hide_{place_key}"):
                            st.session_state[expanded_key] = False
                            st.rerun()
                        
                        st.markdown("---")
                
                if i < len(places) - 1:
                    st.markdown("---")
        else:
            st.info("No places mentioned in this session.")
    
    with tab3:
        events = session_data.get("events", [])
        if events:
            st.markdown(f"**Found {len(events)} events mentioned:**")
            for i, event in enumerate(events):
                event_key = f"event_{hash(str(event))}"
                
                # Compact display
                col1, col2 = st.columns([4, 1])
                with col1:
                    event_name = event.get('event', 'N/A')
                    timeframe = event.get('timeframe', 'Unknown')
                    trauma_relevance = event.get('trauma_relevance', 'low')
                    
                    # Color coding for trauma relevance
                    relevance_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(trauma_relevance, "🟢")
                    
                    st.markdown(f"{relevance_color} **{event_name}**")
                    st.caption(f"Timeframe: {timeframe} | Trauma relevance: {trauma_relevance}")
                
                with col2:
                    if st.button("Details", key=f"btn_{event_key}", use_container_width=True):
                        expanded_key = f"expanded_{event_key}"
                        if expanded_key not in st.session_state:
                            st.session_state[expanded_key] = False
                        st.session_state[expanded_key] = not st.session_state[expanded_key]
                
                # Show expanded details
                expanded_key = f"expanded_{event_key}"
                if st.session_state.get(expanded_key, False):
                    with st.container():
                        st.markdown("**📋 Detailed Information:**")
                        detail_col1, detail_col2 = st.columns(2)
                        
                        with detail_col1:
                            st.write(f"**Event:** {event.get('event', 'N/A')}")
                            st.write(f"**Timeframe:** {event.get('timeframe', 'Unknown')}")
                        
                        with detail_col2:
                            st.write(f"**Trauma Relevance:** {event.get('trauma_relevance', 'low')}")
                            if event.get('timestamp'):
                                st.write(f"**Mentioned At:** {format_timestamp(event.get('timestamp'))}")
                        
                        if event.get('description'):
                            st.write(f"**Description:** {event.get('description')}")
                        
                        if st.button("Hide Details", key=f"hide_{event_key}"):
                            st.session_state[expanded_key] = False
                            st.rerun()
                        
                        st.markdown("---")
                
                if i < len(events) - 1:
                    st.markdown("---")
        else:
            st.info("No events mentioned in this session.")
    
    with tab4:
        substances = session_data.get("substances", [])
        if substances:
            st.markdown(f"**Found {len(substances)} substances mentioned:**")
            for i, substance in enumerate(substances):
                substance_key = f"substance_{hash(str(substance))}"
                
                # Compact display
                col1, col2 = st.columns([4, 1])
                with col1:
                    substance_name = substance.get('substance', 'N/A')
                    usage_pattern = substance.get('usage_pattern', 'N/A')
                    
                    st.markdown(f"💊 **{substance_name}**")
                    st.caption(f"Usage: {usage_pattern[:50]}..." if len(usage_pattern) > 50 else f"Usage: {usage_pattern}")
                
                with col2:
                    if st.button("Details", key=f"btn_{substance_key}", use_container_width=True):
                        expanded_key = f"expanded_{substance_key}"
                        if expanded_key not in st.session_state:
                            st.session_state[expanded_key] = False
                        st.session_state[expanded_key] = not st.session_state[expanded_key]
                
                # Show expanded details
                expanded_key = f"expanded_{substance_key}"
                if st.session_state.get(expanded_key, False):
                    with st.container():
                        st.markdown("**📋 Detailed Information:**")
                        st.write(f"**Substance:** {substance.get('substance', 'N/A')}")
                        st.write(f"**Usage Pattern:** {substance.get('usage_pattern', 'N/A')}")
                        st.write(f"**Context:** {substance.get('context', 'N/A')}")
                        if substance.get('timestamp'):
                            st.write(f"**Mentioned At:** {format_timestamp(substance.get('timestamp'))}")
                        
                        if st.button("Hide Details", key=f"hide_{substance_key}"):
                            st.session_state[expanded_key] = False
                            st.rerun()
                        
                        st.markdown("---")
                
                if i < len(substances) - 1:
                    st.markdown("---")
        else:
            st.info("No substances mentioned in this session.")

def switch_to_chat():
    """Switch back to chat mode"""
    st.session_state.admin_mode = False
    # Clear conversation view
    if hasattr(st.session_state, 'view_conversation_session'):
        delattr(st.session_state, 'view_conversation_session')
    st.rerun()

def switch_to_admin():
    """Switch to admin mode"""
    st.session_state.admin_mode = True
    st.rerun()

def format_chat_timestamp(timestamp):
    """Format timestamp for chat display (WhatsApp style)"""
    try:
        dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.datetime.now()
        
        # If today, show only time
        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        # If this year, show day and month
        elif dt.year == now.year:
            return dt.strftime("%b %d, %H:%M")
        # If different year, show full date
        else:
            return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return datetime.datetime.now().strftime("%H:%M")

# Initialize session state
if "message_history" not in st.session_state:
    st.session_state.message_history = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = generate_thread_id()
if "chat_threads" not in st.session_state:
    # Initialize with current user's threads
    current_user = st.session_state.get('current_user', 'default_user')
    st.session_state.chat_threads = retrieve_user_threads(current_user)
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "selected_user" not in st.session_state:
    st.session_state.selected_user = "default_user"
if "current_user" not in st.session_state:
    st.session_state.current_user = "default_user"
if "show_user_management" not in st.session_state:
    st.session_state.show_user_management = False

add_thread(st.session_state.thread_id)


st.set_page_config(
    page_title="Dual Brain Psychology Chatbot",
    page_icon="🧠",
    layout="wide"
)

# Show user management if requested
if st.session_state.show_user_management and not st.session_state.admin_mode:
    show_user_management()
    
    if st.button("← Back to Chat", use_container_width=True):
        st.session_state.show_user_management = False
        st.rerun()

# Admin Mode
elif st.session_state.admin_mode:
    # Admin header with switch button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🛠️ Admin Dashboard")
    with col2:
        if st.button("Switch to Chat", use_container_width=True):
            switch_to_chat()
    
    # User selection - Updated for new user system
    st.subheader("Select User")
    
    # Get users with NER data
    available_users = get_available_users()
    all_users = get_all_users()
    
    if available_users or all_users:
        # Create combined user list
        user_options = []
        user_mapping = {}
        
        # Add users with NER data
        for user_id in available_users:
            if user_id in all_users:
                user_info = all_users[user_id]
                display_name = f"{user_info['name']} ({user_info['cnic']}) - Has Data"
                user_options.append(display_name)
                user_mapping[display_name] = user_id
            else:
                display_name = f"{user_id} - Has Data (Legacy)"
                user_options.append(display_name)
                user_mapping[display_name] = user_id
        
        # Add users without NER data
        for user_id, user_info in all_users.items():
            if user_id not in available_users:
                display_name = f"{user_info['name']} ({user_info['cnic']}) - No Data"
                user_options.append(display_name)
                user_mapping[display_name] = user_id
        
        if user_options:
            # Try to maintain previous selection
            default_index = 0
            if st.session_state.selected_user in user_mapping.values():
                for i, (display, user_id) in enumerate(user_mapping.items()):
                    if user_id == st.session_state.selected_user:
                        default_index = i
                        break
            
            selected_display = st.selectbox(
                "Choose a user to view data:",
                user_options,
                index=default_index
            )
            selected_user = user_mapping[selected_display]
            st.session_state.selected_user = selected_user
            
            # Load and display user data
            if st.button("Load User Data", use_container_width=True):
                user_data = load_user_ner_data(selected_user)
                st.session_state.current_user_data = user_data
            
            # Display data if loaded
            if "current_user_data" in st.session_state:
                display_ner_data(st.session_state.current_user_data, selected_user)
        else:
            st.warning("No users found.")
    else:
        st.warning("No users found. Users will appear here after they are added and start chatting.")

# Chat Mode
else:
    st.title("🧠 Dual Brain Psychology Therapist")

    # Main navigation
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Admin Dashboard", use_container_width=True):
            switch_to_admin()

    # Sidebar with user info
    st.sidebar.title("Chat Sessions")
    st.sidebar.button("New Chat", on_click=reset_chat, use_container_width=True)
    
    # Display current user info
    display_current_user_info()
    
    # Add NER Insights button
    if st.sidebar.button("View Profile Insights", use_container_width=True):
        current_user = st.session_state.get('current_user', 'default_user')
        insights = get_user_ner_insights(current_user)
        st.sidebar.write("**Profile Summary:**")
        st.sidebar.json(insights["summary"])
        st.sidebar.write(f"**Total Sessions:** {insights['total_sessions']}")
    
    st.sidebar.header("My Conversations")

    # Get current user's threads and update session state
    current_user = st.session_state.get('current_user', 'default_user')
    user_threads = retrieve_user_threads(current_user)
    
    # Update session state with current user's threads
    st.session_state.chat_threads = user_threads

    for thread_id in user_threads[::-1]:  # Show most recent first
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(str(thread_id), key=f"thread_{thread_id}"):
                # Load conversation with proper timestamps
                processed_messages = load_conversation(thread_id)
                st.session_state.thread_id = thread_id
                st.session_state.message_history = processed_messages
        
        with col2:
            if st.button("🗑️", key=f"del_{thread_id}", help="Delete", use_container_width=True):
                result = delete_session(thread_id, current_user)
                if result["success"]:
                    st.success("Session deleted")
                    # If we deleted the current thread, reset to new thread
                    if st.session_state.thread_id == thread_id:
                        st.session_state.thread_id = generate_thread_id()
                        st.session_state.message_history = []
                    # Update threads immediately
                    update_user_threads()
                    st.rerun()

    if not st.session_state.message_history:
        # Display current user name if available
        current_user = st.session_state.get('current_user', 'default_user')
        user_info = get_user_info(current_user)
        
        if user_info:
            st.markdown(f"**Welcome, {user_info['name']}!**")
        
        st.markdown("""
        Welcome to your therapeutic space. I'm here to listen and support you through your journey. Feel free to start sharing whenever you're ready.
        """)

    # Display chat messages with timestamps
    for message in st.session_state.message_history:
        # Display timestamp label (WhatsApp style)
        timestamp_display = format_chat_timestamp(message.get("timestamp", datetime.datetime.now().isoformat()))
        st.markdown(f"<div style='text-align: center; margin: 10px 0;'><small style='background-color: #f0f0f0; padding: 2px 8px; border-radius: 10px; color: #666;'>📅 {timestamp_display}</small></div>", unsafe_allow_html=True)
        
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Type Here...")
    if user_input:
        # Validation
        if len(user_input.strip()) == 0:
            st.warning("Please enter a message before sending.")
        elif len(user_input) > 2000:
            st.warning("Your message is too long. Please keep it under 2000 characters.")
        else:
            current_time = datetime.datetime.now()
            timestamp_str = current_time.isoformat()
            current_user = st.session_state.get('current_user', 'default_user')
            
            # Check if this is the first message for this thread
            is_first_message = len(st.session_state.message_history) == 0
            
            # Add thread to chat_threads immediately when first message is sent
            if is_first_message:
                add_thread(st.session_state.thread_id)
                # Update threads immediately for first message
                update_user_threads()
            
            # Add user message with timestamp
            st.session_state.message_history.append({
                "role": "user", 
                "content": user_input,
                "timestamp": timestamp_str
            })
            
            # Display timestamp and user message
            timestamp_display = format_chat_timestamp(timestamp_str)
            st.markdown(f"<div style='text-align: center; margin: 10px 0;'><small style='background-color: #f0f0f0; padding: 2px 8px; border-radius: 10px; color: #666;'>📅 {timestamp_display}</small></div>", unsafe_allow_html=True)
            
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Processing your message with care..."):
                    ai_response = get_final_response(st.session_state.thread_id, user_input, current_user)
                st.markdown(ai_response)
            
            # Add AI response with its own timestamp
            ai_timestamp = datetime.datetime.now()
            st.session_state.message_history.append({
                "role": "assistant", 
                "content": ai_response,
                "timestamp": ai_timestamp.isoformat()
            })
            
            # Force immediate rerun for first message to show session in sidebar
            if is_first_message:
                st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        <p>🔒 This is a supportive AI companion, Made By Fayaz Noor ---- Wow Very Dangerous.</p>
    </div>
    """, unsafe_allow_html=True)