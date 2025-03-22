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
    #cuisines = data.get("cuisines", [])
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
        You are an expert nutritionist creating a practical, realistic meal plan. Return a **1-day meal plan** in **VALID JSON ONLY**. No text outside JSON.

        ### User Profile:
        - Daily targets: Calories: {total_calories}, Protein: {total_protein}g, Carbs: {total_carbs}g, Fats: {total_fats}g
        - Meals per day: {meals_per_day}
        - Diet type: {diet_type}
        - Food restrictions: {', '.join(food_res)}

        ### Meal Planning Guidelines:
        1) Create realistic, culturally appropriate meals for each time of day:
        - Breakfast: Include breakfast-appropriate foods (eggs, oatmeal, yogurt, toast, fruit)
        - Lunch: Focus on practical, commonly eaten lunch foods
        - Dinner: Can include more elaborate meals but still realistic for everyday
        - Snacks (if applicable): Convenient, portable options

        2) Practical considerations:
        - Focus on commonly available, affordable ingredients
        - Limit specialty or expensive items (like salmon) to 1-2 times per week
        - Ensure variety while maintaining some staple items
        - Consider preparation time and complexity

        3) Food appropriateness:
        - Do not include dinner foods for breakfast (e.g., no chicken breast with rice at breakfast)
        - Ensure foods are appropriate for the meal type and time of day

        ### Output Format:
        1) **VALID JSON ONLY**. No extra text.
        2) The day must have {meals_per_day} meals with appropriate foods for that meal type
        3) Each meal must contain:
        - "day" (int)
        - "meal_type" (string: "breakfast", "lunch", "dinner", or "snack")
        - "foods": [list of **strings only**, formatted as "item, qty, cal, pro, carb, fat"]
        4) Limit to 3-5 foods per meal
        5) No meal totals or supplements in the output

        ### Example of appropriate breakfast foods:
        - Eggs, oatmeal, Greek yogurt, toast, fruit, smoothies, breakfast cereals

        ### Example of appropriate lunch/dinner foods:
        - Sandwiches, salads, soups, stir-fries, lean meats with sides
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional nutritionist. Always return a valid JSON object. Do not wrap JSON in code blocks (` ```json `)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=1000
        )

        try:
            diet_plan_content = response.choices[0].message.content.strip()
            print("Raw OpenAI Response:", diet_plan_content)  # Debugging Step

            diet_plan = json.loads(diet_plan_content)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format received from OpenAI", "raw_response": diet_plan_content}, status=500)


        return Response(diet_plan, status=200)

    except OpenAIError as e:
        return Response({"error": str(e)}, status=500)
    except Exception as e:
        return Response({"error": f"Unexpected error: {str(e)}"}, status=500)