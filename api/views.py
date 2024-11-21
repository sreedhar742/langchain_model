import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .models import UploadedFile
from .serializers import UploadedFileSerializer
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from api_rag.settings import API_KEY
from langchain_groq import ChatGroq
from rest_framework.decorators import api_view
groq_api_key = API_KEY
llm = ChatGroq(groq_api_key=groq_api_key, model_name="mixtral-8x7b-32768")

FAISS_INDEX_DIR = "faiss_indexes/"

@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/upload',
        '/query/<int:file_number>/',
        '/files'
    ]
    return Response(routes)
 
class FileUploadAPIView(APIView):
    def get(self,request):
        return Response({"message":"Get Request Not allowed"},status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    serializer_class=UploadedFileSerializer
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = UploadedFile(file=file)
        uploaded_file.save()
        
        file_path = uploaded_file.file.path

        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            final_documents = text_splitter.split_documents(docs)

            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vectors = FAISS.from_documents(final_documents, embeddings)

            faiss_path = os.path.join(FAISS_INDEX_DIR, f"{uploaded_file.id}_index")
            os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
            vectors.save_local(faiss_path)

            uploaded_file.embedding_path = faiss_path
            uploaded_file.embedding_created = True
            uploaded_file.save()
            return Response({"message": f"File uploaded {uploaded_file.id} and processed successfully.","File processed":f"{uploaded_file.embedding_created}","uploaded_time":{uploaded_file.created_at}}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
      
from rest_framework.authentication import SessionAuthentication,BasicAuthentication
class Csrfexemptsessionauthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return 
    
# class QueryAPIView(APIView):
#     # @method_decorator(csrf_exempt, name='dispatch')
#     authentication_classes=(Csrfexemptsessionauthentication,BasicAuthentication)
#     def post(self, request, file_id):
#         question = request.data.get('question')
        
#         if not question:
#             return Response({"error": "No question provided."}, status=status.HTTP_400_BAD_REQUEST)
#         try:
#             file_instance = UploadedFile.objects.get(id=file_id, embedding_created=True)
#             embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
#             vectors = FAISS.load_local(file_instance.embedding_path, embeddings,allow_dangerous_deserialization=True)
#             retriever = vectors.as_retriever()
#             prompt_template = ChatPromptTemplate.from_template(
#                 """
#                 Answer the question based on the provided context only.
#                 Please provide the most accurate response based on the question.
#                 <context>
#                 {context}
#                 <context>
#                 Question: {input}
#                 """
#             )

#             # Set up document chain and retrieval chain
#             document_chain = create_stuff_documents_chain(llm, prompt_template)
#             retrieval_chain = create_retrieval_chain(retriever, document_chain)            
#             # response = retriever.retrieve({"input": question})
#             response = retrieval_chain.invoke({"input": question})
#             # Return the response
            
#             return Response({"question": question, "answer": response['answer']}, status=status.HTTP_200_OK)

#         except UploadedFile.DoesNotExist:
#             return Response(
#                 {"error": "File not found or embeddings not created."},
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:
#             return Response(
#                 {"error": "An error occurred during processing.", "details": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

class QueryAPIView(APIView):
    authentication_classes = (Csrfexemptsessionauthentication, BasicAuthentication)
    def get(self,request):
        return Response({"message":"Get Request is not allowed"},status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    
    def post(self, request):
        question = request.data.get('question')
        if not question:
            return Response({"error": "No question provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the most recent file with embeddings created
            file_instance = UploadedFile.objects.filter(embedding_created=True).latest('id')
            
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            vectors = FAISS.load_local(file_instance.embedding_path, embeddings, allow_dangerous_deserialization=True)
            retriever = vectors.as_retriever()
            prompt_template = ChatPromptTemplate.from_template(
                """
                Answer the question based on the provided context only.
                Please provide the most accurate response based on the question.
                <context>
                {context}
                <context>
                Question: {input}
                """
            )

            # Set up document chain and retrieval chain
            document_chain = create_stuff_documents_chain(llm, prompt_template)
            retrieval_chain = create_retrieval_chain(retriever, document_chain)
            response = retrieval_chain.invoke({"input": question})
            
            return Response({"question": question, "answer": response['answer']}, status=status.HTTP_200_OK)

        except UploadedFile.DoesNotExist:
            return Response(
                {"error": "No processed files found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": "An error occurred during processing.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileListAPIView(APIView):
    def get(self, request):
        files = UploadedFile.objects.all()
        serializer = UploadedFileSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




