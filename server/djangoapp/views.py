from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from .models import *
from .restapis import *
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from datetime import datetime
import logging
import json

# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create your views here.


# Create an `about` view to render a static about page
def about(request):
    context={}
    if request.method=='GET':
        return render(request, 'djangoapp/about.html',context)


# Create a `contact` view to return a static contact page
def contact(request):
    context={}
    if request.method=='GET':
        return render(request, 'djangoapp/contact.html',context)

# Create a `login_request` view to handle sign in request
def login_request(request):
    context={}
    if request.method=='POST':
        username=request.POST['username']
        password=request.POST['psw']
        user=authenticate(username=username,password=password)
        if user is not None:
            login(request, user)
            return redirect('djangoapp:index')
        context['message']='Invalid login credentials'
        return render(request, 'djangoapp/login.html', context)
    return render(request, 'djangoapp/login.html', context)

# Create a `logout_request` view to handle sign out request
def logout_request(request):
    logout(request)
    return redirect('djangoapp:index')

# Create a `registration_request` view to handle sign up request
def registration_request(request):
    context={}
    if request.method=='GET':
        return render(request,'djangoapp/registration.html', context)
    username=request.POST['username']
    password=request.POST['psw']
    firstname=request.POST['firstname']
    lastname=request.POST['lastname']
    user_exists=False
    try: 
        User.objects.get(username=username)
        user_exists=True
    except:
        logger.debug(f'{username} is new user')
    if not user_exists:
        user= User.objects.create_user(username=username, first_name=firstname, last_name=lastname, password=password)
        login(request, user)
        return redirect('/djangoapp/')
    return render(request, 'djangoapp/registration.html', context)        

# Update the `get_dealerships` view to render the index page with a list of dealerships
def get_dealerships(request):
    context = {}
    #if request.method == "GET":
    #    return render(request, 'djangoapp/index.html', context)
    if request.method == "GET":
        url = "https://ash24366-3000.theiadocker-2-labs-prod-theiak8s-4-tor01.proxy.cognitiveclass.ai/dealerships/get"
        context['dealerships']=get_dealers_from_cf(url)
        return render(request, 'djangoapp/index.html', context)

# Create a `get_dealer_details` view to render the reviews of a dealer
# def get_dealer_details(request, dealer_id):
# ...
def get_dealer_details(request, dealer_id):
    context = {}
    if request.method == "GET":
        url = f'https://ash24366-5000.theiadocker-2-labs-prod-theiak8s-4-tor01.proxy.cognitiveclass.ai/api/get_reviews?id={dealer_id}'
        reviews = get_dealer_reviews_from_cf(url)
        context = {
            "reviews":  reviews, 
            "dealer_id": dealer_id
        }

        return render(request, 'djangoapp/dealer_details.html', context)

# Create a `add_review` view to submit a review
# def add_review(request, dealer_id):
# ...
def add_review(request, dealer_id):
    # User must be logged in before posting a review
    if request.user.is_authenticated:
        # GET request renders the page with the form for filling out a review
        if request.method == "GET":
            url = f"https://ash24366-3000.theiadocker-2-labs-prod-theiak8s-4-tor01.proxy.cognitiveclass.ai/dealerships/get?id={dealer_id}"
            # Get dealer details from the API
            context = {
                "cars": CarModel.objects.all(),
                "dealer": get_dealer_by_id(url),
            }
            return render(request, 'djangoapp/add_review.html', context)

        # POST request posts the content in the review submission form to the Cloudant DB using the post_review Cloud Function
        if request.method == "POST":
            form = request.POST
            review = dict()
            review["name"] = f"{request.user.first_name} {request.user.last_name}"
            review["dealership"] = dealer_id
            review["review"] = form["content"]
            review["purchase"] = form.get("purchasecheck")
            if review["purchase"]:
                review["purchase_date"] = datetime.strptime(form.get("purchasedate"), "%m/%d/%Y").isoformat()
            car = CarModel.objects.get(pk=form["car"])
            review["car_make"] = car.car_make.name
            review["car_model"] = car.name
            review["car_year"] = car.year
            
            # If the user bought the car, get the purchase date
            if form.get("purchasecheck"):
                review["purchase_date"] = datetime.strptime(form.get("purchasedate"), "%m/%d/%Y").isoformat()
            else: 
                review["purchase_date"] = None

            url = f"https://ash24366-5000.theiadocker-2-labs-prod-theiak8s-4-tor01.proxy.cognitiveclass.ai/api/post_review?id={dealer_id}"  # API Cloud Function route
            json_payload = {"review": review}  # Create a JSON payload that contains the review data

            # Performing a POST request with the review
            result = post_request(url, json_payload)
            if int(result.status_code) == 200:
                print("Review posted successfully.")

            # After posting the review the user is redirected back to the dealer details page
            return redirect("djangoapp:dealer_details", dealer_id=dealer_id)

    else:
        # If user isn't logged in, redirect to login page
        print("User must be authenticated before posting a review. Please log in.")
        return redirect("/djangoapp/login")
