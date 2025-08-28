How to install and run the Chanakya Dost Backend:

Step 1: Create a Virtual Environment(Sandbox). 
Step 2: Install all the dependencies mentioned in the requirements.txt file in that environment.
Step 3: Run the fastAPI Server present under app using: FastAPI_App:app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)), reload=True . Can also be directly run using the command under the parent directory: python FastAPI_App:app host="0.0.0.0", port=int(os.getenv("PORT", 10000)), reload=True
Step 4: The main.py is the main orchaestrator that performs the operations of calling the other modules stepwise.
Step 5: The FastAPI has an end-point of /process-query , under which the queries are processed accordingly:
        1. If Voice+Image input, then it calls the OCR function for the image within the fastAPI module and the whisper function for transcription.
        2. If Voice only, then it only calls the whisper function and then performs the OCR and then receives the text for the transcribed audio.
        3. If Image only, then only image module called and the OCR text is received.
        4. If Image + text then as well only image module is first called.
        5. If only text is there then no processing module is called.

Step 6: After the processing of the query in pure text is available the query_checker.py Module is called which receives only text input(for Image > OCR, for Audio > Transcribed Audio, null for plain text).

Step 7: The Query Checker makes and API call to OpenAI to decide if it is a general query or a Dost Type request and then routes the query as per the context text received and returns a json schema with enhanced query if the user has requested a specific type of Dost.If the user had made a request in any other language then it also translates that to English for the rag engine to work accurately.

Step 8: If the response sent by query checker is general and not dost type, then the FastAPI directly sends the content received from the API call back to the client.

Step 9: If it is a dost type, request, it calls the retriever.py module which is a RAG based system which retrieves the top 51 chunks from our topology, acadza_concept_tree.py where each chunk is in the form of: Subject > Chapter > Concept > SubConcept , the rag_engine.py , are supportive modules used inside this process. The files such as embedding_vectors.npy,faiss_index.idx are used for the semantic search to retrieve the most relevant chunk for the given text(received from query_checker.py).

Step 10: Then the rag_gpt_prompt.py is called with param_config.py(list of all dosts + their default values)which receives the enhanced user text + the top 51 chunks, and then generates a json schema based on the user request.

Step 11: The received json schema contains, the name of the dost and the portion and the script for the student as to why was that particular dost recommended.

Step 12: Upon the received schema, the builders.py is run which enriches the portion and adds SubConcept level protions to the payload, using the acadza_concept_tree.py module.

Step 13: The final payload for each dost type is created with the portion for respective dosts and then each dost type is called accordingly one after the other and the links recieved from the API calls are saved.

Step 14: The final Script(if general/dost type request or both) is send to the client along with the links in a strict json schema format which the frontend processes and renders.


