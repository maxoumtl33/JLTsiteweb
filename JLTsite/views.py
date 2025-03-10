from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from .forms import *
from .forms import *
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail
import requests
from django.http import HttpResponse


def is_admin(user):
    return user.is_staff  # Checks if the user is a staff member (admin)


# Create your views here.
def home(request):
    if request.method == 'GET':
        categories = CategorieBoiteALunch.objects.all()
        boites = BoiteALunch.objects.all()
        context = {
            'title': 'Home',
            'categories': categories,
            'boites': boites,
            # Add other context data if necessary
        }
        return render(request, 'JLTsite/home.html', context
        )


@user_passes_test(is_admin)
def dashboard(request):
    # Display all BoiteALunch objects
    boites = BoiteALunch.objects.all()
    return render(request, 'JLTsite/dashboard.html', {'boites': boites})

@user_passes_test(is_admin)
def create_boite(request):
    if request.method == "POST":
        # Check which form is being submitted
        if 'boite_submit' in request.POST:
            boite_form = BoiteALunchForm(request.POST, request.FILES)
            categorie_form = CategorieBoiteALunchForm()  # Just create an empty form for categories
            
            if boite_form.is_valid():
                boite = boite_form.save()  # Save the BoiteALunch instance
                return redirect('dashboard')  # Redirect after saving
        elif 'categorie_submit' in request.POST:
            categorie_form = CategorieBoiteALunchForm(request.POST)
            boite_form = BoiteALunchForm()  # Just create an empty form for lunch boxes
            
            if categorie_form.is_valid():
                categorie_form.save()  # Save the CategorieBoiteALunch instance
                return redirect('dashboard')  # Redirect after saving
    else:
        boite_form = BoiteALunchForm()
        categorie_form = CategorieBoiteALunchForm()

    return render(request, 'JLTsite/create_boite.html', {
        'boite_form': boite_form,
        'categorie_form': categorie_form,
    })

@user_passes_test(is_admin)
def edit_boite(request, pk):
    boite = get_object_or_404(BoiteALunch, pk=pk)
    if request.method == "POST":
        form = BoiteALunchForm(request.POST, request.FILES, instance=boite)
        if form.is_valid():
            form.save()
            return redirect('dashboard')  # Redirect to the dashboard after saving
    else:
        form = BoiteALunchForm(instance=boite)
    return render(request, 'JLTsite/edit_boite.html', {'form': form, 'boite': boite})


def get_boites(request, category_id):
    boites = BoiteALunch.objects.filter(categorie_id=category_id)  # Filter BoiteALunch by selected category
    boite_list = [{
        'nom': boite.nom,
        'description': boite.description,
        'photo1': boite.photo1.url if boite.photo1 else '',
        'photo2': boite.photo2.url if boite.photo2 else '',
        'id': boite.id,
        'prix': boite.prix,
        'detail_url': f'/boite/{boite.id}/',
        'categorie': {
            'id': boite.categorie.id,
            'nom': boite.categorie.nom,
        }
    } for boite in boites]
    return JsonResponse(boite_list, safe=False)  # Return a JSON response


def boite_detail(request, boite_id):
    # Retrieve the specific BoiteALunch object
    boite = get_object_or_404(BoiteALunch, id=boite_id)
    return render(request, 'JLTsite/boite_detail.html', {'boite': boite})


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']

            ### Send Email ###
            send_mail(
                subject=f'Message from {name}',
                message=message,
                from_email=email,
                recipient_list=['testjltemail@gmail.com'],  # Replace with your email
            )
            
            return HttpResponse('Thank you for your message!')

    else:
        form = ContactForm()
    return render(request, 'JLTsite/contact.html', {'form': form})


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(name, email, message):
    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = 'recipient@example.com'  # Your email here
    msg['Subject'] = f'Message from {name}'

    # Attach the message content
    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        # Use your app-specific password here.
        server.login('your_email@gmail.com', 'your_app_specific_password')  
        server.send_message(msg)
        server.quit()
        print('Email sent successfully!')
    except Exception as e:
        print(f'Failed to send email: {e}')

# Example usage
send_email(name='John Doe', email='john.doe@example.com', message='Hello, this is a test email.')



def home_events(request):
    # Retrieve the specific BoiteALunch object

    if request.method == 'GET':
        # Any logic to prepare data for the template
        context = {
            'title': 'Home',
            # Add other context data if necessary
        }
        return render(request, 'JLTsite/home_event.html', context)
    
    # Add a default response if needed, e.g., if not GET
    return HttpResponse(status=405)  # Method Not Allowed