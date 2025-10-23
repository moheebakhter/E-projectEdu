from http.client import responses

import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from Education.firebase_config import db
from django.shortcuts import render
from .scrapper import scrape_propakistani_blogs
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.http import HttpResponse
import firebase_admin
from firebase_admin import credentials, firestore
import os
import pandas as p
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def register(req):
    if req.method == "POST":
        n = req.POST.get("name")
        e = req.POST.get("email")
        p = req.POST.get("password")
        r = req.POST.get("role")

        if not n or not e or not p:
            messages.error(req, "All Fields are required")
            return redirect("reg")

        if len(p) < 8:
            messages.error(req, "Password must be 8 characters long")
            return redirect("reg")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={settings.FIRE}"
        playload = {
            "email": e,
            "password": p,
            "returnSecureToken": True
        }

        response = requests.post(url, playload)

        if response.status_code == 200:
            db.collection("User").add({
                "Name": n,
                "Email": e,
                "Pswd": p,
                "Role": r,
            })

            messages.success(req, "User Registered Successfully ✅ Now Login")
            return redirect("log")

        else:
            error_msg = response.json().get("error", {}).get("message", "Something went wrong")
            messages.error(req, f"Registration Failed: {error_msg}")
            return redirect("reg")

    return render(req, "myapp/Register.html")


def Login(req):
    if req.method == "POST":
        e = req.POST.get("email")
        p = req.POST.get("password")

        if not e or not p:
            messages.error(req, "All Fields are Required")
            return redirect("log")

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIRE}"
        playload = {
            "email": e,
            "password": p,
            "returnSecureToken": True
        }
        res = requests.post(url, json=playload)

        if res.status_code == 200:
            userinfo = res.json()
            req.session["email"] = userinfo.get("email")
            return redirect("index")
        else:
            error = res.json().get("error", {}).get("message", "Message Not Found")
            print(error)
            if error == "INVALID_LOGIN_CREDIENTIALS":
                messages.error(req, "Invalid credentials, Login Again")
            elif error == "INVALID_PASSWORD":
                messages.error(req, "Password is Incorrect")
            return redirect("log")
    return render(req, "myapp/login.html")


# 👇 yahan security add ki gayi hai (Step 1 + Step 2)
@never_cache
def home(request):
    email = request.session.get("email")
    if not email:                       # Agar user login nahi hai to redirect
        return redirect("log")
    return render(request, "myapp/index.html", {"email": email})


def Index(request):
    return render(request,"myapp/index.html")

def About(request):
    return render(request,"myapp/about.html")

def Course(request):
    return render(request,"myapp/course.html")


def Contact(request):
    if request.method == "POST":
        n = request.POST.get("name")
        e = request.POST.get("email")
        s = request.POST.get("subject")
        m = request.POST.get("message")

        contact_data = {
            "name": n,
            "email": e,
            "subject": s,
            "message": m
        }
        db.collection("contacts").add(contact_data)

        messages.success(request, "Your message has been sent successfully!")
        return redirect("con")

    return render(request, "myapp/contact.html")

def blog_list(request):
    blogs = scrape_propakistani_blogs()
    return render(request, 'myapp/news.html', {'blogs': blogs})


def predict_view(request):
    result = None

    if request.method == "POST":
        hours = float(request.POST.get("hours"))

        # Load dataset
        mydata = p.read_csv("Expanded_data_with_more_features.csv")
        x = mydata[["WklyStudyHours"]]
        y = mydata["WritingScore"]
        x = x.dropna()
        y = y.loc[x.index]

        # Train model
        model = LinearRegression()
        model.fit(x, y)

        # Predict
        prediction = model.predict([[hours]])
        result = round(prediction[0], 2)

    return render(request, "myapp/predict.html", {"result": result})

# 🔹 Train model once when the server starts
df = p.read_csv("student_dropout_dataset.csv")

x = df[["Attendance", "StudyHours", "ParentalSupport", "PreviousGrade"]]
y = df["Dropout"]

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

model = LogisticRegression()
model.fit(x_train, y_train)

accuracy = round(accuracy_score(y_test, model.predict(x_test)), 3)
print(f"✅ Dropout Model trained (Accuracy: {accuracy})")


# 🔹 Django view for form and prediction
def dropout_view(request):
    result = None
    if request.method == "POST":
        attendance = float(request.POST.get("attendance"))
        studyhours = float(request.POST.get("studyhours"))
        parent = int(request.POST.get("parent"))
        grade = float(request.POST.get("grade"))

        # Prediction
        user_data = [[attendance, studyhours, parent, grade]]
        prediction = model.predict(user_data)[0]

        if prediction == 1:
            result = "⚠️ Highly chance of Dropout"
        else:
            result = "✅ Great! The student is on the right track and likely to complete studies."

    return render(request, "myapp/dropout.html", {"result": result, "accuracy": accuracy})

def logout_view(request):
    logout(request)            # ← user ka session clear ho jayega
    request.session.flush()    # ← session puri tarah se clear
    return redirect('/l')

if not firebase_admin._apps:
    # expect serviceAccountKey.json in project root
    cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'serviceAccountKey.json')
    cred_path = os.path.abspath(cred_path)
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        # initialize default app (some firebase functions will error until key provided)
        try:
            firebase_admin.initialize_app()
        except Exception:
            pass

# get firestore client if possible
try:
    db = firestore.client()
except Exception:
    db = None

def home(request):
    return render(request, 'myapp/home.html')

# Students CRUD
def students_list(request):
    students = []
    if db:
        docs = db.collection('students').stream()
        for d in docs:
            s = d.to_dict(); s['id'] = d.id
            students.append(s)
    return render(request, 'myapp/students_list.html', {'students': students})

def students_add(request):
    if request.method == 'POST' and db:
        data = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'grade': request.POST.get('grade'),
        }
        db.collection('students').add(data)
        return redirect('students_list')
    return render(request, 'myapp/students_form.html', {'action': 'Add'})

def students_edit(request, doc_id):
    if not db:
        return HttpResponse('Firestore not configured', status=500)
    doc_ref = db.collection('students').document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        return HttpResponse('Not found', status=404)
    if request.method == 'POST':
        doc_ref.update({
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'grade': request.POST.get('grade'),
        })
        return redirect('students_list')
    student = doc.to_dict(); student['id'] = doc.id
    return render(request, 'myapp/students_form.html', {'action': 'Edit', 'student': student})

# Courses CRUD
def courses_list(request):
    courses = []
    if db:
        docs = db.collection('courses').stream()
        for d in docs:
            c = d.to_dict(); c['id'] = d.id
            courses.append(c)
    return render(request, 'myapp/courses_list.html', {'courses': courses})

def courses_add(request):
    if request.method == 'POST' and db:
        data = {
            'title': request.POST.get('title'),
            'code': request.POST.get('code'),
            'description': request.POST.get('description'),
        }
        db.collection('courses').add(data)
        return redirect('courses_list')
    return render(request, 'myapp/courses_form.html', {'action': 'Add'})

def courses_edit(request, doc_id):
    if not db:
        return HttpResponse('Firestore not configured', status=500)
    doc_ref = db.collection('courses').document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        return HttpResponse('Not found', status=404)
    if request.method == 'POST':
        doc_ref.update({
            'title': request.POST.get('title'),
            'code': request.POST.get('code'),
            'description': request.POST.get('description'),
        })
        return redirect('courses_list')
    course = doc.to_dict(); course['id'] = doc.id
    return render(request, 'myapp/courses_form.html', {'action': 'Edit', 'course': course})
