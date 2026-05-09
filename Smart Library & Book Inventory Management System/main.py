from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Base, Book, BorrowRecord, AuditLog
from schemas import BookCreate, BorrowBook

import pandas as pd
import shutil

from fastapi import File, UploadFile
# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Database connection function
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Home API
@app.get("/")
def home():
    return {"message": "LibTrack API is Running Successfully"}

# Add Book API
@app.post("/add-book")
def add_book(book: BookCreate, db: Session = Depends(get_db)):

    new_book = Book(
        title=book.title,
        author=book.author,
        quantity=book.quantity
    )

    db.add(new_book)
    log = AuditLog(
    action="ADD_BOOK",
    details=f"Book Added: {book.title}")

    db.add(log)
    db.commit()
    db.refresh(new_book)

    return {
        "message": "Book Added Successfully",
        "book": new_book.title
    }
    
    # Get All Books API
@app.get("/books")
def get_books(db: Session = Depends(get_db)):

    books = db.query(Book).all()

    return books

# Delete Book API
@app.delete("/delete-book/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):

    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        return {"message": "Book Not Found"}

    db.delete(book)
    log = AuditLog(
    action="DELETE_BOOK",
    details=f"Deleted Book: {book.title}"
)

    db.add(log)
    db.commit()

    return {"message": "Book Deleted Successfully"}


# Update Book API
@app.put("/update-book/{book_id}")
def update_book(
    book_id: int,
    updated_book: BookCreate,
    db: Session = Depends(get_db)
):

    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        return {"message": "Book Not Found"}

    # Update values
    book.title = updated_book.title
    book.author = updated_book.author
    book.quantity = updated_book.quantity

    db.commit()
    db.refresh(book)

    return {
        "message": "Book Updated Successfully",
        "updated_book": book
    }
    
# Borrow Book API
@app.post("/borrow-book/{book_id}")
def borrow_book(
    book_id: int,
    borrow_data: BorrowBook,
    db: Session = Depends(get_db)
):

    # Find book
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        return {"message": "Book Not Found"}

    # Check quantity
    if book.quantity < borrow_data.quantity:
        return {"message": "Not Enough Books Available"}

    # Reduce inventory
    book.quantity -= borrow_data.quantity

    # Create borrow record
    borrow_record = BorrowRecord(
        student_name=borrow_data.student_name,
        book_title=book.title,
        quantity_borrowed=borrow_data.quantity
    )

    db.add(borrow_record)

    db.commit()
    log = AuditLog(
    action="BORROW_BOOK",
    details=f"{borrow_data.student_name} borrowed {book.title}"
)

    db.add(log)

    return {
        "message": "Book Borrowed Successfully",
        "remaining_books": book.quantity
    }
    
# Return Book API
@app.put("/return-book/{book_id}")
def return_book(
    book_id: int,
    return_data: BorrowBook,
    db: Session = Depends(get_db)
):

    # Find book
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        return {"message": "Book Not Found"}

    # Increase quantity
    book.quantity += return_data.quantity

    db.commit()
    db.refresh(book)

    return {
        "message": "Book Returned Successfully",
        "updated_quantity": book.quantity
    }
    

# CSV Upload API
@app.post("/upload-csv")
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # Save uploaded file
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Read CSV using pandas
    df = pd.read_csv(file_path)

    # Insert each row into database
    for index, row in df.iterrows():

        new_book = Book(
            title=row["title"],
            author=row["author"],
            quantity=int(row["quantity"])
        )

        db.add(new_book)

    db.commit()
    log = AuditLog(
    action="CSV_UPLOAD",
    details=f"{len(df)} books uploaded from CSV"
)

    db.add(log)

    return {
        "message": "CSV Uploaded Successfully",
        "total_books_added": len(df)
    }
    
# Total Books Analytics API
@app.get("/analytics/total-books")
def total_books(db: Session = Depends(get_db)):

    books = db.query(Book).all()

    total = len(books)

    return {
        "total_books": total
    }

# Total Inventory API
@app.get("/analytics/total-inventory")
def total_inventory(db: Session = Depends(get_db)):

    books = db.query(Book).all()

    total_quantity = 0

    for book in books:
        total_quantity += book.quantity

    return {
        "total_inventory": total_quantity
    }
    
    # Most Available Book API
@app.get("/analytics/most-available-book")
def most_available_book(db: Session = Depends(get_db)):

    books = db.query(Book).all()

    if not books:
        return {"message": "No Books Found"}

    max_book = books[0]

    for book in books:
        if book.quantity > max_book.quantity:
            max_book = book

    return {
        "title": max_book.title,
        "author": max_book.author,
        "quantity": max_book.quantity
    }
    
# Audit Logs API
@app.get("/audit-logs")
def get_logs(db: Session = Depends(get_db)):

    logs = db.query(AuditLog).all()

    return logs

# Search Book By Title
@app.get("/search/title/{title}")
def search_by_title(title: str, db: Session = Depends(get_db)):

    books = db.query(Book).filter(
        Book.title.contains(title)
    ).all()

    return books

# Search Book By Author
@app.get("/search/author/{author}")
def search_by_author(author: str, db: Session = Depends(get_db)):

    books = db.query(Book).filter(
        Book.author.contains(author)
    ).all()

    return books

# Low Stock Books API
@app.get("/low-stock")
def low_stock_books(db: Session = Depends(get_db)):

    books = db.query(Book).filter(
        Book.quantity < 5
    ).all()

    return books
