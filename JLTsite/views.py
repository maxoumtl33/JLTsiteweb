from django.shortcuts import render, redirect


def home(request):
    

    return render(request, 'JLTsite/home.html', {
        
    })

def repas(request):

    return render(request, 'JLTsite/repas.html', {

    })


def evenement(request):

    return render(request, 'JLTsite/evenement.html', {

    })


def contacts(request):

    return render(request, 'JLTsite/contacts.html', {

    })