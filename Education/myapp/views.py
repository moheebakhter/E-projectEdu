import datetime
import requests
import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.http import HttpResponse
from Education.firebase_config import db
from .scrapper import scrape_propakistani_blogs
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from django.http import JsonResponse

# 🔹 Authentication: Register
def register(req):
    if req.method == "POST":
        n = req.POST.get("name")
        e = req.POST.get("email")
        p = req.POST.get("password")
        r = req.POST.get("role")

        if not n or not e or not p:
            messages.error(req, "All fields are required")
            return redirect("reg")

        if len(p) < 8:
            messages.error(req, "Password must be at least 8 characters")
            return redirect("reg")

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={settings.FIRE}"
        payload = {"email": e, "password": p, "returnSecureToken": True}

        response = requests.post(url, json=payload)

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


# 🔹 Authentication: Login
def Login(req):
    if req.method == "POST":
        e = req.POST.get("email")
        p = req.POST.get("password")

        if not e or not p:
            messages.error(req, "All fields are required")
            return redirect("log")

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={settings.FIRE}"
        payload = {"email": e, "password": p, "returnSecureToken": True}
        res = requests.post(url, json=payload)

        if res.status_code == 200:
            userinfo = res.json()
            req.session["email"] = userinfo.get("email")
            return redirect("index")
        else:
            error = res.json().get("error", {}).get("message", "Invalid credentials")
            messages.error(req, error)
            return redirect("log")
    return render(req, "myapp/login.html")


# 🔹 Dashboard Protection
@never_cache
def home(request):
    email = request.session.get("email")
    if not email:
        return redirect("log")
    return render(request, "myapp/index.html", {"email": email})


def Index(request):
    return render(request, "myapp/index.html")


def About(request):
    return render(request, "myapp/about.html")


def Course(request):
    return render(request, "myapp/course.html")


# 🔹 Contact Form
def Contact(request):
    if request.method == "POST":
        data = {
            "name": request.POST.get("name"),
            "email": request.POST.get("email"),
            "subject": request.POST.get("subject"),
            "message": request.POST.get("message")
        }
        db.collection("contacts").add(data)
        messages.success(request, "Your message has been sent successfully!")
        return redirect("con")
    return render(request, "myapp/contact.html")


# 🔹 Blog
def blog_list(request):
    blogs = scrape_propakistani_blogs()
    return render(request, "myapp/news.html", {"blogs": blogs})

def predict_view(request):
    result = None

    if request.method == "POST":
        hours = float(request.POST.get("hours"))

        # Load dataset
        mydata = pd.read_csv("Expanded_data_with_more_features.csv")
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
df = pd.read_csv("student_dropout_dataset.csv")

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
            result = "⚠️ High Chance of dropout"
        else:
            result = "✅ Great! The student is on the right track and likely to complete studies"

    return render(request, "myapp/dropout.html", {"result": result, "accuracy": accuracy})

# 🔹 Logout
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("log")


# ==============================================================
# ✅ STUDENTS CRUD (With Email Notification)
# ==============================================================

def students_list(request):
    students = []
    docs = db.collection("students").stream()
    for d in docs:
        s = d.to_dict()
        s["id"] = d.id
        students.append(s)
    return render(request, "myapp/students_list.html", {"students": students})


from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
import datetime

def students_add(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        grade = request.POST.get("grade")
        password = request.POST.get("password")
        contact = request.POST.get("contact")

        # Generate unique enrollment number
        today = datetime.datetime.now().strftime("%Y%m%d")
        enrollment = f"ENR-{today}-{int(datetime.datetime.now().timestamp()) % 1000:03d}"

        # Save student data to Firebase
        data = {
            "name": name,
            "email": email,
            "grade": grade,
            "password": password,
            "contact": contact,
            "enrollment": enrollment,
        }

        try:
            db.collection("students").add(data)

            # Send Email Notification
            subject = "Welcome to Education System 🎓"
            message = f"""
Dear {name},

You have been successfully added to the Education System by the Admin.

Your account details are as follows:
📘 Grade: {grade}
📞 Contact: {contact}
🆔 Enrollment No: {enrollment}
🔑 Password: {password}

Please keep this information safe and do not share your password with anyone.

Best regards,
Education System Admin
"""
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, f"✅ Student added and email sent to {email}")
        except Exception as e:
            messages.warning(request, f"Student added but email not sent: {e}")

        return redirect("students_list")

    return render(request, "myapp/add_edit_student.html", {"action": "Add"})



def students_edit(request, doc_id):
    doc_ref = db.collection("students").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return redirect("students_list")

    student = doc.to_dict()

    if request.method == "POST":
        student.update({
            "name": request.POST.get("name"),
            "email": request.POST.get("email"),
            "grade": request.POST.get("grade"),
            "password": request.POST.get("password"),
            "contact": request.POST.get("contact"),
        })
        doc_ref.update(student)
        return redirect("students_list")

    return render(request, "myapp/add_edit_student.html", {"action": "Edit", "student": student})


def delete_student(request, id):
    if request.method == "POST":
        try:
            db.collection("students").document(id).delete()
            messages.success(request, "Student deleted successfully")
        except Exception as e:
            messages.error(request, f"Error deleting student: {e}")
    return redirect("students_list")


# ==============================================================
# ✅ COURSES CRUD
# ==============================================================

def courses_list(request):
    # Render a completely blank black page
    return render(request, "myapp/courses_list.html")



def courses_add(request):
    if request.method == "POST":
        data = {
            "title": request.POST.get("title"),
            "code": request.POST.get("code"),
            "description": request.POST.get("description"),
        }
        db.collection("courses").add(data)
        return redirect("courses_list")
    return render(request, "myapp/courses_form.html", {"action": "Add"})


def courses_edit(request, doc_id):
    doc_ref = db.collection("courses").document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return HttpResponse("Not found", status=404)

    if request.method == "POST":
        doc_ref.update({
            "title": request.POST.get("title"),
            "code": request.POST.get("code"),
            "description": request.POST.get("description"),
        })
        return redirect("courses_list")

    course = doc.to_dict()
    course["id"] = doc.id
    return render(request, "myapp/courses_form.html", {"action": "Edit", "course": course})

def dashboard_home(request):
    email = request.session.get("email")
    if not email:
        return redirect("log")
    return render(request, "myapp/home.html", {"email": email})



def get_counts(request):
    students_ref = db.collection("students").stream()
    student_count = sum(1 for _ in students_ref)

    courses_ref = db.collection("courses").stream()
    course_count = sum(1 for _ in courses_ref)

    return JsonResponse({
        "student_count": student_count,
        "course_count": course_count,
    })




