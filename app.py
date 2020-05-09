import os
import requests

from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_url_path='/static')
# Check for environment variable
#if not os.getenv("DATABASE_URL"):
#    raise RuntimeError("DATABASE_URL is not set")
#DATABASE_URL=$(heroku config:get DATABASE_URL -a book-review-db-1)
# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
#For Deployment
engine = create_engine(os.getenv("DATABASE_URL"))
#For Local
#engine = create_engine("postgres://rljdkhwyibrclr:83b8058cc1429ab991e99a6bdf0f137575a6a87654989daa21d4cce4891134fc@ec2-50-17-90-177.compute-1.amazonaws.com:5432/d2adq2pnnb6dg2")
db = scoped_session(sessionmaker(bind=engine))
KEY="6iGmZfPMsrgbm0i8iqfcw"


@app.route("/",methods =["POST","GET"])
def index():
    if request.method=="POST":
        session.pop('id', None)
    if 'id' in session:
        return render_template("main.html")
    else:
        return render_template('login.html')

@app.route("/registration",methods =["POST","GET"])
def register():
    return render_template('registration.html')

@app.route("/registration/true?",methods =["POST"])
def check():
    username = request.form.get("username")
    password = request.form.get("password")
    new = db.execute("SELECT id FROM users WHERE username = :username",{"username":username}).fetchone()
    if new is None:
        password_h = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        db.execute("INSERT INTO users (username, password_h, reviews) VALUES (:username, :password_h, :reviews)",{"username": username, "password_h": password_h, "reviews":0})
        db.commit()
        return render_template('registrationS.html')
    else:
        return render_template('registrationF.html')

@app.route("/main",methods =["POST","GET"])
def main():
    if request.method == "GET":
        if 'id' in session:
            return render_template("main.html")
        else:
            return render_template("loginF.html")
    else:
        username = request.form.get("username")
        password_inp = request.form.get("password")
        id = db.execute("SELECT id FROM users WHERE username = :username",{"username":username}).fetchone()
        db.commit()
        if id is None:
            return render_template("loginF.html")
        id = id[0]
        password = db.execute("SELECT password_h FROM users WHERE id = :id",{"id":id}).fetchone()
        db.commit()
        password=password[0]
        if check_password_hash(password,password_inp):
            session["id"] = id
            return render_template("main.html")
        else:
            return render_template("loginF.html")

@app.route("/userinfo",methods = ["POST","GET"])
def user():
    id = session["id"]
    row = db.execute("SELECT username,reviews FROM users WHERE id = :id",{"id":id}).fetchone()
    db.commit()
    username = row[0]
    reviews = row[1]
    return render_template('userpage.html',username=username,count = reviews)

@app.route("/search",methods = ["POST","GET"])
def search():
    if request.method == "POST":
        string = request.form.get("string")
        #EXECUTE SEARCH FUNCTION PASS RESULTS TO SEARCH.html
        string = string.lower()
        string = '%' + string + '%'
        results = db.execute("SELECT id,title FROM books WHERE LOWER (books.title) LIKE :string", {"string":string}).fetchall()
        db.commit()
        if len(results)<1:
            return render_template('search.html', msg = "Sorry, we could not find what you were looking for.")
        else:
            return render_template('search.html', msg = "Select the book you were looking for: ",results = results)
        
    else:
        return render_template('search.html', msg = "Results will appear here, please wait")

@app.route("/search/<int:book_id>", methods = ["GET"])
def book(book_id):
    bid = int(book_id)
    row = db.execute("SELECT * FROM books WHERE id = :id",{"id":bid}).fetchone()
    db.commit()
    data = {'bid':bid}
    isbn=row[1]
    res=requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})
    try:
        res=res.json()
        GRrating=res['books'][0]['average_rating']
        reviews = db.execute("SELECT review,rating,username,id FROM reviews WHERE book_id = :book_id",{"book_id":bid}).fetchall()
        count = len(reviews)
        GRrating = str(GRrating)+"/5!"
        mybool = True
        for review in reviews:
            if review[3] == session["id"]:
                mybool = False
        
        return render_template('book_id.html',title = row[2],author = row[3],data = data,reviews = reviews, count = count, GRrating = GRrating, isbn=isbn, mybool = mybool)
    except:
        reviews = db.execute("SELECT review,rating,username FROM reviews WHERE book_id = :book_id",{"book_id":bid}).fetchall()
        count = len(reviews)
        GRrating = "Sorry could not fetch Goodreads rating..."
        return render_template('book_id.html',title = row[2],author = row[3],data = data,reviews = reviews, count = count, GRrating = GRrating)

    

@app.route("/API",methods = ["POST","GET"])
def api():
    return render_template('api.html')

@app.route("/review", methods = ["POST"])
def review():
    book_id = request.form.get("book_id")
    bid = int(book_id)
    uid = session['id']
    row = db.execute("SELECT title FROM books WHERE id = :id",{"id":bid}).fetchone()
    username = db.execute("SELECT username FROM users WHERE id = :id",{"id":uid}).fetchone()
    db.commit()
    username = username[0]
    title = row[0]
    data = {"bid":bid}
    return render_template("review_page.html", data = data, username = username,title = title)

@app.route("/review/success",methods = ["POST"])
def success():
    book_id = request.form.get("book_id")
    review = request.form.get("review")
    rating = request.form.get("rating")
    uid = session['id']
    book_id = int(book_id)
    row = db.execute("SELECT username,reviews FROM users WHERE id = :id",{"id":uid}).fetchone()
    username = row[0]
    review_count = row[1]
    db.execute("INSERT INTO reviews (book_id,review,rating,username) VALUES (:book_id,:review,:rating,:username)",{"book_id":book_id,"review":review,"rating":rating,"username":username})
    review_count = review_count + 1
    db.execute("UPDATE users SET reviews = :value WHERE id = :id",{"value":review_count,"id":uid})
    db.commit()
    return render_template('review_success.html')

#suryachereddy
@app.route("/API/<string:isbn>")
def api_out(isbn):
    isbn=str(isbn)
    book=db.execute("SELECT * FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
    if book is None:
        return jsonify({"error":"Invalid ISBN"}),422
    #print(book)
    #return jsonify({"test":"testing"})
    
    return jsonify({
        "title":book[2],
        "author":book[3],
        "year":book[4],
        "isbn":book[1],
        "review_count":0,
        "average_score":0
    })
#suryachereddy end 
    