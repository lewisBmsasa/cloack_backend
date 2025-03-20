import requests
from faker import Faker
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import pytesseract
import io
import base64

fake = Faker()










def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def anonymize_pdf_results(filepath, output_path):
    images = convert_from_path(filepath)
    # Step 2: Redact each image and collect results
    redacted_images = []
    all_redacted_pii = []
    for i, image in enumerate(images):
        print(f"\nProcessing page {i+1}:")
        redacted_image, redacted_pii = redact_image(image)
        redacted_images.append(redacted_image)
        all_redacted_pii.extend(redacted_pii)

    # Step 3: Save redacted images as a new PDF
    
    redacted_images[0].save(
        output_path,
        save_all=True,
        append_images=redacted_images[1:] if len(redacted_images) > 1 else [],
        format="PDF"
    )

    print(f"\nRedacted PDF saved to '{output_path}'")
    print("Summary of all redacted PII:")
    for pii in all_redacted_pii:
        print(f"- {pii['entity_type']}: '{pii['text']}'")

    return output_path
def redact_image(image):
    redactor_url = "http://localhost:5003/redact"
    # Convert PIL Image to bytes (PNG format)
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()

    # Prepare API request
    files = {"image": ("image.png", img_byte_arr, "image/png")}
    payload = {
        "analyze_args": {"language": "en"},
        "analyze_image": True ,  # Ensure PII detection is enabled
        "return_analyzer_results": True,
        "return_analyzed_text": True  # Include detected text and entities
    }

    # Call the redactor API
    response = requests.post(redactor_url, files=files, data=payload)
    print("ressssspooonseee", response)
    if response.status_code != 200:
        print(f"Redactor error: {response.text}")
        return image, []
    
    redacted_image = Image.open(io.BytesIO(response.content))

    # Parse response
    # result = response.json()
    # redacted_image_base64 = result["redacted_image"]
    # analyzed_results = result.get("analyzed_results", [])

    # Decode redacted image from base64
    # redacted_image_bytes = base64.b64decode(redacted_image_base64)
    # redacted_image = Image.open(io.BytesIO(redacted_image_bytes))

    # Extract and display redacted PII
    redacted_pii = []
    # if analyzed_results:
    #     original_text = result.get("text", "")
    #     for res in analyzed_results:
    #         entity_type = res["entity_type"]
    #         start = res["start"]
    #         end = res["end"]
    #         redacted_text = original_text[start:end]
    #         redacted_pii.append({"entity_type": entity_type, "text": redacted_text})
    #         print(f"Redacted: {entity_type} - '{redacted_text}'")

    return redacted_image, redacted_pii



def anonymize_pdf(filepath, output_path):
    redactor_url = "http://localhost:5003/redact"

    # Convert PDF to images
    images = convert_from_path(filepath)

    redacted_images = []
    for i, image in enumerate(images):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_bytes = img_byte_arr.getvalue()
        files = {"image": ("image.png", img_bytes, "image/png")}
        payload = {
            #"fill_color": "black",  # Optional: Customize redaction color
            "analyze_image": True ,  # Ensure PII detection is enabled
            "return_analyzer_results": True,
        }
        response = requests.post(redactor_url, files=files, data=payload)
        print("response_pdf", response)
        if response.status_code != 200:
            print(f"Redactor error on page {i+1}: {response.text}")
            continue
        redacted_image = Image.open(io.BytesIO(response.content))
        redacted_images.append(redacted_image)
        print(f"Redacted page {i+1}")


    if redacted_images:
        redacted_images[0].save(
            output_path,
            save_all=True,
            append_images=redacted_images[1:] if len(redacted_images) > 1 else [],
            format="PDF"
        )
        print(f"Redacted PDF saved to '{output_path}'")
    else:
        print("No images were redacted.")
    return output_path

def anonymize_text_post(text, language="en", use_fake=True):
    analyzer_url = "http://localhost:5002/analyze"
    analyzer_payload = {"text": text, "language": language}
    print("analyzer input: ", analyzer_payload)
    analyzer_response = requests.post(analyzer_url, json=analyzer_payload)
    results = analyzer_response.json()
    print("analyze", results)
    anonymizer_url = "http://localhost:5001/anonymize"

    operators = {}
    if use_fake:
        for result in results:
            entity_type = result["entity_type"]
            if entity_type == "PERSON":
                operators[entity_type] = {"type": "replace", "new_value": fake.name().split(" ")[0]}
            elif entity_type == "EMAIL_ADDRESS":
                operators[entity_type] = {"type": "replace", "new_value": fake.email()}
            elif entity_type == "PHONE_NUMBER":
                operators[entity_type] = {"type": "replace", "new_value": fake.phone_number()}

    anonymizer_payload = {"text": text, "analyzer_results": results, "anonymizers": operators}
    print("anony_input: ", anonymizer_payload)
    anonymizer_response = requests.post(anonymizer_url, json=anonymizer_payload)
    print(anonymizer_response.json())
    
    return anonymizer_response