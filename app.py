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
DB_NAME = os.getenv("DB_NAME", "postgres")
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

# Route to fetch all material IDs
@app.route("/materials", methods=["GET"])
def get_all_materials():
    # Connect to the database
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Unable to connect to the database"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query to fetch distinct material IDs and descriptions
        query = "SELECT DISTINCT material_id, material_description FROM material_data"
        cursor.execute(query)
        results = cursor.fetchall()

        if not results:
            return jsonify({"error": "No materials found"}), 404
        
        # Prepare the response as key-value pairs
        materials = [
            {"material_id": row["material_id"], "material_description": row["material_description"]}
            for row in results
        ]
        return jsonify({"materials": materials}), 200
    except Exception as e:
        print("Error while fetching materials:", e)
        return jsonify({"error": "An error occurred while fetching materials"}), 500
    finally:
        cursor.close()
        conn.close()

# Route to fetch all purchasing_groups
@app.route("/purchasing_group", methods=["GET"])
def get_all_purchasing_groups():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Unable to connect to the database"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT DISTINCT Purchasing_Group FROM purchasing_groupwise_materialids_warora"
        cursor.execute(query)
        results = cursor.fetchall()
        #hello

        if not results:
            return jsonify({"error": "No purchasing groups found"}), 404

        purchasing_groups = [{"purchasing_group": row["purchasing_group"]} for row in results]
        
        return jsonify({"purchasing_groups": purchasing_groups}), 200

    except Exception as e:
        print("Error while fetching purchasing groups:", e) # Updated message
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500 # More detailed error response
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Route to fetch data for a selected purchasing_group
@app.route("/purchasing_group/data", methods=["GET"])
def get_purchasing_group_data():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Unable to connect to the database"}), 500

    try:
        purchasing_groups = request.args.get("purchasing_groups")
        
        if not purchasing_groups:
            return jsonify({"error": "No purchasing groups provided"}), 400

        purchasing_groups_list = purchasing_groups.split(",")[:4]

        query = """
            SELECT purchasing_group, material_id
            FROM purchasing_groupwise_materialids_warora 
            WHERE purchasing_group = ANY(%s)
        """
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (purchasing_groups_list,))
        results = cursor.fetchall()

        if not results:
            return jsonify({"error": "No data found for given purchasing groups"}), 404

        grouped_data = {}
        for row in results:
            pg = row["purchasing_group"]
            if pg not in grouped_data:
                grouped_data[pg] = []
            grouped_data[pg].append(row["material_id"])

        return jsonify({"data": grouped_data}), 200
    except Exception as e:
        print("Error while fetching data:", e)
        return jsonify({"error": "An error occurred while fetching the data"}), 500
    finally:
        cursor.close()
        conn.close()

# Run the Flask app (for Cloud Run)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

