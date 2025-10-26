# Pakistan-Specific Wellness Features

## 🇵🇰 **Local Problem-Solving Features**

### 1. **🏥 Healthcare Integration**
- **Doctor Locator**: Integration with local hospitals and clinics (Mayo, Shaukat Khanum, etc.)
- **Prescription Tracker**: Track medications with Pakistani generic names
- **Health Insurance Navigator**: Guide through SEHAT card, company insurance
- **Emergency Contacts**: Quick access to 1122, local hospital numbers
- **Medical History in Urdu**: Support for Urdu medical terminology

### 2. **🍽️ Pakistani Cuisine Intelligence**
- **Local Food Database**: Complete nutritional data for Pakistani dishes
  - Biryani, Karahi, Nihari, Haleem, Roti, Naan varieties
  - Street food: Samosa, Pakora, Chaat, Gol Gappa
  - Regional specialties: Sindhi, Punjabi, Balochi, Pathan dishes
- **Ramadan Meal Planning**: Specialized Sehri/Iftar meal plans
- **Sabzi Mandi Integration**: Seasonal vegetable/fruit availability and prices
- **Halal Food Certification**: Ensure all recommendations are halal-compliant
- **Local Grocery Stores**: Integration with Carrefour, Metro, local kiryana stores

### 3. **🏃‍♂️ Climate-Adaptive Fitness**
- **Weather-Based Workouts**: Indoor alternatives for extreme heat/monsoon
- **Prayer Time Integration**: Schedule workouts around 5 daily prayers
- **Local Sports Integration**: Cricket, Badminton, Football recommendations
- **Home Workout Focus**: Minimal equipment exercises for small spaces
- **Pollution-Aware Exercise**: Air quality-based outdoor activity recommendations

### 4. **🧠 Culturally-Sensitive Mental Health**
- **Family Dynamics Support**: Navigate joint family pressures
- **Religious Coping Strategies**: Islamic prayers, meditation, Dhikr integration
- **Cultural Stigma Management**: Anonymous support groups, discrete help
- **Marriage/Relationship Counseling**: Cultural context for relationships
- **Career Pressure Support**: Job market stress, competitive exam anxiety
- **Urdu Language Support**: Mental health resources in Urdu

### 5. **💼 Work-Life Balance Pakistani Style**
- **Traffic-Aware Scheduling**: Plan activities considering Karachi/Lahore traffic
- **Office Culture Integration**: Chai breaks, late work culture adaptations
- **Load-shedding Adaptations**: Backup plans for power outages
- **Wedding Season Planning**: Maintain wellness during shaadi season
- **Eid Festival Management**: Healthy eating during celebrations

### 6. **🏠 Home & Family Features**
- **Multi-Generational Wellness**: Include elderly care, children's health
- **Domestic Helper Integration**: Meal planning with cook/maid support
- **Extended Family Coordination**: Share health goals with family members
- **Mother-in-Law Approved Meals**: Cultural food preferences navigation
- **Joint Family Exercise**: Group activities for whole family

### 7. **💰 Economic-Conscious Wellness**
- **Budget-Friendly Options**: Affordable healthy alternatives
- **Government Health Programs**: Integration with BISP, Sehat Sahulat
- **Local Market Prices**: Real-time sabzi mandi rates
- **Generic Medicine Database**: Pakistani pharmaceutical alternatives
- **Free Exercise Locations**: Parks, community centers, mosques

### 8. **🌍 Community & Social Features**
- **Mosque Fitness Groups**: Connect with local mosque wellness programs
- **Neighborhood Walking Groups**: Safety-conscious group exercise
- **Cultural Event Planning**: Healthy options for mehndi, walima
- **Charitable Wellness**: Combine fitness with charity (walkathons for causes)
- **Social Media Integration**: WhatsApp groups for accountability

### 9. **📱 Technology & Connectivity**
- **Offline Mode**: Function during internet connectivity issues
- **Urdu Voice Commands**: Voice interaction in Urdu/English mix
- **SMS Reminders**: For users with limited smartphone usage
- **Low-Data Mode**: Optimize for limited internet packages
- **JazzCash/EasyPaisa Integration**: Local payment methods for premium features

### 10. **🎓 Education & Awareness**
- **Health Literacy in Urdu**: Medical education in local language
- **Myth Busting**: Address local health misconceptions
- **Traditional Medicine Integration**: Safe use of desi totke with modern medicine
- **Women's Health Focus**: Culturally sensitive reproductive health info
- **Diabetes/Hypertension Focus**: Address prevalent local health issues

## 🗄️ **SQL Database Integration Plan**

### **Tables to Create (Structured Data)**

#### 1. **Users Table**
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    cnic VARCHAR(15) UNIQUE,
    email VARCHAR(100),
    password_hash VARCHAR(255),
    phone VARCHAR(15),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### 2. **User_Profiles Table**
```sql
CREATE TABLE user_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(20) REFERENCES users(user_id),
    age INT,
    gender ENUM('Male', 'Female', 'Other'),
    height DECIMAL(5,2),
    current_weight DECIMAL(5,2),
    target_weight DECIMAL(5,2),
    initial_weight DECIMAL(5,2),
    activity_level ENUM('sedentary', 'lightly_active', 'moderately_active', 'very_active'),
    diet_type ENUM('vegetarian', 'non_vegetarian', 'keto', 'low_carb', 'balanced', 'other'),
    city VARCHAR(50),
    area VARCHAR(100),
    preferred_language ENUM('English', 'Urdu', 'Mixed') DEFAULT 'English',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### 3. **Health_Data Table**
```sql
CREATE TABLE health_data (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(20) REFERENCES users(user_id),
    date DATE,
    weight DECIMAL(5,2),
    blood_pressure_systolic INT,
    blood_pressure_diastolic INT,
    blood_sugar INT,
    stress_level INT CHECK (stress_level BETWEEN 1 AND 5),
    sleep_hours DECIMAL(3,1),
    mood_rating INT CHECK (mood_rating BETWEEN 1 AND 10),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. **Sessions Table**
```sql
CREATE TABLE sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(20) REFERENCES users(user_id),
    agent_type ENUM('MENTAL_HEALTH', 'DIET', 'EXERCISE'),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    total_messages INT DEFAULT 0,
    session_rating INT CHECK (session_rating BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. **Routine_Plans Table**
```sql
CREATE TABLE routine_plans (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(20) REFERENCES users(user_id),
    plan_type ENUM('mental_health', 'diet', 'exercise', 'comprehensive'),
    title VARCHAR(200),
    description TEXT,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### 6. **Progress_Logs Table**
```sql
CREATE TABLE progress_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id VARCHAR(50) REFERENCES routine_plans(plan_id),
    user_id VARCHAR(20) REFERENCES users(user_id),
    log_date DATE,
    completed_activities INT,
    total_activities INT,
    satisfaction_level INT CHECK (satisfaction_level BETWEEN 1 AND 10),
    notes TEXT,
    challenges TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 7. **Local_Healthcare Table** (Pakistan-specific)
```sql
CREATE TABLE local_healthcare (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200),
    type ENUM('hospital', 'clinic', 'pharmacy', 'lab'),
    city VARCHAR(50),
    area VARCHAR(100),
    address TEXT,
    phone VARCHAR(15),
    emergency_services BOOLEAN DEFAULT FALSE,
    accepts_sehat_card BOOLEAN DEFAULT FALSE,
    specializations JSON,
    rating DECIMAL(2,1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Keep in JSON (Unstructured Data)**
- Conversation messages and AI responses
- NER entities (complex nested structures)
- Agent-specific entity extractions
- Routine daily schedules (complex nested activities)
- Cultural preferences and customizations
- AI model outputs and structured responses

### **Migration Strategy**
1. **Phase 1**: Create SQL tables alongside existing JSON files
2. **Phase 2**: Dual-write to both SQL and JSON during transition
3. **Phase 3**: Migrate existing JSON data to SQL using migration scripts
4. **Phase 4**: Switch reads to SQL, keep JSON for backup
5. **Phase 5**: Remove JSON dependencies, keep only for unstructured data

This approach maintains data integrity while providing better performance and structure for user management, health tracking, and progress monitoring.