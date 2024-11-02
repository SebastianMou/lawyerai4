from django.shortcuts import render
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
                {"role": "system", "content": "Summarize the following conversation."},
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
        conversation_history = [{"role": "system", "content": "You are an AI assistant. Please respond in Markdown format."}]
        if summary_text:
            conversation_history.append({"role": "assistant", "content": f"Summary of previous conversation: {summary_text}"})
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
        prompt_for_name = f"Generate a concise and meaningful chat session name based on the following question: '{user_input}'"
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
                {"role": "system", "content": "Summarize the following conversation."},
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
        messages = [{"role": "system", "content": "You are a helpful assistant and your name is creator."}]
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
        messages = [{"role": "system", "content": "You are a therapist that helps coupled with problems in their relationship an you name is chatsessionor"}]
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
