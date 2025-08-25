from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import db_helper
import generic_helper
import mysql.connector
import difflib

app = FastAPI()
inprogress_orders = {}

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()

    intent = payload["queryResult"]["intent"]["displayName"]
    parameters = payload["queryResult"]["parameters"]
    output_contexts = payload["queryResult"]["outputContexts"]
    session_id = generic_helper.extract_session_id(output_contexts[0]["name"])

   
    intent_handler_dict={
        "order.add- context: ongoing-order":add_to_order,
        "order.remove - context: ongoing-order":remove_from_order,
        "order.complete - context: ongoing-order": complete_order,        
        "track.order - context: ongoing-tracking":track_order,
    }
    return intent_handler_dict[intent](parameters, session_id)


# function to remove the order
def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having trouble finding your order. Sorry! Can you place a new order, please?"
        })

    food_items = parameters.get("food-items", [])
    if isinstance(food_items, str):
        food_items = [food_items]  # Ensure it's always a list

    current_order = inprogress_orders[session_id]
    removed_items = []
    no_such_items = []
    fulfillment_text = ""

    for item in food_items:
        # Fuzzy match with current order keys
        match = difflib.get_close_matches(item.lower(), [food.lower() for food in current_order.keys()], n=1, cutoff=0.6)

        if match:
            # Find the exact key from current_order (case-sensitive)
            exact_key = next(food for food in current_order if food.lower() == match[0])
            removed_items.append(exact_key)
            del current_order[exact_key]
        else:
            no_such_items.append(item)

    # Build response text
    if removed_items:
        fulfillment_text += f"✅ Removed {', '.join(removed_items)} from your order!"

    if no_such_items:
        fulfillment_text += f" ❌ Couldn't find {', '.join(no_such_items)} in your current order."

    if len(current_order) == 0:
        fulfillment_text += " 🛒 Your order is now empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" 📝 Here's what's left in your order: {order_str}.\n Do you need anything else?"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


# function to complete the order
def complete_order(Parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={"fulfillmentText": "Sorry! I lost your order. Can you place it again?"}) 
    else:
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I could not process your order. please place the new order."
        else:
            order_total=db_helper.get_total_order_price(order_id)
            fulfillment_text = f"Awesome 🎉! Your order ID is {order_id}. Total price: {int(order_total)} $." 

        del  inprogress_orders[session_id]    
        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })
def save_to_db(order: dict):
    try:
        # Get next order ID
        next_order_id = db_helper.get_next_order_id()
        # Insert each food item
        for food_item,quantity in order.items():
            rcode =  db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        ) 
            if rcode == -1:
                return -1          
        # Insert order tracking
        track_result = db_helper.insert_order_tracking(next_order_id, "inprogress")
        if track_result == -1:
            print("❌ Failed to insert order tracking!")
            return -1
        print(f"✅ Order {next_order_id} saved successfully!")
        return next_order_id
    except Exception as e:
        print(f"⚠️ Unexpected Error in save_to_db(): {e}")
        return -1
 

def add_to_order(parameters: dict, session_id: str):
    try:
        # Get quantities & food items from Dialogflow parameters
        raw_quantities = parameters.get("number", [])
        food_items = parameters.get("food-items", [])

        # Convert all quantities to integers
        quantities = []
        for q in raw_quantities:
            try:
                quantities.append(int(q))  # Convert safely
            except ValueError:
                return JSONResponse(content={
                    "fulfillmentText": f"Sorry 😅, I couldn't understand the quantity '{q}'. Please use numbers only."
                })

        # Check if quantities and food items match
        if len(food_items) != len(quantities):
            fulfillment_text = "Sorry, I didn't understand 😅. Please specify food items and quantities clearly."
        else:      
            new_food_dict = dict(zip(food_items,quantities))
            if session_id in inprogress_orders:
                current_food_dict = inprogress_orders[session_id]
                current_food_dict.update(new_food_dict)
            else:
                inprogress_orders[session_id] = new_food_dict

            order_str =  generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
            
            fulfillment_text = f"Okay ✅! I have added: {order_str}. Do you need any thing else?"

        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })

    except Exception as e:
        # Catch unexpected errors so Dialogflow doesn't crash
        return JSONResponse(content={
            "fulfillmentText": f"Oops! Something went wrong 😢: {str(e)}"
        })



def track_order(parameters: dict, session_id: str = None):
    # Get order_id from parameters sent by Dialogflow
    order_numbers = parameters.get("number")
    if not order_numbers:
        return JSONResponse(content={"fulfillmentText": "Please provide an order ID to track."})

    order_id = int(order_numbers[0])

    # Fetch order status from database
    order_status = db_helper.get_order_status(order_id)

    # Prepare response for Dialogflow
    if order_status:
        fulfillment_text = f"For your order ID {order_id}, the status is: {order_status}"
    else:
        fulfillment_text = f"No order found with ID {order_id}"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})


      