import os, csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine=create_engine(os.getenv("DATABASE_URL"))
db=scoped_session(sessionmaker(bind=engine))

fileObj = open("books.csv")
data=csv.reader(fileObj)

#books table



for isbn, title, author, year in data:
    db.execute("INSERT INTO books(isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
    {"isbn":isbn,
    "title":title,
    "author":author,
    "year":year})
    print(f"{title} Added")
db.commit()