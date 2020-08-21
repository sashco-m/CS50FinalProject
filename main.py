import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session,url_for, json
from flask_session import Session
from tempfile import mkdtemp
from random import choice
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

from datetime import datetime

#sqlite3 stuff
import sqlite3
from sqlite3 import Error

web_site = Flask(__name__)
bruh=os.urandom(24)
web_site.secret_key = bruh

#ensure templates are auto-reloaded
web_site.config["TEMPLATES_AUTO_RELOAD"] = True


#something about not caching responses
#@web_site.after_request
#def after_request(response):
#  response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#  response.headers["Expires"] = 0
#  response.headers["Pragma"] = "no-cache"
#  return response


#configuring sessions
web_site.config["SESSION_FILE_DIR"] = mkdtemp()
web_site.config["SESSION_PERMANENT"] = False
web_site.config["SESSION_TYPE"] = "filesystem"
Session(web_site)

@web_site.route("/", methods=["GET", "POST"])
def index():
  if request.method == "POST":
    if request.form['submit_button'] == 'sortItem':
      connection = sqlite3.connect("stock.db", check_same_thread=False)
      cursor = connection.cursor()
      sortMethod=request.form.get("sort")
      if sortMethod=="dateAsc":
        cursor.execute("SELECT * FROM stock ORDER BY list_date DESC")
      elif sortMethod=="dateDesc":
        cursor.execute("SELECT * FROM stock ORDER BY list_date")
      elif sortMethod=="sizeAsc":
        cursor.execute("SELECT * FROM stock ORDER BY size")
      elif sortMethod=="sizeDesc":
        cursor.execute("SELECT * FROM stock ORDER BY size DESC")
      elif sortMethod=="priceAsc":
        cursor.execute("SELECT * FROM stock ORDER BY price")
      elif sortMethod=="priceDesc":
        cursor.execute("SELECT * FROM stock ORDER BY price DESC")

      data=cursor.fetchall()
      connection.commit()
      connection.close()

      sold=[]
      unsold=[]

      for items in data:
        if items[2]==None:
          unsold.append(items)
        else:
          sold.append(items)
      
      cart=session.get("cart",[])
      numItems=len(cart)
      return render_template("index.html", sold=sold,unsold=unsold,admin=session.get("admin",False),sortMethod=sortMethod,numItems=numItems)
    elif request.form['submit_button'] == 'addItem':
      connection = sqlite3.connect("stock.db", check_same_thread=False)
      cursor = connection.cursor()
      #data from form
      title=request.form.get("title")
      cover=request.form.get("url")
      img2=request.form.get("url_2")
      img3=request.form.get("url_3")
      sold=request.form.get("sold")
      price=request.form.get("price")
      description=request.form.get("description")
      size=request.form.get("size")
      
      if not title or not cover:
        cursor.execute("SELECT * FROM stock")
        data=cursor.fetchall()
        return render_template("index.html", stock=data,admin=session.get("admin",False))
      if not sold=="sold":
        cursor.execute("INSERT INTO stock (list_date,title,image_url,image_2,image_3,price,description,size) VALUES(?,?,?,?,?,?,?,?)",(datetime.now(),title,cover,img2,img3,price,description,size))
      else:
        cursor.execute("INSERT INTO stock (list_date,purchase_date,title,image_url,image_2,image_3,price,description,size) VALUES(?,?,?,?,?,?,?,?,?)",(datetime.now(),datetime.now(),title,cover,img2,img3,price,description,size))
      #print(data)
      cursor.execute("SELECT * FROM stock")
      data=cursor.fetchall()
      #ok so this works now
      connection.commit()
      connection.close()

      sold=[]
      unsold=[]

      for items in data:
      #print(items[2])
        if items[2]==None:
          unsold.append(items)
        else:
          sold.append(items)

      cart=session.get("cart",[])
      numItems=len(cart)
      return render_template("index.html", sold=sold,unsold=unsold,admin=session.get("admin",False),numItems=numItems)
  else:
    connection = sqlite3.connect("stock.db", check_same_thread=False)
    cursor = connection.cursor()
    #cursor.execute("DELETE FROM stock")
    cursor.execute("SELECT * FROM stock")
    #deletes all users quickly
    #cursor.execute("DELETE FROM users")
    
    data=cursor.fetchall()
    #print(data)
    sold=[]
    unsold=[]

    for items in data:
      if items[2]==None:
        unsold.append(items)
      else:
        sold.append(items)

    connection.commit()
    connection.close()

    cart=session.get("cart",[])
    numItems=len(cart)
    #print(cart)
    return render_template("index.html", sold=sold,unsold=unsold,admin=session.get("admin",False),numItems=numItems)

@web_site.route("/checkout/<int:purchased>", methods=["GET", "POST"])
def checkout(purchased):
  if request.method == "POST":
    #use post for removing items from cart
    #convert the item_id to an int, then remove from the cart. add the cart to the session.
    item_id=request.form["remove_from_cart"]
    cartID=session.get("cart",[])
    cartID.remove(int(item_id,10))
    session["cart"]=cartID

    return redirect("/checkout/0")
  elif request.method == "GET":
    #get the id
    if purchased==1:
      connection = sqlite3.connect("stock.db", check_same_thread=False)
      cursor = connection.cursor()
      cartID=session.get("cart",[])
      for items in cartID:
        cursor.execute("UPDATE stock SET purchase_date=? WHERE id=?",(datetime.now(),items))

      session["cart"]=[]
      cart=[]
      total=0

      connection.commit()
      connection.close()

      return redirect("/")
    else:
      cart=[]
      cartID=session.get("cart",[])
      #print(cartID)
      numItems=len(cartID)
      connection = sqlite3.connect("stock.db", check_same_thread=False)
      cursor = connection.cursor()
      for items in cartID:
        cursor.execute("SELECT * FROM stock WHERE id=?",[items])
        cart.append(cursor.fetchall()[0])
      total=0

      connection.commit()
      connection.close()

      for items in cart:
        total+=items[7]
      return render_template("checkout.html",numItems=numItems,cart=cart,total=total)

@web_site.route("/item/<int:num>/<int:purchased>", methods=["GET", "POST"])
def item(num,purchased): #this id is passed from the index page

  if request.method == "POST":
    #use post when adding item to cart
    #also use post for admin control and manually adding items to sold
    #num is the id of the item, use that to add it to cart  
      connection = sqlite3.connect("stock.db", check_same_thread=False)
      cursor = connection.cursor()
      cursor.execute("SELECT * FROM stock WHERE id=?",[num])
      data=cursor.fetchall()
      connection.commit()
      connection.close()
      #add data to session
      session.setdefault("cart",[])
      #only append the id (i think session was getting too large)
      session["cart"].append(num)

      cart=session.get("cart",[])
      numItems=len(cart)

      return render_template("item.html",items=data[0],inCart=True,numItems=numItems,admin=session["admin"])
  else:
    connection = sqlite3.connect("stock.db", check_same_thread=False)
    cursor = connection.cursor()
    if purchased==1:
      cursor.execute("UPDATE stock SET purchase_date=? WHERE id=?",(datetime.now(),num))
      cartID=session.get("cart",[])
      if num in cartID:
        cartID.remove(num)
        session["cart"]=cartID#prevents user from purchasing twice, on item page and in cart
    cursor.execute("SELECT * FROM stock WHERE id=?",[num]) #where to get the num from
    data=cursor.fetchall()

    connection.commit()
    connection.close()
    inCart=False
    cart=session.get("cart",[])

    if data[0][0] in cart:
      inCart=True
    
    numItems=len(cart)

    return render_template("item.html",items=data[0],inCart=inCart,numItems=numItems,admin=session["admin"])

#login method borrowed from cs50 web track starter code
@web_site.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        password=request.form.get("password")
        username=request.form.get("username")
        # Ensure username was submitted
        if not request.form.get("username"):
          return render_template("login.html",error="No username inputted")
        # Ensure password was submitted
        if not request.form.get("password"):
          return render_template("login.html",error="No password inputted")
        # Query database for username
        connection = sqlite3.connect("stock.db", check_same_thread=False)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?",[username])
        data=cursor.fetchall()
        connection.commit()
        connection.close()
        # Ensure username exists and password is correct
        if len(data) != 1 or not check_password_hash(data[0][2], password):
          return render_template("login.html",error="Incorrect username/password")
        #print("3")
        # Remember which user has logged in
        session["user_id"] = data[0][0]
        #admin check
        if session["user_id"] in [1]:
          session["admin"] = True;
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@web_site.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    #if they submit the form
    if request.method == "POST":

        password=request.form.get("password")
        username=request.form.get("username")

        # Ensure username was submitted
        if not username:
          return render_template("register.html")
        #print("1")
        # Ensure password was submitted
        if not password:
          return render_template("register.html")
        #print("2")
        # Ensure passwords are the same
        if request.form.get("password-confirm") != password:
          return render_template("register.html")
        #print("3")
        #checks if the username already exists
        #update this with the new db method
        connection = sqlite3.connect("stock.db", check_same_thread=False)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?",[username])
        data=cursor.fetchall()
        connection.commit()
        connection.close()
        if data:
          return render_template("register.html")
        #print("4")
        #inserting the username and password
        connection = sqlite3.connect("stock.db", check_same_thread=False)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO users (username,hash) VALUES (?,?)",(request.form.get("username"),generate_password_hash(request.form.get("password"))))
        connection.commit()
        connection.close()

        #getting the user id
        connection = sqlite3.connect("stock.db", check_same_thread=False)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?",[username])
        data=cursor.fetchall()
        connection.commit()
        connection.close()

        # Remember which user has logged in
        session["user_id"] = data[0][0]
        #admin check
        #the first two accounts created are admin accounts
        if session["user_id"] in [1,2]:
          session["admin"] = True;

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")


web_site.run(host='0.0.0.0', port=8080)
