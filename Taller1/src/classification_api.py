from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import uvicorn
import numpy as np

class InputData(BaseModel):
    x1: int
    x2: float
    x3: float
    x4: float
    x5: float
    x6: int
    x7: float
    x8: float
    
app = FastAPI()
model = joblib.load("model_logreg.pkl")

@app.post("/predict")
async def predict(data: InputData):
    x1 = data.x1
    x2 = data.x2
    x3 = data.x3
    x4 = data.x4
    x5 = data.x5
    x6 = data.x6
    x7 = data.x7
    x8 = data.x8
    
    input_data = np.array([x1,x2,x3,x4,x5,x6,x7,x8]).reshape(1,-1)
    
    prediction = model.predict(input_data)[0].item()
    
    return {"prediction": prediction}
    
if __name__ == "__main__":
    uvicorn.run("classification_api:app",host="0.0.0.0",port = 8989)