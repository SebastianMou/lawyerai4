from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage

from .tokens import account_activation_token
from .forms import CustomLoginForm, RegisterForm  
from api.models import ContractProject

# Create your views here.
def index(request):
    return render(request, 'index.html')

def chats(request):
    return render(request, 'chats.html')

def contracts(request):
    return render(request, 'documents/contracts.html')

def contract(request, pk):
    # Retrieve the ContractProject object based on its primary key (pk)
    contract = get_object_or_404(ContractProject, pk=pk)
    contract = {
        'contract': contract,
    }
    return render(request, 'documents/contract.html', contract)

def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)  # Use CustomLoginForm here
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome {username}!")
                return redirect('/')  # Replace with your desired redirect URL after login
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomLoginForm()  # Use CustomLoginForm here
    context =  {
        'form': form,
    }
    return render(request, 'authentication/login.html', context)

def logout_view(request):
    logout(request)  # This logs out the user
    return redirect('login')

def signup(request):
    if request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')

            # Check if the email is already registered
            if User.objects.filter(email=email).exists():
                messages.error(request, 'This email is already registered.')
                return redirect('signup')
            else:
                user = form.save(commit=False)
                user.is_active = False  # Set user as inactive until email is verified
                user.save()

                # Call your email activation function to handle the email verification process
                activateEmail(request, user, email)

                # Redirect to 'check_email' page instead of the homepage
                return redirect('check_email')
    else:
        form = RegisterForm()
    
    context = {
        'form': form,
    }
    return render(request, 'authentication/signup.html', context)


def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        # Log the user in
        login(request, user)

        messages.success(request, 'Thank you for confirming your email. You can now log in to your account.')
        return redirect('login')  # Redirect to the login page
    else:
        messages.error(request, 'The activation link is not valid!')
    return render(request, 'index.html')

def activateEmail(request, user, to_email):
    mail_subject = 'Activate your user account.'
    message = render_to_string('authentication/template_activate_account.html', {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    email.content_subtype = "html"
    if email.send():
        messages.success(request, f'Dear {user.username}, please check your email {to_email} and click on the activation link you have received to confirm and complete the registration. Note: Check your spam folder.')
    else:
        messages.error(request, f'Problem sending confirmation email to {to_email}, please check if you entered it correctly.')

def check_email(request):
    return render(request, 'authentication/check_email.html')
