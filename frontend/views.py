from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
import requests
from google.auth.transport import requests
from django.utils.html import strip_tags

from io import BytesIO
import re
from xhtml2pdf import pisa

from .tokens import account_activation_token
from .forms import CustomLoginForm, RegisterForm  
from api.models import ContractProject, ChatSession, ContractSteps, ValidationResult

# Create your views here.
def hero(request):
    return render(request, 'hero.html')

@login_required(login_url='/login/')  
def index(request):
    return render(request, 'index.html')

@login_required(login_url='/login/')  
def chats(request):
    return render(request, 'chats.html')

@login_required(login_url='/login/')  
def contracts(request):
    return render(request, 'documents/contracts.html')

@login_required(login_url='/login/')  
def view_chat_session(request, session_id):
    try:
        # Retrieve the ChatSession object
        chat_session = get_object_or_404(ChatSession, id=session_id, owner=request.user)
        return render(request, 'chat.html', {'chat_session': chat_session})  # Assuming chats.html is the template for chat sessions
    except ChatSession.DoesNotExist:
        return HttpResponse("Sesión de chat no encontrada.", status=404)

@login_required(login_url='/login/')
def contract(request, pk):
    # Retrieve the ContractProject object
    contract = get_object_or_404(ContractProject, pk=pk)

    contract.has_changes = True 
    contract.save()

    context = {'contract': contract}
    return render(request, 'documents/contract.html', context)


User = get_user_model()

def login_view(request):
    # Redirect if the user is already authenticated
    if request.user.is_authenticated:
        return redirect('/')  # Redirect to the main page or desired URL for logged-in users

    if request.method == 'POST':
        form = CustomLoginForm(request.POST)  # Use the updated form
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username_or_email')
            password = form.cleaned_data.get('password')

            # Check if the input is an email
            if '@' in username_or_email:
                try:
                    # Attempt to get the user by email
                    user = User.objects.get(email=username_or_email)
                    username = user.username
                except User.DoesNotExist:
                    username = None  # Ensures authentication will fail if email not found
            else:
                # Assume it's a username
                username = username_or_email

            # Attempt authentication
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"¡Bienvenido {user.username}!")
                return redirect('/')  # Redirect after successful login
            else:
                messages.error(request, "Correo electrónico o nombre de usuario o contraseña incorrecta.")
        else:
            messages.error(request, "Correo electrónico o nombre de usuario o contraseña incorrecta.")
    else:
        form = CustomLoginForm()

    context = {
        'form': form,
    }
    return render(request, 'authentication/login.html', context)

def logout_view(request):
    logout(request)  # This logs out the user
    return redirect('login')

def signup(request):
    # Redirect if the user is already authenticated
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')

            # Check if the email is already registered
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Este correo electrónico ya está registrado.')
            else:
                user = form.save(commit=False)
                user.is_active = False  # Set user as inactive until email is verified
                user.save()

                # Call your email activation function to handle the email verification process
                activateEmail(request, user, email)

                # Redirect to 'check_email' page instead of the homepage
                return redirect('check_email')
        else:
            # Add specific error messages for each field
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
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

        messages.success(request, 'Gracias por confirmar tu correo electrónico. Ya puedes iniciar sesión en tu cuenta.')
        return redirect('login')  # Redirect to the login page
    else:
        messages.error(request, 'El enlace de activación no es válido!')
    return render(request, 'index.html')

def activateEmail(request, user, to_email):
    mail_subject = 'Activa tu cuenta de usuario.'
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
        messages.success(request, f'Estimado {user.username}, por favor revisa tu correo electrónico {to_email} y haz clic en el enlace de activación que has recibido para confirmar y completar el registro. Nota: Revisa tu carpeta de spam.')
    else:
        messages.error(request, f'Hubo un problema al enviar el correo de confirmación a {to_email}, por favor verifica si lo ingresaste correctamente.')

def check_email(request):
    return render(request, 'authentication/check_email.html')

@login_required(login_url='/login/')  
def invoice(request):
    return render(request, 'invoice.html')

@login_required(login_url='/login/')  
def contract_checklist_basis(request):
    return render(request, 'documents/contract-checklist-basis.html')

@login_required(login_url='/login/')  
def contract_step(request, pk):
    contract = get_object_or_404(ContractSteps, pk=pk)
    return render(request, 'documents/contract-step.html', {'contract': contract})

@login_required(login_url='/login/')  
def pages(request):
    if request.method == 'POST':
        user = request.user
        new_username = request.POST.get('username', user.username)
        new_first_name = request.POST.get('first_name', user.first_name)
        new_last_name = request.POST.get('last_name', user.last_name)

        # Definir la longitud máxima
        if len(new_username) > 30:
            messages.error(request, "El nombre de usuario no puede exceder los 30 caracteres.")
            return render(request, 'authentication/pages.html')
        
        if len(new_first_name) > 30:
            messages.error(request, "El nombre no puede exceder los 30 caracteres.")
            return render(request, 'authentication/pages.html')
        
        if len(new_last_name) > 30:
            messages.error(request, "El apellido no puede exceder los 30 caracteres.")
            return render(request, 'authentication/pages.html')

        # Verificar si el nombre de usuario ya existe
        if User.objects.filter(username=new_username).exclude(id=user.id).exists():
            messages.error(request, "El nombre de usuario ya está en uso. Por favor elige otro.")
            return render(request, 'authentication/pages.html')

        try:
            user.username = new_username
            user.first_name = new_first_name
            user.last_name = new_last_name
            user.save()
            messages.success(request, "¡Perfil actualizado con éxito!")
        except IntegrityError:
            messages.error(request, "Ocurrió un error al actualizar el perfil. Inténtalo de nuevo.")
        
        return redirect('pages')

    return render(request, 'authentication/pages.html')

@login_required(login_url='/login/')  
def delete_account(request):
    if request.method == 'POST':
        deleteUser = User.objects.get(username=request.user)
        deleteUser.delete()
        return redirect('login')

def download_contract_pdf(request, pk):
    # Fetch the ContractProject along with its related ContractSteps
    contract_project = get_object_or_404(ContractProject, pk=pk)
    
    # Render the HTML template with contract data
    html_content = render_to_string('documents/contract_project_pdf.html', {'contract': contract_project})
    
    # Create an HTTP response with PDF content type
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{contract_project.name}.pdf"'
    
    # Convert HTML to PDF using xhtml2pdf
    pisa_status = pisa.CreatePDF(html_content, dest=response)
    
    # Check for errors in PDF generation
    if pisa_status.err:
        return HttpResponse('An error occurred while generating the PDF.', status=500)
    
    return response

@login_required(login_url='/login/')  
def search(request):
    query = request.GET.get('search', '')

    contract_projects = ContractProject.objects.filter(name__icontains=query)
    chat_sessions = ChatSession.objects.filter(name__icontains=query)

    context = {
        'contract_projects': contract_projects,
        'chat_sessions': chat_sessions,
        'query': query,
    }
    return render(request, 'search.html', context)

@login_required(login_url='/login/')  
def search(request):
    query = request.GET.get('searched', '')

    # Get the current logged-in user
    user = request.user

    # Search for ContractProject related to the logged-in user
    contract_projects_list = ContractProject.objects.filter(owner=user, name__icontains=query)
    paginator_cp = Paginator(contract_projects_list, 5)  # Adjust the number per page as needed
    page_number_cp = request.GET.get('page_cp', 1)
    contract_projects = paginator_cp.get_page(page_number_cp)

    # Search for ChatSession related to the logged-in user
    chat_sessions_list = ChatSession.objects.filter(owner=user, name__icontains=query)
    paginator_cs = Paginator(chat_sessions_list, 5)  # Adjust the number per page as needed
    page_number_cs = request.GET.get('page_cs', 1)
    chat_sessions = paginator_cs.get_page(page_number_cs)

    context = {
        'contract_projects': contract_projects,
        'chat_sessions': chat_sessions,
        'query': query,
    }
    return render(request, 'search/search_chatandcontract.html', context)

@login_required(login_url='/login/')  
def feedback(request):
    return render(request, 'search/feedback.html')

@login_required(login_url='/login/')
def contract_stepbystep(request):
    return render(request, 'documents/contract-steps.html')

@login_required(login_url='/login/')
def contract_check_basis_view(request, pk):
    contract = get_object_or_404(ContractSteps, id=pk, user=request.user)
    contract_project = getattr(contract, 'contract_project', None)  # Get the related ContractProject if it exists

    latest_validation_result = ValidationResult.objects.filter(contract=contract).order_by('-created_at').first()

    # Check if changes have been made to the ContractProject
    has_changes = False  # Default to False
    if contract_project and contract_project.has_changes:
        has_changes = True  # Set to True if the project has changes
        contract_project.has_changes = False  # Reset it to False after displaying the warning
        contract_project.save()

    return render(request, 'documents/contract-check-basis.html', {
        'contract': contract, 
        'pk': pk, 
        'ai_check_completed': contract.check_completed,  
        'latest_validation_result': latest_validation_result, 
        'has_changes': has_changes,  # Pass this to the template so it can display the pop-up
    })

@login_required(login_url='/login/')
def paper(request):
    return render(request, 'documents/paper.html')

@login_required(login_url='/login/')
def generate_contract_pdf(request, contract_id):
    # Fetch the ContractSteps instance
    contract = get_object_or_404(ContractSteps, id=contract_id)

    # Sanitize the contract title to avoid invalid characters in the filename
    sanitized_title = re.sub(r'[^a-zA-Z0-9_-]', '_', contract.title) if contract.title else f'contract_{contract_id}'

    # Render the HTML template with contract data
    html_content = render_to_string('documents/contract_pdf.html', {'contract': contract})

    # Create an HTTP response with PDF content type
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{sanitized_title}.pdf"'

    # Convert HTML to PDF using xhtml2pdf
    pisa_status = pisa.CreatePDF(html_content, dest=response)

    # Check for errors in PDF generation
    if pisa_status.err:
        return HttpResponse('An error occurred while generating the PDF.', status=500)

    return response

@login_required(login_url='/login/')
def generate_contract_pdf_full_doc(request, contract_id):
    # Fetch the ContractProject instance
    contract = get_object_or_404(ContractProject, id=contract_id)

    # Sanitize the contract name to avoid invalid characters in the filename
    sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', contract.name) if contract.name else f'contract_{contract_id}'

    # Render the HTML template with contract project data
    html_content = render_to_string('documents/generate_contract_pdf_full_doc.html', {'contract': contract})

    # Create an HTTP response with PDF content type
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{sanitized_name}.pdf"'

    # Convert HTML to PDF using xhtml2pdf
    pisa_status = pisa.CreatePDF(html_content, dest=response)

    # Check for errors in PDF generation
    if pisa_status.err:
        return HttpResponse('An error occurred while generating the PDF.', status=500)

    return response

@login_required(login_url='/login/')
def full_doc_ai_check(request, pk):
    contract = get_object_or_404(ContractProject, pk=pk)
    context = {
        'contract': contract,
    }
    return render(request, 'documents/full-doc-ai-check.html', context)