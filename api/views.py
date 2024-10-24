from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

import json
import openai
import random
from rest_framework.views import APIView

from .models import ContractProject, AIHighlightChat, ChatSession, Message
from .serializer import ContractProjectSerializer, AIHighlightChatSerializer, MessageSerializer, ChatSessionSerializer

openai.api_key = settings.OPENAI_API_KEY

# Create your views here.
@api_view(['GET'])
def apiOverview(request):
    api_urls = {
        ## Contract projects
        'Contract Projects': '/contract-project/',
        'Contract Project Detail View': '/contract-detail/<int:pk>/',
        'Contract Project Create': '/contract-create/',
        'Contract Project Update': '/contract-update/<int:pk>/',
        'Contract Project Delete': '/contract-delete/<int:pk>/',

        ## AI Chat for Contracts
        'Create AI Chat for Contract': '/create-ai-chat-contract/<int:contract_project_id>/',
        'Chat history for Contract': '/get-chat-history-contract/<int:contract_project_id>/',

        ## Chat with AI (ChatSessionLawyer)
        'Start Chat Session': '/start-chat-session/',
        'Send Message to AI': '/send-message/<int:session_id>/',
        'Get Chat History': '/chat-history/<int:session_id>/',
    }
    return Response(api_urls)

@api_view(['GET'])
def contract_project(request):
    contracts = ContractProject.objects.filter(owner=request.user)
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
        print('Data saved successfully')  # Add this log to confirm successful save
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
        print(f"Request data: {request.data}")
        print(f"Contract Project ID: {contract_project_id}")
        
        # Get the contract project the AI chat is associated with
        contract_project = ContractProject.objects.get(id=contract_project_id)

        # Get the user, highlighted text, and instruction from the request data
        user = request.user
        highlighted_text = request.data.get('highlighted_text', '').strip()  # Default to empty string if None
        instruction = request.data.get('instruction')

        # Modify the prompt based on whether text was highlighted or not
        if highlighted_text:
            prompt = f"Highlight: {highlighted_text}\nInstruction: {instruction}\n"
        else:
            prompt = f"Instruction: {instruction}\n"

        # OpenAI's chat-based API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if available in your plan
            messages=[
                {"role": "system", "content": "You are an AI assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extract the AI's response from the 'choices' array
        ai_response = response.choices[0].message.content.strip()

        # Save AI chat in the database
        ai_chat = AIHighlightChat.objects.create(
            user=user,
            contract_project=contract_project,
            highlighted_text=highlighted_text,
            instruction=instruction,
            ai_response=ai_response
        )

        return JsonResponse({'ai_response': ai_response}, status=201)

    except ContractProject.DoesNotExist:
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

##################################################################################################################


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    try:
        # Get the user's input message
        user_input = request.data.get('message', '')

        if not user_input:
            return Response({"error": "Message content is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate the session name via OpenAI API
        prompt_for_name = f"Generate a concise and meaningful chat session name based on the following question: '{user_input}'"
        
        # OpenAI's chat-based API call to generate session name
        session_name_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # You can use "gpt-4" if available
            messages=[
                {"role": "system", "content": "You are an AI assistant that generates session names based on user input."},
                {"role": "user", "content": prompt_for_name}
            ],
            max_tokens=10,  # Control the length of the response (you can adjust this)
            temperature=0.7  # Adjust creativity level
        )

        # Extract the AI's generated session name
        session_name = session_name_response.choices[0].message.content.strip()

        # Create the chat session with the generated name
        chat_session = ChatSession.objects.create(
            name=session_name,
            owner=request.user
        )

        # Create the first message (the user's input)
        user_message = Message.objects.create(
            chat_session=chat_session,
            content=user_input,
            sender='user'
        )

        # Generate the AI's answer to the user's question
        prompt_for_answer = f"{user_input}"  # Directly use user's question as the prompt for the AI to answer

        ai_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # You can use "gpt-4" if available
            messages=[
                {"role": "system", "content": "You are an AI assistant that helps answer questions."},
                {"role": "user", "content": prompt_for_answer}
            ],
            max_tokens=500,  # Set a reasonable max token limit for the answer
            temperature=0.7  # Adjust creativity level
        )

        # Extract the AI's answer from the 'choices' array
        ai_answer = ai_response.choices[0].message.content.strip()

        # Save the AI's response as a new message in the chat session
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

        # Create a new message from the user in the existing chat session
        user_message = Message.objects.create(
            chat_session=chat_session,
            content=user_input,
            sender='user'
        )
        
        # Generate the AI's response to the new question
        prompt_for_answer = f"{user_input}"  # Use the user's new message as the prompt for the AI
        
        ai_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # You can use "gpt-4" if available
            messages=[
                {"role": "system", "content": "You are an AI assistant that helps answer questions."},
                {"role": "user", "content": prompt_for_answer}
            ],
            max_tokens=500,  # Set a reasonable max token limit for the answer
            temperature=0.7  # Adjust creativity level
        )
        
        # Extract the AI's response from the 'choices' array
        ai_answer = ai_response.choices[0].message.content.strip()

        # Save the AI's response as a new message in the same chat session
        Message.objects.create(
            chat_session=chat_session,
            content=ai_answer,
            sender='AI'
        )

        # Return the full chat session with all messages
        session_serializer = ChatSessionSerializer(chat_session)
        return Response(session_serializer.data, status=status.HTTP_201_CREATED)

    except ChatSession.DoesNotExist:
        return Response({"error": "Chat session not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error occurred: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_chat_sessions(request):
    # Filter chat sessions by the currently authenticated user
    chat_sessions = ChatSession.objects.filter(owner=request.user)

    # Serialize the chat sessions
    serializer = ChatSessionSerializer(chat_sessions, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)