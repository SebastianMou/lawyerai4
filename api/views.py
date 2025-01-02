from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse
import json
import openai
import random
import stripe
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework import status, pagination

from .models import ContractProject, AIHighlightChat, ChatSession, Message, ContractSteps, ValidationResult, Subscription
from .serializer import ContractProjectSerializer, AIHighlightChatSerializer, MessageSerializer, ChatSessionSerializer, FeedbackSerializer, ContractStepsSerializer, ValidationResultSerializer

openai.api_key = settings.OPENAI_API_KEY

# Create your views here.
@api_view(['GET'])
def apiOverview(request):
    api_urls = {
        # Contract Project URLs
        'Contract Projects': '/contract-project/',
        'Contract Project Detail': '/contract-detail/<int:pk>/',
        'Contract Project Create': '/contract-create/',
        'Contract Project Update': '/contract-update/<int:pk>/',
        'Contract Project Delete': '/contract-delete/<int:pk>/',

        # AI Chat for Contracts
        'Create AI Chat for Contract': '/create-ai-chat-contract/<int:contract_project_id>/',
        'Get Chat History for Contract': '/get-chat-history-contract/<int:contract_project_id>/',
        'Delete Chat History for Contract': '/delete-chat-history-contract/<int:contract_project_id>/',

        # Search and Feedback
        'Search API': '/search/',
        'Submit Feedback': '/feed-back/',

        # Steps for Contract Creation
        'Contract Steps': '/contract-steps/',
        'Generate Suggestions': '/generate-suggestions/',
        'Generate AI Text': '/generate-ai-text/',
        'Contract Check Basis': '/contract-check-basis/<int:pk>/',
        'Legality Check View': '/contract/<int:pk>/test-legality-check/',

        # Contract Steps Projects
        'Contract Steps Project': '/contract-steps-project/',
        'Contract Steps Project Detail': '/contract-steps-project-detail/<int:pk>/',
        'Contract Steps Project Update': '/contract-steps-project-update/<int:pk>/',
        'Contract Steps Project Delete': '/contract-steps-project-delete/<int:pk>/',

        # Chat Sessions Lawyer URLs
        'List Chat Sessions': '/chatsessions/',
        'Create Chat Session': '/chatsessions/create/',
        'Retrieve Chat Session': '/chatsessions/<int:session_id>/',
        'Send Message to Chat Session': '/chatsessions/<int:session_id>/send_message/',
        'List User Chat Sessions': '/chatsessions/user/',
        'Update Chat Session': '/chatsessions/<int:session_id>/update/',
        'Delete Chat Session': '/chatsessions/<int:session_id>/delete/',
    }
    return Response(api_urls)

@api_view(['GET'])
def contract_project(request):
    contracts = ContractProject.objects.filter(owner=request.user).order_by('-created_at')
    serializer = ContractProjectSerializer(contracts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def contract_project_detail(request, pk):
    contracts = ContractProject.objects.get(id=pk)
    serializer = ContractProjectSerializer(contracts, many=False)
    return Response(serializer.data)

@api_view(['POST'])
def contract_project_create(request):
    serializer = ContractProjectSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(owner=request.user)
        return Response(serializer.data, status=201)
    else:
        print(serializer.errors)  # Log errors to see what went wrong
        return Response(serializer.errors, status=400)

@api_view(['PUT'])
def contract_project_update(request, pk):
    contract = ContractProject.objects.get(id=pk)
    data = request.data.copy()  # Make a copy of the request data

    # Log the incoming data to check if it is being received correctly
    print('Incoming data:', data)

    # Ensure the description is not None
    if data.get('description') is None:
        data['description'] = ''  # Replace None with an empty string

    serializer = ContractProjectSerializer(instance=contract, data=data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        contract.has_changes = True 
        contract.save()
        print('Data saved successfully, changes were marked as True')  # Add this log to confirm successful save
        return JsonResponse(serializer.data, status=200)
    else:
        print('Serializer errors:', serializer.errors)  # Log errors to help debug
    
    return JsonResponse(serializer.errors, status=400)

@api_view(['DELETE'])
def contract_project_delete(request, pk):
    contract = ContractProject.objects.get(id=pk)
    contract.delete()
    return Response('Contract project deleted successfully :)')

@api_view(['POST']) 
def create_ai_chat_contract(request, contract_project_id):
    try:
        print("Starting create_ai_chat_contract function...")
        
        # Fetch the contract project and check for user input
        contract_project = ContractProject.objects.get(id=contract_project_id)
        print(f"Contract Project ID: {contract_project_id}, User: {request.user}")

        user = request.user
        highlighted_text = request.data.get('highlighted_text', '').strip()
        instruction = request.data.get('instruction')
        print(f"Highlighted Text: {highlighted_text}, Instruction: {instruction}")

        # Retrieve chat history
        chat_history = AIHighlightChat.objects.filter(
            user=user,
            contract_project=contract_project
        ).order_by('created_at')
        print(f"Total chat history messages: {len(chat_history)}")

        # Initialize summary and recent messages
        summary_text = ""
        recent_messages = list(chat_history)[-15:]  # Last 15 messages for context
        print("Recent messages for prompt context:", [msg.instruction for msg in recent_messages])

        # Summarize older messages if chat exceeds 20 messages
        if len(chat_history) > 20:
            # Concatenate older messages to create summary prompt
            older_messages = " ".join([msg.instruction for msg in list(chat_history)[:-15]])
            print("Older messages to summarize:", older_messages)

            summary_prompt = [
                {"role": "system", "content": "Resume la siguiente conversación."},
                {"role": "user", "content": older_messages}
            ]

            # Generate summary for older messages
            summary_response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=summary_prompt,
                max_tokens=150
            )
            summary_text = summary_response.choices[0].message.content.strip()
            print("Generated summary text:", summary_text)

        # Build the prompt including the summary and recent messages
        conversation_history = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente legal en una plataforma de creación de documentos, enfocado en ayudar a los usuarios "
                    "a organizar, redactar y mejorar texto, especialmente en el contexto de contratos legales y documentos formales. "
                    "Responde en español, usando un tono profesional y claro. Utiliza el formato Markdown para organizar las respuestas "
                    "de manera estructurada, con listas, encabezados y ejemplos cuando sea útil.\n\n"
                    "Tu función principal es servir como copiloto legal para el usuario, ayudándolo a:\n\n"
                    "- **Organizar y dar formato a textos**: Asegúrate de que el texto esté bien estructurado y profesional.\n"
                    "- **Proveer información legal**: Responde preguntas sobre el proceso legal en México y ofrece explicaciones "
                    "generales sobre temas como custodia, contratos, mediación, y otros procedimientos relevantes.\n"
                    "- **Sugerir opciones de redacción profesional**: Ayuda a mejorar el tono y estilo de los textos para que "
                    "suenen formales y legales.\n\n"
                    "Recuerda siempre incluir un recordatorio de que el usuario debe consultar a un abogado para obtener asesoramiento "
                    "legal personalizado, ya que eres solo una herramienta de apoyo y no reemplazas la asesoría profesional."
                )
            }
        ]
        if summary_text:
            conversation_history.append({"role": "assistant", "content": f"Resumen de la conversación anterior: {summary_text}"})
            print("Added summary to conversation history.")

        # Append recent messages to the prompt
        for message in recent_messages:
            conversation_history.append({"role": "user", "content": message.instruction})
            conversation_history.append({"role": "assistant", "content": message.ai_response})

        print("Final conversation history sent to OpenAI:", conversation_history)

        # Add the latest user instruction with Markdown request
        prompt = f"Highlight: {highlighted_text}\nInstruction: {instruction}\nRespond in Markdown format.\n" if highlighted_text else f"Instruction: {instruction}\nRespond in Markdown format.\n"
        conversation_history.append({"role": "user", "content": prompt})

        # Call the OpenAI API with the structured conversation history
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation_history,
            max_tokens=500,
            temperature=0.7
        )
        ai_response = response.choices[0].message.content.strip()
        print("AI response:", ai_response)

        # Save the chat message for future context
        ai_chat = AIHighlightChat.objects.create(
            user=user,
            contract_project=contract_project,
            highlighted_text=highlighted_text,
            instruction=instruction,
            ai_response=ai_response
        )
        print("Chat message saved to database.")

        return JsonResponse({'ai_response': ai_response}, status=201)

    except ContractProject.DoesNotExist:
        print("Error: Contract project not found.")
        return JsonResponse({'error': 'Contract project not found'}, status=404)
    except Exception as e:
        print(f"Error occurred: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
def get_chat_history_contract(request, contract_project_id):
    try:
        # Get all chat messages related to the contract project
        chat_history = AIHighlightChat.objects.filter(contract_project_id=contract_project_id).order_by('created_at')
        serializer = AIHighlightChatSerializer(chat_history, many=True)
        
        return JsonResponse({'chat_history': serializer.data}, status=200)
    
    except ContractProject.DoesNotExist:
        return JsonResponse({'error': 'Contract project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['DELETE'])
def delete_chat_history_contract(request, contract_project_id):
    try:
        # Filter chat history for the specific contract and delete all related messages
        chat_history = AIHighlightChat.objects.filter(contract_project_id=contract_project_id)
        deleted_count, _ = chat_history.delete()
        
        print(f"Deleted {deleted_count} chat messages for contract project ID {contract_project_id}.")
        return JsonResponse({'message': f'{deleted_count} chat messages deleted successfully.'}, status=200)

    except ContractProject.DoesNotExist:
        return JsonResponse({'error': 'Contract project not found'}, status=404)
    except Exception as e:
        print(f"Error occurred: {e}")
        return JsonResponse({'error': str(e)}, status=500)

##################################################################################################################

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    try:
        # Get the user's input message
        user_input = request.data.get('message', '')

        if not user_input:
            return Response({"error": "Message content is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a session name based on the user input question
        prompt_for_name = f"Genere un nombre de sesión de chat conciso y significativo basado en la siguiente pregunta: '{user_input}'"
        session_name_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that generates short session names based on user input."},
                {"role": "user", "content": prompt_for_name}
            ],
            max_tokens=50,
            temperature=0.7
        )
        session_name = session_name_response.choices[0].message.content.strip()

        # Create the chat session with the generated name
        chat_session = ChatSession.objects.create(
            name=session_name,
            owner=request.user
        )

        # Create and save the initial user message
        Message.objects.create(
            chat_session=chat_session,
            content=user_input,
            sender='user'
        )

        # Retrieve chat history and limit to recent messages if applicable
        chat_history = Message.objects.filter(chat_session=chat_session).order_by('created_at')
        recent_messages = list(chat_history)[-15:]  # Keep the last 15 messages for context

        # Summarize older messages if the chat has more than 20 messages
        summary_text = ""
        if len(chat_history) > 20:
            # Concatenate older messages for the summary
            older_messages = " ".join([msg.content for msg in list(chat_history)[:-15]])
            summary_prompt = [
                {"role": "system", "content": "Resume la siguiente conversación."},
                {"role": "user", "content": older_messages}
            ]
            # Generate summary for older messages
            summary_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=summary_prompt,
                max_tokens=150
            )
            summary_text = summary_response.choices[0].message.content.strip()

        # Build the AI's response prompt including summary and recent messages
        messages = [
            {
                "role": "system", 
                "content": (
                    "Eres un asistente legal nombre Anton enfocado en proporcionar orientación en asuntos legales en México. "
                    "Responde de manera estructurada y profesional, y utiliza un lenguaje claro y accesible. "
                    "Utiliza el formato de markdown para que las respuestas sean claras y bien organizadas, incluyendo "
                    "listas, encabezados y énfasis cuando sea necesario. Evita dar consejos específicos que solo un "
                    "abogado calificado puede brindar; en su lugar, proporciona opciones generales, procesos legales típicos "
                    "y pasos recomendados. Siempre incluye un recordatorio de que el usuario debe consultar a un abogado para "
                    "consejos personalizados.\n\n"
                    "Al responder, considera lo siguiente:\n\n"
                    "- **Haz preguntas aclaratorias al usuario** para entender mejor su situación.\n"
                    "- **Ofrece opciones legales comunes en México**, como mediación, convenios estipulados, o procesos de modificación de custodia.\n"
                    "- **Explica cada opción** en términos simples y menciona cualquier documento o proceso requerido.\n\n"
                    "Recuerda siempre enfocar las respuestas en el contexto legal de México y evitar suposiciones o interpretaciones personales."
                )
            }
        ]
        if summary_text:
            messages.append({"role": "assistant", "content": f"Summary of previous conversation: {summary_text}"})

        # Append recent messages to the prompt
        for message in recent_messages:
            messages.append({
                "role": "user" if message.sender == "user" else "assistant",
                "content": message.content
            })

        # Add the initial user message to the prompt
        messages.append({"role": "user", "content": user_input})

        # Generate the AI's response
        ai_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        ai_answer = ai_response.choices[0].message.content.strip()

        # Save the AI's response in the chat session
        Message.objects.create(
            chat_session=chat_session,
            content=ai_answer,
            sender='AI'
        )

        # Serialize and return the created session with the messages
        session_serializer = ChatSessionSerializer(chat_session)
        return Response(session_serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"Error occurred: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message_to_chat_session(request, session_id):
    try:
        # Retrieve the chat session
        chat_session = ChatSession.objects.get(id=session_id, owner=request.user)
        
        # Get the user's new message
        user_input = request.data.get('message', '')
        
        if not user_input:
            return Response({"error": "Message content is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Save the user's message in the database
        user_message = Message.objects.create(
            chat_session=chat_session,
            content=user_input,
            sender='user'
        )

        # Retrieve chat history
        chat_history = Message.objects.filter(chat_session=chat_session).order_by('created_at')

        # Initialize summary and recent messages
        summary_text = ""
        recent_messages = list(chat_history)[-15:]  # Last 15 messages for context

        # Summarize older messages if chat exceeds 20 messages
        if len(chat_history) > 20:
            # Concatenate older messages to create summary prompt
            older_messages = " ".join([msg.content for msg in list(chat_history)[:-15]])
            summary_prompt = [
                {"role": "system", "content": "Summarize the following conversation."},
                {"role": "user", "content": older_messages}
            ]

            # Generate summary for older messages
            summary_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=summary_prompt,
                max_tokens=150  # Limit the summary length
            )
            summary_text = summary_response.choices[0].message.content.strip()

        # Build the prompt including the summary and recent messages
        messages = [
            {
                "role": "system", 
                "content": (
                    "Eres un asistente legal nombre Anton enfocado en proporcionar orientación en asuntos legales en México. "
                    "Responde de manera estructurada y profesional, y utiliza un lenguaje claro y accesible. "
                    "Utiliza el formato de markdown para que las respuestas sean claras y bien organizadas, incluyendo "
                    "listas, encabezados y énfasis cuando sea necesario. Evita dar consejos específicos que solo un "
                    "abogado calificado puede brindar; en su lugar, proporciona opciones generales, procesos legales típicos "
                    "y pasos recomendados. Siempre incluye un recordatorio de que el usuario debe consultar a un abogado para "
                    "consejos personalizados.\n\n"
                    "Al responder, considera lo siguiente:\n\n"
                    "- **Haz preguntas aclaratorias al usuario** para entender mejor su situación.\n"
                    "- **Ofrece opciones legales comunes en México**, como mediación, convenios estipulados, o procesos de modificación de custodia.\n"
                    "- **Explica cada opción** en términos simples y menciona cualquier documento o proceso requerido.\n\n"
                    "Recuerda siempre enfocar las respuestas en el contexto legal de México y evitar suposiciones o interpretaciones personales."
                )
            }
        ]
        if summary_text:
            messages.append({"role": "assistant", "content": f"Summary of previous conversation: {summary_text}"})

        # Append recent messages to the prompt
        for message in recent_messages:
            messages.append({
                "role": "user" if message.sender == "user" else "assistant",
                "content": message.content
            })

        # Add the latest user message to the prompt
        messages.append({"role": "user", "content": user_input})

        # Generate AI's response with the updated context
        ai_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        # Extract the AI's generated response
        ai_answer = ai_response.choices[0].message.content.strip()

        # Save the AI's response as a new message in the same chat session
        Message.objects.create(
            chat_session=chat_session,
            content=ai_answer,
            sender='AI'
        )

        # Serialize and return the updated session with all messages
        session_serializer = ChatSessionSerializer(chat_session)
        return Response(session_serializer.data, status=status.HTTP_201_CREATED)

    except ChatSession.DoesNotExist:
        return Response({"error": "Chat session not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error occurred: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_chat_sessions(request):
    chat_sessions = ChatSession.objects.filter(owner=request.user)
    serializer = ChatSessionSerializer(chat_sessions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def retrieve_chat_session(request, session_id):
    try:
        chat_session = ChatSession.objects.get(id=session_id, owner=request.user)
    except ChatSession.DoesNotExist:
        return Response({"error": "Chat session not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = ChatSessionSerializer(chat_session)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_chat_sessions(request):
    # Filter chat sessions by the currently authenticated user
    chat_sessions = ChatSession.objects.filter(owner=request.user).order_by('-created_at')

    # Serialize the chat sessions
    serializer = ChatSessionSerializer(chat_sessions, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_contract_to_project(request, pk):
    try:
        # Fetch the ContractSteps object
        contract_steps = get_object_or_404(ContractSteps, id=pk, user=request.user)

        # Check if a ContractProject already exists for this ContractSteps
        if hasattr(contract_steps, 'contract_project'):  # Check if the related project exists
            return Response(
                {
                    "message": "ContractProject already exists.",
                    "contract_project_id": contract_steps.contract_project.id,
                },
                status=status.HTTP_200_OK,
            )

        # Create a new ContractProject from ContractSteps
        contract_project = ContractProject.objects.create(
            name=contract_steps.title,  # Use the title as the name
            description=(
                f"<h1>{contract_steps.title}</h1>"
                f"<p><strong>Effective Date:</strong> {contract_steps.effective_date or ''}</p>"
                f"<p><strong>Party One:</strong> {contract_steps.party_one_name or ''} "
                f"({contract_steps.party_one_role or ''})</p>"
                f"<p><strong>Party Two:</strong> {contract_steps.party_two_name or ''} "
                f"<p>({contract_steps.party_two_role or ''})</p>"
                f"<p>{contract_steps.purpose or ''}</p>"
                f"<p>{contract_steps.obligations or ''}</p>"
                f"<p>{contract_steps.payment_terms or ''}</p>"
                f"<p>{contract_steps.duration or ''}</p>"
                f"<p>{contract_steps.termination_clause or ''}</p>"
                f"<p>{contract_steps.confidentiality_clause or ''}</p>"
                f"<p>{contract_steps.dispute_resolution or ''}</p>"
                f"<p>{contract_steps.penalties_for_breach or ''}</p>"
                f"<p>{contract_steps.notarization or ''}</p>"
            ),
            owner=request.user,  # Associate with the current user
            contract_steps=contract_steps  # Link to the ContractSteps
        )

        return Response(
            {
                "message": "Contract successfully transferred to a project.",
                "contract_project_id": contract_project.id,
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#########################################################################################################################

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_chat_session(request, session_id):
    try:
        # Get the chat session by its ID and make sure it belongs to the current user
        chat_session = ChatSession.objects.get(id=session_id, owner=request.user)

        # Get the incoming data from the request
        data = request.data.copy()

        # Log the incoming data to check if it is being received correctly
        print('Incoming data:', data)

        # Update the chat session using a serializer
        serializer = ChatSessionSerializer(instance=chat_session, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            print('Chat session updated successfully')  # Add this log to confirm successful save
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            print('Serializer errors:', serializer.errors)  # Log errors to help debug
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except ChatSession.DoesNotExist:
        return Response({"error": "Chat session not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error occurred: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_chat_session(request, session_id):
    try:
        # Get the chat session by its ID and make sure it belongs to the current user
        chat_session = ChatSession.objects.get(id=session_id, owner=request.user)

        # Delete the chat session
        chat_session.delete()

        # Return a success response
        return Response({"message": "Chat session deleted successfully."}, status=status.HTTP_200_OK)

    except ChatSession.DoesNotExist:
        return Response({"error": "Chat session not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error occurred: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def search_api(request):
    if request.method == 'GET':
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        query = request.query_params.get('query', '')
        # Filter using the correct field names, assuming `owner` is the foreign key to the User model
        chat_sessions_query = ChatSession.objects.filter(owner=user, name__icontains=query)
        contract_projects_query = ContractProject.objects.filter(owner=user, name__icontains=query)

        # Pagination setup
        paginator = pagination.PageNumberPagination()
        paginator.page_size = 10  # Customize the page size as needed

        # Paginate ChatSession results
        paginated_chat_sessions = paginator.paginate_queryset(chat_sessions_query, request)
        chat_serializer = ChatSessionSerializer(paginated_chat_sessions, many=True, context={'request': request})

        # Paginate ContractProject results
        paginated_contract_projects = paginator.paginate_queryset(contract_projects_query, request)
        contract_serializer = ContractProjectSerializer(paginated_contract_projects, many=True, context={'request': request})

        # Combine results
        result = {
            'chat_sessions': chat_serializer.data,
            'contract_projects': contract_serializer.data,
            'pagination': {
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'count': paginator.page.paginator.count,
                'total_pages': paginator.page.paginator.num_pages,
            }
        }
        return Response(result)
    else:
        return Response({"error": "GET request required"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def contract_steps(request):
    try:
        if request.method == 'POST':
            data = request.data.copy()  # Make a copy of the request data
            if 'notary_required' not in data:
                data['notary_required'] = 'false'  
            serializer = ContractStepsSerializer(data=request.data)
            if serializer.is_valid():
                # Automatically assign the user
                serializer.save(user=request.user)
                return Response({"id": serializer.instance.id, "message": "Contract created successfully"}, status=201)
            else:
                return Response(serializer.errors, status=400)

        
        elif request.method == 'PUT':
            # Update an existing contract step
            contract_id = request.data.get("id")  # Ensure the primary key is provided
            try:
                contract = ContractSteps.objects.get(id=contract_id, user=request.user)
            except ContractSteps.DoesNotExist:
                return Response({"error": "Contract not found"}, status=404)
            
            data = request.data.copy()
            if 'notary_required' not in data:
                data['notary_required'] = 'false'  
            
            serializer = ContractStepsSerializer(contract, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Contract updated successfully"}, status=200)
            else:
                return Response(serializer.errors, status=400)
    except Exception as e:
        print(f"Unexpected error: {e}")  # Debugging
        return Response({"error": "An unexpected error occurred."}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contract_steps_project(request):
    contracts = ContractSteps.objects.filter(user=request.user).order_by('-created_at')
    serializer = ContractStepsSerializer(contracts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def contract_steps_project_detail(request, pk):
    contracts = ContractSteps.objects.get(id=pk)
    serializer = ContractStepsSerializer(contracts, many=False)
    return Response(serializer.data)

@api_view(['PUT'])
def contract_steps_project_update(request, pk):
    try:
        contract = ContractSteps.objects.get(id=pk)
    except ContractSteps.DoesNotExist:
        return JsonResponse({'error': 'Contract not found'}, status=404)

    # Make a copy of the request data
    data = request.data.copy()

    # Fields that should be allowed to be saved as empty
    text_fields = [
        'purpose',
        'obligations',
        'payment_terms',
        'termination_clause',
        'confidentiality_clause',
        'dispute_resolution',
        'penalties_for_breach',
        'notarization'
    ]

    # Set empty strings for empty fields instead of ignoring them
    for field in text_fields:
        if field in data and data[field] == '':
            data[field] = ''  # Explicitly set the field to an empty string

    serializer = ContractStepsSerializer(instance=contract, data=data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return JsonResponse(serializer.data, status=200)
    else:
        return JsonResponse(serializer.errors, status=400)


@api_view(['DELETE'])
def contract_steps_project_delete(request, pk):
    contract = ContractSteps.objects.get(id=pk)
    contract.delete()
    return Response('Contract project deleted successfully :)')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_suggestions(request):
    try:
        user_input = request.data.get("input", "").strip()
        if not user_input:
            return Response({"error": "Input is required"}, status=400)

        print(f"Received input: {user_input}")

        # Create a prompt to generate three suggestions
        prompt = (
            f"You are an AI assistant that generates professional contract names based on user input. "
            f"Suggest three professional or legal contract names for the input: '{user_input}'. "
            f"If the input doesn't fit a legal name, make them sound more professional. (Don't format it in a list like adding numbers or dashes)"
        )

        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You suggest three professional or legal contract names."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.7,
            n=1
        )

        suggestions_text = response.choices[0].message.content.strip()
        suggestions = suggestions_text.split("\n")

        # Ensure we have exactly three suggestions
        suggestions = [s.strip() for s in suggestions if s.strip()][:3]

        return Response({"suggestions": suggestions}, status=200)

    except Exception as e:
        print(f"Error: {e}")
        return Response({"error": "Failed to generate suggestions."}, status=500)


FIELD_PROMPTS = {
    "purpose": (
        "You are refining the 'Purpose' section of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to make it clearer, more professional, and legally compliant. "
        "Focus only on the 'Purpose' section. Do not add information about other contract sections."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "obligations": (
        "You are refining the 'Obligations and Responsibilities' section of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to clearly define the responsibilities and obligations of the parties. "
        "Do not include unrelated sections such as payment terms or confidentiality clauses."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "payment_terms": (
        "You are refining the 'Payment Terms' section of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to clarify the payment terms, ensuring they are legally sound and easy to understand. "
        "Do not reference other sections such as obligations or penalties."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "duration": (
        "You are refining the 'Duration' section of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to clearly specify the duration of the contract, ensuring the timeframe is unambiguous. "
        "Avoid referencing unrelated sections like termination clauses."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "termination_clause": (
        "You are refining the 'Termination Clause' of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to clearly define the conditions under which the contract can be terminated. "
        "Ensure the language is professional and legally compliant. Do not reference other sections."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "confidentiality_clause": (
        "You are refining the 'Confidentiality Clause' of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to clearly define the confidentiality obligations of the parties. "
        "Ensure the clause is legally sound and avoids referencing unrelated sections."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "dispute_resolution": (
        "You are refining the 'Dispute Resolution' section of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to clarify how disputes will be resolved, ensuring the methods are fair and legally compliant. "
        "Avoid referencing unrelated sections such as penalties or obligations."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "penalties_for_breach": (
        "You are refining the 'Penalties for Breach' section of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to clearly define the penalties for breaching the agreement. "
        "Ensure the penalties are enforceable and do not include details about other contract sections."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
    "notary_required": (
        "You are refining the 'Notary Required' section of a contract. "
        "The user's input is:\n\n'{user_input}'\n\n"
        "Rewrite this section to specify if a notary is required and under what conditions. "
        "Avoid referencing other sections or adding unrelated details."
        "Use Markdown for headers, bullet points, and numbered lists to enhance readability if needed."
    ),
}

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_ai_text(request):
    try:
        # Retrieve the user input and title
        user_input = request.data.get("input", "").strip()
        title = request.data.get("title", "").strip()  # Get the title from the request
        field = request.data.get("field", "").strip()

        if not user_input or not title or not field:
            return Response({"error": "Input text, title, and field are required."}, status=400)

        print(f"Received input for field '{field}': {user_input}")
        print(f"Received title: {title}")

        # Fetch the field-specific prompt
        field_prompt_template = FIELD_PROMPTS.get(field)
        if not field_prompt_template:
            return Response({"error": f"Field '{field}' is not supported."}, status=400)

        # Create the prompt by formatting the field-specific template
        prompt = field_prompt_template.format(user_input=user_input)

        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You assist in drafting structured legal documents following Mexican law."},
                {"role": "user", "content": f"Contract Title: {title}\n\n{prompt}"}
            ],
            max_tokens=500,
            temperature=0.7,
            n=1
        )

        generated_text = response.choices[0].message.content.strip()

        return Response({"generated_text": generated_text}, status=200)

    except Exception as e:
        print(f"Error generating AI text: {e}")
        return Response({"error": "Failed to generate AI text."}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contract_check_basis(request, pk):
    """
    API endpoint to fetch contract details directly using the serializer.
    """
    # Fetch the contract object or return a 404
    contract = get_object_or_404(ContractSteps, id=pk, user=request.user)
    
    # Serialize the contract
    serializer = ContractStepsSerializer(contract)
    
    # Return the serialized data
    return Response(serializer.data, status=200)

def legality_check_ai(contract_id):
    """
    Perform AI legality check on the specified contract and save the results.
    """
    # Fetch the contract
    contract = get_object_or_404(ContractSteps, id=contract_id)

    # Prepare contract text for AI
    contract_text = f"""
        Title: {contract.title}
        Party One: {contract.party_one_name} ({contract.party_one_role})
        Party Two: {contract.party_two_name} ({contract.party_two_role})
        Effective Date: {contract.effective_date}
        Purpose: {contract.purpose}
        Obligations: {contract.obligations}
        Payment Terms: {contract.payment_terms}
        Duration: {contract.duration}
        Termination Clause: {contract.termination_clause}
        Confidentiality Clause: {contract.confidentiality_clause}
        Dispute Resolution: {contract.dispute_resolution}
        Penalties for Breach: {contract.penalties_for_breach}
        Notary Required: {contract.notary_required}
    """

    # AI prompt
    prompt = f"""
        Analyze the following contract for legality according to Mexican law.
        Identify any inconsistencies, missing elements, and suggest improvements.
        Make your Responds short, concise & clear.

        Contract:
        {contract_text}
    """

    try:
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # Use the appropriate model
            messages=[
                {"role": "system", "content": "You are a legal expert specializing in Mexican law."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.2,
        )

        # Extract AI response
        ai_response = response.choices[0].message.content.strip()

        # Determine if issues are present
        passed = "no issues" in ai_response.lower()

        # Save result to ValidationResult model
        validation_result = ValidationResult.objects.create(
            contract=contract,
            check_type="Legal Check",
            passed=passed,
            issues=ai_response if not passed else None  # Store issues if validation fails
        )

        contract.check_completed = True
        contract.save()

        return validation_result

    except Exception as e:
        # Handle errors and save as a failed validation result
        validation_result = ValidationResult.objects.create(
            contract=contract,
            check_type="Legal Check",
            passed=False,
            issues=f"Error during legality check: {str(e)}"
        )
        return validation_result

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def legality_check_view(request, pk):
    """
    API endpoint to perform a legality check on a contract.
    """
    if request.method == 'GET':
        return Response({"message": "Use POST to perform the legality check."}, status=400)

    try:
        validation_result = legality_check_ai(pk)
        serializer = ValidationResultSerializer(validation_result)
        return Response(serializer.data, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def feed_back(request):
    serializer = FeedbackSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user if request.user.is_authenticated else None)
        return Response(serializer.data, status=201)
    else:
        print(serializer.errors)
        return Response(serializer.errors, status=400)

