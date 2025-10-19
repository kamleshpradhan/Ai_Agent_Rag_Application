from pymongo import MongoClient

def connec_db():
    try:
        # Replace with your MongoDB URI
        client = MongoClient("mongodb://localhost:27017/")  
        
        # Select database
        db = client["test"]
        
        print("✅ MongoDB connection successful")
        return db
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None