import os, json

from flask import Flask, session, redirect, render_template, request, jsonify, url_for,flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from authentication import auth

from werkzeug.security import check_password_hash, generate_password_hash

import requests

##res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "LvAO4PSdsqCfYdRuAcmYUw", "isbns": "9781632168146"})
##book=res.json() 
##print(book["books"][0]["average_rating"]) 


app = Flask(__name__)

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
    return render_template("landing.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        user= request.form.get("user")
        data = {"username": user, "email": user}
        result = db.execute("SELECT * FROM users WHERE username = :username or email = :email",data).fetchone()
        if result == None or not check_password_hash(result[2], request.form.get("password")):
            return render_template("error.html", message="User Not Found")
        session["user_id"] = result[0]
        session["user_name"] = result[1] 
        flash(f"Welcome back {result[4]}", "success")
        return redirect("/search")
        
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        Cpassword = request.form.get("Cpassword")
        if( password != Cpassword):
            flash("Password Mismatch","danger")
            return render_template("error.html", message="Password and Conform Password does not match")
        data = {"username": username, "email": email}
        check_user = db.execute("SELECT * FROM users WHERE username = :username OR email= :email",data).fetchone()
        if check_user:
            return render_template("error.html", message="Username or Email Already Exits")
        hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
        data = {"username":username, "password":hashedPassword, "email":email, "name":name}
        db.execute("INSERT INTO users (username, password, email, name) VALUES (:username, :password, :email, :name)",data)
        db.commit()
        result = db.execute("SELECT * FROM users WHERE username = :username",{"username": username}).fetchone()
        session["user_id"] = result[0]
        session["user_name"] = result[1]
        flash(f"Welcome {name}", "success")
        return redirect("/search")
    else:
        return render_template("register.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")



@app.route("/search", methods=["GET", "POST"])
def search():
    if auth():
        if request.method == "POST":
            book = request.form.get("book")
            catogry = request.form.get("catogry")
            book=book.title()
            result = db.execute(f"SELECT * FROM books WHERE {catogry} = '{book}'").fetchall()
            if len(result) == 0:
                flash("Book Not Found", "danger")
                return render_template("error.html", message="Book You're Searching for does not found")
            return render_template("view.html", result=result)
        else:
            return render_template("search.html")
    else:
        flash("Login required", "danger")
        return render_template("error.html")


@app.route("/book/<isbn>", methods=["GET", "POST"])
def book(isbn):
    catogry = "isbn"
    print(f"SELECT * FROM books WHERE {catogry} = '{isbn}'")
    if auth():
        if request.method == "POST":
            user_id = session["user_id"]
            book_result = db.execute(f"SELECT * FROM books WHERE {catogry} = '{isbn}'").fetchone()
            if not book_result:
                flash("Book Not Found", "danger")
                return render_template("error.html", message="Book You're Searching for does not found")

            result = db.execute(f"SELECT * FROM reviews WHERE user_id = {user_id} AND book_id = {book_result[0]}").fetchone()
            

            if  result:
                flash("Review Error", "danger")
                return render_template("error.html", message="You already made your review. You can't add more review")
            
            rating = request.form.get("rating")
            review = request.form.get("review")

            db.execute(f"INSERT INTO reviews(user_id, book_id, comment, rating) VALUES ({user_id}, {book_result[0]}, '{review}', {rating})")
            db.commit()
            res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "LvAO4PSdsqCfYdRuAcmYUw", "isbns": isbn})
            book=res.json() 
            book_info = book["books"][0]
            reviews = db.execute(f"SELECT users.name, comment, rating, to_char(time, 'DD Mon YY - HH24:MI:SS') as time from users INNER JOIN reviews ON users.id = reviews.user_id WHERE book_id = {book_result[0]} ORDER BY time").fetchall()
            return render_template("book_isbn.html", reviews = reviews, book_Info = book_info, book_result = book_result)
        else:
            book_result = db.execute(f"SELECT * FROM books WHERE {catogry} = '{isbn}'").fetchone()
            if not book_result:
                flash("Book Not Found", "danger")
                return render_template("error.html", message="Book You're Searching for does not found")
            res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "LvAO4PSdsqCfYdRuAcmYUw", "isbns": isbn})
            book=res.json() 
            book_info = book["books"][0]
            reviews = db.execute(f"SELECT users.name, comment, rating, to_char(time, 'DD Mon YY - HH24:MI:SS') as time from users INNER JOIN reviews ON users.id = reviews.user_id WHERE book_id = {book_result[0]} ORDER BY time").fetchall()
            print(reviews)
            return render_template("book_isbn.html", reviews = reviews, book_Info = book_info, book_result = book_result)

    else:
        flash("Login required", "danger")
        return render_template("error.html", message="You need to be logged in to view this page")



@app.route("/api/<isbn>")
def api_route(isbn):
    dict_result={}
    result = db.execute(f"SELECT books.title, books.isbn, books.author, books.year, COUNT(reviews.comment) as review_count, AVG(reviews.rating) as average_score FROM books INNER JOIN reviews on books.id = reviews.book_id WHERE isbn LIKE '{isbn}' GROUP BY books.title, books.author, books.isbn ,books.year ").fetchone()
    print(result)
    dict_result["title"]=result[0]
    dict_result["isbn"]=result[1]
    dict_result["author"]=result[2]
    dict_result["year"]=int(result[3])
    dict_result["review_count"]=result[4]
    dict_result["average_score"]=float('%.2f'%(result[5]))
    print(dict_result)


    return jsonify(dict_result)


            







