from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import pandas as pd
from psycopg2.extras import RealDictCursor

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Environment variables for database credentials
DB_NAME = os.getenv("DB_NAME", "material_db")
DB_USER = os.getenv("DB_USER", "replicator")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Ant-admin@123")
DB_HOST = os.getenv("DB_HOST", "34.100.200.180")
DB_PORT = int(os.getenv("DB_PORT", 5432))

# Function to connect to the database
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print("Database connection error:", e)
        return None


# Route to fetch all purchasing_groups
@app.route("/purchasing_group", methods=["GET"])
def get_all_purchasing_groups():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Unable to connect to the database"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT DISTINCT purchasing_group from purchasing_group_warora"
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            return jsonify({"error": "No purchasing groups found"}), 404

        purchasing_group = [{"purchasing_group": row["purchasing_group"]} for row in results]
        
        return jsonify({"purchasing_group": purchasing_group}), 200

    except Exception as e:
        print("Error while fetching purchasing groups:", e) # Updated message
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500 # More detailed error response
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

from flask import Flask, request, jsonify, current_app
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Configure Logging
logging.basicConfig(level=logging.INFO)

def get_db_connection():
    try:
        return psycopg2.connect(
            dbname="your_db",
            user="your_user",
            password="your_password",
            host="your_host",
            port="your_port"
        )
    except Exception as e:
        current_app.logger.error(f"Database connection error: {e}")
        return None

@app.route("/purchasing_group/data", methods=["GET"])
def get_purchasing_group_data():
    """ Fetch material IDs for given purchasing groups. """
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Unable to connect to the database"}), 500

    cursor = None  # Initialize cursor to avoid reference issues in finally block

    try:
        # Get purchasing_groups parameter from URL
        purchasing_groups = request.args.get("purchasing_groups")
        
        if not purchasing_groups:
            return jsonify({"error": "No purchasing groups provided"}), 400

        # Convert to list and limit to 4 items
        purchasing_groups_list = purchasing_groups.split(",")[:4]

        # Ensure valid input (remove empty strings)
        purchasing_groups_list = [pg.strip() for pg in purchasing_groups_list if pg.strip()]
        
        if not purchasing_groups_list:
            return jsonify({"error": "Invalid purchasing groups provided"}), 400

        # SQL Query
        query = """
            SELECT purchasing_group, material_id
            FROM purchasing_group_warora 
            WHERE purchasing_group = ANY(%s)
        """

        # Execute Query
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (purchasing_groups_list,))
        
        results = cursor.fetchall()

        if not results:
            return jsonify({"error": "No data found for given purchasing groups"}), 404

        # Organize data by purchasing group
        grouped_data = {}
        for row in results:
            pg = row["purchasing_group"]
            if pg not in grouped_data:
                grouped_data[pg] = []
            grouped_data[pg].append(row["material_id"])

        return jsonify({"data": grouped_data}), 200

    except Exception as e:
        current_app.logger.error(f"Error while fetching data: {e}")
        return jsonify({"error": "An error occurred while fetching the data"}), 500

    finally:
        # Ensure cursor and connection are closed properly
        if cursor:
            cursor.close()
        conn.close()


# Run the Flask app (for Cloud Run)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

