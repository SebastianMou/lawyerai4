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
import datetime

from .tokens import account_activation_token
from .forms import CustomLoginForm, RegisterForm  
from api.models import ContractProject, ChatSession, ContractSteps, ValidationResult, Subscription, PaymentRecord
from django.conf import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

print(f"Stripe API key being used: {stripe.api_key}")

# Create your views here.
def hero(request):
    return render(request, 'hero.html', {'stripe_public_key': settings.STRIPE_PUBLIC_KEY})

def create_checkout_session(request):
    try:
        user_email = request.user.email  # Get the email of the logged-in user
        subscription_type = request.POST.get('subscription_type')  # Get the selected subscription type

        # Map subscription_type to Stripe price IDs
        price_mapping = {
            "basic_plan": 'price_1QZ4yWIs3n8Cewzv25GnCP3z',  # Basic Subscription Price ID
            "pro_plan": 'price_1QbANhIs3n8CewzvcXYreVPM',    # Pro Subscription Price ID
            "weekly_access": 'price_1QbqpeIs3n8CewzvRaTup0Iz'  # One-Time Weekly Access Price ID
        }

        # Check if the subscription type is valid
        price_id = price_mapping.get(subscription_type)
        if not price_id:
            return HttpResponse("Invalid subscription type.", status=400)

        # Determine mode based on subscription type
        mode = 'subscription' if subscription_type != 'weekly_access' else 'payment'

        # Create the Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode=mode,  # 'subscription' for subscriptions, 'payment' for one-time payments
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            customer_email=user_email,
            billing_address_collection='auto',
            locale='es-419',
            success_url=request.build_absolute_uri('/success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/cancel/'),
        )
        # Redirect the user to the Stripe Checkout page
        return redirect(session.url)
    except Exception as e:
        return HttpResponse(f"An error occurred: {e}")


def success_view(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return HttpResponse("Missing session ID.", status=400)
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)

        # Check if the session was a one-time payment or a subscription
        if session.mode == 'subscription':
            subscription_id = session.subscription
            customer_id = session.customer
            subscription_data = stripe.Subscription.retrieve(subscription_id)
            
            product_name = subscription_data['items']['data'][0]['price']['product']  # Get product ID
            product_details = stripe.Product.retrieve(product_name)  # Fetch product details from Stripe

            user = request.user
            subscription, created = Subscription.objects.get_or_create(user=user)
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_customer_id = customer_id
            subscription.subscription_status = "active"
            subscription.product_name = product_details['name']  # Save product name
            subscription.save()
        else:
            # Handle one-time payment (Acceso por Una Semana)
            product_name = "Acceso por Una Semana"
            user = request.user

            # Save the one-time payment details to the database
            PaymentRecord.objects.create(
                user=user,
                stripe_session_id=session_id,
                product_name=product_name,
                amount=session.amount_total / 100,  # Convert cents to currency
                currency=session.currency,
                status="paid"
            )

            print(f"User {user.email} purchased {product_name} with session ID {session_id}")

        return render(request, 'payments/success.html', {'subscription': None, 'product_name': product_name})
    except Exception as e:
        return HttpResponse(f"An error occurred: {e}", status=500)


"""
    There's a problem where if admincanceled subscription through stripe adminit will 
    not update in the Django Database
"""
@csrf_exempt
def stripe_webhook(request):
    import logging
    logger = logging.getLogger(__name__)

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"Webhook received: {event['type']}")  # Log event type
        logger.info(f"Webhook payload: {event}")  # Log full payload
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        return JsonResponse({'error': 'Invalid webhook signature'}, status=400)
    
    if event['type'] == 'customer.subscription.updated':
        subscription_data = event['data']['object']
        stripe_subscription_id = subscription_data['id']
        status = subscription_data['status']
        logger.info(f"Subscription {stripe_subscription_id} status updated to {status}")

        try:
            subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
            subscription.subscription_status = status
            subscription.save()
            logger.info(f"Subscription {stripe_subscription_id} updated in database")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription {stripe_subscription_id} does not exist in the database")

    return JsonResponse({'status': 'success'}, status=200)

def cancel_view(request):
    return render(request, 'payments/cancel.html')  # Render a cancel page

@login_required
def cancel_subscription(request):
    try:
        # Fetch the user's subscription from the database
        subscription = Subscription.objects.get(user=request.user)

        if subscription.stripe_subscription_id:
            # Use the Stripe API to cancel the subscription
            stripe.Subscription.delete(subscription.stripe_subscription_id)

            # Update the subscription status in the database
            subscription.subscription_status = 'canceled'
            subscription.save()

            # Redirect to a page displaying success status
            return render(request, 'payments/status_subscriptions.html', {
                'message': "Tu suscripción ha sido cancelada exitosamente.",
                'status': 'success'
            })
        else:
            # Redirect to a page displaying error status
            return render(request, 'payments/status_subscriptions.html', {
                'message': "No se encontró una suscripción activa para este usuario.",
                'status': 'error'
            })
    except Subscription.DoesNotExist:
        return render(request, 'payments/status_subscriptions.html', {
            'message': "La suscripción no existe.",
            'status': 'error'
        })
    except Exception as e:
        return render(request, 'payments/status_subscriptions.html', {
            'message': f"Ocurrió un error: {e}",
            'status': 'error'
        })

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

        # Specify the backend explicitly
        backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user, backend=backend)  # Provide the backend

        messages.success(request, 'Gracias por confirmar tu correo electrónico. Ya puedes iniciar sesión en tu cuenta.')
        return redirect('login')  # Redirect to the login page
    else:
        messages.error(request, 'El enlace de activación no es válido!')
    return redirect('login')  # Redirect to the login page even if activation fails


def activateEmail(request, user, to_email):
    domain = get_current_site(request).domain
    print(f"Domain fetched: {domain}")  # Add this for debugging

    mail_subject = 'Activate your user account.'
    message = render_to_string('authentication/template_activate_account.html', {
        'user': user.username,
        'domain': '127.0.0.1:7000',  # Overridden domain
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'http'  # Keep this as 'http' for local development
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    email.content_subtype = "html"
    if email.send():
        messages.success(request, f'Dear {user.username}, please check your email {to_email} and click the activation link.')
    else:
        messages.error(request, f'Problem sending confirmation email to {to_email}.')


def check_email(request):
    return render(request, 'authentication/check_email.html')

from django.utils.timezone import make_aware, now

@login_required(login_url='/login/')
def invoice(request):
    try:
        # Example context data
        all_plans = [
            {'id': 'weekly_access', 'name': 'Acceso por Una Semana', 'price': '$299 MXN / mes'},
            {'id': 'basic_plan', 'name': 'Suscripción Básica', 'price': '$250 MXN / mes'},
            {'id': 'pro_plan', 'name': 'Suscripción Estándar', 'price': '$350 MXN / mes'}
        ]
        
        # Retrieve subscription details
        subscription = Subscription.objects.filter(user=request.user).first()
        
        payments = []
        card_details = None
        cardholder_name = None
        payment_interval = None
        subscription_price = None

        # Retrieve one-time payment records
        one_time_payments = PaymentRecord.objects.filter(user=request.user).order_by('-created_at')

        # English-to-Spanish mapping for intervals
        interval_translation = {
            "day": "Día",
            "week": "Semana",
            "month": "Mes",
            "year": "Año",
        }

        if subscription and subscription.stripe_customer_id:
            # Retrieve subscription details
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            price_object = stripe_subscription['items']['data'][0]['price']  # Debug output
            print("Price Object from Stripe:", price_object)  # Debug price object

            subscription_price = price_object.get('unit_amount', 0) / 100  # Convert to currency
            print("Extracted Price:", subscription_price)  # Debug extracted price
            
            # Fetch invoices for the customer
            invoices = stripe.Invoice.list(customer=subscription.stripe_customer_id)
            for invoice in invoices['data']:
                payments.append({
                    'date': make_aware(datetime.datetime.fromtimestamp(invoice['created'])),  # Make datetime timezone-aware
                    'amount': invoice['amount_paid'] / 100,
                    'status': invoice['status'],
                    'type': 'subscription',  # Add type to differentiate subscription payments
                })

            # Fetch payment methods for the customer
            payment_methods = stripe.PaymentMethod.list(
                customer=subscription.stripe_customer_id,
                type="card"
            )
            if payment_methods['data']:
                card = payment_methods['data'][0]['card']
                card_details = {
                    'brand': card['brand'],
                    'last4': card['last4'],
                    'exp_month': card['exp_month'],
                    'exp_year': card['exp_year'],
                }

            # Retrieve the customer details for the cardholder name
            customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
            cardholder_name = customer.get('name', 'Nombre no disponible')

            # Retrieve subscription details
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            interval = stripe_subscription['items']['data'][0]['price']['recurring']['interval']  # e.g., "month", "week"
            payment_interval = interval_translation.get(interval, interval)  # Translate to Spanish

            # Retrieve price information
            subscription_price = stripe_subscription['items']['data'][0]['price']['unit_amount'] / 100  # Convert cents to currency

        # Add one-time payments to the combined list
        for otp in one_time_payments:
            payments.append({
                'date': otp.created_at,
                'amount': otp.amount,
                'status': otp.status,
                'type': 'one-time',  # Add type to differentiate one-time payments
                'product_name': otp.product_name,  # Include product name for one-time payments
            })

        # Sort payments by date (newest first)
        payments = sorted(payments, key=lambda x: x['date'], reverse=True)

        return render(request, 'invoice.html', {
            'subscription': subscription,  # Active subscription details
            'payments': payments,  # Combined payment history
            'one_time_payments': one_time_payments,  # List of one-time payments
            'card_details': card_details,
            'cardholder_name': cardholder_name,
            'payment_interval': payment_interval,
            'subscription_price': subscription_price,
            'all_plans': all_plans,
        })
    except Exception as e:
        return HttpResponse(f"An error occurred: {e}", status=500)



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


from django.http import JsonResponse

@login_required(login_url='/login/')
def full_doc_ai_check(request, pk):
    contract = get_object_or_404(ContractProject, pk=pk)
    context = {
        'contract': contract,
    }
    return render(request, 'documents/full-doc-ai-check.html', context)

