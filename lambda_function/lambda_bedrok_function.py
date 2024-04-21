"""
Author: Noureddine ECH-CHOUKY
Description: Generates a movie poster design using the Bedrock API and stores the image in an S3 bucket. Returns a pre-signed URL of the image.
Date: 2024-04-21
"""

import json
import boto3
import base64
import datetime
import os
import logging
import mimetypes

# Setup logging
logging.basicConfig(level=logging.INFO)

# Constants
BEDROCK_API_CONTENT_TYPE = "application/json"
MODEL_ID = os.environ.get("MODEL_ID", "stability.stable-diffusion-xl-v0")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "movieposterdesign3467")

# Create clients
client_bedrock = boto3.client("bedrock-runtime")
client_s3 = boto3.client("s3")


def invoke_bedrock_model(prompt):
    """
    Invokes the Bedrock model with the given prompt and returns the image content as a byte array.

    :param prompt: The prompt to generate the movie poster design.

    :return: The image content as a byte array.
    """
    try:
        response = client_bedrock.invoke_model(
            contentType=BEDROCK_API_CONTENT_TYPE,
            accept=BEDROCK_API_CONTENT_TYPE,
            modelId=MODEL_ID,
            body=json.dumps(
                {
                    "text_prompts": [{"text": prompt}],
                    "cfg_scale": 10,
                    "steps": 30,
                    "seed": 0,
                }
            ),
        )
        response_byte = json.loads(response["body"].read())
        image_data = base64.b64decode(response_byte["artifacts"][0]["base64"])
        return image_data
    except Exception as e:
        logging.error(f"Error invoking Bedrock model: {e}")
        raise

def upload_image_to_s3(image_data, file_extension='png'):
    """
    Uploads image data to S3 and returns the generated pre-signed URL.

    :param image_data: The image data to upload to S3.
    :param file_extension: The file extension for the image.

    :return: The pre-signed URL of the uploaded image.
    """
    try:
        # Assume the image data is in the correct format (e.g., PNG)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        poster_name = f"poster_{current_time}.{file_extension}"

        content_type = f'image/{file_extension}'

        client_s3.put_object(
            Bucket=BUCKET_NAME,
            Body=image_data,
            Key=poster_name,
            ContentType=content_type  # Specify the content type
        )

        url = client_s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": poster_name},
            ExpiresIn=3600,
        )

        return url
    except Exception as e:
        logging.error(f"Error uploading image to S3: {e}")
        raise



def lambda_ai(event, context):
    """
    Handles incoming Lambda events by generating a movie poster and returning its URL.

    :param event: The incoming event data.
    :param context: The Lambda context.

    :return: The response data containing the pre-signed URL of the generated movie poster.
    """
    prompt = event["prompt"]
    logging.info(f"Received prompt: {prompt}")
    image_data = invoke_bedrock_model(prompt)

    # Here you would specify 'png' or 'jpeg' based on the format Bedrock returns
    pre_signed_url = upload_image_to_s3(image_data, file_extension='png')

    return {
        "statusCode": 200,
        "body": json.dumps({"url": pre_signed_url})
    }
