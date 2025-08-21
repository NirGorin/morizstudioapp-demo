from pydantic import BaseModel




class CreateUserRequest(BaseModel):
    First_Name : str
    Last_Name : str
    Username : str
    Email : str
    Password : str
    Role: str
    Phone_Number: str

class CreateTraineeProfileRequest(BaseModel):
    Age: int
    Gender: str
    Height: int
    Weight: int
    Level: str
    Number_Of_Week_Training: str
    Limitation: str = None

class CreateStudioRequest(BaseModel):
    Name: str
    Email: str


    


class Token(BaseModel):
    access_token: str
    token_type: str