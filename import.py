import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
	f = open("books.csv")
	reader = csv.reader(f)
	engine.execute("""CREATE TABLE book (id serial PRIMARY KEY,isbn VARCHAR UNIQUE NOT NULL,title varchar,author VARCHAR,year VARCHAR)""")
	engine.execute("""CREATE TABLE users(id serial PRIMARY KEY,username VARCHAR UNIQUE NOT NULL,password VARCHAR NOT NULL,name VARCHAR NOT NULL)""")
	engine.execute("""CREATE TABLE reviews(id serial PRIMARY KEY,user_id INTEGER REFERENCES users,book_id INTEGER REFERENCES book,review VARCHAR NOT NULL,rating INTEGER NOT NULL CHECK(rating>=1 AND rating <= 5))""")
	for isbn,title,author,year in reader:
		db.execute("INSERT INTO book (isbn,title,author,year) values (:isbn, :title, :author, :year)",{"isbn":isbn,"title":title,"author":author,"year":year})
		print(f"{title} has been added to database")
	db.commit()
if __name__== "__main__":
	main()
