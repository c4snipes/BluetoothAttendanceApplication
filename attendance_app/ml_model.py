# ml_model.py

import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import numpy as np

class MLModel:
    def __init__(self, model_file='ml_model.pkl'):
        """
        Initialize the MLModel.

        :param model_file: Path to the file where the trained model is saved.
        """
        self.model_file = model_file
        self.model = None
        self.label_encoder = LabelEncoder()
        self.load_model()
    
    def load_model(self):
        """Load the trained ML model from a file if it exists."""
        if os.path.exists(self.model_file):
            with open(self.model_file, 'rb') as f:
                self.model, self.label_encoder = pickle.load(f)
    
    def save_model(self):
        """Save the trained ML model to a file."""
        with open(self.model_file, 'wb') as f:
            pickle.dump((self.model, self.label_encoder), f)
    
    def train_model(self, attendance_logs):
        """
        Train the ML model using attendance logs.

        :param attendance_logs: Dictionary containing attendance records.
        """
        # Prepare the dataset
        X = []
        y = []
        for student, records in attendance_logs.items():
            for record in records:
                mac = record.get('mac_address', '').upper()
                if mac:
                    # Simple feature: hash of MAC address
                    mac_hash = self.hash_mac(mac)
                    X.append([mac_hash])
                    y.append(student)
        
        if not X or not y:
            print("Insufficient data to train the model.")
            return
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
    
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
    
        # Initialize and train the model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
    
        # Evaluate the model
        accuracy = self.model.score(X_test, y_test)
        print(f"Model trained with accuracy: {accuracy*100:.2f}%")
    
        # Save the model
        self.save_model()
    
    def predict_student(self, mac):
        """
        Predict the student name based on the MAC address.

        :param mac: MAC address to predict.
        :return: Predicted student name or None if unknown.
        """
        if not self.model:
            print("Model is not trained yet.")
            return None
    
        mac_hash = self.hash_mac(mac.upper())
        prediction = self.model.predict([mac_hash])
        student = self.label_encoder.inverse_transform(prediction)[0]
        return student

