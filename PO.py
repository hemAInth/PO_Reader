import streamlit as st
import os
import tempfile
from PIL import Image
from dotenv import load_dotenv
import fitz  # PyMuPDF for PDF processing
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")


if api_key is None:
    st.error("Google API Key is not set. Check your .env file.")
else:
    genai.configure(api_key=api_key)

# Function to get response from Gemini Flash 1.5
def get_gemini_response(input_text, image_parts, prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([input_text, image_parts[0], prompt])
        return response.text
    except Exception as e:
        st.error(f"Error with Gemini model: {e}")
        return None

# Helper function to process uploaded image for Gemini API
def input_image_setup(uploaded_file):
    try:
        if uploaded_file is not None:
            # Read the image file into bytes
            bytes_data = uploaded_file.getvalue()
            image_parts = [
                {
                    "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
                    "data": bytes_data
                }
            ]
            return image_parts
        else:
            st.warning("No file uploaded.")
            return None
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return None

# Helper function to process uploaded PDF for Gemini API
def process_pdf(uploaded_file):
    try:
        pdf_text = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.read())
            pdf_document = fitz.open(temp_pdf.name)
            for page_num in range(pdf_document.page_count):
                pdf_text += pdf_document[page_num].get_text("text")
            pdf_document.close()
        return pdf_text
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

# Initialize Streamlit app
st.set_page_config(page_title="PO Automation System - CSR Validation", layout="wide")
st.title("Purchase Order Automation System")

# Layout with two columns: file display on the left, input and output on the right
col1, col2 = st.columns([1, 2], gap="medium")  # Adjust column widths for better spacing

# Step 1: Upload PO Image or PDF
with col1:
    uploaded_file = st.file_uploader("Upload a Purchase Order (JPG, JPEG, PNG, or PDF)", type=["jpg", "jpeg", "png", "pdf"])
    image_data = None
    pdf_text = None

    if uploaded_file:
        file_type = uploaded_file.type
        if file_type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded PO Image", use_column_width=True)
            image_data = input_image_setup(uploaded_file)
        elif file_type == "application/pdf":
            pdf_text = process_pdf(uploaded_file)
            if pdf_text:
                st.subheader("Uploaded PDF Content Preview")
                st.text_area("PDF Content", pdf_text[:1500] + "...", height=400)  # Limiting preview text for display
            # Convert PDF text to image format for Gemini
            image_data = [{"mime_type": "text/plain", "data": pdf_text.encode()}]

# Step 2: Input Query on the right column
with col2:
    st.subheader("Question and Response")
    query = st.text_input("Enter your question about the Purchase Order:")

    # Step 3: Process and Retrieve Answer using Gemini
    submit = st.button("Submit Query")

    input_prompt = """
                   You are an expert in understanding purchase orders. 
                   You will receive input images as POs or PDF content as text,
                   and you will answer questions based on the input document. 
                   """

    if submit:
        if image_data and query:
            response = get_gemini_response(query, image_data, input_prompt)
            
            # Display the model's response
            if response:
                st.subheader("System Response")
                st.write(response)
            else:
                st.warning("No response received. Check model setup or query.")
        else:
            st.warning("Please upload an image or PDF and enter a query.")

        # Step 4: CSR Validation
        st.subheader("Validate the Response")
        validation = st.radio("Is this response correct?", ("Yes", "No"))

        # Step 5: Collect Feedback for Model Tuning
        feedback = st.text_area("Additional feedback (if any):")

        if st.button("Submit Feedback"):
            # Log feedback for model tuning
            feedback_log = {
                "query": query,
                "response": response,
                "validation": validation,
                "feedback": feedback
            }

            # Append feedback to a log file for further use
            with open("feedback_log.txt", "a") as log_file:
                log_file.write(str(feedback_log) + "\n")
            
            st.success("Feedback submitted. Thank you for helping improve the system!")
