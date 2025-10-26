from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from prompts import (mental_health_prompt, diet_prompt, exercise_prompt, router_prompt, 
                     language_safety_prompt, ner_prompt, mental_health_ner_prompt, 
                     diet_ner_prompt, exercise_ner_prompt, mental_health_routine_prompt,
                     diet_routine_prompt, exercise_routine_prompt)
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict, Literal, Annotated, Optional
from pydantic import Field, BaseModel
from dotenv import load_dotenv
import operator
import json
import sqlite3
from datetime import datetime, date
import os
import re
import hashlib

# Import SQL database functions (with fallback to JSON)
try:
    from database import (
        init_database, create_user_sql, get_user_sql, update_user_last_active_sql,
        create_user_profile_sql, get_user_profile_sql, log_health_data_sql,
        get_user_health_history_sql, create_session_sql, update_session_sql,
        get_user_sessions_sql, get_db_connection
    )
    SQL_AVAILABLE = True
    # Initialize database on import
    init_database()
    print("✓ SQL Database initialized successfully")
except ImportError:
    SQL_AVAILABLE = False
    print("⚠ SQL Database not available, using JSON fallback")

load_dotenv()

WELLNESS_DATA_DIR = "wellness_data"
USERS_DATA_FILE = "users_data.json"

# Hybrid data mode configuration
USE_SQL_FOR_STRUCTURED = SQL_AVAILABLE  # User data, profiles, health data, sessions
USE_JSON_FOR_CONVERSATIONS = True       # NER entities, conversation history

model = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, max_tokens=2000)
router_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, max_tokens=50)

# Custom Message classes with timestamps
class TimestampedHumanMessage(HumanMessage):
    timestamp: datetime = Field(default_factory=datetime.now)

class TimestampedAIMessage(AIMessage):
    timestamp: datetime = Field(default_factory=datetime.now)

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    time_stamps: Annotated[list[datetime], operator.add]
    ner_entities: Annotated[list[str], operator.add]
    chat_response: str
    current_user: str
    current_agent: str
    user_context: dict

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

# Agent-Specific Entity Models

# Mental Health Entities
class MentalHealthPerson(BaseModel):
    """Person mentioned in mental health context"""
    name: str = Field(description="Full name of the person mentioned")
    relationship: str = Field(description="Relationship to user (therapist, family member, friend, partner, colleague, etc.)")
    emotional_impact: Literal["supportive", "triggering", "neutral", "conflicted"] = Field(description="How this person affects user's mental state")
    support_level: Literal["high", "medium", "low", "negative"] = Field(description="Level of support this person provides")
    interaction_context: str = Field(description="Context of recent interactions or ongoing relationship dynamics", default="")

class MentalHealthCondition(BaseModel):
    """Mental health condition or symptom"""
    condition: str = Field(description="Specific condition mentioned (anxiety, depression, stress, panic, PTSD, etc.)")
    severity: Literal["mild", "moderate", "severe", "crisis"] = Field(description="User's perceived severity")
    symptoms: list[str] = Field(default_factory=list, description="Specific symptoms described")
    triggers: list[str] = Field(default_factory=list, description="What triggers this condition")
    duration: str = Field(description="How long user has experienced this", default="")
    impact_on_daily_life: str = Field(description="How it affects daily functioning", default="")

class CopingStrategy(BaseModel):
    """Coping method or strategy"""
    strategy: str = Field(description="Specific coping method (meditation, therapy, exercise, journaling, etc.)")
    effectiveness: Literal["very_effective", "somewhat_effective", "not_effective"] = Field(description="How well it works for the user")
    frequency: str = Field(description="How often user employs this strategy", default="")
    context: str = Field(description="When or where this strategy is used", default="")
    barriers: list[str] = Field(default_factory=list, description="What prevents consistent use")

class EmotionalState(BaseModel):
    """Current or recent emotional state"""
    emotion: str = Field(description="Primary emotion (anxious, depressed, hopeful, angry, overwhelmed, etc.)")
    intensity: str = Field(description="Strength of emotion (1-10 scale if mentioned, or mild/moderate/intense)", default="")
    duration: str = Field(description="How long this emotional state has persisted", default="")
    situation_context: str = Field(description="What situation triggered this emotional state", default="")
    physical_manifestations: list[str] = Field(default_factory=list, description="Physical symptoms accompanying the emotion")

class TherapeuticGoal(BaseModel):
    """Mental health goal or objective"""
    goal: str = Field(description="Specific mental health goal (reduce anxiety, improve sleep, build confidence, etc.)")
    timeline: str = Field(description="Desired timeline for achieving goal", default="")
    progress: str = Field(description="Current progress toward goal", default="")
    obstacles: list[str] = Field(default_factory=list, description="What's preventing progress")
    support_needed: str = Field(description="What kind of support would help achieve this goal", default="")

class MentalHealthEntities(BaseModel):
    people: list[MentalHealthPerson] = Field(default_factory=list)
    conditions: list[MentalHealthCondition] = Field(default_factory=list)
    coping_strategies: list[CopingStrategy] = Field(default_factory=list)
    emotional_states: list[EmotionalState] = Field(default_factory=list)
    therapeutic_goals: list[TherapeuticGoal] = Field(default_factory=list)

# Diet and Nutrition Entities
class DietFoodItem(BaseModel):
    """Food item mentioned in diet context"""
    item: str = Field(description="Specific food or dish mentioned (biryani, daal, chicken, apple, etc.)")
    quantity: str = Field(description="Amount consumed or planned (1 cup, 2 rotis, 200g, etc.)", default="")
    meal_context: str = Field(description="Which meal (breakfast, lunch, dinner, snack, pre-workout, etc.)", default="")
    preparation_method: str = Field(description="How it's prepared (fried, grilled, boiled, raw, etc.)", default="")
    nutritional_intent: str = Field(description="Why this food was chosen (protein, energy, craving, convenience, etc.)", default="")
    satisfaction_level: Literal["very_satisfied", "satisfied", "still_hungry", "too_full", "unknown"] = Field(description="How satisfied user felt after eating", default="unknown")

class NutritionalGoal(BaseModel):
    """Nutrition-related goal"""
    goal: str = Field(description="Specific nutrition goal (weight loss, muscle gain, energy increase, better digestion, etc.)")
    target_timeline: str = Field(description="When user wants to achieve this", default="")
    current_challenge: str = Field(description="What's making this goal difficult", default="")
    preferred_approach: str = Field(description="User's preference (gradual changes, strict plan, flexible approach, etc.)", default="")
    motivation_level: Literal["very_motivated", "somewhat_motivated", "struggling"] = Field(description="How motivated user feels", default="somewhat_motivated")

class EatingPattern(BaseModel):
    """Eating behavior pattern"""
    pattern: str = Field(description="Specific eating behavior (intermittent fasting, late night eating, skipping meals, etc.)")
    frequency: str = Field(description="How often this pattern occurs", default="")
    triggers: list[str] = Field(default_factory=list, description="What causes this eating pattern (stress, boredom, work schedule, etc.)")
    impact: str = Field(description="How this pattern affects user (energy levels, weight, mood, etc.)", default="")
    desire_to_change: bool = Field(description="Whether user wants to modify this pattern", default=False)

class DietaryRestriction(BaseModel):
    """Dietary restriction or limitation"""
    restriction: str = Field(description="Specific restriction (vegetarian, diabetic, low-sodium, halal, etc.)")
    reason: str = Field(description="Why this restriction exists (health, religious, personal choice, etc.)", default="")
    strictness: Literal["always", "mostly", "sometimes", "struggling"] = Field(description="How strictly user follows it", default="mostly")
    challenges: list[str] = Field(default_factory=list, description="Difficulties in maintaining this restriction")
    support_needed: str = Field(description="What would help maintain this restriction", default="")

class MealPlan(BaseModel):
    """Meal planning information"""
    meal_type: str = Field(description="Type of meal planning (daily prep, weekly prep, specific event, etc.)")
    preparation_time: str = Field(description="Available time for meal prep", default="")
    budget_constraint: str = Field(description="Budget considerations for meals", default="")
    cooking_skill: Literal["beginner", "intermediate", "advanced"] = Field(description="User's cooking ability level", default="intermediate")
    equipment_available: list[str] = Field(default_factory=list, description="Kitchen equipment and resources available")
    family_considerations: str = Field(description="Needs to consider family members' preferences", default="")

class BodyResponse(BaseModel):
    """Physical response to food"""
    response: str = Field(description="Physical response to food (bloating, energy boost, allergic reaction, etc.)")
    food_trigger: str = Field(description="Which food(s) caused this response", default="")
    timing: str = Field(description="When this response occurs (immediately, after 30 minutes, hours later, etc.)", default="")
    severity: Literal["mild", "moderate", "severe"] = Field(description="How severe the response is", default="mild")
    pattern: bool = Field(description="If this is a recurring response to certain foods", default=False)

class DietEntities(BaseModel):
    food_items: list[DietFoodItem] = Field(default_factory=list)
    nutritional_goals: list[NutritionalGoal] = Field(default_factory=list)
    eating_patterns: list[EatingPattern] = Field(default_factory=list)
    dietary_restrictions: list[DietaryRestriction] = Field(default_factory=list)
    meal_plans: list[MealPlan] = Field(default_factory=list)
    body_responses: list[BodyResponse] = Field(default_factory=list)

# Exercise and Fitness Entities
class ExerciseActivity(BaseModel):
    """Exercise or physical activity"""
    activity: str = Field(description="Specific exercise or sport (push-ups, running, cricket, yoga, gym workout, etc.)")
    duration: str = Field(description="How long the activity lasted or is planned", default="")
    intensity: Literal["light", "moderate", "vigorous", "maximum_effort"] = Field(description="Level of exertion", default="moderate")
    sets_reps: str = Field(description="Number of sets and repetitions if applicable", default="")
    equipment_used: list[str] = Field(default_factory=list, description="Equipment needed or used")
    location: str = Field(description="Where exercise takes place (home, gym, park, office, etc.)", default="")
    completion_status: Literal["completed", "planned", "partially_done", "skipped"] = Field(description="Whether completed, planned, or partially done", default="planned")

class FitnessGoal(BaseModel):
    """Fitness objective or goal"""
    goal: str = Field(description="Specific fitness objective (weight loss, muscle gain, endurance, flexibility, etc.)")
    target_metric: str = Field(description="Measurable target (lose 10kg, run 5km, do 50 push-ups, etc.)", default="")
    timeline: str = Field(description="Desired timeframe for achievement", default="")
    current_level: str = Field(description="Present fitness level or ability", default="")
    motivation: str = Field(description="Primary reason for this goal", default="")
    progress_tracking: str = Field(description="How user measures progress", default="")

class PhysicalLimitation(BaseModel):
    """Physical constraint or limitation"""
    limitation: str = Field(description="Specific limitation (knee pain, back issues, lack of equipment, time constraints, etc.)")
    severity: Literal["minor_inconvenience", "significant_barrier", "complete_prevention"] = Field(description="How much this limits activity", default="minor_inconvenience")
    affected_activities: list[str] = Field(default_factory=list, description="Which exercises are impacted")
    management_strategy: str = Field(description="How user works around this limitation", default="")
    professional_guidance: bool = Field(description="Whether medical/professional advice was sought", default=False)

class WorkoutPreference(BaseModel):
    """Exercise preferences and constraints"""
    preference: str = Field(description="Specific preference (morning workouts, home exercises, group activities, etc.)")
    reasoning: str = Field(description="Why user prefers this approach", default="")
    flexibility: Literal["very_flexible", "somewhat_flexible", "not_flexible"] = Field(description="How willing user is to try alternatives", default="somewhat_flexible")
    time_availability: str = Field(description="When user can typically exercise", default="")
    social_aspect: Literal["solo", "group", "both", "no_preference"] = Field(description="Preference for solo or group activities", default="no_preference")

class PhysicalResponse(BaseModel):
    """Body's response to exercise"""
    response: str = Field(description="Body's response to exercise (muscle soreness, increased energy, fatigue, etc.)")
    exercise_trigger: str = Field(description="Which specific exercise caused this response", default="")
    timing: str = Field(description="When response occurs (during, immediately after, next day, etc.)", default="")
    impact: str = Field(description="How this affects subsequent workouts or daily activities", default="")
    recovery_method: str = Field(description="How user deals with this response", default="")

class FitnessEnvironment(BaseModel):
    """Exercise environment and resources"""
    location: str = Field(description="Exercise location (home gym, commercial gym, park, office, etc.)", default="")
    equipment_available: list[str] = Field(default_factory=list, description="Available equipment and resources")
    space_constraints: str = Field(description="Physical space limitations", default="")
    time_constraints: str = Field(description="Available time slots for exercise", default="")
    weather_considerations: str = Field(description="How weather affects exercise plans", default="")
    social_support: str = Field(description="Workout partners or family support", default="")

class PerformanceMetric(BaseModel):
    """Performance tracking information"""
    metric: str = Field(description="What user tracks (weight, reps, distance, time, calories, etc.)")
    current_value: str = Field(description="Present measurement", default="")
    target_value: str = Field(description="Goal measurement", default="")
    tracking_method: str = Field(description="How measurement is recorded", default="")
    progress_trend: Literal["improving", "maintaining", "declining", "unknown"] = Field(description="Whether improving, maintaining, or declining", default="unknown")
    frequency: str = Field(description="How often measurements are taken", default="")

class ExerciseEntities(BaseModel):
    activities: list[ExerciseActivity] = Field(default_factory=list)
    fitness_goals: list[FitnessGoal] = Field(default_factory=list)
    physical_limitations: list[PhysicalLimitation] = Field(default_factory=list)
    workout_preferences: list[WorkoutPreference] = Field(default_factory=list)
    physical_responses: list[PhysicalResponse] = Field(default_factory=list)
    fitness_environments: list[FitnessEnvironment] = Field(default_factory=list)
    performance_metrics: list[PerformanceMetric] = Field(default_factory=list)

# Routine Management Models
class DailyScheduleItem(BaseModel):
    """Individual item in daily schedule"""
    time: str = Field(description="Time slot (e.g., '07:00', '14:30')")
    activity: str = Field(description="Activity name or description")
    duration: int = Field(description="Duration in minutes")
    category: Literal["mental_health", "diet", "exercise", "general"] = Field(description="Wellness category")
    priority: Literal["high", "medium", "low"] = Field(description="Priority level", default="medium")
    instructions: str = Field(description="Detailed instructions or notes", default="")
    flexible: bool = Field(description="Whether timing can be adjusted", default=True)

class WeeklyGoal(BaseModel):
    """Weekly goal or milestone"""
    goal: str = Field(description="Specific weekly goal")
    category: Literal["mental_health", "diet", "exercise", "general"] = Field(description="Wellness category")
    target_metric: str = Field(description="How success is measured", default="")
    progress_tracking: str = Field(description="How to track progress", default="")
    reward: str = Field(description="Reward for achieving goal", default="")

class RoutinePlan(BaseModel):
    """Complete routine plan for user"""
    user_id: str
    plan_type: Literal["mental_health", "diet", "exercise", "comprehensive"] = Field(description="Type of routine plan")
    created_date: date = Field(default_factory=date.today)
    
    # Daily structure
    daily_schedule: list[DailyScheduleItem] = Field(default_factory=list)
    
    # Weekly structure
    weekly_goals: list[WeeklyGoal] = Field(default_factory=list)
    
    # Emergency/Crisis strategies
    emergency_strategies: list[str] = Field(default_factory=list)
    
    # Progress tracking
    tracking_methods: list[str] = Field(default_factory=list)
    
    # Personalized elements
    motivational_quotes: list[str] = Field(default_factory=list)
    cultural_adaptations: list[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    active: bool = Field(default=True)

# User Profile Models for Wellness Assistant
class UserProfile(BaseModel):
    # Basic Info
    full_name: str
    age: int
    gender: Literal["Male", "Female", "Other"]
    email: str
    password_hash: str
    
    # Physical & Lifestyle Info
    height: float  # in cm
    current_weight: float  # in kg
    target_weight: float  # in kg
    activity_level: Literal["sedentary", "lightly_active", "moderately_active", "very_active"]
    diet_type: Literal["vegetarian", "non_vegetarian", "keto", "low_carb", "balanced", "other"]
    favorite_foods: list[str] = Field(default_factory=list)
    
    # Health Background
    common_issues: list[str] = Field(default_factory=list)  # stress, anxiety, fatigue, etc.
    medical_conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    
    # Daily Inputs (updated regularly)
    daily_stress_level: int = Field(default=3, ge=1, le=5)
    wake_up_time: str = Field(default="07:00")
    sleep_time: str = Field(default="23:00") 
    workout_duration_preference: int = Field(default=30)  # minutes
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    preferred_agent: str = Field(default="MENTAL_HEALTH")

class DailyLog(BaseModel):
    user_id: str
    date: date
    stress_level: int
    wake_up_time: str
    sleep_time: str
    meals_logged: list[dict] = Field(default_factory=list)
    workouts_completed: list[dict] = Field(default_factory=list)
    mental_health_notes: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)

os.makedirs(WELLNESS_DATA_DIR, exist_ok=True)
# Authentication and User Management Functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def validate_email(email: str) -> bool:
    """Basic email validation"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

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

def create_user_profile(profile_data: dict) -> dict:
    """Create a new user profile for wellness assistant"""
    try:
        # Validate required fields
        required_fields = ['full_name', 'age', 'gender', 'email', 'password', 'height', 'current_weight', 'target_weight']
        for field in required_fields:
            if field not in profile_data or not profile_data[field]:
                return {"success": False, "message": f"Missing required field: {field}"}
        
        # Validate email format
        if not validate_email(profile_data['email']):
            return {"success": False, "message": "Invalid email format"}
        
        users_data = load_users_data()
        
        # Check if email already exists
        for user_id, user_info in users_data.items():
            if user_info.get("email") == profile_data['email']:
                return {"success": False, "message": "User with this email already exists"}
        
        # Create new user ID
        user_id = f"user_{len(users_data) + 1:04d}"
        
        # Create user profile
        user_profile = {
            "user_id": user_id,
            "full_name": profile_data['full_name'].strip().title(),
            "age": int(profile_data['age']),
            "gender": profile_data['gender'],
            "email": profile_data['email'].lower(),
            "password_hash": hash_password(profile_data['password']),
            "height": float(profile_data['height']),
            "current_weight": float(profile_data['current_weight']),
            "target_weight": float(profile_data['target_weight']),
            "activity_level": profile_data.get('activity_level', 'moderately_active'),
            "diet_type": profile_data.get('diet_type', 'balanced'),
            "favorite_foods": profile_data.get('favorite_foods', []),
            "common_issues": profile_data.get('common_issues', []),
            "medical_conditions": profile_data.get('medical_conditions', []),
            "medications": profile_data.get('medications', []),
            "daily_stress_level": int(profile_data.get('daily_stress_level', 3)),
            "wake_up_time": profile_data.get('wake_up_time', '07:00'),
            "sleep_time": profile_data.get('sleep_time', '23:00'),
            "workout_duration_preference": int(profile_data.get('workout_duration_preference', 30)),
            "preferred_agent": profile_data.get('preferred_agent', 'MENTAL_HEALTH'),
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        
        users_data[user_id] = user_profile
        save_users_data(users_data)
        
        # Initialize wellness data for new user
        initialize_user_wellness_data(user_id)
        
        return {"success": True, "message": f"User profile created successfully", "user_id": user_id}
        
    except Exception as e:
        return {"success": False, "message": f"Error creating user profile: {str(e)}"}

def authenticate_user(email: str, password: str) -> dict:
    """Authenticate user login"""
    users_data = load_users_data()
    
    for user_id, user_info in users_data.items():
        if user_info.get("email") == email.lower():
            if verify_password(password, user_info.get("password_hash", "")):
                # Update last active
                user_info["last_active"] = datetime.now().isoformat()
                users_data[user_id] = user_info
                save_users_data(users_data)
                
                return {
                    "success": True, 
                    "message": "Authentication successful", 
                    "user_id": user_id,
                    "user_name": user_info.get("full_name", "User")
                }
            else:
                return {"success": False, "message": "Invalid password"}
    
    return {"success": False, "message": "User not found"}

def update_daily_inputs(user_id: str, daily_data: dict) -> dict:
    """Update user's daily inputs"""
    try:
        users_data = load_users_data()
        
        if user_id not in users_data:
            return {"success": False, "message": "User not found"}
        
        user_profile = users_data[user_id]
        
        # Update daily fields
        if 'daily_stress_level' in daily_data:
            user_profile['daily_stress_level'] = int(daily_data['daily_stress_level'])
        if 'stress_level' in daily_data:  # Backwards compatibility
            user_profile['daily_stress_level'] = int(daily_data['stress_level'])
        if 'wake_up_time' in daily_data:
            user_profile['wake_up_time'] = daily_data['wake_up_time']
        if 'sleep_time' in daily_data:
            user_profile['sleep_time'] = daily_data['sleep_time']
        if 'current_weight' in daily_data:
            user_profile['current_weight'] = float(daily_data['current_weight'])
        if 'workout_duration_preference' in daily_data:
            user_profile['workout_duration_preference'] = int(daily_data['workout_duration_preference'])
        
        user_profile['last_active'] = datetime.now().isoformat()
        users_data[user_id] = user_profile
        save_users_data(users_data)
        
        return {"success": True, "message": "Daily inputs updated successfully"}
        
    except Exception as e:
        return {"success": False, "message": f"Error updating daily inputs: {str(e)}"}

def update_user_profile(user_id: str, profile_data: dict) -> dict:
    """Update user's profile information"""
    try:
        users_data = load_users_data()
        
        if user_id not in users_data:
            return {"success": False, "message": "User not found"}
        
        user_profile = users_data[user_id]
        
        # Update profile fields (only allow specific fields to be updated)
        allowed_fields = [
            'full_name', 'email', 'age', 'gender', 'height', 'target_weight',
            'activity_level', 'diet_type', 'favorite_foods', 'common_issues',
            'medical_conditions', 'medications', 'dietary_restrictions',
            'fitness_goals', 'preferred_workout_types'
        ]
        
        for field, value in profile_data.items():
            if field in allowed_fields:
                if field in ['age', 'height']:
                    user_profile[field] = int(value) if value else user_profile.get(field, 0)
                elif field in ['target_weight']:
                    user_profile[field] = float(value) if value else user_profile.get(field, 0.0)
                elif field in ['favorite_foods', 'common_issues', 'medical_conditions', 
                              'medications', 'dietary_restrictions', 'preferred_workout_types']:
                    # Handle list fields
                    if isinstance(value, list):
                        user_profile[field] = value
                    elif isinstance(value, str):
                        user_profile[field] = [item.strip() for item in value.split(',') if item.strip()]
                    else:
                        user_profile[field] = []
                else:
                    user_profile[field] = value
        
        user_profile['last_active'] = datetime.now().isoformat()
        users_data[user_id] = user_profile
        save_users_data(users_data)
        
        return {"success": True, "message": "Profile updated successfully"}
        
    except Exception as e:
        return {"success": False, "message": f"Error updating profile: {str(e)}"}

def get_user_info(user_id: str) -> dict:
    """Get user information"""
    users_data = load_users_data()
    return users_data.get(user_id, {})

# Legacy functions for compatibility
def validate_cnic(cnic: str) -> bool:
    """Validate CNIC format (13 digits) - Legacy function"""
    cnic_cleaned = re.sub(r'[-\s]', '', cnic)
    return len(cnic_cleaned) == 13 and cnic_cleaned.isdigit()

def format_cnic(cnic: str) -> str:
    """Format CNIC as XXXXX-XXXXXXX-X - Legacy function"""
    cnic_cleaned = re.sub(r'[-\s]', '', cnic)
    if len(cnic_cleaned) == 13:
        return f"{cnic_cleaned[:5]}-{cnic_cleaned[5:12]}-{cnic_cleaned[12]}"
    return cnic

# ===== HYBRID USER MANAGEMENT (SQL + JSON) =====

def add_user_hybrid(name: str, cnic: str, email: str = None, phone: str = None) -> dict:
    """Add a new user using hybrid SQL/JSON approach"""
    if not validate_cnic(cnic):
        return {"success": False, "message": "Invalid CNIC format. Must be 13 digits."}
    
    formatted_cnic = format_cnic(cnic)
    
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        # Use SQL database
        try:
            # Generate user ID
            user_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            user_data = {
                "user_id": user_id,
                "full_name": name.strip().title(),
                "cnic": formatted_cnic,
                "email": email,
                "phone": phone
            }
            
            result = create_user_sql(user_data)
            if result["success"]:
                # Initialize JSON data for conversations
                initialize_user_wellness_data(user_id)
                return {"success": True, "message": f"User {name} added successfully.", "user_id": user_id}
            else:
                return result
                
        except Exception as e:
            # Fallback to JSON
            return add_user_json_fallback(name, formatted_cnic)
    else:
        # Use JSON fallback
        return add_user_json_fallback(name, formatted_cnic)

def add_user_json_fallback(name: str, formatted_cnic: str) -> dict:
    """JSON fallback for adding users"""
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
    initialize_user_wellness_data(user_id)
    
    return {"success": True, "message": f"User {name} added successfully.", "user_id": user_id}

def get_user_hybrid(user_id: str) -> dict:
    """Get user information using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            user_data = get_user_sql(user_id)
            if user_data:
                return user_data
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback
    users_data = load_users_data()
    return users_data.get(user_id, {})

def get_all_users_hybrid() -> dict:
    """Get all users using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE is_active = TRUE")
                rows = cursor.fetchall()
                
                users_dict = {}
                for row in rows:
                    user_data = dict(row)
                    users_dict[user_data["user_id"]] = user_data
                
                return users_dict
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback
    return load_users_data()

def update_user_last_active_hybrid(user_id: str):
    """Update user's last active timestamp using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            update_user_last_active_sql(user_id)
            return
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback
    users_data = load_users_data()
    if user_id in users_data:
        users_data[user_id]["last_active"] = datetime.now().isoformat()
        save_users_data(users_data)

def search_user_by_cnic_hybrid(cnic: str) -> str:
    """Search user by CNIC using hybrid approach"""
    if not validate_cnic(cnic):
        return None
    
    formatted_cnic = format_cnic(cnic)
    
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE cnic = ? AND is_active = TRUE", (formatted_cnic,))
                row = cursor.fetchone()
                return row["user_id"] if row else None
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback
    users_data = load_users_data()
    for user_id, user_info in users_data.items():
        if user_info.get("cnic") == formatted_cnic:
            return user_id
    return None

# ===== LEGACY FUNCTIONS (for backward compatibility) =====

def add_user(name: str, cnic: str) -> dict:
    """Add a new user - Legacy function"""
    return add_user_hybrid(name, cnic)

# ===== HYBRID PROFILE MANAGEMENT =====

def create_user_profile_hybrid(user_id: str, profile_data: dict) -> dict:
    """Create or update user profile using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            profile_data["user_id"] = user_id
            result = create_user_profile_sql(profile_data)
            if result["success"]:
                return result
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback - use existing function
    return update_user_profile(user_id, profile_data)

def get_user_profile_hybrid(user_id: str) -> dict:
    """Get user profile using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            profile_data = get_user_profile_sql(user_id)
            if profile_data:
                return profile_data
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback
    wellness_data = load_user_wellness_data(user_id)
    return wellness_data.get("profile", {})

# ===== HYBRID HEALTH DATA MANAGEMENT =====

def log_daily_health_data_hybrid(user_id: str, health_data: dict) -> dict:
    """Log daily health data using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            health_data["user_id"] = user_id
            if "date" not in health_data:
                health_data["date"] = date.today().isoformat()
            
            result = log_health_data_sql(health_data)
            if result["success"]:
                return result
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback - add to user's wellness data
    try:
        wellness_data = load_user_wellness_data(user_id)
        if "health_logs" not in wellness_data:
            wellness_data["health_logs"] = {}
        
        log_date = health_data.get("date", date.today().isoformat())
        wellness_data["health_logs"][log_date] = health_data
        
        save_user_wellness_data(wellness_data, user_id)
        return {"success": True, "message": "Health data logged successfully (JSON)"}
    except Exception as e:
        return {"success": False, "message": f"Error logging health data: {str(e)}"}

def get_user_health_history_hybrid(user_id: str, days: int = 30) -> list:
    """Get user's health history using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            return get_user_health_history_sql(user_id, days)
        except Exception as e:
            print(f"SQL error, falling back to JSON: {e}")
    
    # JSON fallback
    try:
        wellness_data = load_user_wellness_data(user_id)
        health_logs = wellness_data.get("health_logs", {})
        
        # Convert to list format and sort by date
        health_history = []
        for log_date, log_data in health_logs.items():
            log_data["date"] = log_date
            health_history.append(log_data)
        
        # Sort by date (newest first) and limit
        health_history.sort(key=lambda x: x["date"], reverse=True)
        return health_history[:days]
    except Exception as e:
        print(f"Error getting health history: {e}")
        return []

# ===== HYBRID SESSION MANAGEMENT =====

def create_session_hybrid(user_id: str, session_id: str, agent_type: str) -> dict:
    """Create a new session using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "agent_type": agent_type,
                "start_time": datetime.now()
            }
            result = create_session_sql(session_data)
            if result["success"]:
                return result
        except Exception as e:
            print(f"SQL session creation error, using JSON: {e}")
    
    # JSON fallback - sessions are handled in wellness data
    return {"success": True, "message": "Session will be created in JSON format"}

def update_session_hybrid(session_id: str, user_id: str, update_data: dict) -> dict:
    """Update session using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            result = update_session_sql(session_id, update_data)
            if result["success"]:
                return result
        except Exception as e:
            print(f"SQL session update error: {e}")
    
    # JSON fallback - update in wellness data if needed
    return {"success": True, "message": "Session updated in JSON format"}

def get_user_sessions_hybrid(user_id: str, agent_type: str = None) -> list:
    """Get user sessions using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            return get_user_sessions_sql(user_id, agent_type)
        except Exception as e:
            print(f"SQL sessions retrieval error, falling back to JSON: {e}")
    
    # JSON fallback
    try:
        wellness_data = load_user_wellness_data(user_id)
        sessions = wellness_data.get("sessions", {})
        
        session_list = []
        for session_id, session_data in sessions.items():
            if agent_type is None or session_data.get("agent_type") == agent_type:
                session_info = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_type": session_data.get("agent_type", "unknown"),
                    "created_at": session_data.get("created_at", ""),
                    "last_updated": session_data.get("last_updated", ""),
                    "total_messages": len(session_data.get("messages", []))
                }
                session_list.append(session_info)
        
        # Sort by last updated (newest first)
        session_list.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return session_list
    except Exception as e:
        print(f"Error getting sessions from JSON: {e}")
        return []

# ===== HYBRID ROUTINE MANAGEMENT =====

def create_routine_plan_hybrid(user_id: str, plan_data: dict) -> dict:
    """Create routine plan using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            # Generate plan ID if not provided
            if "plan_id" not in plan_data:
                plan_data["plan_id"] = f"plan_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            plan_data["user_id"] = user_id
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO routine_plans 
                    (plan_id, user_id, plan_type, title, description, start_date, end_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plan_data["plan_id"],
                    plan_data["user_id"],
                    plan_data.get("plan_type", "comprehensive"),
                    plan_data.get("title", ""),
                    plan_data.get("description", ""),
                    plan_data.get("start_date", date.today().isoformat()),
                    plan_data.get("end_date"),
                    plan_data.get("is_active", True)
                ))
                conn.commit()
            
            return {"success": True, "message": "Routine plan created successfully", "plan_id": plan_data["plan_id"]}
        except Exception as e:
            print(f"SQL routine creation error, falling back to JSON: {e}")
    
    # JSON fallback
    try:
        wellness_data = load_user_wellness_data(user_id)
        if "routine_plans" not in wellness_data:
            wellness_data["routine_plans"] = {}
        
        plan_id = plan_data.get("plan_id", f"plan_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        plan_data["plan_id"] = plan_id
        plan_data["created_at"] = datetime.now().isoformat()
        
        wellness_data["routine_plans"][plan_id] = plan_data
        save_user_wellness_data(wellness_data, user_id)
        
        return {"success": True, "message": "Routine plan created successfully (JSON)", "plan_id": plan_id}
    except Exception as e:
        return {"success": False, "message": f"Error creating routine plan: {str(e)}"}

def get_user_routine_plans_hybrid(user_id: str) -> list:
    """Get user's routine plans using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM routine_plans 
                    WHERE user_id = ? AND is_active = TRUE 
                    ORDER BY created_at DESC
                """, (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"SQL routine retrieval error, falling back to JSON: {e}")
    
    # JSON fallback
    try:
        wellness_data = load_user_wellness_data(user_id)
        routine_plans = wellness_data.get("routine_plans", {})
        
        plans_list = []
        for plan_id, plan_data in routine_plans.items():
            if plan_data.get("is_active", True):
                plans_list.append(plan_data)
        
        # Sort by created_at (newest first)
        plans_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return plans_list
    except Exception as e:
        print(f"Error getting routine plans from JSON: {e}")
        return []

def log_progress_hybrid(user_id: str, plan_id: str, progress_data: dict) -> dict:
    """Log progress using hybrid approach"""
    if USE_SQL_FOR_STRUCTURED and SQL_AVAILABLE:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO progress_logs 
                    (plan_id, user_id, log_date, completed_activities, total_activities, 
                     satisfaction_level, notes, challenges)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plan_id,
                    user_id,
                    progress_data.get("log_date", date.today().isoformat()),
                    progress_data.get("completed_activities", 0),
                    progress_data.get("total_activities", 0),
                    progress_data.get("satisfaction_level", 5),
                    progress_data.get("notes", ""),
                    progress_data.get("challenges", "")
                ))
                conn.commit()
            
            return {"success": True, "message": "Progress logged successfully"}
        except Exception as e:
            print(f"SQL progress logging error, falling back to JSON: {e}")
    
    # JSON fallback
    try:
        wellness_data = load_user_wellness_data(user_id)
        if "progress_logs" not in wellness_data:
            wellness_data["progress_logs"] = {}
        if plan_id not in wellness_data["progress_logs"]:
            wellness_data["progress_logs"][plan_id] = []
        
        progress_data["logged_at"] = datetime.now().isoformat()
        wellness_data["progress_logs"][plan_id].append(progress_data)
        
        save_user_wellness_data(wellness_data, user_id)
        return {"success": True, "message": "Progress logged successfully (JSON)"}
    except Exception as e:
        return {"success": False, "message": f"Error logging progress: {str(e)}"}

# ===== LEGACY FUNCTIONS (for backward compatibility) =====

def get_all_users() -> dict:
    """Get all users - Legacy function"""
    return get_all_users_hybrid()

def update_user_last_active(user_id: str):
    """Update user's last active timestamp - Legacy function"""
    update_user_last_active_hybrid(user_id)

def search_user_by_cnic(cnic: str) -> str:
    """Search user by CNIC and return user_id - Legacy function"""
    return search_user_by_cnic_hybrid(cnic)

def get_messages_with_timestamps_from_state(thread_id: str):
    """Extract messages with timestamps from SQLite state - Legacy compatibility"""
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

def get_user_ner_insights(user_id: str = "default_user"):
    """Get aggregated insights about entities mentioned across all user sessions"""
    try:
        # Load NER data directly from wellness data
        wellness_data = load_user_wellness_data(user_id)
        
        if not wellness_data or "sessions" not in wellness_data:
            return {
                "user_id": user_id,
                "total_people": 0,
                "total_places": 0,
                "total_events": 0,
                "total_substances": 0,
                "unique_people": [],
                "unique_places": [],
                "unique_events": [],
                "unique_substances": []
            }
        
        sessions = wellness_data["sessions"]
        
        # Aggregate entities from all sessions
        all_people = set()
        all_places = set()
        all_events = set()
        all_substances = set()
        
        for session_id, session_data in sessions.items():
            # Extract people
            for person in session_data.get("people", []):
                if isinstance(person, dict):
                    name = person.get("name", "")
                    if name:
                        all_people.add(name)
                else:
                    all_people.add(str(person))
            
            # Extract places
            for place in session_data.get("places", []):
                if isinstance(place, dict):
                    location = place.get("location") or place.get("name") or place.get("place", "")
                    if location:
                        all_places.add(location)
                else:
                    all_places.add(str(place))
            
            # Extract events
            for event in session_data.get("events", []):
                if isinstance(event, dict):
                    event_name = event.get("event") or event.get("name") or event.get("activity", "")
                    if event_name:
                        all_events.add(event_name)
                else:
                    all_events.add(str(event))
            
            # Extract substances
            for substance in session_data.get("substances", []):
                if isinstance(substance, dict):
                    substance_name = substance.get("substance") or substance.get("name", "")
                    if substance_name:
                        all_substances.add(substance_name)
                else:
                    all_substances.add(str(substance))
        
        return {
            "user_id": user_id,
            "total_people": len(all_people),
            "total_places": len(all_places),
            "total_events": len(all_events),
            "total_substances": len(all_substances),
            "unique_people": sorted(list(all_people)),
            "unique_places": sorted(list(all_places)),
            "unique_events": sorted(list(all_events)),
            "unique_substances": sorted(list(all_substances)),
            "total_sessions": len(sessions),
            "created_at": wellness_data.get("created_at"),
            "last_updated": wellness_data.get("last_updated")
        }
        
    except Exception as e:
        print(f"Error getting NER insights for user {user_id}: {e}")

def get_detailed_user_ner_insights(user_id: str = "default_user"):
    """Get detailed entity information with all attributes for conversation insights"""
    try:
        wellness_data = load_user_wellness_data(user_id)
        
        if not wellness_data or "sessions" not in wellness_data:
            return {
                "user_id": user_id,
                "detailed_people": [],
                "detailed_places": [],
                "detailed_events": [],
                "detailed_substances": [],
                "total_sessions": 0
            }
        
        sessions = wellness_data["sessions"]
        
        # Collect detailed entities from all sessions
        detailed_people = []
        detailed_places = []
        detailed_events = []
        detailed_substances = []
        
        # Track unique entities to avoid duplicates
        seen_people = set()
        seen_places = set()
        seen_events = set()
        seen_substances = set()
        
        for session_id, session_data in sessions.items():
            # Process people with full details
            for person in session_data.get("people", []):
                if isinstance(person, dict):
                    name = person.get("name", "")
                    if name and name not in seen_people:
                        detailed_people.append({
                            "name": name,
                            "relationship": person.get("relationship", "Unknown"),
                            "significance": person.get("significance", ""),
                            "emotional_charge": person.get("emotional_charge", "neutral"),
                            "timestamp": person.get("timestamp", ""),
                            "session_id": session_id
                        })
                        seen_people.add(name)
            
            # Process places with full details
            for place in session_data.get("places", []):
                if isinstance(place, dict):
                    location = place.get("location") or place.get("name") or place.get("place", "")
                    if location and location not in seen_places:
                        detailed_places.append({
                            "location": location,
                            "context": place.get("context", ""),
                            "emotional_association": place.get("emotional_association", ""),
                            "timestamp": place.get("timestamp", ""),
                            "session_id": session_id
                        })
                        seen_places.add(location)
            
            # Process events with full details
            for event in session_data.get("events", []):
                if isinstance(event, dict):
                    event_name = event.get("event") or event.get("name") or event.get("activity", "")
                    if event_name and event_name not in seen_events:
                        detailed_events.append({
                            "event": event_name,
                            "timeframe": event.get("timeframe", "Unknown"),
                            "trauma_relevance": event.get("trauma_relevance", "low"),
                            "description": event.get("description", ""),
                            "timestamp": event.get("timestamp", ""),
                            "session_id": session_id
                        })
                        seen_events.add(event_name)
            
            # Process substances with full details
            for substance in session_data.get("substances", []):
                if isinstance(substance, dict):
                    substance_name = substance.get("substance") or substance.get("name", "")
                    if substance_name and substance_name not in seen_substances:
                        detailed_substances.append({
                            "substance": substance_name,
                            "usage_pattern": substance.get("usage_pattern", ""),
                            "context": substance.get("context", ""),
                            "timestamp": substance.get("timestamp", ""),
                            "session_id": session_id
                        })
                        seen_substances.add(substance_name)
        
        return {
            "user_id": user_id,
            "detailed_people": detailed_people,
            "detailed_places": detailed_places,
            "detailed_events": detailed_events,
            "detailed_substances": detailed_substances,
            "total_sessions": len(sessions),
            "created_at": wellness_data.get("created_at"),
            "last_updated": wellness_data.get("last_updated")
        }
        
    except Exception as e:
        print(f"Error getting detailed NER insights for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "detailed_people": [],
            "detailed_places": [],
            "detailed_events": [],
            "detailed_substances": [],
            "total_sessions": 0
        }
        import traceback
        traceback.print_exc()
        return {
            "user_id": user_id,
            "total_people": 0,
            "total_places": 0,
            "total_events": 0,
            "total_substances": 0,
            "unique_people": [],
            "unique_places": [],
            "unique_events": [],
            "unique_substances": []
        }

# Update the NER_DATA_DIR reference for compatibility
NER_DATA_DIR = WELLNESS_DATA_DIR

def initialize_user_wellness_data(user_id: str):
    """Initialize wellness data structure for new user"""
    wellness_data = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "sessions": {},
        "daily_logs": {},
        "agent_preferences": {
            "MENTAL_HEALTH": {"usage_count": 0, "satisfaction_rating": 0},
            "DIET": {"usage_count": 0, "satisfaction_rating": 0},
            "EXERCISE": {"usage_count": 0, "satisfaction_rating": 0}
        },
        "wellness_summary": {
            "total_sessions": 0,
            "total_mental_health_interactions": 0,
            "total_diet_interactions": 0,
            "total_exercise_interactions": 0,
            "current_streak": 0,
            "goal_progress": {
                "weight_progress": 0,
                "fitness_progress": 0,
                "mental_health_progress": 0
            }
        }
    }
    save_user_wellness_data(wellness_data, user_id)

def get_user_wellness_file(user_id: str = "default_user"):
    """Get the wellness file path for a specific user"""
    return os.path.join(WELLNESS_DATA_DIR, f"{user_id}_wellness.json")

def get_user_ner_file(user_id: str = "default_user"):
    """Get the NER file path for a specific user (legacy compatibility)"""
    return os.path.join(WELLNESS_DATA_DIR, f"{user_id}_wellness.json")

def save_user_wellness_data(wellness_data: dict, user_id: str = "default_user"):
    """Save wellness data for a specific user"""
    file_path = get_user_wellness_file(user_id)
    wellness_data["last_updated"] = datetime.now().isoformat()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(wellness_data, f, indent=4, ensure_ascii=False, default=str)

def load_user_wellness_data(user_id: str = "default_user"):
    """Load wellness data for a specific user"""
    file_path = get_user_wellness_file(user_id)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Create default structure if doesn't exist
    return {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "sessions": {},
        "daily_logs": {},
        "agent_preferences": {
            "MENTAL_HEALTH": {"usage_count": 0, "satisfaction_rating": 0},
            "DIET": {"usage_count": 0, "satisfaction_rating": 0},
            "EXERCISE": {"usage_count": 0, "satisfaction_rating": 0}
        },
        "wellness_summary": {
            "total_sessions": 0,
            "total_mental_health_interactions": 0,
            "total_diet_interactions": 0,
            "total_exercise_interactions": 0,
            "current_streak": 0,
            "goal_progress": {
                "weight_progress": 0,
                "fitness_progress": 0,
                "mental_health_progress": 0
            }
        }
    }

def route_message_to_agent(user_input: str) -> str:
    """Route user message to appropriate agent"""
    try:
        prompt = router_prompt.format(user_input=user_input)
        response = router_model.invoke([HumanMessage(content=prompt)])
        agent = response.content.strip().upper()
        
        # Validate agent response
        valid_agents = ["MENTAL_HEALTH", "DIET", "EXERCISE"]
        if agent in valid_agents:
            return agent
        elif agent == "GENERAL":
            return "MENTAL_HEALTH"  # Map GENERAL to Mental Health
        else:
            return "MENTAL_HEALTH"  # Default fallback
            
    except Exception as e:
        print(f"Error in routing: {e}")
        return "MENTAL_HEALTH"  # Default fallback

def get_user_context_for_agent(user_id: str, agent_type: str) -> str:
    """Get formatted user context for agent prompts"""
    try:
        users_data = load_users_data()
        user_profile = users_data.get(user_id, {})
        
        if not user_profile:
            return "User Profile: No profile information available."
        
        context = f"""User Profile:
- Name: {user_profile.get('full_name', 'N/A')}, Age: {user_profile.get('age', 'N/A')}, Gender: {user_profile.get('gender', 'N/A')}
- Current Weight: {user_profile.get('current_weight', 'N/A')}kg, Target: {user_profile.get('target_weight', 'N/A')}kg, Height: {user_profile.get('height', 'N/A')}cm
- Activity Level: {user_profile.get('activity_level', 'N/A')}
- Diet Type: {user_profile.get('diet_type', 'N/A')}
- Today's Stress Level: {user_profile.get('daily_stress_level', 'N/A')}/5
- Sleep Schedule: {user_profile.get('wake_up_time', 'N/A')} - {user_profile.get('sleep_time', 'N/A')}
- Common Issues: {', '.join(user_profile.get('common_issues', []))}
- Medical Conditions: {', '.join(user_profile.get('medical_conditions', []))}
- Medications: {', '.join(user_profile.get('medications', []))}
- Favorite Foods: {', '.join(user_profile.get('favorite_foods', []))}
- Workout Preference: {user_profile.get('workout_duration_preference', 'N/A')} minutes

"""
        return context
        
    except Exception as e:
        print(f"Error getting user context: {e}")
        return "User Profile: Error loading profile information."

def load_user_ner_data(user_id: str = "default_user"):
    """Load NER data for a specific user - Updated for wellness data"""
    # For backward compatibility, return wellness data in NER format
    wellness_data = load_user_wellness_data(user_id)
    user_info = get_user_info(user_id)
    
    # Convert wellness data to NER-compatible format
    ner_compatible_data = {
        "user_id": user_id,
        "name": user_info.get("full_name", user_info.get("name", "Default User")),
        "cnic": user_info.get("cnic", "Unknown"),
        "created_at": wellness_data.get("created_at", datetime.now().isoformat()),
        "last_updated": wellness_data.get("last_updated", datetime.now().isoformat()),
        "sessions": wellness_data.get("sessions", {}),
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
    
    return ner_compatible_data

def save_user_ner_data(user_data, user_id: str = "default_user"):
    """Save NER data for a specific user - Updated for wellness compatibility"""
    # Convert and save to wellness format
    wellness_data = load_user_wellness_data(user_id)
    
    # Update sessions if they exist in user_data
    if "sessions" in user_data:
        wellness_data["sessions"] = user_data["sessions"]
    
    wellness_data["last_updated"] = datetime.now().isoformat()
    save_user_wellness_data(wellness_data, user_id)

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
    """Extract NER entities with structured output - routes to agent-specific NER"""
    msg = state['messages'][-1].content
    session_id = state.get('session_id', 'default_session')
    timestamp = state.get('time_stamps', [datetime.now()])[-1]
    current_user = state.get('current_user', 'default_user')
    current_agent = state.get('current_agent', 'MENTAL_HEALTH')
    
    # Route to agent-specific NER extraction
    if current_agent == 'MENTAL_HEALTH':
        ner_result = extract_mental_health_entities(msg)
    elif current_agent == 'DIET':
        ner_result = extract_diet_entities(msg)
    elif current_agent == 'EXERCISE':
        ner_result = extract_exercise_entities(msg)
    else:
        # Fallback to general NER
        structured_model = model.with_structured_output(NamedEntity)
        msg_prompt = f"""Extract all named entities from this Message: {msg}"""
        ner_result = structured_model.invoke([
            SystemMessage(content=ner_prompt),
            HumanMessage(content=msg_prompt)
        ])
    
    try:
        add_agent_specific_ner_to_session(ner_result, session_id, timestamp, current_user, current_agent)
        add_message_to_session(session_id, msg, "user", timestamp, current_user)
        print(f"Agent-specific NER data saved for user {current_user}, agent {current_agent}, session {session_id}")
    except Exception as e:
        print(f"Error saving agent-specific NER data: {e}")
    
    return {"ner_entities": [ner_result]}

def extract_mental_health_entities(message: str) -> MentalHealthEntities:
    """Extract mental health specific entities"""
    structured_model = model.with_structured_output(MentalHealthEntities)
    msg_prompt = f"""Extract mental health entities from this message: {message}"""
    
    return structured_model.invoke([
        SystemMessage(content=mental_health_ner_prompt),
        HumanMessage(content=msg_prompt)
    ])

def extract_diet_entities(message: str) -> DietEntities:
    """Extract diet and nutrition specific entities"""
    structured_model = model.with_structured_output(DietEntities)
    msg_prompt = f"""Extract diet and nutrition entities from this message: {message}"""
    
    return structured_model.invoke([
        SystemMessage(content=diet_ner_prompt),
        HumanMessage(content=msg_prompt)
    ])

def extract_exercise_entities(message: str) -> ExerciseEntities:
    """Extract exercise and fitness specific entities"""
    structured_model = model.with_structured_output(ExerciseEntities)
    msg_prompt = f"""Extract exercise and fitness entities from this message: {message}"""
    
    return structured_model.invoke([
        SystemMessage(content=exercise_ner_prompt),
        HumanMessage(content=msg_prompt)
    ])

def add_agent_specific_ner_to_session(ner_result, session_id: str, timestamp: datetime, user_id: str, agent: str):
    """Add agent-specific NER results to user session"""
    wellness_data = load_user_wellness_data(user_id)
    
    if session_id not in wellness_data["sessions"]:
        wellness_data["sessions"][session_id] = {
            "session_id": session_id,
            "agent": agent,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "people": [],
            "places": [],
            "events": [],
            "substances": [],
            "messages": [],
            "agent_specific_entities": {}
        }
    
    session_data = wellness_data["sessions"][session_id]
    session_data["last_updated"] = datetime.now().isoformat()
    
    # Add agent-specific entities
    if agent not in session_data["agent_specific_entities"]:
        session_data["agent_specific_entities"][agent] = {}
    
    timestamp_str = timestamp.isoformat()
    
    if isinstance(ner_result, MentalHealthEntities):
        # Add mental health entities
        for entity_type in ["people", "conditions", "coping_strategies", "emotional_states", "therapeutic_goals"]:
            if entity_type not in session_data["agent_specific_entities"][agent]:
                session_data["agent_specific_entities"][agent][entity_type] = []
            
            entities = getattr(ner_result, entity_type, [])
            for entity in entities:
                entity_dict = entity.dict() if hasattr(entity, 'dict') else dict(entity)
                entity_dict['timestamp'] = timestamp_str
                session_data["agent_specific_entities"][agent][entity_type].append(entity_dict)
    
    elif isinstance(ner_result, DietEntities):
        # Add diet entities
        for entity_type in ["food_items", "nutritional_goals", "eating_patterns", "dietary_restrictions", "meal_plans", "body_responses"]:
            if entity_type not in session_data["agent_specific_entities"][agent]:
                session_data["agent_specific_entities"][agent][entity_type] = []
            
            entities = getattr(ner_result, entity_type, [])
            for entity in entities:
                entity_dict = entity.dict() if hasattr(entity, 'dict') else dict(entity)
                entity_dict['timestamp'] = timestamp_str
                session_data["agent_specific_entities"][agent][entity_type].append(entity_dict)
    
    elif isinstance(ner_result, ExerciseEntities):
        # Add exercise entities
        for entity_type in ["activities", "fitness_goals", "physical_limitations", "workout_preferences", "physical_responses", "fitness_environments", "performance_metrics"]:
            if entity_type not in session_data["agent_specific_entities"][agent]:
                session_data["agent_specific_entities"][agent][entity_type] = []
            
            entities = getattr(ner_result, entity_type, [])
            for entity in entities:
                entity_dict = entity.dict() if hasattr(entity, 'dict') else dict(entity)
                entity_dict['timestamp'] = timestamp_str
                session_data["agent_specific_entities"][agent][entity_type].append(entity_dict)
    
    save_user_wellness_data(wellness_data, user_id)
    return wellness_data

def generate_routine_plan(user_id: str, plan_type: str, user_input: str = "") -> RoutinePlan:
    """Generate personalized routine plan based on user profile and agent type"""
    wellness_data = load_user_wellness_data(user_id)
    user_profile = wellness_data.get("profile", {})
    
    # Get relevant user context
    context = get_user_context_for_agent(user_id, plan_type.upper())
    
    # Prepare context prompt
    context_prompt = f"""
    User Profile:
    - Age: {user_profile.get('age', 'Unknown')}
    - Gender: {user_profile.get('gender', 'Unknown')}
    - Current Weight: {user_profile.get('current_weight', 'Unknown')}kg
    - Target Weight: {user_profile.get('target_weight', 'Unknown')}kg
    - Activity Level: {user_profile.get('activity_level', 'Unknown')}
    - Daily Stress Level: {user_profile.get('daily_stress_level', 3)}/5
    - Wake Up Time: {user_profile.get('wake_up_time', '07:00')}
    - Sleep Time: {user_profile.get('sleep_time', '23:00')}
    - Workout Duration Preference: {user_profile.get('workout_duration_preference', 30)} minutes
    
    User Context: {json.dumps(context, indent=2)}
    
    User Request: {user_input}
    
    Create a comprehensive {plan_type} routine plan that is:
    - Culturally appropriate for Pakistani lifestyle
    - Realistic and achievable based on user's constraints
    - Progressive and sustainable
    - Personalized to user's specific goals and preferences
    """
    
    # Use appropriate routine generation prompt
    if plan_type.lower() == 'mental_health':
        prompt = mental_health_routine_prompt
    elif plan_type.lower() == 'diet':
        prompt = diet_routine_prompt
    elif plan_type.lower() == 'exercise':
        prompt = exercise_routine_prompt
    else:
        prompt = mental_health_routine_prompt  # Default
    
    structured_model = model.with_structured_output(RoutinePlan)
    
    routine_plan = structured_model.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=context_prompt)
    ])
    
    # Set user ID and plan type
    routine_plan.user_id = user_id
    routine_plan.plan_type = plan_type.lower()
    
    # Save routine plan
    save_routine_plan(routine_plan)
    
    return routine_plan

def save_routine_plan(routine_plan: RoutinePlan):
    """Save routine plan to user's wellness data"""
    user_id = routine_plan.user_id
    wellness_data = load_user_wellness_data(user_id)
    
    if "routine_plans" not in wellness_data:
        wellness_data["routine_plans"] = {}
    
    plan_key = f"{routine_plan.plan_type}_{routine_plan.created_date.isoformat()}"
    wellness_data["routine_plans"][plan_key] = routine_plan.dict()
    
    save_user_wellness_data(wellness_data, user_id)

def get_user_routine_plans(user_id: str, plan_type: str = None) -> list[RoutinePlan]:
    """Get user's routine plans, optionally filtered by type"""
    wellness_data = load_user_wellness_data(user_id)
    routine_plans = wellness_data.get("routine_plans", {})
    
    plans = []
    for plan_key, plan_data in routine_plans.items():
        if plan_type is None or plan_data.get("plan_type") == plan_type:
            try:
                # Clean and validate the plan data before creating RoutinePlan
                cleaned_plan_data = clean_routine_plan_data(plan_data)
                plans.append(RoutinePlan(**cleaned_plan_data))
            except Exception as e:
                # If there's an error creating the plan, skip it but log the error
                print(f"Error loading routine plan {plan_key}: {e}")
                continue
    
    # Sort by creation date, most recent first
    plans.sort(key=lambda x: x.created_date, reverse=True)
    return plans

def clean_routine_plan_data(plan_data: dict) -> dict:
    """Clean routine plan data to ensure proper format for Pydantic model"""
    cleaned_data = plan_data.copy()
    
    # Clean daily_schedule
    if "daily_schedule" in cleaned_data:
        daily_schedule = cleaned_data["daily_schedule"]
        cleaned_daily_schedule = []
        
        for item in daily_schedule:
            if isinstance(item, dict):
                # Already a dictionary, keep as is
                cleaned_daily_schedule.append(item)
            elif isinstance(item, str):
                # String representation, try to parse it
                try:
                    # Extract time, activity, duration, flexible from string
                    import re
                    time_match = re.search(r"time='([^']*)'", item)
                    activity_match = re.search(r"activity='([^']*)'", item)
                    duration_match = re.search(r"duration=(\d+)", item)
                    flexible_match = re.search(r"flexible=(True|False)", item)
                    
                    cleaned_item = {
                        "time": time_match.group(1) if time_match else "",
                        "activity": activity_match.group(1) if activity_match else "",
                        "duration": int(duration_match.group(1)) if duration_match else 30,
                        "flexible": flexible_match.group(1) == "True" if flexible_match else False
                    }
                    cleaned_daily_schedule.append(cleaned_item)
                except Exception as e:
                    # If parsing fails, create a default item
                    cleaned_daily_schedule.append({
                        "time": "00:00",
                        "activity": "Activity",
                        "duration": 30,
                        "flexible": False
                    })
            else:
                # Unknown format, create default
                cleaned_daily_schedule.append({
                    "time": "00:00",
                    "activity": "Activity",
                    "duration": 30,
                    "flexible": False
                })
        
        cleaned_data["daily_schedule"] = cleaned_daily_schedule
    
    # Clean weekly_schedule if it exists
    if "weekly_schedule" in cleaned_data:
        weekly_schedule = cleaned_data["weekly_schedule"]
        if not isinstance(weekly_schedule, list):
            cleaned_data["weekly_schedule"] = []
    
    # Ensure required fields exist
    if "created_date" not in cleaned_data:
        cleaned_data["created_date"] = date.today()
    elif isinstance(cleaned_data["created_date"], str):
        try:
            cleaned_data["created_date"] = date.fromisoformat(cleaned_data["created_date"])
        except:
            cleaned_data["created_date"] = date.today()
    
    if "plan_type" not in cleaned_data:
        cleaned_data["plan_type"] = "comprehensive"
    
    if "weekly_goals" not in cleaned_data:
        cleaned_data["weekly_goals"] = []
    
    if "emergency_strategies" not in cleaned_data:
        cleaned_data["emergency_strategies"] = []
    
    if "motivational_quotes" not in cleaned_data:
        cleaned_data["motivational_quotes"] = []
    
    return cleaned_data

def update_routine_progress(user_id: str, plan_key: str, progress_data: dict):
    """Update progress on a routine plan"""
    wellness_data = load_user_wellness_data(user_id)
    
    if "routine_plans" in wellness_data and plan_key in wellness_data["routine_plans"]:
        plan = wellness_data["routine_plans"][plan_key]
        
        if "progress_tracking" not in plan:
            plan["progress_tracking"] = []
        
        progress_entry = {
            "date": date.today().isoformat(),
            "timestamp": datetime.now().isoformat(),
            **progress_data
        }
        
        plan["progress_tracking"].append(progress_entry)
        plan["last_updated"] = datetime.now().isoformat()
        
        save_user_wellness_data(wellness_data, user_id)
        return True
    
    return False

def get_agent_specific_insights(user_id: str, agent_type: str):
    """Get detailed insights for specific agent type"""
    wellness_data = load_user_wellness_data(user_id)
    sessions = wellness_data.get("sessions", {})
    
    agent_insights = {
        "user_id": user_id,
        "agent_type": agent_type,
        "total_sessions": 0,
        "entities": {},
        "recent_activities": [],
        "progress_trends": {}
    }
    
    # Aggregate data from sessions for this agent
    for session_id, session_data in sessions.items():
        if session_data.get("agent") == agent_type.upper():
            agent_insights["total_sessions"] += 1
            
            # Get agent-specific entities
            agent_entities = session_data.get("agent_specific_entities", {}).get(agent_type.upper(), {})
            
            for entity_type, entities in agent_entities.items():
                if entity_type not in agent_insights["entities"]:
                    agent_insights["entities"][entity_type] = []
                
                # Add entities with session context
                for entity in entities:
                    entity_with_context = dict(entity)
                    entity_with_context["session_id"] = session_id
                    entity_with_context["session_date"] = session_data.get("created_at", "")
                    agent_insights["entities"][entity_type].append(entity_with_context)
    
    # Remove duplicates and sort by timestamp
    for entity_type in agent_insights["entities"]:
        # Sort by timestamp, most recent first
        agent_insights["entities"][entity_type].sort(
            key=lambda x: x.get("timestamp", ""), reverse=True
        )
    
    return agent_insights

def get_comprehensive_user_insights(user_id: str):
    """Get comprehensive insights across all agents"""
    comprehensive_insights = {
        "user_id": user_id,
        "mental_health": get_agent_specific_insights(user_id, "MENTAL_HEALTH"),
        "diet": get_agent_specific_insights(user_id, "DIET"),
        "exercise": get_agent_specific_insights(user_id, "EXERCISE"),
        "routine_plans": get_user_routine_plans(user_id),
        "overall_stats": {}
    }
    
    # Calculate overall statistics
    total_sessions = sum([
        comprehensive_insights["mental_health"]["total_sessions"],
        comprehensive_insights["diet"]["total_sessions"],
        comprehensive_insights["exercise"]["total_sessions"]
    ])
    
    comprehensive_insights["overall_stats"] = {
        "total_sessions": total_sessions,
        "total_routine_plans": len(comprehensive_insights["routine_plans"]),
        "most_used_agent": max(
            ["MENTAL_HEALTH", "DIET", "EXERCISE"],
            key=lambda x: comprehensive_insights[x.lower()]["total_sessions"]
        ) if total_sessions > 0 else "MENTAL_HEALTH"
    }
    
    return comprehensive_insights

def calculate_progress_metrics(user_id: str):
    """Calculate progress metrics based on user goals and routine completion"""
    wellness_data = load_user_wellness_data(user_id)
    profile = wellness_data.get("profile", {})
    routine_plans = get_user_routine_plans(user_id)
    
    progress_metrics = {
        "weight_progress": 0,
        "fitness_progress": 0,
        "mental_health_progress": 0,
        "overall_routine_adherence": 0,
        "weekly_activity_completion": 0
    }
    
    # Calculate weight progress
    current_weight = profile.get("current_weight", 0)
    target_weight = profile.get("target_weight", 0)
    initial_weight = profile.get("initial_weight", current_weight)  # We'll need to store this
    
    if initial_weight and target_weight and initial_weight != target_weight:
        weight_lost = initial_weight - current_weight
        target_weight_loss = initial_weight - target_weight
        if target_weight_loss != 0:
            progress_metrics["weight_progress"] = min(100, max(0, (weight_lost / target_weight_loss) * 100))
    
    # Calculate routine adherence from progress logs
    total_adherence = 0
    total_plans = 0
    
    for plan in routine_plans:
        if hasattr(plan, 'progress_tracking') and plan.progress_tracking:
            # Calculate average satisfaction from recent progress logs
            recent_logs = plan.progress_tracking[-7:]  # Last 7 entries
            if recent_logs:
                avg_satisfaction = sum(log.get('satisfaction_level', 0) for log in recent_logs) / len(recent_logs)
                total_adherence += (avg_satisfaction / 10) * 100  # Convert to percentage
                total_plans += 1
    
    if total_plans > 0:
        progress_metrics["overall_routine_adherence"] = total_adherence / total_plans
    
    # Calculate agent-specific progress
    mental_health_plans = [p for p in routine_plans if p.plan_type == "mental_health"]
    diet_plans = [p for p in routine_plans if p.plan_type == "diet"]
    exercise_plans = [p for p in routine_plans if p.plan_type == "exercise"]
    
    for plan_type, plans in [("mental_health", mental_health_plans), ("fitness", exercise_plans)]:
        if plans:
            type_adherence = 0
            type_count = 0
            for plan in plans:
                if hasattr(plan, 'progress_tracking') and plan.progress_tracking:
                    recent_logs = plan.progress_tracking[-7:]
                    if recent_logs:
                        avg_satisfaction = sum(log.get('satisfaction_level', 0) for log in recent_logs) / len(recent_logs)
                        type_adherence += (avg_satisfaction / 10) * 100
                        type_count += 1
            
            if type_count > 0:
                if plan_type == "mental_health":
                    progress_metrics["mental_health_progress"] = type_adherence / type_count
                else:
                    progress_metrics["fitness_progress"] = type_adherence / type_count
    
    # Calculate weekly activity completion
    if routine_plans:
        total_weekly_activities = sum(len(plan.daily_schedule) * 7 for plan in routine_plans if plan.daily_schedule)
        completed_activities = 0
        
        for plan in routine_plans:
            if hasattr(plan, 'progress_tracking') and plan.progress_tracking:
                # Get this week's logs
                this_week_logs = [log for log in plan.progress_tracking 
                                if (datetime.now() - datetime.fromisoformat(log.get('timestamp', '2000-01-01T00:00:00'))).days <= 7]
                
                for log in this_week_logs:
                    completed_activities += log.get('completed_activities', 0)
        
        if total_weekly_activities > 0:
            progress_metrics["weekly_activity_completion"] = min(100, (completed_activities / total_weekly_activities) * 100)
    
    return progress_metrics

def agent_router_node(state: State):
    """Route message to appropriate agent"""
    user_message = state['messages'][-1].content
    current_user = state.get('current_user', 'default_user')
    
    # Route to appropriate agent
    agent_type = route_message_to_agent(user_message)
    
    # Get user context
    user_context = get_user_context_for_agent(current_user, agent_type)
    
    return {
        "current_agent": agent_type,
        "user_context": {"context": user_context, "agent": agent_type}
    }

def wellness_chat_node(state: State):
    """Multi-agent wellness chat node with routine generation capability"""
    current_agent = state.get('current_agent', 'MENTAL_HEALTH')
    user_context = state.get('user_context', {}).get('context', '')
    current_user = state.get('current_user', 'default_user')
    user_message = state['messages'][-1].content.lower()
    
    # Check if user is asking for routine/plan generation
    routine_keywords = [
        'routine', 'schedule', 'plan', 'timetable', 'daily plan', 'weekly plan',
        'diet plan', 'meal plan', 'workout plan', 'exercise routine', 
        'mental health routine', 'create routine', 'make plan', 'help me plan'
    ]
    
    is_routine_request = any(keyword in user_message for keyword in routine_keywords)
    
    # Select appropriate prompt based on agent
    if current_agent == 'MENTAL_HEALTH':
        system_prompt = mental_health_prompt
    elif current_agent == 'DIET':
        system_prompt = diet_prompt
    elif current_agent == 'EXERCISE':
        system_prompt = exercise_prompt
    else:
        system_prompt = mental_health_prompt  # Default fallback
    
    # Construct full prompt with user context
    full_prompt = f"{user_context}\n{system_prompt}"
    
    # Generate response
    response = model.invoke([SystemMessage(content=full_prompt)] + state["messages"])
    
    # If user requested a routine, generate structured routine plan
    routine_plan = None
    if is_routine_request:
        try:
            routine_plan = generate_routine_plan(
                user_id=current_user,
                plan_type=current_agent.lower(),
                user_input=state['messages'][-1].content
            )
            
            # Enhance response with routine information
            if routine_plan:
                routine_summary = f"\n\n🗓️ **I've created a personalized {current_agent.lower()} routine for you!**\n"
                routine_summary += f"📅 Created on: {routine_plan.created_date}\n"
                routine_summary += f"⏰ Daily activities: {len(routine_plan.daily_schedule)} items\n"
                routine_summary += f"🎯 Weekly goals: {len(routine_plan.weekly_goals)} goals\n"
                routine_summary += f"\n✨ You can view your complete routine in the 'My Routines' section of your profile!"
                
                response_content = response.content + routine_summary
            else:
                response_content = response.content
        except Exception as e:
            print(f"Error generating routine plan: {e}")
            response_content = response.content
    else:
        response_content = response.content
    
    # Update agent usage statistics
    try:
        wellness_data = load_user_wellness_data(current_user)
        # Only update stats for valid wellness agents
        if current_agent in ["MENTAL_HEALTH", "DIET", "EXERCISE"]:
            wellness_data["agent_preferences"][current_agent]["usage_count"] += 1
            
            # Track routine generation
            if routine_plan:
                if "routine_generation_count" not in wellness_data["agent_preferences"][current_agent]:
                    wellness_data["agent_preferences"][current_agent]["routine_generation_count"] = 0
                wellness_data["agent_preferences"][current_agent]["routine_generation_count"] += 1
            
            save_user_wellness_data(wellness_data, current_user)
    except Exception as e:
        print(f"Error updating agent stats for {current_agent}: {e}")
    
    return {"chat_response": response_content}

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

graph = StateGraph(State)
graph.add_node("agent_router_node", agent_router_node)
graph.add_node("wellness_chat_node", wellness_chat_node)
graph.add_node("ner_node", ner_node)
graph.add_node("language_safety_node", language_safety_node)

graph.add_edge(START, "agent_router_node")
graph.add_edge(START, "ner_node")
graph.add_edge("agent_router_node", "wellness_chat_node")
graph.add_edge("wellness_chat_node", "language_safety_node")
graph.add_edge("ner_node", END)
graph.add_edge("language_safety_node", END)

chatbot = graph.compile(checkpointer=checkpointer)