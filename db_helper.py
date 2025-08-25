import mysql.connector
from mysql.connector import Error
import difflib
from difflib import get_close_matches


def get_order_status(order_id: int):
    try: # for each function use another connection
        cnx = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Mysql@1234",
            database="pandeyji_eatery"
        )
        cursor = cnx.cursor()
        query = "SELECT status FROM order_tracking WHERE order_id = %s"
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()
        cursor.close()
        cnx.close()      

        return result[0] if result else None
    except Error as e:
        return f"Database error: {e}"
    


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Mysql@1234",
        database="pandeyji_eatery"
    )


# Function to get the next available order_id
def get_next_order_id():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT MAX(order_id) FROM orders"
        cursor.execute(query)
        result = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return 1 if result is None else result + 1

    except mysql.connector.Error as err:
        print(f"Error fetching next order ID: {err}")
        return -1



def insert_order_item(food_item, quantity, order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ✅ Get all food items
        cursor.execute("SELECT name FROM food_items")
        items = [row[0] for row in cursor.fetchall()]
        # ✅ Find the closest match
        best_match = get_close_matches(food_item, items, n=1, cutoff=0.3)
        if not best_match:
            print(f"❌ Food item not found in menu: {food_item}")
            return -1
        matched_name = best_match[0]
        print(f"🔹 Closest match found: {matched_name}")
        # ✅ Call stored procedure with NAME, not item_id
        cursor.callproc('insert_order_item', (matched_name, quantity, order_id))
        conn.commit()
        cursor.close()
        conn.close()    
    except mysql.connector.Error as err:
        print(f"❌ Error inserting order item: {err}")
        return -1   
    
            

def get_total_order_price(order_id: int):
    try:
        # Get DB connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Call the stored function safely
        query = "SELECT get_total_order_price(%s)"
        cursor.execute(query, (order_id,))

        # Fetch the result
        result = cursor.fetchone()[0]

        # Close cursor & connection
        cursor.close()
        conn.close()

        # Return the total price
        return result if result is not None else 0
    except Exception as e:
        print(f"Error fetching total order price: {e}")
        return None


# -------- INSERT INTO ORDER TRACKING ----------

def insert_order_tracking(order_id: int, status: str ):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
        cursor.execute(query, (order_id, status))

        conn.commit()
        cursor.close()
        conn.close()
        return 1

    except mysql.connector.Error as err:
        print(f"Error inserting order tracking: {err}")
        return -1
    















       

    
