from http.client import responses

import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from Education.firebase_config import db
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache


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

    return render(req, "myapp/registration.html")


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
            return redirect("home")
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
    return render(request, "myapp/home.html", {"email": email})


def logout_view(request):
    logout(request)            # ← user ka session clear ho jayega
    request.session.flush()    # ← session puri tarah se clear
    return redirect('/l')
