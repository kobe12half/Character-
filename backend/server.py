import os
import uuid
import base64
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
import json

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
    }
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
    return {"status": "healthy", "message": "Weight Gain App API is running"}

@app.post("/api/users")
async def create_user(user_data: dict):
    """Create new user profile"""
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
            badges_earned=[]
        )
        
        await db.users.insert_one(user.dict())
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
    """Create new food log entry with gamification"""
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
        
        return {
            "log_id": log_id, 
            "food_log": food_log.dict(),
            "points_earned": points_earned,
            "new_badges": new_badges,
            "badge_points": badge_points,
            "current_streak": new_streak
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
    """Create new weight entry with gamification"""
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
        
        return {
            "entry_id": entry_id, 
            "weight_entry": weight_entry.dict(),
            "points_earned": points_earned,
            "new_badges": new_badges if 'new_badges' in locals() else [],
            "badge_points": badge_points if 'badge_points' in locals() else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/weight-entries/{user_id}")
async def get_weight_entries(user_id: str):
    """Get weight entries for user"""
    entries = await db.weight_entries.find({"user_id": user_id}, {"_id": 0}).sort("date", -1).to_list(100)
    return entries

@app.get("/api/daily-stats/{user_id}/{date}")
async def get_daily_stats(user_id: str, date: str):
    """Get daily nutrition stats for user with gamification data"""
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
            target_hit_percentage=target_hit_percentage
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
            goal_completion_rate=round(goal_completion_rate, 1)
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
            {"_id": 0, "name": 1, "total_points": 1, "current_streak": 1, "badges_earned": 1}
        ).sort("total_points", -1).limit(limit).to_list(limit)
        
        # Add ranking
        for i, user in enumerate(users):
            user['rank'] = i + 1
            user['badge_count'] = len(user.get('badges_earned', []))
        
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)