import requests
from faker import Faker
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import pytesseract
import io

fake = Faker()











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
            "analyze_image": True   # Ensure PII detection is enabled
        }
        response = requests.post(redactor_url, files=files, data=payload)

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