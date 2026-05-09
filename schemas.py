from pydantic import BaseModel

class BookCreate(BaseModel):
    title: str
    author: str
    quantity: int
    
class BorrowBook(BaseModel):
    student_name: str
    quantity: int