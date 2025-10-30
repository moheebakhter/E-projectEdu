import datetime
import requests
from collections import defaultdict
from statistics import mean
import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.http import HttpResponse
from Education.firebase_config import db
from firebase_admin import auth

from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
import datetime
from .scrapper import scrape_propakistani_blogs
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from django.http import JsonResponse
from sklearn.ensemble import RandomForestClassifier
from google.cloud import firestore  # add this import at the top
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_control
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split


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
    # 🟦 Session se email lo
    email = request.session.get('email')
    print("Session Email:", email)

    if not email:
        return render(request, "myapp/index.html", {
            "error": "⚠️ Session expired. Please login again."
        })

    # ==========================
    # 🎯 PART 1 — Average Score (predictions collection)
    # ==========================
    predictions_ref = db.collection('predictions')
    docs = predictions_ref.where('user_email', '==', email).stream()

    scores = []
    for doc in docs:
        data = doc.to_dict()
        scores.append(data.get('predicted_score', 0))

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0
    print("Average Score:", avg_score)

    # ==========================
    # 🔥 PART 2 — Dropout Prediction (dropout_predictions collection)
    # ==========================
    dropout_ref = db.collection('dropout_predictions')
    dropout_docs = dropout_ref.where('user_email', '==', email).stream()

    dropout_count = 0
    continue_count = 0

    for doc in dropout_docs:
        data = doc.to_dict()
        prediction_text = str(data.get('prediction', '')).lower().strip()
        print("Prediction Text:", prediction_text)

        if "dropout" in prediction_text:
            dropout_count += 1
        elif "continue" in prediction_text:
            continue_count += 1

    print(f"Dropout Count: {dropout_count}, Continue Count: {continue_count}")

    # 🧠 Final dropout result
    if dropout_count > continue_count:
        result_message = "⚠️ High Chance of Dropout"
    elif continue_count > dropout_count:
        result_message = "✅ Student likely to continue studies"
    else:
        result_message = "ℹ️ Not enough data for prediction"

    # ==========================
    # ✅ Return Data
    # ==========================
    context = {
        "avg_score": avg_score,
        "dropout_count": dropout_count,
        "continue_count": continue_count,
        "result_message": result_message
    }

    return render(request, "myapp/index.html", context)






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

        # ✅ Save prediction result to Firebase
        try:
            db.collection("predictions").add({
                "hours": hours,
                "predicted_score": result,
                "user_email": request.session.get("email", "guest"),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as e:
            print(f"⚠️ Firebase Save Error: {e}")

    return render(request, "myapp/predict.html", {"result": result})



# 🔹 Django view for form and prediction
def dropout_view(request):
    result = None
    accuracy = None

    # ✅ Correct CSV path (based on your project)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "student_dropout_dataset.csv")

    # ✅ Load dataset
    mydata = pd.read_csv(csv_path)

    # ✅ Adjust columns to match your CSV (check names carefully!)
    X = mydata[["Attendance", "StudyHours", "ParentalSupport", "PreviousGrade"]]
    y = mydata["Dropout"]

    # ✅ Split & train model
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)

    # ✅ Handle POST request for prediction
    if request.method == "POST":
        attendance = float(request.POST.get("attendance"))
        studyhours = float(request.POST.get("studyhours"))
        parent = float(request.POST.get("parent"))
        grade = float(request.POST.get("grade"))

        # Make prediction
        user_data = [[attendance, studyhours, parent, grade]]
        prediction = model.predict(user_data)[0]

        if prediction == 1:
            result = "⚠️ High Chance of Dropout"
        else:
            result = "✅ Student likely to continue studies"

        # ✅ Save to Firebase
        try:
            db.collection("dropout_predictions").add({
                "attendance": attendance,
                "study_hours": studyhours,
                "parental_support": parent,
                "previous_grade": grade,
                "prediction": result,
                "accuracy": accuracy,
                "user_email": request.session.get("email", "guest"),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as e:
            print(f"⚠️ Firebase Save Error: {e}")

    # ✅ Render page
    return render(request, "myapp/dropout.html", {"result": result, "accuracy": accuracy})


# 🔹 Logout

def logout_view(request):
    # Check if user is logged in
    if request.session.get("email"):
        # Clear session
        request.session.flush()
        # Add success message
        messages.success(request, "Logout successful!")
    else:
        messages.warning(request, "You are not logged in.")

    # Redirect to login page
    return redirect('log')

# ==============================================================
# ✅ STUDENTS CRUD (With Email Notification)
# ==============================================================
@never_cache
def students_list(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    students = []
    docs = db.collection("students").stream()
    for d in docs:
        s = d.to_dict()
        s["id"] = d.id
        students.append(s)
    return render(request, "myapp/students_list.html", {"students": students})



def students_add(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        grade = request.POST.get("grade")
        password = request.POST.get("password")
        contact = request.POST.get("contact")

        # Validation
        if not all([name, email, grade, password, contact]):
            messages.error(request, "All fields are required!")
            return redirect("students_add")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect("students_add")

        # Generate unique enrollment number
        today = datetime.datetime.now().strftime("%Y%m%d")
        enrollment = f"ENR-{today}-{int(datetime.datetime.now().timestamp()) % 1000:03d}"

        # Prepare student data for Firestore
        data = {
            "name": name,
            "email": email,
            "grade": grade,
            "password": password,
            "contact": contact,
            "enrollment": enrollment,
        }

        try:
            # 1️⃣ Add to Firestore
            db.collection("students").add(data)

            # 2️⃣ Create Firebase Authentication user
            try:
                auth.create_user(
                    email=email,
                    password=password,
                    display_name=name,
                )
            except auth.EmailAlreadyExistsError:
                messages.warning(request, f"{email} already exists in Firebase Auth.")
            except Exception as e:
                messages.error(request, f"Firebase Auth error: {e}")

            # 3️⃣ Send Email Notification
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
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                messages.warning(request, f"Student added, but email not sent: {e}")

            messages.success(request, f"✅ Student added successfully!")

        except Exception as e:
            messages.error(request, f"Error adding student: {e}")

        return redirect("students_list")  # Replace with your list route

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

# ✅ Admin Login
@never_cache
def admin_login(request):
    # Agar already login hai to dashboard bhej do
    if request.session.get('admin_logged_in'):
        return redirect('dashboard_home')

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if username == "admin" and password == "admin123":
            request.session['admin_logged_in'] = True
            messages.success(request, "Admin login successful!")
            return redirect('dashboard_home')
        else:
            messages.error(request, "Invalid username or password!")

    response = render(request, 'myapp/admin_login.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response



# ✅ Admin Dashboard (protected)
@never_cache
def dashboard_home(request):

    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    # ✅ Total Students Count
    students_ref = db.collection('students').get()
    total_students = len(students_ref)

    # ✅ Fetch Predictions (latest first)
    predictions_ref = db.collection('predictions').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()

    predictions = []
    for i, doc in enumerate(predictions_ref, start=1):
        data = doc.to_dict()
        predictions.append({
            'id': i,
            'user_email': data.get('user_email', ''),
            'hours': data.get('hours', ''),
            'predicted_score': data.get('predicted_score', ''),
            'timestamp': data.get('timestamp', ''),
        })

    return render(request, "myapp/home.html", {
        'student_count': total_students,
        'predictions': predictions,
    })


# ✅ Admin Logout (safe)
@never_cache
def admin_logout(request):
    if request.session.get('admin_logged_in'):
        del request.session['admin_logged_in']

    list(messages.get_messages(request))
    messages.info(request, "Admin logged out successfully!")

    response = redirect('admin_login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def students_dashboard(request):
    email = request.session.get("email")
    if not email:
        return redirect('log')

    # ✅ Fetch all students
    students_ref = db.collection("students").stream()
    students = []

    for i, doc in enumerate(students_ref, start=1):
        data = doc.to_dict()
        students.append({
            "id": i,
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "grade": data.get("grade", ""),
            "contact": data.get("contact", ""),
            "enrollment": data.get("enrollment", ""),
        })

    return render(request, "myapp/students_dashboard.html", {"students": students})



def get_counts(request):
    students_ref = db.collection("students").stream()
    student_count = sum(1 for _ in students_ref)

    courses_ref = db.collection("courses").stream()
    course_count = sum(1 for _ in courses_ref)

    return JsonResponse({
        "student_count": student_count,
        "course_count": course_count,
    })
def student_profile(request):
    # Get the logged-in user's email from session
    user_email = request.session.get("email")
    print(user_email)
    if not user_email:
        messages.error(request, "You must log in first.")
        return redirect("login")  # your login route name

    # Fetch student data from Firestore
    students_ref = db.collection("students")
    query = students_ref.where("email", "==", user_email).limit(1).get()

    if not query:
        messages.error(request, "No student found with your email.")
        return redirect("/login")  # homepage or wherever

    student_doc = query[0]
    student_data = student_doc.to_dict()

    if request.method == "POST":
        # Get updated data from form
        name = request.POST.get("name")
        password = request.POST.get("password")

        # Update Firestore
        student_doc.reference.update({
            "name": name,
            "password": password
        })
        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    return render(request, "myapp/profile.html", {"student": student_data})



@never_cache
def predict_student_all(request):
    # ✅ Fetch Predictions (latest first)

    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    predictions_ref = db.collection('predictions') \
        .order_by('timestamp', direction=firestore.Query.DESCENDING) \
        .stream()

    # 🔹 Group by user_email
    grouped = defaultdict(list)

    for doc in predictions_ref:
        data = doc.to_dict()
        email = data.get('user_email', '').strip().lower()
        if not email:
            continue
        grouped[email].append({
            'hours': float(data.get('hours', 0)),
            'predicted_score': float(data.get('predicted_score', 0)),
            'timestamp': data.get('timestamp', '')
        })

    # 🔹 Calculate averages per email
    predictions = []
    for i, (email, entries) in enumerate(grouped.items(), start=1):
        avg_hours = mean(e['hours'] for e in entries)
        avg_score = mean(e['predicted_score'] for e in entries)

        # Get latest timestamp for that email
        latest_time = max(e['timestamp'] for e in entries if e['timestamp'])

        predictions.append({
            'id': i,
            'user_email': email,
            'hours': round(avg_hours, 2),
            'predicted_score': round(avg_score, 2),
            'timestamp': latest_time,
        })

    # 🔹 Sort by timestamp (newest first)
    predictions.sort(key=lambda x: x['timestamp'], reverse=True)

    return render(request, "myapp/showpredict.html", {
        'predictions': predictions,
    })

@never_cache
def dropout_all(request):
    # ✅ Fetch all dropout prediction records (latest first)

    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    dropout_ref = db.collection('dropout_predictions') \
        .order_by('timestamp', direction=firestore.Query.DESCENDING) \
        .stream()

    dropout_data = []
    for i, doc in enumerate(dropout_ref, start=1):
        data = doc.to_dict()
        dropout_data.append({
            'id': i,
            'user_email': data.get('user_email', ''),
            'attendance': data.get('attendance', ''),
            'study_hours': data.get('study_hours', ''),
            'parental_support': data.get('parental_support', ''),
            'previous_grade': data.get('previous_grade', ''),
            'prediction': data.get('prediction', ''),
            'accuracy': data.get('accuracy', ''),
            'timestamp': data.get('timestamp', ''),
        })

    return render(request, "myapp/dropoutpredictionfetchall.html", {
        'dropout_data': dropout_data,
    })


def predict_course(request):
    # Load dataset
    df = pd.read_csv("course_suggestion_dataset.csv")

    # Courses dropdown
    courses = df["SuggestedCourse"].unique().tolist()

    result = None
    if request.method == "POST":
        attendance = int(request.POST.get("attendance"))
        percentage = int(request.POST.get("percentage"))
        interest_tech = int(request.POST.get("interest_tech"))
        interest_design = int(request.POST.get("interest_design"))
        interest_management = int(request.POST.get("interest_management"))

        # Model features and target
        X = df[["Attendance", "Percentage", "Interest_Tech", "Interest_Design", "Interest_Management"]]
        y = df["SuggestedCourse"]

        # Train Decision Tree
        model = DecisionTreeClassifier(random_state=42)
        model.fit(X, y)

        # Predict
        new_data = [[attendance, percentage, interest_tech, interest_design, interest_management]]
        result = model.predict(new_data)[0]

    return render(request, "myapp/predict_course.html", {"courses": courses, "result": result})
