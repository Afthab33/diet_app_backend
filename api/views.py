import json
import os
from openai import OpenAI, OpenAIError
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['POST'])
def generate_diet(request):

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    data = request.data

    # Extracting data from frontend
    total_calories = int(data.get("calories", 0))
    total_protein = int(data.get("protein", 0))
    total_carbs = int(data.get("carbs", 0))
    total_fats = int(data.get("fats", 0))
    meals_per_day = int(data.get("meals_per_day", 3))
    diet_type = data.get("diet_type", "non-veg")
    cuisines = data.get("cuisines", [])
    food_res = data.get("food_restrictions", [])

    # Suggested meal timing
    meal_timing_map = {
        3: ["8:00 AM", "1:00 PM", "7:00 PM"],
        4: ["8:00 AM", "12:00 PM", "4:00 PM", "8:00 PM"]
    }
    meal_timings = meal_timing_map.get(meals_per_day, [])

    # Distribute macros across meals evenly
    meal_ratios = [0.33, 0.33, 0.34] if meals_per_day == 3 else [1.0 / meals_per_day] * meals_per_day

    adjusted_meal_plan = []
    for i, ratio in enumerate(meal_ratios):
        adjusted_meal_plan.append({
            "meal_number": i + 1,
            "calories": round(total_calories * ratio),
            "protein": round(total_protein * ratio),
            "carbs": round(total_carbs * ratio),
            "fats": round(total_fats * ratio)
        })

    # Prompt for GPT
    prompt = f"""
    You are an expert nutritionist. Return a **1-day meal plan** in **VALID JSON ONLY**. No text outside JSON.

    ### Restrictions:
    - **Exclude**: {', '.join(food_res)}
    - Replace with alternatives.

    ### Targets:
    - Calories: {total_calories}, Protein: {total_protein}, Carbs: {total_carbs}, Fats: {total_fats}

    ### Plan:
    - Meals: {meals_per_day}, Diet: {diet_type}, Cuisine: {', '.join(cuisines)}

    ### Breakdown:
    """
    for meal in adjusted_meal_plan:
        prompt += f"""
    - Meal {meal['meal_number']}:
        - Foods (strictly **3-5 items**, format: "item, qty, cal, pro, carb, fat"):
        """

    prompt += """
    ### Rules:
    1) **VALID JSON ONLY**. No extra text.
    2) **Exclude**: {', '.join(food_res)}
    3) Replace restricted foods with **alternatives**.
    4) Use **integers only** for macros (calories, protein, carbs, fats).
    5) Each meal must contain:
        - "meal_number" (int)
        - "foods": [list of **strings only**, formatted as "item, qty, cal, pro, carb, fat"]
    6) **Limit: strictly 3-5 foods per meal**.
    7) **No meal timings, no calorie totals** in the output.
    8) Use **only the specified cuisines**.
    9) **No supplements in meals**.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional nutritionist. Respond with JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=1000
        )

        diet_plan_content = response.choices[0].message.content.strip()
        try:
            diet_plan = json.loads(diet_plan_content)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format received from OpenAI"}, status=500)

        return Response(diet_plan, status=200)

    except OpenAIError as e:
        return Response({"error": str(e)}, status=500)
    except Exception as e:
        return Response({"error": f"Unexpected error: {str(e)}"}, status=500)