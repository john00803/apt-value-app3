from google.cloud import vision
import io

# Google Vision API로 OCR 처리
def extract_text_from_image(image_file):
    client = vision.ImageAnnotatorClient()

    content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        return texts[0].description
    else:
        return ""
