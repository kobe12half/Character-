import os
import uuid
import base64
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
import json
import random

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(MONGO_URL)
db = client.weight_gain_app

# Emergent LLM key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', 'sk-emergent-41dE6724c7d2d54166')

# Pydantic models
class User(BaseModel):
    user_id: str
    name: str
    age: int
    height_cm: float
    weight_kg: float
    gender: str  # 'male' or 'female'
    activity_level: str  # 'sedentary', 'light', 'moderate', 'active', 'very_active'
    goal_weight_kg: float
    target_weekly_gain: float  # 0.25, 0.5, or 1.0 kg per week
    daily_calorie_target: int
    daily_protein_target: int
    daily_carb_target: int
    daily_fat_target: int
    created_date: str
    # Gamification fields
    total_points: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    last_log_date: Optional[str] = None
    badges_earned: List[str] = []
    # Coaching fields
    last_checkin_date: Optional[str] = None
    coaching_preferences: Dict = {}
    tdee_adjustment_history: List[Dict] = []
    # Challenge fields
    active_challenges: List[str] = []
    completed_challenges: List[str] = []
    challenge_points: int = 0

class FoodItem(BaseModel):
    name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    portion_size: str

class FoodLog(BaseModel):
    log_id: str
    user_id: str
    date: str
    meal_type: str  # 'breakfast', 'lunch', 'dinner', 'snack'
    food_items: List[FoodItem]
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    image_base64: Optional[str] = None
    created_at: str
    points_earned: int = 0

class WeightEntry(BaseModel):
    entry_id: str
    user_id: str
    weight_kg: float
    date: str
    created_at: str
    points_earned: int = 0

class Achievement(BaseModel):
    achievement_id: str
    user_id: str
    badge_type: str
    badge_name: str
    badge_description: str
    points_awarded: int
    earned_date: str
    created_at: str

class Challenge(BaseModel):
    challenge_id: str
    challenge_type: str  # 'daily', 'weekly', 'streak', 'macro', 'variety'
    title: str
    description: str
    goal_value: int
    goal_unit: str  # 'calories', 'protein', 'logs', 'days', 'foods'
    points_reward: int
    duration_days: int
    start_date: str
    end_date: str
    is_active: bool = True
    difficulty: str = "medium"  # 'easy', 'medium', 'hard', 'epic'

class UserChallenge(BaseModel):
    user_challenge_id: str
    user_id: str
    challenge_id: str
    current_progress: int
    goal_value: int
    is_completed: bool = False
    points_earned: int = 0
    started_date: str
    completed_date: Optional[str] = None

class CoachingTip(BaseModel):
    tip_id: str
    user_id: str
    tip_type: str  # 'nutrition', 'motivation', 'reminder', 'meal_suggestion', 'progress', 'challenge'
    title: str
    message: str
    priority: str  # 'low', 'medium', 'high', 'urgent'
    context: Dict  # Additional context data
    is_read: bool = False
    created_at: str
    expires_at: Optional[str] = None

class WeeklyCheckin(BaseModel):
    checkin_id: str
    user_id: str
    week_start_date: str
    week_end_date: str
    starting_weight: float
    ending_weight: float
    weight_change: float
    expected_change: float
    avg_daily_calories: float
    goal_hit_rate: float
    tdee_adjustment: int
    coaching_summary: str
    created_at: str

class DailyStats(BaseModel):
    date: str
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    calorie_target: int
    protein_target: int
    carb_target: int
    fat_target: int
    # Gamification stats
    points_earned_today: int = 0
    streak_status: bool = False
    target_hit_percentage: float = 0.0
    # Coaching stats
    coaching_tips: List[CoachingTip] = []
    # Challenge stats
    active_challenges: List[UserChallenge] = []
    completed_challenges_today: List[UserChallenge] = []

class UserStats(BaseModel):
    user_id: str
    total_points: int
    current_streak: int
    longest_streak: int
    badges_earned: List[str]
    total_logs: int
    total_weight_entries: int
    days_active: int
    avg_daily_calories: float
    goal_completion_rate: float
    # Challenge stats
    challenge_points: int = 0
    active_challenges_count: int = 0
    completed_challenges_count: int = 0

# Badge definitions
BADGES = {
    "first_meal": {
        "name": "First Meal Logger",
        "description": "Logged your first meal!",
        "points": 50,
        "icon": "🍽️"
    },
    "streak_3": {
        "name": "3-Day Warrior",
        "description": "3 days of consistent logging",
        "points": 100,
        "icon": "🔥"
    },
    "streak_7": {
        "name": "Week Champion",
        "description": "7 days of consistent logging",
        "points": 250,
        "icon": "👑"
    },
    "streak_14": {
        "name": "Fortnight Master",
        "description": "14 days of consistent logging",
        "points": 500,
        "icon": "💎"
    },
    "streak_30": {
        "name": "Monthly Legend",
        "description": "30 days of consistent logging",
        "points": 1000,
        "icon": "🏆"
    },
    "calorie_target": {
        "name": "Calorie Crusher",
        "description": "Hit your daily calorie target",
        "points": 75,
        "icon": "🎯"
    },
    "protein_master": {
        "name": "Protein Master",
        "description": "Hit your protein target 5 times",
        "points": 200,
        "icon": "💪"
    },
    "weight_logger": {
        "name": "Weight Tracker",
        "description": "Logged your weight 5 times",
        "points": 150,
        "icon": "⚖️"
    },
    "goal_achieved": {
        "name": "Goal Achiever",
        "description": "Reached your target weight!",
        "points": 2000,
        "icon": "🎉"
    },
    "macro_balance": {
        "name": "Macro Balancer",
        "description": "Perfect macro balance 3 days in a row",
        "points": 300,
        "icon": "⚡"
    },
    "challenge_champion": {
        "name": "Challenge Champion",
        "description": "Completed 5 challenges",
        "points": 500,
        "icon": "🏅"
    },
    "variety_explorer": {
        "name": "Variety Explorer",
        "description": "Logged 20 different foods",
        "points": 300,
        "icon": "🌈"
    }
}

# Challenge templates
CHALLENGE_TEMPLATES = {
    "daily_calorie_hit": {
        "title": "Daily Calorie Champion",
        "description": "Hit your daily calorie target for 3 days in a row",
        "goal_value": 3,
        "goal_unit": "days",
        "points_reward": 150,
        "duration_days": 7,
        "difficulty": "medium",
        "type": "streak"
    },
    "protein_power": {
        "title": "Protein Power Week",
        "description": "Get 150g+ protein for 5 days this week",
        "goal_value": 5,
        "goal_unit": "days",
        "points_reward": 200,
        "duration_days": 7,
        "difficulty": "medium",
        "type": "macro"
    },
    "logging_legend": {
        "title": "Logging Legend",
        "description": "Log meals every day for a full week",
        "goal_value": 7,
        "goal_unit": "days",
        "points_reward": 300,
        "duration_days": 7,
        "difficulty": "hard",
        "type": "consistency"
    },
    "food_explorer": {
        "title": "Food Explorer",
        "description": "Try 10 new foods this week",
        "goal_value": 10,
        "goal_unit": "foods",
        "points_reward": 250,
        "duration_days": 7,
        "difficulty": "medium",
        "type": "variety"
    },
    "morning_warrior": {
        "title": "Morning Warrior",
        "description": "Log breakfast before 10 AM for 5 days",
        "goal_value": 5,
        "goal_unit": "breakfasts",
        "points_reward": 180,
        "duration_days": 7,
        "difficulty": "medium",
        "type": "timing"
    },
    "mega_meal": {
        "title": "Mega Meal Master",
        "description": "Log a single meal over 800 calories",
        "goal_value": 1,
        "goal_unit": "meals",
        "points_reward": 100,
        "duration_days": 3,
        "difficulty": "easy",
        "type": "single"
    },
    "weekend_warrior": {
        "title": "Weekend Warrior",
        "description": "Hit your calorie target both Saturday and Sunday",
        "goal_value": 2,
        "goal_unit": "days",
        "points_reward": 120,
        "duration_days": 2,
        "difficulty": "medium",
        "type": "weekend"
    },
    "balance_master": {
        "title": "Balance Master",
        "description": "Hit all macro targets (protein, carbs, fat) in one day",
        "goal_value": 1,
        "goal_unit": "days",
        "points_reward": 200,
        "duration_days": 5,
        "difficulty": "hard",
        "type": "macro"
    }
}

# Coaching meal suggestions
MEAL_SUGGESTIONS = {
    "high_calorie_breakfast": [
        "Oatmeal with banana, peanut butter, and whole milk (650 cal)",
        "Scrambled eggs with avocado toast and orange juice (580 cal)",
        "Greek yogurt parfait with granola and berries (520 cal)",
        "Smoothie with protein powder, banana, and oats (480 cal)",
        "Pancakes with syrup, butter, and bacon (720 cal)",
        "French toast with berries and cream (640 cal)"
    ],
    "high_protein_snacks": [
        "Greek yogurt with nuts (250 cal, 20g protein)",
        "Protein smoothie with berries (300 cal, 25g protein)",
        "Cottage cheese with granola (280 cal, 22g protein)",
        "Peanut butter on whole grain toast (320 cal, 16g protein)",
        "Hard-boiled eggs with cheese (200 cal, 18g protein)",
        "Protein bar with almond milk (290 cal, 20g protein)"
    ],
    "evening_meals": [
        "Grilled chicken with quinoa and vegetables (650 cal)",
        "Salmon with sweet potato and broccoli (580 cal)",
        "Pasta with ground turkey and marinara (720 cal)",
        "Stir-fry with tofu and brown rice (540 cal)",
        "Beef and vegetable curry with rice (680 cal)",
        "Pork chops with mashed potatoes (620 cal)"
    ],
    "mass_building": [
        "Mass gainer smoothie: milk, banana, peanut butter, oats (750 cal)",
        "Trail mix with dried fruits and nuts (400 cal)",
        "Protein pancakes with syrup and butter (520 cal)",
        "Chicken and rice bowl with avocado (680 cal)",
        "Pasta with olive oil, parmesan, and chicken (780 cal)",
        "Loaded baked potato with cheese and bacon (650 cal)"
    ]
}

# Helper functions
def calculate_tdee(age: int, height_cm: float, weight_kg: float, gender: str, activity_level: str) -> int:
    """Calculate Total Daily Energy Expenditure using Mifflin-St Jeor equation"""
    # Base Metabolic Rate (BMR)
    if gender.lower() == 'male':
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    
    # Activity multipliers
    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    
    tdee = bmr * activity_multipliers.get(activity_level, 1.55)
    return int(tdee)

def calculate_macro_targets(daily_calories: int):
    """Calculate macro targets: 30% protein, 35% carbs, 35% fat for weight gain"""
    protein_calories = daily_calories * 0.30
    carb_calories = daily_calories * 0.35
    fat_calories = daily_calories * 0.35
    
    protein_grams = int(protein_calories / 4)  # 4 calories per gram
    carb_grams = int(carb_calories / 4)       # 4 calories per gram
    fat_grams = int(fat_calories / 9)         # 9 calories per gram
    
    return protein_grams, carb_grams, fat_grams

def calculate_points_for_log(total_calories: int, calorie_target: int, protein: float, protein_target: int) -> int:
    """Calculate points earned for a food log based on targets hit"""
    points = 25  # Base points for logging
    
    # Bonus points for hitting targets
    calorie_percentage = (total_calories / calorie_target) * 100
    protein_percentage = (protein / protein_target) * 100
    
    if calorie_percentage >= 80:  # Hit 80% of calorie target
        points += 25
    if calorie_percentage >= 100:  # Hit full calorie target
        points += 50
    if protein_percentage >= 80:  # Hit 80% of protein target
        points += 25
    if protein_percentage >= 100:  # Hit full protein target
        points += 50
    
    return points

def calculate_streak(last_log_date: str, current_date: str) -> tuple:
    """Calculate if streak should continue based on dates"""
    if not last_log_date:
        return 1, True  # First log ever
    
    try:
        last_date = datetime.strptime(last_log_date, '%Y-%m-%d')
        today = datetime.strptime(current_date, '%Y-%m-%d')
        
        days_diff = (today - last_date).days
        
        if days_diff == 0:
            return 0, False  # Same day, no streak change
        elif days_diff == 1:
            return 1, True  # Consecutive day, continue streak
        else:
            return 1, True  # Streak broken, start new
    except:
        return 1, True

async def create_challenge(challenge_template: str, start_date: str = None) -> Challenge:
    """Create a challenge from template"""
    if start_date is None:
        start_date = datetime.now().strftime('%Y-%m-%d')
    
    template = CHALLENGE_TEMPLATES.get(challenge_template)
    if not template:
        raise ValueError(f"Unknown challenge template: {challenge_template}")
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = start_dt + timedelta(days=template['duration_days'])
    
    challenge = Challenge(
        challenge_id=str(uuid.uuid4()),
        challenge_type=template['type'],
        title=template['title'],
        description=template['description'],
        goal_value=template['goal_value'],
        goal_unit=template['goal_unit'],
        points_reward=template['points_reward'],
        duration_days=template['duration_days'],
        start_date=start_date,
        end_date=end_dt.strftime('%Y-%m-%d'),
        difficulty=template['difficulty']
    )
    
    return challenge

async def assign_challenge_to_user(user_id: str, challenge: Challenge) -> UserChallenge:
    """Assign a challenge to a user"""
    user_challenge = UserChallenge(
        user_challenge_id=str(uuid.uuid4()),
        user_id=user_id,
        challenge_id=challenge.challenge_id,
        current_progress=0,
        goal_value=challenge.goal_value,
        started_date=challenge.start_date
    )
    
    await db.user_challenges.insert_one(user_challenge.dict())
    return user_challenge

async def update_challenge_progress(user_id: str, context: dict):
    """Update progress for active user challenges"""
    try:
        # Get active challenges for user
        today = datetime.now().strftime('%Y-%m-%d')
        active_challenges = await db.user_challenges.find({
            "user_id": user_id,
            "is_completed": False
        }, {"_id": 0}).to_list(100)
        
        completed_challenges = []
        
        for user_challenge in active_challenges:
            challenge = await db.challenges.find_one(
                {"challenge_id": user_challenge['challenge_id']}, {"_id": 0}
            )
            if not challenge:
                continue
            
            # Check if challenge is still valid (not expired)
            if today > challenge['end_date']:
                continue
            
            progress_made = False
            new_progress = user_challenge['current_progress']
            
            # Update progress based on challenge type
            challenge_type = challenge['challenge_type']
            
            if challenge_type == 'streak' and context.get('trigger') == 'food_logged':
                # Daily calorie hit streak
                if challenge['goal_unit'] == 'days':
                    daily_stats = context.get('daily_stats')
                    if daily_stats and daily_stats['total_calories'] >= daily_stats['calorie_target']:
                        new_progress += 1
                        progress_made = True
            
            elif challenge_type == 'macro' and context.get('trigger') == 'food_logged':
                # Protein targets
                daily_stats = context.get('daily_stats')
                if daily_stats and challenge['goal_unit'] == 'days':
                    if daily_stats['total_protein'] >= 150:  # 150g+ protein
                        new_progress += 1
                        progress_made = True
            
            elif challenge_type == 'consistency' and context.get('trigger') == 'food_logged':
                # Daily logging
                new_progress += 1
                progress_made = True
            
            elif challenge_type == 'variety' and context.get('trigger') == 'food_logged':
                # New foods (simplified - count unique food names)
                food_items = context.get('food_items', [])
                unique_foods = len(set(food['name'] for food in food_items))
                new_progress += unique_foods
                progress_made = True
            
            elif challenge_type == 'single' and context.get('trigger') == 'food_logged':
                # Single meal over 800 calories
                if context.get('meal_calories', 0) >= 800:
                    new_progress = challenge['goal_value']  # Complete immediately
                    progress_made = True
            
            if progress_made:
                # Update progress
                await db.user_challenges.update_one(
                    {"user_challenge_id": user_challenge['user_challenge_id']},
                    {"$set": {"current_progress": new_progress}}
                )
                
                # Check if challenge is completed
                if new_progress >= challenge['goal_value']:
                    await db.user_challenges.update_one(
                        {"user_challenge_id": user_challenge['user_challenge_id']},
                        {"$set": {
                            "is_completed": True,
                            "points_earned": challenge['points_reward'],
                            "completed_date": today
                        }}
                    )
                    
                    # Award points to user
                    await db.users.update_one(
                        {"user_id": user_id},
                        {"$inc": {
                            "total_points": challenge['points_reward'],
                            "challenge_points": challenge['points_reward']
                        },
                        "$push": {"completed_challenges": challenge['challenge_id']}}
                    )
                    
                    completed_challenges.append({
                        "challenge": challenge,
                        "points": challenge['points_reward']
                    })
        
        return completed_challenges
        
    except Exception as e:
        print(f"Error updating challenge progress: {e}")
        return []

async def generate_ai_coaching_tip(user_data: dict, context: dict) -> str:
    """Generate personalized coaching tip using AI"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"coaching_{uuid.uuid4()}",
            system_message="You are a supportive weight gain coach. Provide encouraging, personalized tips that are actionable and motivating."
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""
        Create a personalized coaching tip for this user:
        
        User Profile:
        - Name: {user_data.get('name', 'User')}
        - Goal: Gain weight from {user_data.get('weight_kg')}kg to {user_data.get('goal_weight_kg')}kg
        - Daily calorie target: {user_data.get('daily_calorie_target')} calories
        - Current streak: {user_data.get('current_streak', 0)} days
        
        Current Context:
        - Today's calories: {context.get('calories_today', 0)}/{user_data.get('daily_calorie_target')}
        - Today's protein: {context.get('protein_today', 0)}g/{user_data.get('daily_protein_target')}g
        - Time of day: {context.get('time_of_day', 'unknown')}
        - Last meal: {context.get('last_meal_type', 'none')}
        - Days since last log: {context.get('days_since_last_log', 0)}
        - Active challenges: {context.get('active_challenges', 0)}
        
        Provide a short, encouraging tip (1-2 sentences) that's specific to their situation. Be supportive and actionable.
        """
        
        response = await chat.send_message(UserMessage(text=prompt))
        return response.strip()
    except Exception as e:
        # Fallback tips
        challenge_tips = [
            "You're doing great! Check out your active challenges for extra motivation.",
            "Keep pushing towards your goals - every meal counts towards your success!",
            "Consistency is key! Try to hit your targets and complete challenges for bonus points.",
            "Remember, small consistent gains lead to big results. You've got this!"
        ]
        return random.choice(challenge_tips)

async def analyze_user_patterns(user_id: str) -> dict:
    """Analyze user eating patterns and behaviors"""
    try:
        # Get last 7 days of food logs
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        recent_logs = await db.food_logs.find({
            "user_id": user_id,
            "date": {"$gte": seven_days_ago}
        }, {"_id": 0}).to_list(100)
        
        # Analyze patterns
        daily_calories = {}
        meal_times = {"breakfast": 0, "lunch": 0, "dinner": 0, "snack": 0}
        total_days = 0
        unique_foods = set()
        
        for log in recent_logs:
            date = log['date']
            if date not in daily_calories:
                daily_calories[date] = 0
                total_days += 1
            daily_calories[date] += log['total_calories']
            meal_times[log['meal_type']] += 1
            
            # Track unique foods
            for food in log.get('food_items', []):
                unique_foods.add(food['name'])
        
        avg_daily_calories = sum(daily_calories.values()) / max(total_days, 1)
        most_common_meal = max(meal_times, key=meal_times.get)
        
        return {
            "avg_daily_calories": avg_daily_calories,
            "most_common_meal": most_common_meal,
            "logging_consistency": total_days / 7,  # 0-1 scale
            "daily_calories": daily_calories,
            "unique_foods_count": len(unique_foods),
            "food_variety": list(unique_foods)
        }
    except Exception as e:
        return {
            "avg_daily_calories": 0,
            "most_common_meal": "breakfast",
            "logging_consistency": 0,
            "daily_calories": {},
            "unique_foods_count": 0,
            "food_variety": []
        }

async def create_coaching_tip(user_id: str, tip_type: str, title: str, message: str, 
                             priority: str = "medium", context: dict = None, expires_hours: int = 24):
    """Create and store a coaching tip"""
    tip_id = str(uuid.uuid4())
    expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
    
    tip = CoachingTip(
        tip_id=tip_id,
        user_id=user_id,
        tip_type=tip_type,
        title=title,
        message=message,
        priority=priority,
        context=context or {},
        is_read=False,
        created_at=datetime.now().isoformat(),
        expires_at=expires_at
    )
    
    await db.coaching_tips.insert_one(tip.dict())
    return tip

async def generate_contextual_tips(user_id: str, trigger_context: dict):
    """Generate contextual coaching tips based on user behavior"""
    try:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return
        
        today = datetime.now().strftime('%Y-%m-%d')
        current_hour = datetime.now().hour
        
        # Get today's stats
        daily_stats = await get_daily_stats_data(user_id, today)
        if not daily_stats:
            return
        
        patterns = await analyze_user_patterns(user_id)
        
        # Time-based context
        time_of_day = "morning" if current_hour < 12 else "afternoon" if current_hour < 18 else "evening"
        
        # Get active challenges count
        active_challenges_count = await db.user_challenges.count_documents({
            "user_id": user_id,
            "is_completed": False
        })
        
        context = {
            "calories_today": daily_stats['total_calories'],
            "protein_today": daily_stats['total_protein'],
            "time_of_day": time_of_day,
            "current_hour": current_hour,
            "patterns": patterns,
            "active_challenges": active_challenges_count
        }
        
        # Generate tips based on different scenarios
        
        # 1. Low calories by afternoon/evening
        calorie_percentage = (daily_stats['total_calories'] / daily_stats['calorie_target']) * 100
        if calorie_percentage < 50 and current_hour > 15:
            ai_message = await generate_ai_coaching_tip(user, context)
            await create_coaching_tip(
                user_id, "nutrition", "Calorie Boost Needed",
                f"You're at {daily_stats['total_calories']} calories today. {ai_message}",
                "high", context
            )
        
        # 2. Challenge motivation
        if active_challenges_count > 0 and random.random() < 0.3:  # 30% chance
            await create_coaching_tip(
                user_id, "challenge", "Challenge Update",
                f"You have {active_challenges_count} active challenges! Check your progress and keep pushing! 🏆",
                "medium", context
            )
        
        # 3. Food variety encouragement
        if patterns['unique_foods_count'] < 5 and random.random() < 0.2:  # 20% chance
            await create_coaching_tip(
                user_id, "nutrition", "Try Something New",
                f"You've logged {patterns['unique_foods_count']} different foods this week. Try adding some variety to your meals! 🌈",
                "low", context
            )
        
        # 4. Low protein
        protein_percentage = (daily_stats['total_protein'] / daily_stats['protein_target']) * 100
        if protein_percentage < 60 and current_hour > 12:
            suggestions = random.sample(MEAL_SUGGESTIONS["high_protein_snacks"], 2)
            await create_coaching_tip(
                user_id, "meal_suggestion", "Protein Power-Up",
                f"Your protein is at {int(daily_stats['total_protein'])}g. Try: {suggestions[0]} or {suggestions[1]}",
                "medium", context
            )
        
        # 5. Great streak encouragement with challenge mention
        if user.get('current_streak', 0) >= 3:
            await create_coaching_tip(
                user_id, "motivation", "Streak Champion!",
                f"Amazing {user['current_streak']}-day streak! 🔥 Keep it up and tackle some challenges for bonus points!",
                "low", context
            )
            
    except Exception as e:
        print(f"Error generating contextual tips: {e}")

async def check_and_award_badges(user_id: str, user_data: dict, log_count: int = 0, weight_count: int = 0):
    """Check for new badge achievements and award them"""
    current_badges = user_data.get('badges_earned', [])
    new_badges = []
    
    # First meal badge
    if 'first_meal' not in current_badges and log_count == 1:
        new_badges.append('first_meal')
    
    # Streak badges
    current_streak = user_data.get('current_streak', 0)
    streak_badges = [
        ('streak_3', 3), ('streak_7', 7), 
        ('streak_14', 14), ('streak_30', 30)
    ]
    
    for badge_key, required_streak in streak_badges:
        if badge_key not in current_badges and current_streak >= required_streak:
            new_badges.append(badge_key)
    
    # Weight logger badge
    if 'weight_logger' not in current_badges and weight_count >= 5:
        new_badges.append('weight_logger')
    
    # Challenge champion badge
    completed_challenges_count = len(user_data.get('completed_challenges', []))
    if 'challenge_champion' not in current_badges and completed_challenges_count >= 5:
        new_badges.append('challenge_champion')
    
    # Variety explorer badge
    patterns = await analyze_user_patterns(user_id)
    if 'variety_explorer' not in current_badges and patterns['unique_foods_count'] >= 20:
        new_badges.append('variety_explorer')
    
    # Calorie target badge (check today's performance)
    today = datetime.now().strftime('%Y-%m-%d')
    daily_stats = await get_daily_stats_data(user_id, today)
    if daily_stats and 'calorie_target' not in current_badges:
        if daily_stats['total_calories'] >= daily_stats['calorie_target']:
            new_badges.append('calorie_target')
    
    # Award new badges
    total_points_awarded = 0
    for badge_key in new_badges:
        badge_info = BADGES[badge_key]
        achievement = Achievement(
            achievement_id=str(uuid.uuid4()),
            user_id=user_id,
            badge_type=badge_key,
            badge_name=badge_info['name'],
            badge_description=badge_info['description'],
            points_awarded=badge_info['points'],
            earned_date=datetime.now().isoformat(),
            created_at=datetime.now().isoformat()
        )
        
        await db.achievements.insert_one(achievement.dict())
        total_points_awarded += badge_info['points']
    
    # Update user badges and points
    if new_badges:
        updated_badges = current_badges + new_badges
        updated_points = user_data.get('total_points', 0) + total_points_awarded
        
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "badges_earned": updated_badges,
                "total_points": updated_points
            }}
        )
    
    return new_badges, total_points_awarded

async def get_daily_stats_data(user_id: str, date: str) -> dict:
    """Helper function to get daily stats data"""
    try:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return None
        
        logs = await db.food_logs.find({"user_id": user_id, "date": date}, {"_id": 0}).to_list(100)
        
        total_calories = sum(log['total_calories'] for log in logs)
        total_protein = sum(log['total_protein'] for log in logs)
        total_carbs = sum(log['total_carbs'] for log in logs)
        total_fat = sum(log['total_fat'] for log in logs)
        
        return {
            'date': date,
            'total_calories': total_calories,
            'total_protein': total_protein,
            'total_carbs': total_carbs,
            'total_fat': total_fat,
            'calorie_target': user['daily_calorie_target'],
            'protein_target': user['daily_protein_target'],
            'carb_target': user['daily_carb_target'],
            'fat_target': user['daily_fat_target']
        }
    except:
        return None

async def analyze_food_image(image_base64: str) -> dict:
    """Use Emergent LLM to analyze food image and extract nutritional information"""
    try:
        # Create chat instance with Emergent LLM key
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"food_analysis_{uuid.uuid4()}",
            system_message="You are a nutrition expert. Analyze food images and provide accurate calorie and macro information."
        ).with_model("openai", "gpt-4o")
        
        # Create image content
        image_content = ImageContent(image_base64=image_base64)
        
        # Analyze the image
        user_message = UserMessage(
            text="""Analyze this food image and provide nutritional information in the following JSON format:
            
            {
                "foods": [
                    {
                        "name": "Food name",
                        "portion_size": "estimated portion (e.g., '1 cup', '150g', '1 medium')",
                        "calories": estimated_calories_as_integer,
                        "protein": protein_grams_as_float,
                        "carbs": carb_grams_as_float,
                        "fat": fat_grams_as_float
                    }
                ],
                "total_calories": total_calories_as_integer,
                "total_protein": total_protein_as_float,
                "total_carbs": total_carbs_as_float,
                "total_fat": total_fat_as_float,
                "confidence": "high/medium/low"
            }
            
            Be as accurate as possible with portion sizes and nutritional values. If multiple foods are visible, list each separately.""",
            file_contents=[image_content]
        )
        
        response = await chat.send_message(user_message)
        
        # Parse the JSON response
        try:
            # Extract JSON from response
            response_text = response.strip()
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            elif '{' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
            else:
                json_text = response_text
            
            nutrition_data = json.loads(json_text)
            return nutrition_data
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response: {response}")
            # Fallback with estimated values
            return {
                "foods": [{
                    "name": "Unknown Food",
                    "portion_size": "1 serving",
                    "calories": 300,
                    "protein": 15.0,
                    "carbs": 30.0,
                    "fat": 10.0
                }],
                "total_calories": 300,
                "total_protein": 15.0,
                "total_carbs": 30.0,
                "total_fat": 10.0,
                "confidence": "low"
            }
            
    except Exception as e:
        print(f"Error analyzing food image: {e}")
        # Return fallback data
        return {
            "foods": [{
                "name": "Unknown Food",
                "portion_size": "1 serving",
                "calories": 300,
                "protein": 15.0,
                "carbs": 30.0,
                "fat": 10.0
            }],
            "total_calories": 300,
            "total_protein": 15.0,
            "total_carbs": 30.0,
            "total_fat": 10.0,
            "confidence": "low"
        }

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Weight Gain App API with Challenges & Entertainment is running"}

@app.post("/api/users")
async def create_user(user_data: dict):
    """Create new user profile with coaching initialization and starter challenges"""
    try:
        user_id = str(uuid.uuid4())
        
        # Calculate TDEE and surplus for weight gain
        tdee = calculate_tdee(
            user_data['age'], 
            user_data['height_cm'], 
            user_data['weight_kg'], 
            user_data['gender'], 
            user_data['activity_level']
        )
        
        # Add caloric surplus based on target weekly gain
        surplus_map = {0.25: 250, 0.5: 500, 1.0: 750}  # kcal/day
        surplus = surplus_map.get(user_data['target_weekly_gain'], 500)
        daily_calorie_target = tdee + surplus
        
        # Calculate macro targets
        protein_target, carb_target, fat_target = calculate_macro_targets(daily_calorie_target)
        
        user = User(
            user_id=user_id,
            name=user_data['name'],
            age=user_data['age'],
            height_cm=user_data['height_cm'],
            weight_kg=user_data['weight_kg'],
            gender=user_data['gender'],
            activity_level=user_data['activity_level'],
            goal_weight_kg=user_data['goal_weight_kg'],
            target_weekly_gain=user_data['target_weekly_gain'],
            daily_calorie_target=daily_calorie_target,
            daily_protein_target=protein_target,
            daily_carb_target=carb_target,
            daily_fat_target=fat_target,
            created_date=datetime.now().isoformat(),
            total_points=0,
            current_streak=0,
            longest_streak=0,
            last_log_date=None,
            badges_earned=[],
            # Coaching initialization
            last_checkin_date=None,
            coaching_preferences={},
            tdee_adjustment_history=[],
            # Challenge initialization
            active_challenges=[],
            completed_challenges=[],
            challenge_points=0
        )
        
        await db.users.insert_one(user.dict())
        
        # Create welcome coaching tip
        await create_coaching_tip(
            user_id, "motivation", "Welcome to Your Journey!",
            f"Welcome {user_data['name']}! 🎉 Your daily calorie target is {daily_calorie_target}. Start by logging your first meal and take on some challenges to earn bonus points!",
            "high", {"onboarding": True}, expires_hours=72
        )
        
        # Create starter challenges
        starter_challenges = ["mega_meal", "morning_warrior"]
        for challenge_template in starter_challenges:
            challenge = await create_challenge(challenge_template)
            await db.challenges.insert_one(challenge.dict())
            await assign_challenge_to_user(user_id, challenge)
        
        return {"user_id": user_id, "user": user.dict()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get user profile"""
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/analyze-food")
async def analyze_food(file: UploadFile = File(...), user_id: str = Form(...)):
    """Analyze food image and return nutritional information"""
    try:
        # Read and encode image
        image_data = await file.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Analyze with AI
        nutrition_data = await analyze_food_image(image_base64)
        
        return {
            "nutrition_data": nutrition_data,
            "image_base64": image_base64
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/food-logs")
async def create_food_log(log_data: dict):
    """Create new food log entry with gamification, coaching, and challenges"""
    try:
        log_id = str(uuid.uuid4())
        
        # Calculate totals
        total_calories = sum(food['calories'] for food in log_data['food_items'])
        total_protein = sum(food['protein'] for food in log_data['food_items'])
        total_carbs = sum(food['carbs'] for food in log_data['food_items'])
        total_fat = sum(food['fat'] for food in log_data['food_items'])
        
        # Get user data for points calculation
        user = await db.users.find_one({"user_id": log_data['user_id']}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate points for this log
        points_earned = calculate_points_for_log(
            total_calories, user['daily_calorie_target'],
            total_protein, user['daily_protein_target']
        )
        
        # Update streak
        current_date = log_data['date']
        streak_increase, streak_continues = calculate_streak(
            user.get('last_log_date'), current_date
        )
        
        new_streak = user.get('current_streak', 0)
        if streak_continues:
            new_streak += streak_increase
        else:
            new_streak = 1
        
        longest_streak = max(user.get('longest_streak', 0), new_streak)
        
        # Create food log
        food_log = FoodLog(
            log_id=log_id,
            user_id=log_data['user_id'],
            date=log_data['date'],
            meal_type=log_data['meal_type'],
            food_items=log_data['food_items'],
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            image_base64=log_data.get('image_base64'),
            created_at=datetime.now().isoformat(),
            points_earned=points_earned
        )
        
        await db.food_logs.insert_one(food_log.dict())
        
        # Update user streak and points
        updated_points = user.get('total_points', 0) + points_earned
        await db.users.update_one(
            {"user_id": log_data['user_id']},
            {"$set": {
                "current_streak": new_streak,
                "longest_streak": longest_streak,
                "last_log_date": current_date,
                "total_points": updated_points
            }}
        )
        
        # Check for new badges
        log_count = await db.food_logs.count_documents({"user_id": log_data['user_id']})
        user_updated = await db.users.find_one({"user_id": log_data['user_id']}, {"_id": 0})
        new_badges, badge_points = await check_and_award_badges(
            log_data['user_id'], user_updated, log_count=log_count
        )
        
        # Update challenge progress
        daily_stats = await get_daily_stats_data(log_data['user_id'], current_date)
        challenge_context = {
            "trigger": "food_logged",
            "meal_type": log_data['meal_type'],
            "meal_calories": total_calories,
            "food_items": log_data['food_items'],
            "daily_stats": daily_stats
        }
        
        completed_challenges = await update_challenge_progress(log_data['user_id'], challenge_context)
        
        # Generate contextual coaching tips
        await generate_contextual_tips(log_data['user_id'], challenge_context)
        
        return {
            "log_id": log_id, 
            "food_log": food_log.dict(),
            "points_earned": points_earned,
            "new_badges": new_badges,
            "badge_points": badge_points,
            "current_streak": new_streak,
            "completed_challenges": completed_challenges
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/food-logs/{user_id}")
async def get_food_logs(user_id: str, date: Optional[str] = None):
    """Get food logs for user, optionally filtered by date"""
    query = {"user_id": user_id}
    if date:
        query["date"] = date
    
    logs = await db.food_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return logs

@app.post("/api/weight-entries")
async def create_weight_entry(weight_data: dict):
    """Create new weight entry with gamification, coaching, and challenges"""
    try:
        entry_id = str(uuid.uuid4())
        
        # Points for weight logging
        points_earned = 30
        
        weight_entry = WeightEntry(
            entry_id=entry_id,
            user_id=weight_data['user_id'],
            weight_kg=weight_data['weight_kg'],
            date=weight_data['date'],
            created_at=datetime.now().isoformat(),
            points_earned=points_earned
        )
        
        await db.weight_entries.insert_one(weight_entry.dict())
        
        # Update user points
        user = await db.users.find_one({"user_id": weight_data['user_id']}, {"_id": 0})
        if user:
            updated_points = user.get('total_points', 0) + points_earned
            await db.users.update_one(
                {"user_id": weight_data['user_id']},
                {"$set": {"total_points": updated_points}}
            )
            
            # Check for weight-related badges
            weight_count = await db.weight_entries.count_documents({"user_id": weight_data['user_id']})
            new_badges, badge_points = await check_and_award_badges(
                weight_data['user_id'], user, weight_count=weight_count
            )
            
            # Generate coaching tip based on weight progress
            await generate_weight_progress_tip(weight_data['user_id'], weight_data['weight_kg'])
        
        return {
            "entry_id": entry_id, 
            "weight_entry": weight_entry.dict(),
            "points_earned": points_earned,
            "new_badges": new_badges if 'new_badges' in locals() else [],
            "badge_points": badge_points if 'badge_points' in locals() else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def generate_weight_progress_tip(user_id: str, current_weight: float):
    """Generate coaching tip based on weight progress"""
    try:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return
        
        # Get weight history
        weight_entries = await db.weight_entries.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("date", -1).limit(10).to_list(10)
        
        if len(weight_entries) < 2:
            return
        
        # Calculate progress
        previous_weight = weight_entries[1]['weight_kg']
        weight_change = current_weight - previous_weight
        target_weight = user['goal_weight_kg']
        remaining_weight = target_weight - current_weight
        
        if weight_change > 0:
            await create_coaching_tip(
                user_id, "progress", "Weight Gain Progress! 🎉",
                f"Fantastic! You've gained {weight_change:.1f}kg. Only {remaining_weight:.1f}kg to your goal! Keep up the great work and tackle some challenges! 💪",
                "high", {"weight_change": weight_change, "remaining": remaining_weight}
            )
        elif weight_change < -0.5:
            await create_coaching_tip(
                user_id, "progress", "Stay Strong! 💪",
                f"Don't worry about the {abs(weight_change):.1f}kg dip. Focus on consistent eating and completing challenges - you'll bounce back stronger! 🔥",
                "medium", {"weight_change": weight_change}
            )
            
    except Exception as e:
        print(f"Error generating weight progress tip: {e}")

@app.get("/api/weight-entries/{user_id}")
async def get_weight_entries(user_id: str):
    """Get weight entries for user"""
    entries = await db.weight_entries.find({"user_id": user_id}, {"_id": 0}).sort("date", -1).to_list(100)
    return entries

@app.get("/api/daily-stats/{user_id}/{date}")
async def get_daily_stats(user_id: str, date: str):
    """Get daily nutrition stats for user with gamification, coaching and challenge data"""
    try:
        # Get user targets
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get food logs for the date
        logs = await db.food_logs.find({"user_id": user_id, "date": date}, {"_id": 0}).to_list(100)
        
        # Calculate totals
        total_calories = sum(log['total_calories'] for log in logs)
        total_protein = sum(log['total_protein'] for log in logs)
        total_carbs = sum(log['total_carbs'] for log in logs)
        total_fat = sum(log['total_fat'] for log in logs)
        
        # Calculate gamification stats
        points_earned_today = sum(log.get('points_earned', 0) for log in logs)
        calorie_percentage = (total_calories / user['daily_calorie_target']) * 100
        target_hit_percentage = min(calorie_percentage, 100)
        streak_status = user.get('last_log_date') == date
        
        # Get coaching tips for today
        coaching_tips = await db.coaching_tips.find({
            "user_id": user_id,
            "created_at": {"$gte": date + "T00:00:00", "$lte": date + "T23:59:59"},
            "is_read": False
        }, {"_id": 0}).sort("priority", -1).to_list(10)
        
        # Get active challenges
        active_challenges = await db.user_challenges.find({
            "user_id": user_id,
            "is_completed": False
        }, {"_id": 0}).to_list(20)
        
        # Get completed challenges today
        completed_challenges_today = await db.user_challenges.find({
            "user_id": user_id,
            "completed_date": date
        }, {"_id": 0}).to_list(20)
        
        stats = DailyStats(
            date=date,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            calorie_target=user['daily_calorie_target'],
            protein_target=user['daily_protein_target'],
            carb_target=user['daily_carb_target'],
            fat_target=user['daily_fat_target'],
            points_earned_today=points_earned_today,
            streak_status=streak_status,
            target_hit_percentage=target_hit_percentage,
            coaching_tips=coaching_tips,
            active_challenges=active_challenges,
            completed_challenges_today=completed_challenges_today
        )
        
        return stats.dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user-stats/{user_id}")
async def get_user_stats(user_id: str):
    """Get comprehensive user statistics and achievements"""
    try:
        # Get user data
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get aggregate statistics
        total_logs = await db.food_logs.count_documents({"user_id": user_id})
        total_weight_entries = await db.weight_entries.count_documents({"user_id": user_id})
        
        # Get challenge statistics
        active_challenges_count = await db.user_challenges.count_documents({
            "user_id": user_id,
            "is_completed": False
        })
        completed_challenges_count = await db.user_challenges.count_documents({
            "user_id": user_id,
            "is_completed": True
        })
        
        # Calculate average daily calories (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        recent_logs = await db.food_logs.find({
            "user_id": user_id,
            "date": {"$gte": thirty_days_ago}
        }, {"_id": 0}).to_list(1000)
        
        # Group by date and calculate daily totals
        daily_calories = {}
        for log in recent_logs:
            date = log['date']
            if date not in daily_calories:
                daily_calories[date] = 0
            daily_calories[date] += log['total_calories']
        
        avg_daily_calories = sum(daily_calories.values()) / max(len(daily_calories), 1)
        days_active = len(daily_calories)
        
        # Calculate goal completion rate
        target_hits = sum(1 for calories in daily_calories.values() 
                         if calories >= user['daily_calorie_target'] * 0.8)
        goal_completion_rate = (target_hits / max(days_active, 1)) * 100
        
        stats = UserStats(
            user_id=user_id,
            total_points=user.get('total_points', 0),
            current_streak=user.get('current_streak', 0),
            longest_streak=user.get('longest_streak', 0),
            badges_earned=user.get('badges_earned', []),
            total_logs=total_logs,
            total_weight_entries=total_weight_entries,
            days_active=days_active,
            avg_daily_calories=round(avg_daily_calories, 1),
            goal_completion_rate=round(goal_completion_rate, 1),
            challenge_points=user.get('challenge_points', 0),
            active_challenges_count=active_challenges_count,
            completed_challenges_count=completed_challenges_count
        )
        
        return stats.dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/achievements/{user_id}")
async def get_user_achievements(user_id: str):
    """Get all achievements for a user"""
    achievements = await db.achievements.find({"user_id": user_id}, {"_id": 0}).sort("earned_date", -1).to_list(100)
    
    # Add badge info to achievements
    for achievement in achievements:
        badge_key = achievement['badge_type']
        if badge_key in BADGES:
            achievement['icon'] = BADGES[badge_key]['icon']
    
    return achievements

@app.get("/api/badges")
async def get_all_badges():
    """Get all available badges with their requirements"""
    return BADGES

@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get top users by points (for future social features)"""
    try:
        # Get top users by total points
        users = await db.users.find(
            {}, 
            {"_id": 0, "name": 1, "total_points": 1, "current_streak": 1, "badges_earned": 1, "challenge_points": 1}
        ).sort("total_points", -1).limit(limit).to_list(limit)
        
        # Add ranking and ensure all fields are present
        for i, user in enumerate(users):
            user['rank'] = i + 1
            user['total_points'] = user.get('total_points', 0)
            user['current_streak'] = user.get('current_streak', 0)
            user['badges_earned'] = user.get('badges_earned', [])
            user['badge_count'] = len(user['badges_earned'])
            user['challenge_points'] = user.get('challenge_points', 0)
        
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Coaching API Endpoints
@app.get("/api/coaching/tips/{user_id}")
async def get_coaching_tips(user_id: str, limit: int = 20, unread_only: bool = False):
    """Get coaching tips for user"""
    try:
        query = {"user_id": user_id}
        if unread_only:
            query["is_read"] = False
        
        # Also filter out expired tips
        current_time = datetime.now().isoformat()
        query["$or"] = [
            {"expires_at": {"$gt": current_time}},
            {"expires_at": None}
        ]
        
        tips = await db.coaching_tips.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return tips
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/coaching/tips/{tip_id}/read")
async def mark_tip_as_read(tip_id: str):
    """Mark a coaching tip as read"""
    try:
        result = await db.coaching_tips.update_one(
            {"tip_id": tip_id},
            {"$set": {"is_read": True}}
        )
        if result.modified_count > 0:
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Tip not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/coaching/generate-tips/{user_id}")
async def generate_tips_manual(user_id: str):
    """Manually trigger coaching tip generation"""
    try:
        await generate_contextual_tips(user_id, {"trigger": "manual"})
        return {"success": True, "message": "Coaching tips generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/coaching/meal-suggestions/{user_id}")
async def get_meal_suggestions(user_id: str, meal_type: str = "any"):
    """Get personalized meal suggestions"""
    try:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        today = datetime.now().strftime('%Y-%m-%d')
        daily_stats = await get_daily_stats_data(user_id, today)
        
        if not daily_stats:
            # Fallback suggestions
            suggestions = random.sample(MEAL_SUGGESTIONS["high_calorie_breakfast"], 3)
        else:
            current_hour = datetime.now().hour
            calorie_percentage = (daily_stats['total_calories'] / daily_stats['calorie_target']) * 100
            protein_percentage = (daily_stats['total_protein'] / daily_stats['protein_target']) * 100
            
            # Smart suggestions based on current status
            if current_hour < 11:
                suggestions = random.sample(MEAL_SUGGESTIONS["high_calorie_breakfast"], 3)
            elif protein_percentage < 70:
                suggestions = random.sample(MEAL_SUGGESTIONS["high_protein_snacks"], 3)
            elif current_hour >= 18:
                suggestions = random.sample(MEAL_SUGGESTIONS["evening_meals"], 3)
            elif calorie_percentage < 60:
                suggestions = random.sample(MEAL_SUGGESTIONS["mass_building"], 3)
            else:
                suggestions = random.sample(MEAL_SUGGESTIONS["high_protein_snacks"], 3)
        
        return {
            "suggestions": suggestions,
            "context": {
                "current_hour": datetime.now().hour,
                "calories_needed": max(0, daily_stats['calorie_target'] - daily_stats['total_calories']) if daily_stats else user['daily_calorie_target'],
                "protein_needed": max(0, daily_stats['protein_target'] - daily_stats['total_protein']) if daily_stats else user['daily_protein_target']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/coaching/weekly-checkin/{user_id}")
async def perform_weekly_checkin(user_id: str):
    """Perform weekly check-in and TDEE adjustment"""
    try:
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate week dates
        today = datetime.now()
        week_start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        week_end = today.strftime('%Y-%m-%d')
        
        # Get weight entries for the week
        weight_entries = await db.weight_entries.find({
            "user_id": user_id,
            "date": {"$gte": week_start, "$lte": week_end}
        }, {"_id": 0}).sort("date", 1).to_list(100)
        
        if len(weight_entries) < 2:
            return {"success": False, "message": "Need at least 2 weight entries for weekly check-in"}
        
        starting_weight = weight_entries[0]['weight_kg']
        ending_weight = weight_entries[-1]['weight_kg']
        weight_change = ending_weight - starting_weight
        expected_change = user['target_weekly_gain']
        
        # Get food logs for the week
        food_logs = await db.food_logs.find({
            "user_id": user_id,
            "date": {"$gte": week_start, "$lte": week_end}
        }, {"_id": 0}).to_list(1000)
        
        # Calculate average daily calories
        daily_calories = {}
        for log in food_logs:
            date = log['date']
            if date not in daily_calories:
                daily_calories[date] = 0
            daily_calories[date] += log['total_calories']
        
        avg_daily_calories = sum(daily_calories.values()) / max(len(daily_calories), 1)
        goal_hit_rate = sum(1 for calories in daily_calories.values() 
                           if calories >= user['daily_calorie_target'] * 0.8) / max(len(daily_calories), 1) * 100
        
        # Determine TDEE adjustment
        tdee_adjustment = 0
        if weight_change < expected_change * 0.7:  # Less than 70% of expected gain
            tdee_adjustment = 150  # Increase calories
        elif weight_change > expected_change * 1.3:  # More than 130% of expected gain
            tdee_adjustment = -100  # Decrease calories slightly
        
        # Generate coaching summary
        context = {
            "weight_change": weight_change,
            "expected_change": expected_change,
            "avg_calories": avg_daily_calories,
            "goal_hit_rate": goal_hit_rate
        }
        
        coaching_summary = await generate_ai_coaching_tip(user, context)
        
        # Create weekly check-in record
        checkin = WeeklyCheckin(
            checkin_id=str(uuid.uuid4()),
            user_id=user_id,
            week_start_date=week_start,
            week_end_date=week_end,
            starting_weight=starting_weight,
            ending_weight=ending_weight,
            weight_change=weight_change,
            expected_change=expected_change,
            avg_daily_calories=avg_daily_calories,
            goal_hit_rate=goal_hit_rate,
            tdee_adjustment=tdee_adjustment,
            coaching_summary=coaching_summary,
            created_at=datetime.now().isoformat()
        )
        
        await db.weekly_checkins.insert_one(checkin.dict())
        
        # Update user's calorie target if adjustment needed
        if tdee_adjustment != 0:
            new_target = user['daily_calorie_target'] + tdee_adjustment
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "daily_calorie_target": new_target,
                    "last_checkin_date": week_end
                },
                "$push": {
                    "tdee_adjustment_history": {
                        "date": week_end,
                        "adjustment": tdee_adjustment,
                        "reason": f"Weekly check-in: {weight_change:.1f}kg vs {expected_change:.1f}kg expected"
                    }
                }}
            )
            
            # Create coaching tip about the adjustment
            await create_coaching_tip(
                user_id, "progress", "Target Adjusted! 🎯",
                f"Based on your progress, your daily target is now {new_target} calories. {coaching_summary} Keep up the great work and tackle some challenges! 💪",
                "high", context, expires_hours=72
            )
        
        return {
            "success": True,
            "checkin": checkin.dict(),
            "tdee_adjustment": tdee_adjustment,
            "new_target": user['daily_calorie_target'] + tdee_adjustment
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/coaching/weekly-checkins/{user_id}")
async def get_weekly_checkins(user_id: str, limit: int = 10):
    """Get weekly check-in history"""
    try:
        checkins = await db.weekly_checkins.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("week_end_date", -1).limit(limit).to_list(limit)
        return checkins
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Challenge API Endpoints
@app.get("/api/challenges")
async def get_available_challenges():
    """Get all available challenge templates"""
    return CHALLENGE_TEMPLATES

@app.get("/api/challenges/active/{user_id}")
async def get_active_challenges(user_id: str):
    """Get active challenges for user with progress"""
    try:
        # Get active user challenges
        user_challenges = await db.user_challenges.find({
            "user_id": user_id,
            "is_completed": False
        }, {"_id": 0}).to_list(50)
        
        # Get challenge details for each
        active_challenges = []
        for user_challenge in user_challenges:
            challenge = await db.challenges.find_one(
                {"challenge_id": user_challenge['challenge_id']}, {"_id": 0}
            )
            if challenge:
                # Check if challenge is still valid
                today = datetime.now().strftime('%Y-%m-%d')
                if today <= challenge['end_date']:
                    combined = {
                        **user_challenge,
                        **challenge,
                        "progress_percentage": (user_challenge['current_progress'] / user_challenge['goal_value']) * 100
                    }
                    active_challenges.append(combined)
        
        return active_challenges
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/challenges/completed/{user_id}")
async def get_completed_challenges(user_id: str, limit: int = 20):
    """Get completed challenges for user"""
    try:
        completed_challenges = await db.user_challenges.find({
            "user_id": user_id,
            "is_completed": True
        }, {"_id": 0}).sort("completed_date", -1).limit(limit).to_list(limit)
        
        # Get challenge details
        for user_challenge in completed_challenges:
            challenge = await db.challenges.find_one(
                {"challenge_id": user_challenge['challenge_id']}, {"_id": 0}
            )
            if challenge:
                user_challenge.update(challenge)
        
        return completed_challenges
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/challenges/join/{user_id}")
async def join_challenge(user_id: str, challenge_data: dict):
    """Join a new challenge"""
    try:
        challenge_template = challenge_data.get('challenge_template')
        if not challenge_template or challenge_template not in CHALLENGE_TEMPLATES:
            raise HTTPException(status_code=400, detail="Invalid challenge template")
        
        # Check if user already has this challenge active
        existing = await db.user_challenges.find_one({
            "user_id": user_id,
            "is_completed": False
        })
        
        # Create new challenge
        challenge = await create_challenge(challenge_template)
        await db.challenges.insert_one(challenge.dict())
        
        # Assign to user
        user_challenge = await assign_challenge_to_user(user_id, challenge)
        
        # Create motivation tip
        await create_coaching_tip(
            user_id, "challenge", "New Challenge Accepted! 🏆",
            f"You've joined '{challenge.title}'! {challenge.description}. Earn {challenge.points_reward} points when you complete it! 💪",
            "high", {"challenge_id": challenge.challenge_id}
        )
        
        return {
            "success": True,
            "challenge": challenge.dict(),
            "user_challenge": user_challenge.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/challenges/create-random/{user_id}")
async def create_random_challenges(user_id: str):
    """Create 2-3 random challenges for user"""
    try:
        # Select 2-3 random challenge templates
        available_templates = list(CHALLENGE_TEMPLATES.keys())
        selected_templates = random.sample(available_templates, min(3, len(available_templates)))
        
        created_challenges = []
        for template in selected_templates:
            challenge = await create_challenge(template)
            await db.challenges.insert_one(challenge.dict())
            user_challenge = await assign_challenge_to_user(user_id, challenge)
            created_challenges.append({
                "challenge": challenge.dict(),
                "user_challenge": user_challenge.dict()
            })
        
        # Create notification
        await create_coaching_tip(
            user_id, "challenge", "New Challenges Available! 🎯",
            f"Great news! {len(created_challenges)} new challenges are ready for you. Complete them to earn bonus points and stay motivated! 🏆",
            "high", {"new_challenges": len(created_challenges)}
        )
        
        return {
            "success": True,
            "challenges_created": len(created_challenges),
            "challenges": created_challenges
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)