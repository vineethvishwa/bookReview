import os
import requests
import json

from flask import Flask, session,render_template,request,redirect,url_for,abort
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import IntegrityError
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secrest_key = os.getenv("SECRET_KEY")

bcrypt = Bcrypt(app)
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():	
	if 'user_id' in session:
		return redirect(url_for('search'))
	return render_template("index.html",title="ReviewIt")




@app.route("/login",methods=["GET","POST"])
def login():
	if request.method=='POST':
		name = request.form.get("name").strip()
		username = request.form.get("username").strip()
		password = request.form.get("password").strip()
		
		if (len(name)>0 and len(username)>0 and len(password)>0) == False:
			return render_template("index.html",message="Enter all requireed fields")

		hashed_password = bcrypt.generate_password_hash(password).decode()

		if db.execute("SELECT username from users where username=:username",{"username":username}).rowcount != 0:
			return render_template("index.html",message="Username already taken.")
		db.execute("INSERT INTO users (username,password,name) VALUES (:username,:password,:name)",{"username":username,"password":hashed_password,"name":name})
		
		db.commit()
		message = "YOU HAVE SUCESSFULLY REGISTERED !!"
		return render_template("login.html",message=message)

	return render_template("login.html",title = "Sign In")




@app.route("/search",methods=["GET","POST"])
def search():
        if request.method=="GET" and 'user_id' in session:
                return render_template("dashboard.html",title="Dashboard",name=session["name"])
        username = request.form.get("username")
        password = request.form.get("password")
        res = db.execute("SELECT password,id,name from users where username=:username",{"username":username}).fetchone()
        if res != None:
                hashed_password=res[0]
                user_id = res[1]
                name = res[2]
        else:
                hashed_password=user_id=name=None
        if hashed_password != None and bcrypt.check_password_hash(hashed_password,password):
                session["user_id"] = user_id
                session["name"] = name
                return render_template("dashboard.html",title="Dashboard",name=session["name"])
        else:
                return render_template("login.html",message="Please enter the correct username and password.")



@app.route("/books",methods=["POST"])
def results():
        isbn = request.form.get("isbn").lower().strip()
        title = request.form.get("title").lower().strip()
        author = request.form.get("author").lower().strip()
        books = db.execute("SELECT * from book where LOWER(isbn) like :isbn and LOWER(title) like :title and LOWER(author) like :author",{"isbn": f"%{isbn}%","title": f"%{title}%","author": f"%{author}%"}).fetchall()
        return render_template("results.html",title="Search Results",books=books)





@app.route("/book/<string:book_id>")
def bookDetails(book_id):
	if 'user_id' not in session:
		return "<a href='/login'>Login to review</a>"
	book = db.execute("SELECT * from book where id =:book_id",{"book_id": book_id}).fetchone()
	
	reader_reviews = db.execute("SELECT review,name,rating from reviews join users u on reviews.user_id = u.id where book_id=:book_id",{"book_id": book_id}).fetchall()
	already_reviewed = db.execute("SELECT * from reviews where book_id=:book_id and user_id=:user_id",{"book_id":book_id,"user_id": session["user_id"]}).rowcount >= 1
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "jmiehbJLWAWwJ1k9SFEFFg", "isbns": book.isbn}).json()

	return render_template("book.html",title=book.title,book=book,res=res['books'][0],reviews=reader_reviews,alredy_reviewed=already_reviewed)






@app.route("/review/<string:book_id>",methods=["POST"])
def review(book_id):
	rating = request.form.get('rating')
	review = request.form.get('review')
	user_id = session["user_id"]
	
	already_reviewed = db.execute("SELECT * from reviews where book_id=:book_id and user_id=:user_id",{"book_id":book_id,"user_id": session["user_id"]}).rowcount >=1
	if not already_reviewed and user_id != None and int(rating) >= 1 and int(rating)<=5:
		db.execute("INSERT INTO reviews(user_id,book_id,review,rating)VALUES(:user_id,:book_id,:review,:rating)",{"user_id":user_id,"book_id":book_id,"review":review,"rating":rating})
		db.commit()
		return render_template("reviewed.html",success=True)
	else:
		return render_template("reviewed.html",success=False,book_id=book_id)





@app.route("/api/<string:isbn>")
def api(isbn):
	book_detail = db.execute("SELECT title,author,year,isbn from book where isbn=:isbn",{"isbn":isbn}).fetchone()
	review_stats = db.execute("select avg(rating),count(review) from book join reviews r on book.id=r.book_id where isbn=:isbn group by book_id",{"isbn":isbn}).fetchone()
	if review_stats==None:
		review_count=0
		average_score=None
	else:
		review_count=review_stats[1]
		average_score=float(review_stats[0])
	if book_detail != None:
		res = {
			"title": book_detail[0],
			"author": book_detail[1],
			"year": book_detail[2],
			"isbn": book_detail[3],
			"review_count": review_count,
			"average_score": average_score
			}
		return json.dumps(res)
	return abort(404)



@app.route("/logout")
def logout():
	session.pop('user_id',None)
	return redirect(url_for('login'))
