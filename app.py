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
            FROM purchasing_group_warora 
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
        #return jsonify({"error": "An error occurred while fetching the data"}), 500
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

# Route to fetch data for a selected material ID
@app.route("/materials/data", methods=["GET"])
def get_material_data():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Unable to connect to the database"}), 500

    try:
        # Get material IDs from request query parameters
        material_ids = request.args.get("material_ids")
        
        if not material_ids:
            return jsonify({"error": "No material IDs provided"}), 400

        # Convert to a list and limit to 4
        material_ids_list = material_ids.split(",")[:4]

        # Format query for multiple material IDs
        query = f"""
            SELECT date, material_id, base_unit_of_measure, quantity, price
            FROM material_data 
            WHERE material_id = ANY(%s)
        """
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (material_ids_list,))
        results = cursor.fetchall()

        if not results:
            return jsonify({"error": "No data found for given material IDs"}), 404

        # Convert results to a DataFrame
        df = pd.DataFrame(results)
        df["date"] = pd.to_datetime(df["date"])
        df["Year"] = df["date"].dt.year
        df["Month"] = df["date"].dt.strftime("%b")

        all_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        # Pivot table to arrange quantity per month
        pivot_quantity = df.pivot_table(
            index=["material_id", "Year"],
            columns="Month",
            values="quantity",
            aggfunc="sum",
            fill_value=0
        ).reindex(columns=all_months, fill_value=0).reset_index()

        # Get latest prices
        latest_prices = df.sort_values(by=["Year", "Month"]).groupby("material_id")["price"].last().reset_index()

        # Get unit of measure per Material ID
        unit_df = df.groupby("material_id")["base_unit_of_measure"].first().reset_index()

        # Merge results
        final_df = pivot_quantity.merge(latest_prices, on="material_id", how="left")
        final_df = final_df.merge(unit_df, on="material_id", how="left")

        # Rename columns
        final_df.rename(columns=lambda x: f"quantity_{x}" if x in all_months else x, inplace=True)
        final_df.rename(columns={"price": "last_price"}, inplace=True)

        return jsonify({"data": final_df.to_dict(orient="records")}), 200

    except Exception as e:
        print("Error while fetching data:", e)
        return jsonify({"error": "An error occurred while fetching the data"}), 500
    finally:
        cursor.close()
        conn.close()

# Run the Flask app (for Cloud Run)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

