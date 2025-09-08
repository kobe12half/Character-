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

class WeightEntry(BaseModel):
    entry_id: str
    user_id: str
    weight_kg: float
    date: str
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
            created_date=datetime.now().isoformat()
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
    """Create new food log entry"""
    try:
        log_id = str(uuid.uuid4())
        
        # Calculate totals
        total_calories = sum(food['calories'] for food in log_data['food_items'])
        total_protein = sum(food['protein'] for food in log_data['food_items'])
        total_carbs = sum(food['carbs'] for food in log_data['food_items'])
        total_fat = sum(food['fat'] for food in log_data['food_items'])
        
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
            created_at=datetime.now().isoformat()
        )
        
        await db.food_logs.insert_one(food_log.dict())
        return {"log_id": log_id, "food_log": food_log.dict()}
        
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
    """Create new weight entry"""
    try:
        entry_id = str(uuid.uuid4())
        
        weight_entry = WeightEntry(
            entry_id=entry_id,
            user_id=weight_data['user_id'],
            weight_kg=weight_data['weight_kg'],
            date=weight_data['date'],
            created_at=datetime.now().isoformat()
        )
        
        await db.weight_entries.insert_one(weight_entry.dict())
        return {"entry_id": entry_id, "weight_entry": weight_entry.dict()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/weight-entries/{user_id}")
async def get_weight_entries(user_id: str):
    """Get weight entries for user"""
    entries = await db.weight_entries.find({"user_id": user_id}, {"_id": 0}).sort("date", -1).to_list(100)
    return entries

@app.get("/api/daily-stats/{user_id}/{date}")
async def get_daily_stats(user_id: str, date: str):
    """Get daily nutrition stats for user"""
    try:
        # Get user targets
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get food logs for the date
        logs = await db.food_logs.find({"user_id": user_id, "date": date}).to_list(100)
        
        # Calculate totals
        total_calories = sum(log['total_calories'] for log in logs)
        total_protein = sum(log['total_protein'] for log in logs)
        total_carbs = sum(log['total_carbs'] for log in logs)
        total_fat = sum(log['total_fat'] for log in logs)
        
        stats = DailyStats(
            date=date,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            calorie_target=user['daily_calorie_target'],
            protein_target=user['daily_protein_target'],
            carb_target=user['daily_carb_target'],
            fat_target=user['daily_fat_target']
        )
        
        return stats.dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)