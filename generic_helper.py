    
import re

def get_str_from_food_dict(food_dict: dict):
    result = ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])
    return result


def extract_session_id(session_str: str):
    match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    return match.group(1) if match else ""



import mysql.connector
from fastapi.responses import JSONResponse

# Database connection function (reuse anywhere)
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Mysql@1234",
        database="pandeyji_eatery"
    )

# Function to insert order into DB and send response to Dialogflow
def insert_order_to_db(parameters: dict, session_id: str):
    try:
        # Extract food items and quantities from Dialogflow parameters
        food_items = parameters.get("food-items", [])
        quantities = parameters.get("number", [])

        # Validate input
        if not food_items or not quantities:
            return JSONResponse(content={
                "fulfillmentText": "Sorry, I didn't understand your order. Please try again."
            })

        # Connect to DB
        connection = get_db_connection()
        cursor = connection.cursor()

        # Insert each item into database
        for item, qty in zip(food_items, quantities):
            cursor.execute(
                "INSERT INTO order_tracking (session_id, food_item, quantity, status) VALUES (%s, %s, %s, %s)",
                (session_id, item, int(qty), "Pending")
            )

        connection.commit()
        cursor.close()
        connection.close()

        # Prepare success response
        items_text = ", ".join([f"{qty} {item}" for item, qty in zip(food_items, quantities)])
        fulfillment_text = f"✅ Your order for {items_text} has been placed successfully! 🎉"

        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })

    except mysql.connector.Error as e:
        # Handle DB errors
        return JSONResponse(content={
            "fulfillmentText": "⚠️ Sorry, I could not process your order. Please place a new order."
        })

    except Exception as e:
        # Handle unexpected errors
        return JSONResponse(content={
            "fulfillmentText": "⚠️ Something went wrong. Please try again later."
        })
