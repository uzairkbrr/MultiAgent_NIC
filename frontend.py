import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Multi-Agentic Wellness Assistant",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

import datetime
from datetime import date
import time
import os
from backend import (
    chatbot, State, authenticate_user, create_user_profile, 
    load_user_wellness_data, get_user_info, update_daily_inputs,
    get_user_context_for_agent, route_message_to_agent, WELLNESS_DATA_DIR,
    add_message_to_session, get_session_conversation, load_users_data,
    retrieve_user_threads, delete_session, check_user_has_data,
    get_all_users, NER_DATA_DIR, get_messages_with_timestamps_from_state,
    get_user_ner_insights, get_detailed_user_ner_insights, search_user_by_cnic, 
    validate_cnic, add_user, load_user_ner_data, get_user_wellness_file, 
    load_user_wellness_data, save_user_wellness_data, update_user_profile,
    get_agent_specific_insights, get_comprehensive_user_insights, 
    get_user_routine_plans, generate_routine_plan, update_routine_progress,
    calculate_progress_metrics, 
    # New hybrid functions
    add_user_hybrid, get_user_hybrid, get_all_users_hybrid,
    create_user_profile_hybrid, get_user_profile_hybrid,
    log_daily_health_data_hybrid, get_user_health_history_hybrid,
    create_session_hybrid, get_user_sessions_hybrid,
    create_routine_plan_hybrid, get_user_routine_plans_hybrid, log_progress_hybrid,
    SQL_AVAILABLE, USE_SQL_FOR_STRUCTURED
)
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

# Page already configured at the top



# Custom CSS
st.markdown("""
<style>
/* Basic app styling */
.stApp {
    background: #f8f9fa;
}
</style>
""", unsafe_allow_html=True)

# Initialize theme state
if "dark_theme" not in st.session_state:
    st.session_state.dark_theme = True

# Dynamic CSS based on theme
if st.session_state.dark_theme:
    # Dark theme CSS
    css_theme = """
        /* Dark Theme */
        .stApp, body {
            background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%) !important;
            color: #f7fafc !important;
        }
        
        /* Dark theme text elements */
        .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: #f7fafc !important;
            background: transparent !important;
        }
        
        /* Dark sidebar */
        .css-1d391kg {
            background: linear-gradient(180deg, #374151 0%, #2d3748 100%) !important;
        }
        
        .css-1d391kg .stMarkdown, .css-1d391kg .stMarkdown p, .css-1d391kg .stMarkdown h1,
        .css-1d391kg .stMarkdown h2, .css-1d391kg .stMarkdown h3, .css-1d391kg .stMarkdown h4 {
            color: #f7fafc !important;
        }
        
        /* Dark input fields */
        .stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea,
        .stTimeInput input {
            background: #374151 !important;
            color: #f7fafc !important;
            border: 2px solid #4a5568 !important;
        }
        
        /* Dark sidebar buttons */
        .css-1d391kg .stButton > button {
            background: linear-gradient(135deg, #374151 0%, #4a5568 100%) !important;
            color: #f7fafc !important;
            border: 1px solid #4a5568 !important;
        }
        
        /* Dark profile cards */
        .profile-card {
            background: linear-gradient(135deg, #374151 0%, #4a5568 100%) !important;
            color: #f7fafc !important;
            border: 1px solid #4a5568 !important;
        }
        
        .profile-card h2, .profile-card h4 {
            color: #f7fafc !important;
        }
        
        /* Dark login form */
        .login-form {
            background: linear-gradient(135deg, #374151 0%, #4a5568 100%) !important;
            color: #f7fafc !important;
            border: 1px solid #4a5568 !important;
        }
        
        .login-form h3 {
            color: #f7fafc !important;
        }
    """
else:
    # Light theme CSS  
    css_theme = """
        /* Light Theme */
        .stApp, body {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%) !important;
            color: #1a202c !important;
        }
        
        /* Light theme text elements */
        .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: #1a202c !important;
            background: transparent !important;
        }
        
        /* Light sidebar */
        .css-1d391kg {
            background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important;
        }
        
        .css-1d391kg .stMarkdown, .css-1d391kg .stMarkdown p, .css-1d391kg .stMarkdown h1,
        .css-1d391kg .stMarkdown h2, .css-1d391kg .stMarkdown h3, .css-1d391kg .stMarkdown h4 {
            color: #1a202c !important;
        }
        
        /* Light input fields */
        .stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea,
        .stTimeInput input {
            background: #ffffff !important;
            color: #1a202c !important;
            border: 2px solid #e2e8f0 !important;
        }
        
        /* Light sidebar buttons */
        .css-1d391kg .stButton > button {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
            color: #1a202c !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        /* Light profile cards */
        .profile-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
            color: #1a202c !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        .profile-card h2, .profile-card h4 {
            color: #2d3748 !important;
        }
        
        /* Light login form */
        .login-form {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
            color: #1a202c !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        .login-form h3 {
            color: #2d3748 !important;
        }
    """

# Apply theme-based CSS
if st.session_state.dark_theme:
    # Dark theme
    st.markdown("""
    <style>
        /* Dark Theme */
        .stApp, body {
            background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%) !important;
            color: #f7fafc !important;
        }
        
        /* Dark theme text elements */
        .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: #f7fafc !important;
        }
        
        /* Dark sidebar */
        .css-1d391kg {
            background: linear-gradient(180deg, #374151 0%, #2d3748 100%) !important;
        }
        
        .css-1d391kg .stMarkdown, .css-1d391kg .stMarkdown p, .css-1d391kg .stMarkdown h1,
        .css-1d391kg .stMarkdown h2, .css-1d391kg .stMarkdown h3, .css-1d391kg .stMarkdown h4 {
            color: #f7fafc !important;
        }
        
        /* Dark input fields */
        .stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea,
        .stTimeInput input {
            background: #374151 !important;
            color: #f7fafc !important;
            border: 2px solid #4a5568 !important;
        }
        
        /* Dark sidebar buttons */
        .css-1d391kg .stButton > button {
            background: #4a5568 !important;
            color: #f7fafc !important;
            border: 1px solid #718096 !important;
        }
        
        /* Dark profile cards */
        .profile-card {
            background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%) !important;
            color: #f7fafc !important;
            border: 1px solid #4a5568 !important;
        }
        
        .profile-card h2, .profile-card h4 {
            color: #f7fafc !important;
        }
        
        /* Dark login form */
        .login-form {
            background: linear-gradient(135deg, #2d3748 0%, #374151 100%) !important;
            color: #f7fafc !important;
            border: 1px solid #4a5568 !important;
        }
        
        .login-form h3 {
            color: #f7fafc !important;
        }
        
        /* Remove column white bars */
        div[data-testid="column"] {
            background: transparent !important;
        }
        
        /* Theme toggle button */
        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 999;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 10px 20px !important;
            font-weight: bold !important;
            cursor: pointer !important;
        }
        
        /* Hide Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
else:
    # Light theme
    st.markdown("""
    <style>
        /* Light Theme */
        .stApp, body {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%) !important;
            color: #1a202c !important;
        }
        
        /* Light theme text elements */
        .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: #1a202c !important;
        }
        
        /* Light sidebar */
        .css-1d391kg {
            background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%) !important;
        }
        
        .css-1d391kg .stMarkdown, .css-1d391kg .stMarkdown p, .css-1d391kg .stMarkdown h1,
        .css-1d391kg .stMarkdown h2, .css-1d391kg .stMarkdown h3, .css-1d391kg .stMarkdown h4 {
            color: #2d3748 !important;
        }
        
        /* Light input fields */
        .stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea,
        .stTimeInput input {
            background: #ffffff !important;
            color: #2d3748 !important;
            border: 2px solid #e2e8f0 !important;
        }
        
        /* Light sidebar buttons */
        .css-1d391kg .stButton > button {
            background: #ffffff !important;
            color: #2d3748 !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        /* Light profile cards */
        .profile-card {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
            color: #1a202c !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        .profile-card h2, .profile-card h4 {
            color: #2d3748 !important;
        }
        
        /* Light login form */
        .login-form {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
            color: #1a202c !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        .login-form h3 {
            color: #2d3748 !important;
        }
        
        /* Remove column white bars */
        div[data-testid="column"] {
            background: transparent !important;
        }
        
        /* Theme toggle button */
        .theme-toggle {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 999;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 10px 20px !important;
            font-weight: bold !important;
            cursor: pointer !important;
        }
        
        /* Hide Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Add common wellness styling for both themes
st.markdown("""
<style>
    /* Wellness header */
    .wellness-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        padding: 20px;
        border-radius: 15px;
        color: white !important;
        text-align: center;
        margin-bottom: 20px;
    }
    
    .wellness-header h1, .wellness-header p {
        color: white !important;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid rgba(102, 126, 234, 0.2);
        margin: 5px;
    }
    
    .metric-card h4 {
        font-size: 0.9rem !important;
        margin-bottom: 8px !important;
        opacity: 0.8;
    }
    
    .metric-card h2 {
        font-size: 1.8rem !important;
        margin: 0 !important;
        font-weight: 700 !important;
        color: #667eea !important;
    }
    
    /* Agent cards - Modern clean design */
    .agent-card {
        padding: 24px;
        border-radius: 12px;
        margin: 8px 0;
        text-align: left;
        cursor: pointer;
        transition: all 0.3s ease;
        border: none;
        background: transparent;
        border-left: 4px solid;
    }
    
    .agent-card h3 {
        font-size: 1.3rem !important;
        margin-bottom: 8px !important;
        font-weight: 600 !important;
    }
    
    .agent-card p, .agent-card strong {
        font-size: 0.95rem !important;
        margin-bottom: 6px !important;
    }
    
    .agent-card ul {
        margin-top: 12px !important;
        padding-left: 16px !important;
    }
    
    .agent-card li {
        font-size: 0.9rem !important;
        margin-bottom: 4px !important;
        list-style-type: none !important;
    }
    
    .mental-health-card { 
        border-left-color: #4CAF50;
        background: linear-gradient(135deg, rgba(76, 175, 80, 0.05) 0%, rgba(76, 175, 80, 0.02) 100%);
    }
    .mental-health-card:hover {
        background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(76, 175, 80, 0.05) 100%);
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.15);
    }
    
    .diet-card { 
        border-left-color: #FF9800;
        background: linear-gradient(135deg, rgba(255, 152, 0, 0.05) 0%, rgba(255, 152, 0, 0.02) 100%);
    }
    .diet-card:hover {
        background: linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, rgba(255, 152, 0, 0.05) 100%);
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(255, 152, 0, 0.15);
    }
    
    .exercise-card { 
        border-left-color: #2196F3;
        background: linear-gradient(135deg, rgba(33, 150, 243, 0.05) 0%, rgba(33, 150, 243, 0.02) 100%);
    }
    .exercise-card:hover {
        background: linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 150, 243, 0.05) 100%);
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
    }
    
    /* Menu toggle button styling */
    div[data-testid="stButton"][data-key="sidebar_toggle"] button {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%) !important;
        color: white !important;
        border: none !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stButton"][data-key="sidebar_toggle"] button:hover {
        background: linear-gradient(135deg, #45a049 0%, #3d8b40 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4) !important;
    }
    
    /* Make sure the menu button is always visible */
    div[data-testid="stButton"][data-key="sidebar_toggle"] {
        position: sticky !important;
        top: 10px !important;
        z-index: 999 !important;
    }
    
    /* Sidebar expansion help */
    .sidebar-help-alert {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 16px !important;
        margin: 16px 0 !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3) !important;
    }
    
    /* Quick navigation buttons styling */
    div[data-testid="stButton"][key^="quick_"] button {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%) !important;
        color: white !important;
        border: none !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stButton"][key^="quick_"] button:hover {
        background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.4) !important;
    }
</style>

<script>
// JavaScript to help with sidebar expansion
function expandSidebar() {
    // Multiple attempts to find and click the sidebar toggle
    const selectors = [
        '[data-testid="collapsedControl"]',
        '.css-1rs6os.edgvbvh3',
        '[aria-label="Show sidebar"]',
        '.css-1kyxreq.etr89bj2'
    ];
    
    for (let selector of selectors) {
        const toggle = document.querySelector(selector);
        if (toggle) {
            toggle.click();
            console.log('Sidebar expanded using selector:', selector);
            return true;
        }
    }
    
    // Try to find by text content
    const buttons = document.querySelectorAll('button');
    for (let button of buttons) {
        if (button.textContent.includes('>') || button.getAttribute('aria-label') === 'Show sidebar') {
            button.click();
            console.log('Sidebar expanded using button text search');
            return true;
        }
    }
    
    console.log('Could not find sidebar toggle');
    return false;
}

// Enhanced menu button functionality
function setupMenuButton() {
    const menuButton = document.querySelector('[data-testid="stButton"][data-key="sidebar_toggle"] button');
    if (menuButton) {
        menuButton.addEventListener('click', function() {
            console.log('Menu button clicked');
            setTimeout(() => {
                const expanded = expandSidebar();
                if (!expanded) {
                    // If we can't expand the sidebar, at least scroll to top
                    window.scrollTo(0, 0);
                    // And try to make the sidebar more visible if it exists
                    const sidebar = document.querySelector('[data-testid="stSidebar"]');
                    if (sidebar) {
                        sidebar.style.display = 'block';
                        sidebar.style.visibility = 'visible';
                    }
                }
            }, 100);
        });
    }
}

// Run when page loads
document.addEventListener('DOMContentLoaded', setupMenuButton);

// Also run when Streamlit updates the page
new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.addedNodes.length > 0) {
            setupMenuButton();
        }
    });
}).observe(document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

def show_theme_toggle():
    """Show theme toggle button"""
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        theme_text = "🌙 Dark" if not st.session_state.dark_theme else "☀️ Light"
        if st.button(theme_text, key="theme_toggle", help="Toggle theme"):
            st.session_state.dark_theme = not st.session_state.dark_theme
            st.rerun()

def initialize_session_state():
    """Initialize all session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = None
    if "current_agent" not in st.session_state:
        st.session_state.current_agent = "MENTAL_HEALTH"
    if "message_history" not in st.session_state:
        st.session_state.message_history = []
    if "thread_id" not in st.session_state:
        current_agent = st.session_state.get('current_agent', 'MENTAL_HEALTH')
        st.session_state.thread_id = generate_agent_thread_id(current_agent)
    if "show_profile_analysis" not in st.session_state:
        st.session_state.show_profile_analysis = False
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    if "show_daily_update" not in st.session_state:
        st.session_state.show_daily_update = False
    if "show_edit_profile" not in st.session_state:
        st.session_state.show_edit_profile = False
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
    if "show_dashboard" not in st.session_state:
        st.session_state.show_dashboard = False
    if "sidebar_expanded" not in st.session_state:
        st.session_state.sidebar_expanded = True

def generate_thread_id():
    """Generate unique thread ID"""
    current_time = datetime.datetime.now()
    return f"wellness_{current_time.strftime('%Y%m%d_%H%M%S')}"

def new_chat():
    """Create a new chat session"""
    st.session_state.message_history = []
    current_agent = st.session_state.get('current_agent', 'MENTAL_HEALTH')
    st.session_state.thread_id = generate_agent_thread_id(current_agent)

def get_agent_specific_threads(user_id: str, agent: str):
    """Get threads specific to an agent"""
    all_threads = retrieve_user_threads(user_id)
    agent_threads = []
    
    for thread_id in all_threads:
        belongs_to_agent = False
        
        # Method 1: Check new agent-specific thread naming pattern (MOST RELIABLE)
        agent_name = agent.lower()
        expected_prefix = f"wellness_{agent_name}_"
        if thread_id.startswith(expected_prefix):
            belongs_to_agent = True
        
        # Method 2: For other agents, check if thread name suggests it belongs to them
        elif agent == "DIET" and "diet" in thread_id.lower():
            belongs_to_agent = True
        elif agent == "EXERCISE" and "exercise" in thread_id.lower():
            belongs_to_agent = True
        
        # Method 3: Check conversation state for current_agent (BUT be careful with GENERAL)
        elif not belongs_to_agent:
            try:
                state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
                if state.values and 'current_agent' in state.values:
                    state_agent = state.values['current_agent']
                    
                    # For Mental Health: Only accept if state is MENTAL_HEALTH AND thread doesn't belong to other agents
                    if agent == "MENTAL_HEALTH" and state_agent == "MENTAL_HEALTH":
                        # Make sure this thread doesn't have diet/exercise in the name
                        if not ("diet" in thread_id.lower() or "exercise" in thread_id.lower()):
                            belongs_to_agent = True
                    
                    # For Diet/Exercise: Accept if state matches AND thread name matches
                    elif agent == "DIET" and state_agent == "DIET":
                        belongs_to_agent = True
                    elif agent == "EXERCISE" and state_agent == "EXERCISE":
                        belongs_to_agent = True
            except:
                pass
        
        # Method 4: For old threads without agent info, only show in MENTAL_HEALTH
        if not belongs_to_agent and agent == "MENTAL_HEALTH":
            # Only include old format threads that are truly unassigned
            if (thread_id.startswith("chat_") or 
                (thread_id.startswith("wellness_") and len(thread_id.split("_")) == 2)):
                
                # Make sure it doesn't belong to other agents by name
                if not ("diet" in thread_id.lower() or "exercise" in thread_id.lower()):
                    belongs_to_agent = True
        
        if belongs_to_agent:
            agent_threads.append(thread_id)
    
    return agent_threads

def generate_agent_thread_id(agent: str):
    """Generate agent-specific thread ID"""
    current_time = datetime.datetime.now()
    return f"wellness_{agent.lower()}_{current_time.strftime('%Y%m%d_%H%M%S')}"

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
            if hasattr(msg, 'content') and msg.content.strip():
                timestamp_str = "Unknown"
                if isinstance(msg, HumanMessage):
                    if user_timestamp_index < len(timestamps):
                        timestamp_str = timestamps[user_timestamp_index].strftime("%H:%M")
                        user_timestamp_index += 1
                    processed_messages.append({
                        "role": "user",
                        "content": msg.content,
                        "timestamp": timestamp_str
                    })
                elif isinstance(msg, AIMessage):
                    if ai_timestamp_index < len(timestamps):
                        timestamp_str = timestamps[ai_timestamp_index].strftime("%H:%M")
                        ai_timestamp_index += 1
                    processed_messages.append({
                        "role": "assistant", 
                        "content": msg.content,
                        "timestamp": timestamp_str
                    })
        
        return processed_messages
    except Exception as e:
        st.error(f"Error loading conversation: {e}")
        return []

def show_login_page():
    """Display login/register page"""
    # Theme toggle
    show_theme_toggle()
    
    st.markdown('<div class="wellness-header"><h1>🌟 Multi-Agentic Wellness Assistant</h1><p>Your Personal Health & Wellness Companion</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.session_state.show_register:
            show_register_form()
        else:
            show_login_form()

def show_login_form():
    """Display login form"""
    st.markdown('<div class="login-form">', unsafe_allow_html=True)
    st.markdown("### 🔐 Login to Your Account")
    
    with st.form("login_form"):
        email = st.text_input("Email Address", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            login_clicked = st.form_submit_button("Login", use_container_width=True)
        with col2:
            register_clicked = st.form_submit_button("Register", use_container_width=True)
    
    if login_clicked:
        if email and password:
            auth_result = authenticate_user(email, password)
            if auth_result["success"]:
                # Get full user profile using user_id
                user_id = auth_result["user_id"]
                user_info = get_user_info(user_id)
                user_info["user_id"] = user_id  # Add user_id to the profile
                
                st.session_state.authenticated = True
                st.session_state.user_profile = user_info
                st.success("Login successful! Welcome back!")
                st.rerun()
            else:
                st.error(auth_result["message"])
        else:
            st.error("Please enter both email and password")
    
    if register_clicked:
        st.session_state.show_register = True
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Demo section
    st.markdown("---")
    st.markdown("### 🎯 What You'll Get:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🧠 Mental Health Agent**
        - Daily mood tracking
        - Stress management techniques
        - Emotional support & coping strategies
        - Mindfulness & motivation
        """)
    
    with col2:
        st.markdown("""
        **🥗 Diet & Nutrition Agent**
        - Personalized meal plans
        - Pakistani food recommendations
        - Calorie & macro tracking
        - Healthy local alternatives
        """)
    
    with col3:
        st.markdown("""
        **💪 Exercise & Fitness Agent**
        - Custom workout routines
        - Home-based exercises
        - Progress tracking
        - Fitness motivation
        """)

def show_register_form():
    """Display registration form"""
    st.markdown('<div class="login-form">', unsafe_allow_html=True)
    st.markdown("### 📝 Create Your Wellness Profile")
    
    with st.form("register_form"):
        st.markdown("**Basic Information**")
        full_name = st.text_input("Full Name", placeholder="Enter your full name")
        email = st.text_input("Email Address", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=13, max_value=100, value=25)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        with col2:
            height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0)
            current_weight = st.number_input("Current Weight (kg)", min_value=30.0, max_value=200.0, value=70.0)
        
        st.markdown("**Health & Lifestyle**")
        target_weight = st.number_input("Target Weight (kg)", min_value=30.0, max_value=200.0, value=current_weight)
        activity_level = st.selectbox("Activity Level", 
                                    ["sedentary", "lightly_active", "moderately_active", "very_active"])
        diet_type = st.selectbox("Diet Preference", 
                               ["vegetarian", "non_vegetarian", "keto", "low_carb", "balanced", "other"])
        
        # Common health issues (multi-select)
        health_issues = st.multiselect("Common Health Concerns (Select all that apply)",
                                     ["Stress", "Anxiety", "Fatigue", "Sleep issues", "Back pain", 
                                      "High blood pressure", "Diabetes", "Weight management", "Other"])
        
        col1, col2 = st.columns(2)
        with col1:
            register_clicked = st.form_submit_button("Create Account", use_container_width=True)
        with col2:
            back_clicked = st.form_submit_button("Back to Login", use_container_width=True)
    
    if register_clicked:
        if password != confirm_password:
            st.error("Passwords do not match!")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters long!")
        elif not all([full_name, email, password]):
            st.error("Please fill in all required fields!")
        else:
            # Create user profile
            profile_data = {
                "full_name": full_name,
                "age": age,
                "gender": gender,
                "email": email,
                "password": password,
                "height": height,
                "current_weight": current_weight,
                "target_weight": target_weight,
                "activity_level": activity_level,
                "diet_type": diet_type,
                "common_issues": health_issues
            }
            
            result = create_user_profile(profile_data)
            if result["success"]:
                st.success("Account created successfully! Please login with your credentials.")
                st.session_state.show_register = False
                st.rerun()
            else:
                st.error(result["message"])
    
    if back_clicked:
        st.session_state.show_register = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_daily_update_page():
    """Show daily update page"""
    user_profile = st.session_state.user_profile
    
    st.markdown('<div class="wellness-header"><h1>📝 Update Today\'s Information</h1><p>Keep your wellness data current</p></div>', unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Dashboard", use_container_width=True):
        st.session_state.show_daily_update = False
        st.rerun()
    
    st.markdown("---")
    
    with st.form("daily_update"):
        st.markdown("### Update Your Daily Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            stress_level = st.slider("Stress Level (1-5)", 1, 5, 
                                    user_profile.get("daily_stress_level", 3))
            wake_up_time = st.time_input("Wake-up Time", 
                                       value=datetime.time(7, 0))
        
        with col2:
            sleep_time = st.time_input("Sleep Time", 
                                     value=datetime.time(23, 0))
            current_weight = st.number_input("Current Weight (kg)", 
                                           min_value=30.0, max_value=200.0, 
                                           value=float(user_profile.get("current_weight", 70.0)))
        
        # Enhanced health data logging section
        st.markdown("### 🏥 Health Data (Optional)")
        
        col3, col4 = st.columns(2)
        with col3:
            blood_pressure_systolic = st.number_input("Blood Pressure (Systolic)", 
                                                    min_value=80, max_value=200, value=120, step=1)
            blood_pressure_diastolic = st.number_input("Blood Pressure (Diastolic)", 
                                                     min_value=40, max_value=120, value=80, step=1)
            blood_sugar = st.number_input("Blood Sugar (mg/dL)", 
                                        min_value=50, max_value=400, value=100, step=1)
        
        with col4:
            sleep_hours = st.number_input("Sleep Hours", 
                                        min_value=0.0, max_value=24.0, value=8.0, step=0.5)
            mood_rating = st.slider("Mood Rating (1-10)", 
                                  min_value=1, max_value=10, value=7)
            health_notes = st.text_area("Health Notes", 
                                      placeholder="Any health observations or notes for today...")
        
        if st.form_submit_button("Update Daily Info", use_container_width=True):
            daily_data = {
                "daily_stress_level": stress_level,
                "wake_up_time": wake_up_time.strftime("%H:%M"),
                "sleep_time": sleep_time.strftime("%H:%M"),
                "current_weight": current_weight
            }
            
            # Prepare health data for hybrid storage
            health_data = {
                "weight": current_weight,
                "blood_pressure_systolic": blood_pressure_systolic,
                "blood_pressure_diastolic": blood_pressure_diastolic,
                "blood_sugar": blood_sugar,
                "stress_level": stress_level,
                "sleep_hours": sleep_hours,
                "mood_rating": mood_rating,
                "notes": health_notes
            }
            
            # Update daily wellness info (JSON)
            result = update_daily_inputs(user_profile["user_id"], daily_data)
            
            # Log health data (Hybrid SQL/JSON)
            health_result = log_daily_health_data_hybrid(user_profile["user_id"], health_data)
            
            if result["success"] and health_result["success"]:
                st.success("Daily information and health data updated successfully!")
                st.info(f"💾 Health data saved using: {'SQL Database' if SQL_AVAILABLE else 'JSON Storage'}")
                # Update session state
                st.session_state.user_profile.update(daily_data)
                st.balloons()
                # Auto redirect back to dashboard after 2 seconds
                import time
                time.sleep(2)
                st.session_state.show_daily_update = False
                st.rerun()
            else:
                if not result["success"]:
                    st.error(f"Daily info update failed: {result['message']}")
                if not health_result["success"]:
                    st.error(f"Health data logging failed: {health_result['message']}")

def show_edit_profile_page():
    """Show edit profile page"""
    user_profile = st.session_state.user_profile
    
    st.markdown('<div class="wellness-header"><h1>✏️ Edit Your Profile</h1><p>Update your personal wellness information</p></div>', unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Dashboard", use_container_width=True):
        st.session_state.show_edit_profile = False
        st.rerun()
    
    st.markdown("---")
    
    with st.form("edit_profile"):
        st.markdown("### Personal Information")
        
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", value=user_profile.get("full_name", ""))
            email = st.text_input("Email", value=user_profile.get("email", ""))
            age = st.number_input("Age", min_value=10, max_value=120, 
                                value=int(user_profile.get("age", 25)))
            
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], 
                                index=["Male", "Female", "Other"].index(user_profile.get("gender", "Male")))
            height = st.number_input("Height (cm)", min_value=100, max_value=250, 
                                   value=int(user_profile.get("height", 170)))
            target_weight = st.number_input("Target Weight (kg)", min_value=30.0, max_value=200.0, 
                                          value=float(user_profile.get("target_weight", 70.0)))
        
        st.markdown("### Wellness Preferences")
        
        col3, col4 = st.columns(2)
        with col3:
            activity_level = st.selectbox("Activity Level", 
                                        ["sedentary", "lightly_active", "moderately_active", "very_active", "extremely_active"],
                                        index=["sedentary", "lightly_active", "moderately_active", "very_active", "extremely_active"].index(
                                            user_profile.get("activity_level", "lightly_active")))
            
            diet_type = st.selectbox("Diet Type", 
                                   ["balanced", "vegetarian", "vegan", "keto", "paleo", "mediterranean"],
                                   index=["balanced", "vegetarian", "vegan", "keto", "paleo", "mediterranean"].index(
                                       user_profile.get("diet_type", "balanced")))
        
        with col4:
            favorite_foods = st.text_area("Favorite Foods (comma-separated)", 
                                        value=", ".join(user_profile.get("favorite_foods", [])))
            
            dietary_restrictions = st.text_area("Dietary Restrictions (comma-separated)", 
                                              value=", ".join(user_profile.get("dietary_restrictions", [])))
        
        st.markdown("### Health Information")
        
        col5, col6 = st.columns(2)
        with col5:
            common_issues = st.text_area("Common Health Issues (comma-separated)", 
                                       value=", ".join(user_profile.get("common_issues", [])))
            medical_conditions = st.text_area("Medical Conditions (comma-separated)", 
                                            value=", ".join(user_profile.get("medical_conditions", [])))
        
        with col6:
            medications = st.text_area("Medications (comma-separated)", 
                                     value=", ".join(user_profile.get("medications", [])))
            fitness_goals = st.text_area("Fitness Goals (comma-separated)", 
                                       value=", ".join(user_profile.get("fitness_goals", [])))
        
        preferred_workout_types = st.text_area("Preferred Workout Types (comma-separated)", 
                                             value=", ".join(user_profile.get("preferred_workout_types", [])))
        
        if st.form_submit_button("Update Profile", use_container_width=True):
            profile_data = {
                "full_name": full_name,
                "email": email,
                "age": age,
                "gender": gender,
                "height": height,
                "target_weight": target_weight,
                "activity_level": activity_level,
                "diet_type": diet_type,
                "favorite_foods": favorite_foods,
                "dietary_restrictions": dietary_restrictions,
                "common_issues": common_issues,
                "medical_conditions": medical_conditions,
                "medications": medications,
                "fitness_goals": fitness_goals,
                "preferred_workout_types": preferred_workout_types
            }
            
            result = update_user_profile(user_profile["user_id"], profile_data)
            if result["success"]:
                st.success("Profile updated successfully!")
                # Update session state with new data
                for key, value in profile_data.items():
                    if key in ['favorite_foods', 'dietary_restrictions', 'common_issues', 
                              'medical_conditions', 'medications', 'fitness_goals', 'preferred_workout_types']:
                        # Handle list fields
                        if isinstance(value, str):
                            st.session_state.user_profile[key] = [item.strip() for item in value.split(',') if item.strip()]
                        else:
                            st.session_state.user_profile[key] = value
                    else:
                        st.session_state.user_profile[key] = value
                st.balloons()
                # Auto redirect back to dashboard after 2 seconds
                import time
                time.sleep(2)
                st.session_state.show_edit_profile = False
                st.rerun()
            else:
                st.error(result["message"])

def show_agent_chat():
    """Display chat interface with agent switching"""
    user_profile = st.session_state.user_profile
    current_agent = st.session_state.current_agent
    
    # Create shared sidebar for chat
    create_shared_sidebar(current_page="chat")
    
    # Theme toggle
    show_theme_toggle()
    
    # Agent-specific info
    agent_info = {
        "MENTAL_HEALTH": {"name": "Mental Health Assistant", "icon": "🧠", "color": "#4CAF50"},
        "DIET": {"name": "Diet & Nutrition Assistant", "icon": "🥗", "color": "#FF9800"},
        "EXERCISE": {"name": "Exercise & Fitness Assistant", "icon": "💪", "color": "#2196F3"}
    }
    
    agent = agent_info[current_agent]
    
    # Main chat area with agent switcher
    st.markdown("#### 🎯 Choose Your Wellness Agent")
    
    # Agent switching buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        agent_selected = current_agent == "MENTAL_HEALTH"
        button_style = "🟢" if agent_selected else ""
        if st.button(f"{button_style} 🧠 Mental Health", key="switch_mental", use_container_width=True):
            st.session_state.current_agent = "MENTAL_HEALTH"
            # Load most recent session for this agent or create new one
            agent_threads = get_agent_specific_threads(user_profile["user_id"], "MENTAL_HEALTH")
            if agent_threads:
                st.session_state.thread_id = agent_threads[-1]  # Most recent
                st.session_state.message_history = load_conversation(agent_threads[-1])
            else:
                st.session_state.thread_id = generate_agent_thread_id("MENTAL_HEALTH")
                st.session_state.message_history = []
            st.rerun()
    
    with col2:
        agent_selected = current_agent == "DIET"
        button_style = "🟢" if agent_selected else ""
        if st.button(f"{button_style} 🥗 Diet & Nutrition", key="switch_diet", use_container_width=True):
            st.session_state.current_agent = "DIET"
            # Load most recent session for this agent or create new one
            agent_threads = get_agent_specific_threads(user_profile["user_id"], "DIET")
            if agent_threads:
                st.session_state.thread_id = agent_threads[-1]  # Most recent
                st.session_state.message_history = load_conversation(agent_threads[-1])
            else:
                st.session_state.thread_id = generate_agent_thread_id("DIET")
                st.session_state.message_history = []
            st.rerun()
    
    with col3:
        agent_selected = current_agent == "EXERCISE"
        button_style = "🟢" if agent_selected else ""
        if st.button(f"{button_style} 💪 Exercise & Fitness", key="switch_exercise", use_container_width=True):
            st.session_state.current_agent = "EXERCISE"
            # Load most recent session for this agent or create new one
            agent_threads = get_agent_specific_threads(user_profile["user_id"], "EXERCISE")
            if agent_threads:
                st.session_state.thread_id = agent_threads[-1]  # Most recent
                st.session_state.message_history = load_conversation(agent_threads[-1])
            else:
                st.session_state.thread_id = generate_agent_thread_id("EXERCISE")
                st.session_state.message_history = []
            st.rerun()
    
    # Display chat messages
    for message in st.session_state.message_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
    

    
    # Chat input
    user_input = st.chat_input(f"Message {agent['name']}...")
    
    if user_input:
        # Add user message
        st.session_state.message_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Display user message immediately
        with st.chat_message("user"):
            st.write(user_input)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_agent_response(user_input, current_agent, user_profile)
                st.write(response)
        
        # Add AI response to history
        st.session_state.message_history.append({
            "role": "assistant",
            "content": response
        })
        
        st.rerun()


def get_agent_response(user_input, agent_type, user_profile):
    """Get response from the selected agent"""
    try:
        current_time = datetime.datetime.now()
        
        # Create state with user context
        state_input: State = {
            "messages": [HumanMessage(content=user_input)],
            "session_id": st.session_state.thread_id,
            "time_stamps": [current_time],
            "ner_entities": [],
            "chat_response": "",
            "current_user": user_profile["user_id"],
            "current_agent": agent_type,
            "user_context": user_profile
        }
        
        config: RunnableConfig = {"configurable": {"thread_id": st.session_state.thread_id}}
        final_result = chatbot.invoke(state_input, config=config)
        
        if 'messages' in final_result and len(final_result['messages']) > 1:
            ai_message = final_result['messages'][-1]
            if hasattr(ai_message, 'content'):
                return ai_message.content
        
        return "I'm here to help you with your wellness journey. Please tell me more about what you need assistance with."
        
    except Exception as e:
        st.error(f"Error getting response: {str(e)}")
        return "I apologize, but I'm experiencing technical difficulties. Please try again."



def show_wellness_overview(user_id):
    """Show wellness overview metrics"""
    # Get session counts by agent
    mental_sessions = len(get_agent_specific_threads(user_id, "MENTAL_HEALTH"))
    diet_sessions = len(get_agent_specific_threads(user_id, "DIET"))
    exercise_sessions = len(get_agent_specific_threads(user_id, "EXERCISE"))
    # Total should be sum of actual agent sessions
    total_sessions = mental_sessions + diet_sessions + exercise_sessions
    
    # Load wellness data
    wellness_data = load_user_wellness_data(user_id)
    summary = wellness_data.get("wellness_summary", {})
    
    # Key metrics
    st.markdown("#### 📈 Wellness Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f'<div class="metric-card"><h4>Total Sessions</h4><h2>{total_sessions}</h2></div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<div class="metric-card"><h4>🧠 Mental Health</h4><h2>{mental_sessions}</h2></div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'<div class="metric-card"><h4>🥗 Diet Sessions</h4><h2>{diet_sessions}</h2></div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown(f'<div class="metric-card"><h4>💪 Exercise Sessions</h4><h2>{exercise_sessions}</h2></div>', unsafe_allow_html=True)
    
    # Goal progress - Calculate real progress metrics
    st.markdown("#### 🎯 Goal Progress")
    progress_metrics = calculate_progress_metrics(user_id)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        weight_progress = round(progress_metrics.get("weight_progress", 0), 1)
        st.progress(min(weight_progress / 100, 1.0))
        st.markdown(f"**Weight Goal Progress:** {weight_progress}%")
        if weight_progress == 0:
            st.caption("💡 Update your profile with current weight to track progress")
    
    with col2:
        fitness_progress = round(progress_metrics.get("fitness_progress", 0), 1)
        st.progress(min(fitness_progress / 100, 1.0))
        st.markdown(f"**Fitness Progress:** {fitness_progress}%")
        if fitness_progress == 0:
            st.caption("💡 Create exercise routines and log progress to track fitness")
    
    with col3:
        mental_health_progress = round(progress_metrics.get("mental_health_progress", 0), 1)
        st.progress(min(mental_health_progress / 100, 1.0))
        st.markdown(f"**Mental Health Progress:** {mental_health_progress}%")
        if mental_health_progress == 0:
            st.caption("💡 Create mental health routines and log daily mood to track progress")
    
    # Additional progress metrics
    st.markdown("#### 📊 Activity & Routine Metrics")
    col1, col2 = st.columns(2)
    
    with col1:
        routine_adherence = round(progress_metrics.get("overall_routine_adherence", 0), 1)
        st.metric("Overall Routine Adherence", f"{routine_adherence}%", 
                 help="Based on your satisfaction ratings when logging progress")
    
    with col2:
        weekly_completion = round(progress_metrics.get("weekly_activity_completion", 0), 1)
        st.metric("Weekly Activity Completion", f"{weekly_completion}%",
                 help="Percentage of planned activities completed this week")

def show_detailed_profile(user_profile):
    """Show detailed profile information"""
    st.markdown("#### 👤 Complete Profile Information")
    
    # Personal Information
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("**Personal Details**")
        st.write(f"**Full Name:** {user_profile.get('full_name', 'N/A')}")
        st.write(f"**Email:** {user_profile.get('email', 'N/A')}")
        st.write(f"**Age:** {user_profile.get('age', 'N/A')} years")
        st.write(f"**Gender:** {user_profile.get('gender', 'N/A')}")
        st.write(f"**User ID:** {user_profile.get('user_id', 'N/A')}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("**Physical Stats**")
        st.write(f"**Height:** {user_profile.get('height', 'N/A')} cm")
        st.write(f"**Current Weight:** {user_profile.get('current_weight', 'N/A')} kg")
        st.write(f"**Target Weight:** {user_profile.get('target_weight', 'N/A')} kg")
        st.write(f"**Activity Level:** {user_profile.get('activity_level', 'N/A').replace('_', ' ').title()}")
        st.write(f"**Diet Type:** {user_profile.get('diet_type', 'N/A').title()}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Health Information
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("**Health & Lifestyle**")
        st.write(f"**Daily Stress Level:** {user_profile.get('daily_stress_level', 'N/A')}/5")
        st.write(f"**Wake-up Time:** {user_profile.get('wake_up_time', 'N/A')}")
        st.write(f"**Sleep Time:** {user_profile.get('sleep_time', 'N/A')}")
        
        concerns = user_profile.get('common_issues', [])
        st.write("**Common Issues:**")
        if concerns:
            for concern in concerns:
                st.write(f"  • {concern}")
        else:
            st.write("  • None listed")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col4:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("**Medical Information**")
        
        conditions = user_profile.get('medical_conditions', [])
        st.write("**Medical Conditions:**")
        if conditions:
            for condition in conditions:
                st.write(f"  • {condition}")
        else:
            st.write("  • None listed")
            
        medications = user_profile.get('medications', [])
        st.write("**Medications:**")
        if medications:
            for med in medications:
                st.write(f"  • {med}")
        else:
            st.write("  • None listed")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Preferences and Goals
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("**Food Preferences**")
        
        fav_foods = user_profile.get('favorite_foods', [])
        st.write("**Favorite Foods:**")
        if fav_foods:
            for food in fav_foods:
                st.write(f"  • {food}")
        else:
            st.write("  • None listed")
            
        restrictions = user_profile.get('dietary_restrictions', [])
        st.write("**Dietary Restrictions:**")
        if restrictions:
            for restriction in restrictions:
                st.write(f"  • {restriction}")
        else:
            st.write("  • None listed")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col6:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown("**Fitness Goals**")
        
        goals = user_profile.get('fitness_goals', [])
        st.write("**Fitness Goals:**")
        if goals:
            for goal in goals:
                st.write(f"  • {goal}")
        else:
            st.write("  • None listed")
            
        workouts = user_profile.get('preferred_workout_types', [])
        st.write("**Preferred Workouts:**")
        if workouts:
            for workout in workouts:
                st.write(f"  • {workout}")
        else:
            st.write("  • None listed")
        st.markdown('</div>', unsafe_allow_html=True)

def show_ner_insights(user_id):
    """Show detailed conversation insights with expandable entity information"""
    st.markdown("#### 💬 Conversation Insights")
    
    try:
        # Get detailed insights
        detailed_insights = get_detailed_user_ner_insights(user_id)
        
        if detailed_insights.get("total_sessions", 0) == 0:
            st.info("No conversation data available yet. Start chatting to see insights!")
            return
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            people_count = len(detailed_insights.get("detailed_people", []))
            st.markdown(f'<div class="metric-card"><h4>👥 People</h4><h2>{people_count}</h2></div>', unsafe_allow_html=True)
        
        with col2:
            places_count = len(detailed_insights.get("detailed_places", []))
            st.markdown(f'<div class="metric-card"><h4>📍 Places</h4><h2>{places_count}</h2></div>', unsafe_allow_html=True)
        
        with col3:
            events_count = len(detailed_insights.get("detailed_events", []))
            st.markdown(f'<div class="metric-card"><h4>📅 Activities</h4><h2>{events_count}</h2></div>', unsafe_allow_html=True)
        
        with col4:
            substances_count = len(detailed_insights.get("detailed_substances", []))
            st.markdown(f'<div class="metric-card"><h4>💊 Health Items</h4><h2>{substances_count}</h2></div>', unsafe_allow_html=True)
        
        # Detailed information with tabs for better organization
        st.markdown("#### 📝 Detailed Information")
        
        # Create tabs for different entity types
        tab1, tab2, tab3, tab4 = st.tabs(["👥 People", "📍 Places", "📅 Activities", "💊 Health Items"])
        
        with tab1:
            people = detailed_insights.get("detailed_people", [])
            if people:
                st.markdown(f"**Found {len(people)} people mentioned in your conversations:**")
                for i, person in enumerate(people):
                    # Create unique key for each person
                    person_key = f"person_{hash(str(person))}"
                    
                    # Compact display with expand button
                    col1, col2 = st.columns([4, 1])
                    with col1:
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
                                st.write(f"**Emotional Association:** {person.get('emotional_charge', 'neutral')}")
                            
                            with detail_col2:
                                if person.get('significance'):
                                    st.write(f"**Significance:** {person.get('significance')}")
                                if person.get('timestamp'):
                                    st.write(f"**First Mentioned:** {format_timestamp(person.get('timestamp'))}")
                            
                            # Close button for details
                            if st.button("Hide Details", key=f"hide_{person_key}"):
                                st.session_state[expanded_key] = False
                                st.rerun()
                            
                            st.markdown("---")
                    
                    if i < len(people) - 1:
                        st.markdown("---")
            else:
                st.info("No people mentioned in conversations yet.")
        
        with tab2:
            places = detailed_insights.get("detailed_places", [])
            if places:
                st.markdown(f"**Found {len(places)} places mentioned in your conversations:**")
                for i, place in enumerate(places):
                    place_key = f"place_{hash(str(place))}"
                    
                    # Compact display
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        location = place.get('location', 'N/A')
                        context = place.get('context', 'N/A')
                        
                        st.markdown(f"📍 **{location}**")
                        if context:
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
                                st.write(f"**First Mentioned:** {format_timestamp(place.get('timestamp'))}")
                            
                            if st.button("Hide Details", key=f"hide_{place_key}"):
                                st.session_state[expanded_key] = False
                                st.rerun()
                            
                            st.markdown("---")
                    
                    if i < len(places) - 1:
                        st.markdown("---")
            else:
                st.info("No places mentioned in conversations yet.")
        
        with tab3:
            events = detailed_insights.get("detailed_events", [])
            if events:
                st.markdown(f"**Found {len(events)} activities/events mentioned in your conversations:**")
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
                        st.caption(f"Timeframe: {timeframe}")
                    
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
                                st.write(f"**Wellness Relevance:** {event.get('trauma_relevance', 'low')}")
                                if event.get('timestamp'):
                                    st.write(f"**First Mentioned:** {format_timestamp(event.get('timestamp'))}")
                            
                            if event.get('description'):
                                st.write(f"**Description:** {event.get('description')}")
                            
                            if st.button("Hide Details", key=f"hide_{event_key}"):
                                st.session_state[expanded_key] = False
                                st.rerun()
                            
                            st.markdown("---")
                    
                    if i < len(events) - 1:
                        st.markdown("---")
            else:
                st.info("No activities or events mentioned in conversations yet.")
        
        with tab4:
            substances = detailed_insights.get("detailed_substances", [])
            if substances:
                st.markdown(f"**Found {len(substances)} health items mentioned in your conversations:**")
                for i, substance in enumerate(substances):
                    substance_key = f"substance_{hash(str(substance))}"
                    
                    # Compact display
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        substance_name = substance.get('substance', 'N/A')
                        usage_pattern = substance.get('usage_pattern', 'N/A')
                        
                        st.markdown(f"💊 **{substance_name}**")
                        if usage_pattern:
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
                            st.write(f"**Item:** {substance.get('substance', 'N/A')}")
                            st.write(f"**Usage Pattern:** {substance.get('usage_pattern', 'N/A')}")
                            st.write(f"**Context:** {substance.get('context', 'N/A')}")
                            if substance.get('timestamp'):
                                st.write(f"**First Mentioned:** {format_timestamp(substance.get('timestamp'))}")
                            
                            if st.button("Hide Details", key=f"hide_{substance_key}"):
                                st.session_state[expanded_key] = False
                                st.rerun()
                            
                            st.markdown("---")
                    
                    if i < len(substances) - 1:
                        st.markdown("---")
            else:
                st.info("No health items mentioned in conversations yet.")  
    except Exception as e:
        st.error(f"Error loading conversation insights: {str(e)}")

def show_session_analysis(user_id):
    """Show detailed session analysis by agent"""
    st.markdown("#### 💬 Session Analysis by Agent")
    
    # Get all sessions
    all_threads = retrieve_user_threads(user_id)
    
    if not all_threads:
        st.info("No conversation sessions found. Start chatting to see session analysis!")
        return
    
    # Organize sessions by agent
    mental_threads = get_agent_specific_threads(user_id, "MENTAL_HEALTH")
    diet_threads = get_agent_specific_threads(user_id, "DIET")
    exercise_threads = get_agent_specific_threads(user_id, "EXERCISE")
    
    # Create tabs for each agent
    tab1, tab2, tab3 = st.tabs([f"🧠 Mental Health ({len(mental_threads)})", 
                                f"🥗 Diet & Nutrition ({len(diet_threads)})", 
                                f"💪 Exercise & Fitness ({len(exercise_threads)})"])
    
    with tab1:
        show_agent_sessions(user_id, mental_threads, "Mental Health", "🧠")
    
    with tab2:
        show_agent_sessions(user_id, diet_threads, "Diet & Nutrition", "🥗")
    
    with tab3:
        show_agent_sessions(user_id, exercise_threads, "Exercise & Fitness", "💪")

def show_agent_sessions(user_id, threads, agent_name, icon):
    """Show sessions for a specific agent"""
    if not threads:
        st.info(f"No {agent_name.lower()} sessions found yet.")
        return
    
    st.markdown(f"### {icon} {agent_name} Sessions")
    
    for thread_id in threads[::-1]:  # Most recent first
        try:
            # Get session summary from NER data
            ner_data = load_user_ner_data(user_id)
            session_data = ner_data.get("sessions", {}).get(thread_id, {})
            
            # Create expandable session card
            with st.expander(f"💬 Session: {thread_id[-12:]} | Messages: {len(session_data.get('messages', []))}"):
                
                if session_data:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Session Info**")
                        st.write(f"**Session ID:** {thread_id}")
                        st.write(f"**Created:** {session_data.get('created_at', 'N/A')}")
                        st.write(f"**Last Updated:** {session_data.get('last_updated', 'N/A')}")
                        st.write(f"**Total Messages:** {len(session_data.get('messages', []))}")
                    
                    with col2:
                        st.markdown("**Entities Mentioned**")
                        st.write(f"**People:** {len(session_data.get('people', []))}")
                        st.write(f"**Places:** {len(session_data.get('places', []))}")
                        st.write(f"**Events:** {len(session_data.get('events', []))}")
                        st.write(f"**Substances:** {len(session_data.get('substances', []))}")
                    
                    # Show entities if any
                    if session_data.get('people') or session_data.get('places') or session_data.get('events') or session_data.get('substances'):
                        st.markdown("**Key Information Mentioned:**")
                        entities_col1, entities_col2 = st.columns(2)
                        
                        with entities_col1:
                            if session_data.get('people'):
                                people_names = []
                                for person in session_data['people'][:5]:
                                    if isinstance(person, dict):
                                        people_names.append(person.get('name', str(person)))
                                    else:
                                        people_names.append(str(person))
                                if people_names:
                                    st.write("👥 **People:** " + ", ".join(people_names))
                            if session_data.get('places'):
                                places_names = []
                                for place in session_data['places'][:5]:
                                    if isinstance(place, dict):
                                        # Try different possible field names for places
                                        location = place.get('location') or place.get('name') or place.get('place')
                                        if location:
                                            places_names.append(location)
                                        else:
                                            places_names.append(str(place))
                                    else:
                                        places_names.append(str(place))
                                if places_names:
                                    st.write("📍 **Places:** " + ", ".join(places_names))
                        
                        with entities_col2:
                            if session_data.get('events'):
                                events_names = []
                                for event in session_data['events'][:5]:
                                    if isinstance(event, dict):
                                        event_name = event.get('event') or event.get('name') or event.get('activity')
                                        if event_name:
                                            events_names.append(event_name)
                                        else:
                                            events_names.append(str(event))
                                    else:
                                        events_names.append(str(event))
                                if events_names:
                                    st.write("📅 **Activities:** " + ", ".join(events_names))
                            if session_data.get('substances'):
                                substances_names = []
                                for substance in session_data['substances'][:5]:
                                    if isinstance(substance, dict):
                                        substance_name = substance.get('substance') or substance.get('name')
                                        if substance_name:
                                            substances_names.append(substance_name)
                                        else:
                                            substances_names.append(str(substance))
                                    else:
                                        substances_names.append(str(substance))
                                if substances_names:
                                    st.write("💊 **Substances:** " + ", ".join(substances_names))
                    
                    # Button to view full conversation
                    if st.button(f"👁️ View Full Conversation", key=f"view_{thread_id}"):
                        # Extract agent type from thread_id (format: AGENT_userID_timestamp)
                        if thread_id.startswith("MENTAL_HEALTH"):
                            st.session_state.current_agent = "MENTAL_HEALTH"
                        elif thread_id.startswith("DIET"):
                            st.session_state.current_agent = "DIET"
                        elif thread_id.startswith("EXERCISE"):
                            st.session_state.current_agent = "EXERCISE"
                        
                        # Set the thread and load conversation
                        st.session_state.thread_id = thread_id
                        st.session_state.message_history = load_conversation(thread_id)
                        
                        # Navigate to chat page (not dashboard)
                        st.session_state.show_profile_analysis = False
                        st.session_state.show_dashboard = False
                        st.session_state.show_chat = True
                        st.rerun()
                
                else:
                    st.write("No detailed session data available for this conversation.")
                    
        except Exception as e:
            st.error(f"Error loading session {thread_id}: {str(e)}")

# Main application logic
def show_main_layout():
    """Main layout with navigation options"""
    user_profile = st.session_state.user_profile
    
    # Simple top bar with app title and logout
    col1, col2 = st.columns([8, 1])
    with col1:
        # App title
        st.markdown("<h3 style='text-align: center; margin: 0; color: #2E86AB;'>🌟 Multi-Agentic Wellness Assistant</h3>", unsafe_allow_html=True)
    
    with col2:
        # Logout button on the right
        if st.button("🚪 Logout", key="top_logout"):
            st.session_state.authenticated = False
            st.session_state.user_profile = None
            st.rerun()
    
    st.markdown("---")
    
    # Sidebar is always visible, so no need for help or menu button
    # Emergency navigation if needed (this shouldn't normally show since sidebar is always visible) 
    if False:  # Disabled since sidebar is forced to be visible
        st.warning("""
        � **Looking for the Navigation Sidebar?**
        
        The sidebar might be collapsed. Here's how to bring it back:
        
        1. **Look for a small arrow (>) at the very top-left of your screen**
        2. **Click the arrow to expand the sidebar**
        3. **If you don't see an arrow, try refreshing the page (F5)**
        
        **Alternative: Use the navigation options below** ⬇️
        """)
        
        # Provide alternative navigation
        st.markdown("### 🧭 Quick Navigation")
        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
        
        with nav_col1:
            if st.button("🏠 Dashboard", key="quick_dashboard", use_container_width=True):
                st.session_state.show_dashboard = True
                st.session_state.show_profile_analysis = False
                st.session_state.show_chat = False
                st.session_state.sidebar_help_visible = False
                st.rerun()
        
        with nav_col2:
            if st.button("📊 Profile Analysis", key="quick_profile", use_container_width=True):
                st.session_state.show_profile_analysis = True
                st.session_state.show_dashboard = False
                st.session_state.show_chat = False
                st.session_state.sidebar_help_visible = False
                st.rerun()
        
        with nav_col3:
            if st.button("💬 Chat", key="quick_chat", use_container_width=True):
                st.session_state.show_dashboard = False
                st.session_state.show_profile_analysis = False
                st.session_state.show_chat = True
                st.session_state.sidebar_help_visible = False
                st.rerun()
        
        with nav_col4:
            if st.button("� Daily Update", key="quick_daily", use_container_width=True):
                st.session_state.show_daily_update = True
                st.session_state.sidebar_help_visible = False
                st.rerun()
        
        # Dismiss button
        if st.button("✅ Got it! Hide this help", key="dismiss_help"):
            st.session_state.sidebar_help_visible = False
            st.rerun()
    
    st.markdown("---")
    
    # Main content area - sidebar for all pages now
    if st.session_state.show_dashboard:
        show_main_dashboard_content()
    elif st.session_state.show_profile_analysis:
        show_profile_analysis_content()
    else:
        # Default to chat (sidebar created inside show_agent_chat)
        show_agent_chat()

def create_shared_sidebar(current_page="chat"):
    """Create fixed sidebar for all pages with navigation and CSS/JS protection"""
    user_profile = st.session_state.user_profile
    
    # Force sidebar to stay expanded - Add CSS and JavaScript (same as chat)
    st.markdown("""
    <style>
    /* Force sidebar to stay visible and expanded - Multiple selectors for compatibility */
    .css-1d391kg, .css-1lcbmhc, .st-emotion-cache-1cypcdb, 
    section[data-testid="stSidebar"] > div, 
    .css-17eq0hr, .css-1544g2n, .e1fqkh3o0 {
        width: 21rem !important;
        min-width: 21rem !important;
        max-width: 21rem !important;
        display: block !important;
        visibility: visible !important;
    }
    
    /* Ensure sidebar container stays expanded */
    section[data-testid="stSidebar"] {
        width: 21rem !important;
        min-width: 21rem !important;
        display: block !important;
        visibility: visible !important;
    }
    
    /* Hide ALL possible sidebar collapse buttons */
    button[kind="header"], 
    button[aria-label="Hide sidebar"],
    button[aria-label="Close sidebar"],
    button[title="Hide sidebar"],
    .css-vk3wp9,
    .css-1rs6os,
    .css-17ziqus,
    section[data-testid="stSidebar"] button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        opacity: 0 !important;
    }
    
    /* Prevent any sidebar animations that might hide it */
    section[data-testid="stSidebar"] * {
        transition: none !important;
        animation: none !important;
    }
    
    /* Force main content to account for sidebar */
    .main .block-container {
        padding-left: 21rem !important;
        max-width: calc(100% - 21rem) !important;
    }
    </style>
    
    <script>
    // Aggressive JavaScript to prevent sidebar collapse
    function preventSidebarCollapse() {
        // Find and expand sidebar if collapsed
        const expandButtons = document.querySelectorAll('[aria-label="Show sidebar"], [title="Show sidebar"]');
        expandButtons.forEach(button => {
            if (button && button.offsetParent !== null) {
                button.click();
            }
        });
        
        // Find and disable/hide ALL collapse buttons
        const collapseSelectors = [
            '[aria-label="Hide sidebar"]',
            '[aria-label="Close sidebar"]', 
            '[title="Hide sidebar"]',
            'button[kind="header"]',
            'section[data-testid="stSidebar"] button[kind="header"]'
        ];
        
        collapseSelectors.forEach(selector => {
            const buttons = document.querySelectorAll(selector);
            buttons.forEach(button => {
                button.style.display = 'none !important';
                button.style.visibility = 'hidden !important';
                button.style.pointerEvents = 'none !important';
                button.disabled = true;
                
                // Remove ALL event listeners
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);
                newButton.style.display = 'none !important';
            });
        });
        
        // Force sidebar to stay visible
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.style.width = '21rem !important';
            sidebar.style.minWidth = '21rem !important';
            sidebar.style.display = 'block !important';
            sidebar.style.visibility = 'visible !important';
            sidebar.style.transform = 'none !important';
        }
        
        // Force all sidebar containers to stay visible
        const sidebarContainers = document.querySelectorAll(
            '.css-1d391kg, .css-1lcbmhc, .st-emotion-cache-1cypcdb, ' +
            'section[data-testid="stSidebar"] > div'
        );
        sidebarContainers.forEach(container => {
            container.style.width = '21rem !important';
            container.style.minWidth = '21rem !important';
            container.style.display = 'block !important';
            container.style.visibility = 'visible !important';
        });
    }
    
    // Run immediately
    preventSidebarCollapse();
    
    // Run multiple times with different delays to catch dynamic loading
    setTimeout(preventSidebarCollapse, 50);
    setTimeout(preventSidebarCollapse, 100);
    setTimeout(preventSidebarCollapse, 200);
    setTimeout(preventSidebarCollapse, 500);
    </script>
    """, unsafe_allow_html=True)
    
    # Sidebar content
    st.sidebar.title("🌟 Wellness Assistant")
    
    # Navigation buttons with current page highlighting
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Navigation")
    
    # Dashboard button
    dashboard_style = "🟢 " if current_page == "dashboard" else ""
    if st.sidebar.button(f"{dashboard_style}🏠 Dashboard", key="sidebar_nav_dashboard", use_container_width=True):
        st.session_state.show_dashboard = True
        st.session_state.show_profile_analysis = False
        st.session_state.show_chat = False
        st.rerun()
    
    # Profile Analysis button
    profile_style = "🟢 " if current_page == "profile" else ""
    if st.sidebar.button(f"{profile_style}📊 Profile Analysis", key="sidebar_nav_profile", use_container_width=True):
        st.session_state.show_profile_analysis = True
        st.session_state.show_dashboard = False
        st.session_state.show_chat = False
        st.rerun()
    
    # Chat button
    chat_style = "🟢 " if current_page == "chat" else ""
    if st.sidebar.button(f"{chat_style}💬 Chat", key="sidebar_nav_chat", use_container_width=True):
        st.session_state.show_dashboard = False
        st.session_state.show_profile_analysis = False
        st.session_state.show_chat = True
        st.rerun()
    
    # Additional sidebar content based on current page
    if current_page == "chat":
        # Chat-specific sidebar content
        current_agent = st.session_state.current_agent
        st.sidebar.button("New Chat", key="sidebar_new_chat_shared", on_click=lambda: new_chat())
        
        # Chat sessions
        st.sidebar.markdown("---")
        st.sidebar.header("My Conversations")
        current_user = user_profile["user_id"]
        agent_threads = get_agent_specific_threads(current_user, current_agent)
        
        for thread_id in agent_threads[::-1]:  # Show most recent first
            col1, col2 = st.sidebar.columns([4, 1])
            with col1:
                if st.sidebar.button(str(thread_id[-8:]), key=f"thread_shared_{thread_id}"):
                    st.session_state.thread_id = thread_id
                    st.session_state.message_history = load_conversation(thread_id)
                    st.rerun()
            with col2:
                if st.sidebar.button("🗑️", key=f"del_shared_{thread_id}", help="Delete"):
                    delete_session(thread_id, current_user)
                    st.rerun()
    
    else:
        # Dashboard and Profile pages - show user info and quick actions
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 User Info")
        st.sidebar.write(f"**Name:** {user_profile['full_name']}")
        st.sidebar.write(f"**Age:** {user_profile.get('age', 'N/A')}")
        st.sidebar.write(f"**Goal:** {user_profile.get('goal', 'General Wellness')}")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚡ Quick Actions")
        
        if st.sidebar.button("✏️ Edit Profile", key="sidebar_edit_profile", use_container_width=True):
            st.session_state.show_edit_profile = True
            st.rerun()
        
        if st.sidebar.button("📝 Daily Update", key="sidebar_daily_update", use_container_width=True):
            st.session_state.show_daily_update = True
            st.rerun()
    
    # Add continuous monitoring at the end (same as chat)
    st.markdown("""
    <script>
    // Ultra-aggressive continuous monitoring to prevent sidebar collapse
    function keepSidebarExpanded() {
        // Comprehensive list of collapse button selectors
        const collapseSelectors = [
            'button[aria-label="Hide sidebar"]',
            'button[aria-label="Close sidebar"]',
            'button[title="Hide sidebar"]',
            'button[kind="header"]',
            'section[data-testid="stSidebar"] button',
            '.css-vk3wp9',
            '.css-1rs6os', 
            '.css-17ziqus'
        ];
        
        // Aggressively disable all collapse buttons
        collapseSelectors.forEach(selector => {
            const buttons = document.querySelectorAll(selector);
            buttons.forEach(button => {
                // Check if this might be a collapse button by checking its position/parent
                const isInSidebarHeader = button.closest('section[data-testid="stSidebar"]') && 
                                         (button.offsetParent && button.offsetParent.offsetHeight < 100);
                
                if (isInSidebarHeader || selector.includes('sidebar') || button.getAttribute('kind') === 'header') {
                    button.style.display = 'none !important';
                    button.style.visibility = 'hidden !important';
                    button.style.pointerEvents = 'none !important';
                    button.style.opacity = '0 !important';
                    button.disabled = true;
                    
                    // Prevent all click events
                    button.onclick = function(e) { 
                        e.preventDefault(); 
                        e.stopPropagation(); 
                        return false; 
                    };
                    
                    // Remove event listeners by cloning
                    try {
                        const newButton = button.cloneNode(true);
                        button.parentNode.replaceChild(newButton, button);
                        newButton.style.display = 'none !important';
                    } catch(e) {}
                }
            });
        });
        
        // Force sidebar to stay expanded with multiple approaches
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.style.cssText = `
                width: 21rem !important;
                min-width: 21rem !important;
                max-width: 21rem !important;
                display: block !important;
                visibility: visible !important;
                transform: translateX(0) !important;
                left: 0 !important;
                position: relative !important;
            `;
            
            // Remove any classes that might hide sidebar
            sidebar.classList.remove('css-1cypcdb', 'collapsed');
        }
        
        // Force all possible sidebar containers
        const containerSelectors = [
            '.css-1d391kg', '.css-1lcbmhc', '.st-emotion-cache-1cypcdb',
            'section[data-testid="stSidebar"] > div',
            '.css-17eq0hr', '.css-1544g2n', '.e1fqkh3o0'
        ];
        
        containerSelectors.forEach(selector => {
            const containers = document.querySelectorAll(selector);
            containers.forEach(container => {
                container.style.cssText = `
                    width: 21rem !important;
                    min-width: 21rem !important;
                    display: block !important;
                    visibility: visible !important;
                `;
            });
        });
        
        // Adjust main content to account for fixed sidebar
        const mainContent = document.querySelector('.main .block-container');
        if (mainContent) {
            mainContent.style.marginLeft = '21rem !important';
            mainContent.style.maxWidth = 'calc(100% - 21rem) !important';
        }
    }
    
    // Run immediately and frequently
    keepSidebarExpanded();
    
    // Multiple intervals to catch any dynamic changes
    setInterval(keepSidebarExpanded, 100);  // Very frequent
    setInterval(keepSidebarExpanded, 500);  // Regular
    setInterval(keepSidebarExpanded, 1000); // Backup
    
    // Event listeners for various triggers
    window.addEventListener('resize', keepSidebarExpanded);
    window.addEventListener('load', keepSidebarExpanded);
    document.addEventListener('DOMContentLoaded', keepSidebarExpanded);
    
    // MutationObserver to watch for DOM changes
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function(mutations) {
            let shouldCheck = false;
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' || mutation.type === 'attributes') {
                    shouldCheck = true;
                }
            });
            if (shouldCheck) {
                setTimeout(keepSidebarExpanded, 10);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class']
        });
    }
    </script>
    """, unsafe_allow_html=True)

def create_sidebar_for_chat():
    """Create sidebar specifically for chat - following working file pattern"""
    user_profile = st.session_state.user_profile
    current_agent = st.session_state.current_agent
    
    # Simple sidebar like the working file
    st.sidebar.title("🌟 Wellness Assistant")
    st.sidebar.button("New Chat", key="sidebar_new_chat_main", on_click=lambda: new_chat())
    
    # Navigation buttons
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigation")
    
    if st.sidebar.button("🏠 Dashboard", key="nav_dashboard"):
        st.session_state.show_dashboard = True
        st.session_state.show_profile_analysis = False
        st.session_state.show_chat = False
        st.rerun()
    
    if st.sidebar.button("📊 Profile Analysis", key="nav_profile"):
        st.session_state.show_profile_analysis = True
        st.session_state.show_dashboard = False
        st.session_state.show_chat = False
        st.rerun()
    
    # Chat sessions
    st.sidebar.markdown("---")
    st.sidebar.header(f"💬 Chat Sessions")
    current_user = user_profile["user_id"]
    agent_threads = get_agent_specific_threads(current_user, current_agent)
    
    if not agent_threads:
        st.sidebar.write("No previous conversations")
    
    for thread_id in agent_threads[::-1]:  # Show most recent first
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.sidebar.button(f"💬 {thread_id[-8:]}", key=f"load_{thread_id}"):
                st.session_state.thread_id = thread_id
                st.session_state.message_history = load_conversation(thread_id)
                st.rerun()
        with col2:
            if st.sidebar.button("🗑️", key=f"del_{thread_id}", help="Delete"):
                delete_session(thread_id, current_user)
                st.rerun()

def create_sidebar_navigation():
    """Create persistent sidebar navigation"""
    user_profile = st.session_state.user_profile
    current_agent = st.session_state.current_agent
    
    # Agent-specific info
    agent_info = {
        "MENTAL_HEALTH": {"name": "Mental Health Assistant", "icon": "🧠", "color": "#4CAF50"},
        "DIET": {"name": "Diet & Nutrition Assistant", "icon": "🥗", "color": "#FF9800"},
        "EXERCISE": {"name": "Exercise & Fitness Assistant", "icon": "💪", "color": "#2196F3"}
    }
    
    agent = agent_info[current_agent]
    
    # User greeting (main header already created in main function)
    st.sidebar.markdown(f"👋 Hello, {user_profile['full_name']}")
    
    # Sidebar info
    st.sidebar.info("� **Sidebar is always visible** - Contains navigation, session history, and quick actions")
    
    # Sidebar navigation with clear current section indicator
    st.sidebar.title("🧭 Navigation")
    
    # Show current section
    current_section = "Chat"
    if st.session_state.get("show_dashboard", False):
        current_section = "Dashboard"
    elif st.session_state.get("show_profile_analysis", False):
        current_section = "Profile Analysis"
    
    st.sidebar.markdown(f"**Current:** {current_section} 📍")
    
    # Navigation buttons with unique keys
    if st.sidebar.button("🏠 Dashboard", key="sidebar_dashboard", use_container_width=True):
        st.session_state.show_dashboard = True
        st.session_state.show_profile_analysis = False
        st.session_state.show_chat = False
        st.rerun()
    
    if st.sidebar.button("📊 Profile Analysis", key="sidebar_profile", use_container_width=True):
        st.session_state.show_profile_analysis = True
        st.session_state.show_dashboard = False
        st.session_state.show_chat = False
        st.rerun()
    
    if st.sidebar.button("💬 Back to Chat", key="sidebar_chat", use_container_width=True):
        st.session_state.show_dashboard = False
        st.session_state.show_profile_analysis = False
        st.session_state.show_chat = True
        st.rerun()
    
    if st.sidebar.button("📝 Update Daily Info", key="sidebar_daily", use_container_width=True):
        st.session_state.show_daily_update = True
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.title("Chat Sessions")
    st.sidebar.button("New Chat", key="sidebar_new_chat", on_click=lambda: new_chat(), use_container_width=True)
    
    # Session history in sidebar - Agent specific
    st.sidebar.header(f"{agent['icon']} {current_agent.replace('_', ' ').title()} Sessions")
    current_user = user_profile["user_id"]
    agent_threads = get_agent_specific_threads(current_user, current_agent)
    
    if not agent_threads:
        st.sidebar.write("No previous conversations")
    
    for thread_id in agent_threads[::-1]:  # Show most recent first
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.sidebar.button(f"💬 {thread_id[-8:]}", key=f"sidebar_load_{thread_id}", use_container_width=True):
                st.session_state.thread_id = thread_id
                st.session_state.message_history = load_conversation(thread_id)
                # Switch to chat view when loading a conversation
                st.session_state.show_dashboard = False
                st.session_state.show_profile_analysis = False
                st.session_state.show_chat = True
                st.rerun()
        with col2:
            if st.sidebar.button("🗑️", key=f"sidebar_del_{thread_id}", help="Delete session"):
                delete_session(thread_id, current_user)
                st.rerun()

def show_main_dashboard_content():
    """Display main dashboard content with fixed sidebar navigation"""
    user_profile = st.session_state.user_profile
    
    # Create shared sidebar for dashboard
    create_shared_sidebar(current_page="dashboard")
    
    # Theme toggle
    show_theme_toggle()
    
    # Header with user info
    st.markdown(f'<div class="wellness-header"><h1>🌟 Welcome, {user_profile["full_name"]}!</h1><p>Your Wellness Journey Dashboard</p></div>', unsafe_allow_html=True)
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><h4>Current Weight</h4><h2>{} kg</h2></div>'.format(user_profile.get("current_weight", "N/A")), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><h4>Target Weight</h4><h2>{} kg</h2></div>'.format(user_profile.get("target_weight", "N/A")), unsafe_allow_html=True)
    with col3:
        activity_level = user_profile.get("activity_level", "N/A").replace("_", " ").title()
        st.markdown('<div class="metric-card"><h4>Activity Level</h4><h2>{}</h2></div>'.format(activity_level), unsafe_allow_html=True)
    with col4:
        # Get actual session count by agent
        mental_sessions = len(get_agent_specific_threads(user_profile["user_id"], "MENTAL_HEALTH"))
        diet_sessions = len(get_agent_specific_threads(user_profile["user_id"], "DIET"))
        exercise_sessions = len(get_agent_specific_threads(user_profile["user_id"], "EXERCISE"))
        total_sessions = mental_sessions + diet_sessions + exercise_sessions
        st.markdown('<div class="metric-card"><h4>Total Sessions</h4><h2>{}</h2></div>'.format(total_sessions), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Wellness Overview
    st.markdown("#### 🎯 Your Wellness Assistant")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('''
        <div class="agent-card mental-health-card">
            <h3>🧠 Mental Health</h3>
            <p><strong>Emotional Wellness & Support</strong></p>
            <ul>
                <li>• Daily mood tracking</li>
                <li>• Stress management</li>
                <li>• Coping strategies</li>
                <li>• Mindful meditation</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
        
        if st.button("🧠 Chat with Mental Health Assistant", key="chat_mental", use_container_width=True):
            st.session_state.current_agent = "MENTAL_HEALTH"
            st.session_state.show_dashboard = False
            st.session_state.show_chat = True
            st.rerun()
    
    with col2:
        st.markdown('''
        <div class="agent-card diet-card">
            <h3>🥗 Diet & Nutrition</h3>
            <p><strong>Personalized Meal Planning</strong></p>
            <ul>
                <li>• Pakistani food recommendations</li>
                <li>• Calorie tracking</li>
                <li>• Macro balancing</li>
                <li>• Healthy alternatives</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
        
        if st.button("🥗 Chat with Diet Assistant", key="chat_diet", use_container_width=True):
            st.session_state.current_agent = "DIET"
            st.session_state.show_dashboard = False
            st.session_state.show_chat = True
            st.rerun()
    
    with col3:
        st.markdown('''
        <div class="agent-card exercise-card">
            <h3>💪 Exercise & Fitness</h3>
            <p><strong>Custom Workout Plans</strong></p>
            <ul>
                <li>• Home-based exercises</li>
                <li>• Progress tracking</li>
                <li>• Fitness challenges</li>
                <li>• Strength building</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
        
        if st.button("💪 Chat with Exercise Assistant", key="chat_exercise", use_container_width=True):
            st.session_state.current_agent = "EXERCISE"
            st.session_state.show_dashboard = False
            st.session_state.show_chat = True
            st.rerun()
    
    # Show routine dashboard
    st.markdown("---")
    show_routine_dashboard(user_profile["user_id"])

def show_profile_analysis_content():
    """Display profile analysis content with fixed sidebar navigation"""
    user_profile = st.session_state.user_profile
    user_id = user_profile["user_id"]
    
    # Create shared sidebar for profile analysis
    create_shared_sidebar(current_page="profile")
    
    # Theme toggle
    show_theme_toggle()
    
    st.markdown('<div class="wellness-header"><h1>📊 Profile Analysis & Management</h1><p>Complete wellness profile with insights and editing</p></div>', unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✏️ Edit Profile", key="profile_edit_btn", use_container_width=True):
            st.session_state.show_edit_profile = True
            st.session_state.show_profile_analysis = False
            st.rerun()
    with col2:
        if st.button("📝 Update Daily Info", key="profile_daily_btn", use_container_width=True):
            st.session_state.show_daily_update = True
            st.session_state.show_profile_analysis = False
            st.rerun()
    
    st.markdown("---")
    
    # Tabs for different analysis sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "👤 Profile Details", "💬 Conversation Insights", "🗓️ My Routines", "📊 Session Analysis"])    
    with tab1:
        show_wellness_overview(user_id)
    
    with tab2:
        show_detailed_profile(user_profile)
    
    with tab3:
        show_ner_insights(user_id)
    
    with tab4:
        show_routine_dashboard(user_id)
    
    with tab5:
        show_session_analysis(user_id)



def show_routine_dashboard(user_id):
    """Show comprehensive routine dashboard with all wellness plans"""
    st.markdown("#### 🗓️ My Wellness Routines")
    
    try:
        # Get all routine plans
        routine_plans = get_user_routine_plans(user_id)
        comprehensive_insights = get_comprehensive_user_insights(user_id)
        
        if not routine_plans:
            st.info("No routine plans created yet. Chat with our wellness agents and ask them to create a personalized routine for you!")
            
            # Show buttons to create routines
            st.markdown("#### 🚀 Quick Actions")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🧠 Create Mental Health Routine", key="create_mental_routine", use_container_width=True):
                    st.info("Switch to Mental Health Agent and say: 'Create a mental health routine for me'")
            
            with col2:
                if st.button("🥗 Create Diet Plan", key="create_diet_routine", use_container_width=True):
                    st.info("Switch to Diet Agent and say: 'Create a meal plan for me'")
            
            with col3:
                if st.button("💪 Create Exercise Routine", key="create_exercise_routine", use_container_width=True):
                    st.info("Switch to Exercise Agent and say: 'Create a workout routine for me'")
            
            return
        
        # Display existing routines
        st.markdown(f"**Total Routines:** {len(routine_plans)}")
        
        # Group routines by type
        mental_health_plans = [p for p in routine_plans if p.plan_type == "mental_health"]
        diet_plans = [p for p in routine_plans if p.plan_type == "diet"]
        exercise_plans = [p for p in routine_plans if p.plan_type == "exercise"]
        
        # Create tabs for different routine types
        routine_tab1, routine_tab2, routine_tab3 = st.tabs(["🧠 Mental Health", "🥗 Diet Plans", "💪 Exercise"])
        
        with routine_tab1:
            show_routine_type_section(user_id, mental_health_plans, "Mental Health", "🧠")
        
        with routine_tab2:
            show_routine_type_section(user_id, diet_plans, "Diet", "🥗")
        
        with routine_tab3:
            show_routine_type_section(user_id, exercise_plans, "Exercise", "💪")
        
        # Overall progress summary
        st.markdown("---")
        st.markdown("#### 📊 Overall Progress Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mental Health Routines", len(mental_health_plans))
        with col2:
            st.metric("Diet Plans", len(diet_plans))
        with col3:
            st.metric("Exercise Routines", len(exercise_plans))
        
    except Exception as e:
        st.error(f"Error loading routine dashboard: {str(e)}")

def show_routine_type_section(user_id, plans, plan_type, icon):
    """Show routine section for specific type"""
    if not plans:
        st.info(f"No {plan_type.lower()} routines created yet.")
        return
    
    for plan in plans:
        with st.expander(f"{icon} {plan_type} Routine - Created {plan.created_date}", expanded=False):
            # Plan overview
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📅 Daily Schedule:**")
                if plan.daily_schedule:
                    for item in plan.daily_schedule[:5]:  # Show first 5 items
                        st.write(f"• {item.time} - {item.activity} ({item.duration}min)")
                    if len(plan.daily_schedule) > 5:
                        st.write(f"... and {len(plan.daily_schedule) - 5} more activities")
                else:
                    st.write("No daily schedule items")
            
            with col2:
                st.markdown("**🎯 Weekly Goals:**")
                if plan.weekly_goals:
                    for goal in plan.weekly_goals[:3]:  # Show first 3 goals
                        st.write(f"• {goal.goal}")
                        if goal.target_metric:
                            st.caption(f"Target: {goal.target_metric}")
                    if len(plan.weekly_goals) > 3:
                        st.write(f"... and {len(plan.weekly_goals) - 3} more goals")
                else:
                    st.write("No weekly goals set")
            
            # Progress tracking section  
            st.markdown("**📈 Progress Tracking:**")
            
            # Try to get progress from both hybrid system and JSON
            progress_entries = []
            
            # Get from JSON (existing system)
            if hasattr(plan, 'progress_tracking') and plan.progress_tracking:
                progress_entries.extend(plan.progress_tracking)
            
            # Get from hybrid system if available
            try:
                plan_id = getattr(plan, 'plan_id', f"{plan.plan_type}_{plan.created_date.isoformat()}")
                
                # Try to get from SQL database via hybrid system
                if SQL_AVAILABLE:
                    from database import get_db_connection
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT log_date, completed_activities, total_activities, 
                                   satisfaction_level, notes, challenges 
                            FROM progress_logs 
                            WHERE plan_id = ? AND user_id = ? 
                            ORDER BY log_date DESC LIMIT 5
                        """, (plan_id, user_id))
                        
                        sql_progress = cursor.fetchall()
                        for row in sql_progress:
                            progress_entry = {
                                "date": row[0],
                                "completed_activities": row[1],
                                "total_activities": row[2],
                                "satisfaction_level": row[3],
                                "notes": row[4],
                                "challenges": row[5],
                                "source": "SQL"
                            }
                            progress_entries.append(progress_entry)
                            
            except Exception as e:
                pass  # Silently continue if SQL is not available
            
            # Display progress entries
            if progress_entries:
                # Sort by date (newest first) and show last 5
                progress_entries.sort(key=lambda x: x.get('date', ''), reverse=True)
                recent_progress = progress_entries[:5]
                
                for progress in recent_progress:
                    date_str = progress.get('date', 'Unknown date')
                    notes = progress.get('notes', 'No notes')
                    satisfaction = progress.get('satisfaction_level', 'N/A')
                    completed = progress.get('completed_activities', 'N/A')
                    total = progress.get('total_activities', 'N/A')
                    
                    st.write(f"• **{date_str}**: {notes}")
                    if satisfaction != 'N/A':
                        st.caption(f"  Satisfaction: {satisfaction}/10 | Completed: {completed}/{total} activities")
                    
                if len(progress_entries) > 5:
                    st.caption(f"... and {len(progress_entries) - 5} more entries")
            else:
                st.write("❓ No progress recorded yet - log your first progress entry!")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                show_progress_button = st.button(f"📝 Log Progress", key=f"progress_{plan.created_date}_{plan.plan_type}")
            
            with col2:
                if st.button(f"📋 View Full Routine", key=f"view_{plan.created_date}_{plan.plan_type}"):
                    show_full_routine_details(plan)
            
            with col3:
                update_routine_button = st.button(f"🔄 Update Routine", key=f"update_{plan.created_date}_{plan.plan_type}")
                if update_routine_button:
                    update_routine_plan(user_id, plan)
            
            # Show progress form when button is clicked
            if show_progress_button:
                show_progress_logging_form(user_id, plan)

def show_progress_logging_form(user_id, plan):
    """Show form for logging progress on routine"""
    st.markdown("#### 📝 Log Your Progress")
    
    with st.form(f"progress_form_{plan.created_date}_{plan.plan_type}"):
        progress_notes = st.text_area("How did today go with your routine?", height=100)
        completed_activities = st.number_input("Activities completed today", min_value=0, max_value=len(plan.daily_schedule), value=0)
        satisfaction_level = st.slider("Satisfaction with today's progress", 1, 10, 5)
        challenges = st.text_area("Any challenges or difficulties?", height=60)
        
        if st.form_submit_button("Save Progress"):
            progress_data = {
                "notes": progress_notes,
                "completed_activities": completed_activities,
                "satisfaction_level": satisfaction_level,
                "challenges": challenges,
                "total_activities": len(plan.daily_schedule),
                "log_date": date.today().isoformat()
            }
            
            # Try hybrid logging first, then fallback to original method
            try:
                # Generate plan_id based on plan attributes
                plan_id = getattr(plan, 'plan_id', f"{plan.plan_type}_{plan.created_date.isoformat()}")
                
                # Use hybrid logging
                result = log_progress_hybrid(user_id, plan_id, progress_data)
                
                if result["success"]:
                    st.success("Progress logged successfully! 🎉")
                    st.info(f"💾 Saved using: {'SQL Database' if 'SQL' in result['message'] else 'JSON Storage'}")
                    st.rerun()  # Refresh to show updated progress
                else:
                    # Fallback to original method
                    plan_key = f"{plan.plan_type}_{plan.created_date.isoformat()}"
                    success = update_routine_progress(user_id, plan_key, progress_data)
                    
                    if success:
                        st.success("Progress logged successfully! 🎉")
                        st.rerun()
                    else:
                        st.error("Failed to log progress. Please try again.")
                        
            except Exception as e:
                # Fallback to original method
                plan_key = f"{plan.plan_type}_{plan.created_date.isoformat()}"
                success = update_routine_progress(user_id, plan_key, progress_data)
                
                if success:
                    st.success("Progress logged successfully! 🎉")
                    st.rerun()
                else:
                    st.error(f"Failed to log progress: {str(e)}")

def update_routine_plan(user_id, plan):
    """Update/regenerate routine plan based on current user profile"""
    plan_type = plan.plan_type
    
    with st.spinner(f"🔄 Regenerating your {plan_type} routine..."):
        try:
            # Get current user profile
            user_profile = get_user_profile_hybrid(user_id)
            if not user_profile:
                # Fallback to session state profile
                user_profile = st.session_state.user_profile
            
            # Generate new routine using the generate_routine_plan function
            new_routine = generate_routine_plan(user_id, plan_type)
            
            if new_routine and hasattr(new_routine, 'daily_schedule'):
                # Update the existing plan with new routine data
                wellness_data = load_user_wellness_data(user_id)
                plan_key = f"{plan.plan_type}_{plan.created_date.isoformat()}"
                
                if "routine_plans" in wellness_data and plan_key in wellness_data["routine_plans"]:
                    # Convert Pydantic objects to dictionaries for JSON storage
                    daily_schedule_dicts = []
                    for item in new_routine.daily_schedule:
                        if hasattr(item, 'dict'):
                            daily_schedule_dicts.append(item.dict())
                        elif isinstance(item, dict):
                            daily_schedule_dicts.append(item)
                        else:
                            # Handle string representation by parsing it
                            daily_schedule_dicts.append({
                                "time": str(getattr(item, 'time', '')),
                                "activity": str(getattr(item, 'activity', '')),
                                "duration": getattr(item, 'duration', 30),
                                "flexible": getattr(item, 'flexible', False)
                            })
                    
                    weekly_schedule_dicts = []
                    weekly_schedule = getattr(new_routine, 'weekly_schedule', [])
                    for item in weekly_schedule:
                        if hasattr(item, 'dict'):
                            weekly_schedule_dicts.append(item.dict())
                        elif isinstance(item, dict):
                            weekly_schedule_dicts.append(item)
                        else:
                            weekly_schedule_dicts.append(item)
                    
                    # Update the existing plan with properly formatted data
                    wellness_data["routine_plans"][plan_key]["daily_schedule"] = daily_schedule_dicts
                    wellness_data["routine_plans"][plan_key]["weekly_schedule"] = weekly_schedule_dicts
                    wellness_data["routine_plans"][plan_key]["last_updated"] = datetime.datetime.now().isoformat()
                    wellness_data["routine_plans"][plan_key]["version"] = wellness_data["routine_plans"][plan_key].get("version", 1) + 1
                    
                    # Save updated plan
                    save_user_wellness_data(wellness_data, user_id)
                    
                    # Also update in SQL if available
                    try:
                        if hasattr(new_routine, 'title') and hasattr(new_routine, 'description'):
                            updated_plan_data = {
                                "title": new_routine.title,
                                "description": new_routine.description
                            }
                            plan_id = getattr(plan, 'plan_id', plan_key)
                            create_routine_plan_hybrid(user_id, updated_plan_data)
                    except:
                        pass  # SQL update is optional
                    
                    st.success("✅ Routine updated successfully!")
                    st.info("🔄 Your routine has been regenerated based on your current profile")
                    st.balloons()
                    
                    # Force refresh to show updated routine
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Could not find routine plan to update")
            else:
                st.error("Failed to generate new routine. Please try again later.")
                
        except Exception as e:
            st.error(f"Error updating routine: {str(e)}")
            st.info("💬 You can also chat with the agent to request manual routine updates")

def show_full_routine_details(plan):
    """Show complete routine details in a modal-like display"""
    st.markdown(f"#### 📋 Complete {plan.plan_type.title()} Routine")
    st.markdown(f"**Created:** {plan.created_date}")
    
    # Daily Schedule
    if plan.daily_schedule:
        st.markdown("#### 📅 Daily Schedule")
        for item in plan.daily_schedule:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 4, 2, 2])
                with col1:
                    st.write(f"**{item.time}**")
                with col2:
                    st.write(item.activity)
                with col3:
                    st.write(f"{item.duration} min")
                with col4:
                    priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.priority, "⚪")
                    st.write(f"{priority_color} {item.priority}")
                
                if item.instructions:
                    st.caption(f"📝 {item.instructions}")
                st.markdown("---")
    
    # Weekly Goals
    if plan.weekly_goals:
        st.markdown("#### 🎯 Weekly Goals")
        for goal in plan.weekly_goals:
            st.write(f"**{goal.goal}**")
            if goal.target_metric:
                st.write(f"Target: {goal.target_metric}")
            if goal.progress_tracking:
                st.write(f"Tracking: {goal.progress_tracking}")
            if goal.reward:
                st.write(f"Reward: {goal.reward}")
            st.markdown("---")
    
    # Emergency Strategies
    if plan.emergency_strategies:
        st.markdown("#### 🚨 Emergency/Crisis Strategies")
        for strategy in plan.emergency_strategies:
            st.write(f"• {strategy}")
    
    # Motivational Elements
    if plan.motivational_quotes:
        st.markdown("#### 💪 Motivational Reminders")
        for quote in plan.motivational_quotes[:3]:  # Show first 3
            st.info(f"💭 {quote}")

def main():
    initialize_session_state()
    
    # Check authentication state
    if not st.session_state.authenticated:
        show_login_page()
    elif st.session_state.show_edit_profile:
        show_edit_profile_page()
    elif st.session_state.show_daily_update:
        show_daily_update_page()
    else:
        # Show main layout - sidebar only for chat
        show_main_layout()

if __name__ == "__main__":
    main()