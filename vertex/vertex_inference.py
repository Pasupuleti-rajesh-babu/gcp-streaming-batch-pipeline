from google.cloud import aiplatform
from google.cloud import pubsub_v1
import json
import base64
import functions_framework
import datetime

# Initialize Vertex AI
aiplatform.init(project='YOUR_PROJECT_ID', location='us-central1')

# Initialize Pub/Sub publisher
publisher = pubsub_v1.PublisherClient()

def get_prediction(event):
    """Get prediction from Vertex AI endpoint."""
    try:
        # Initialize the endpoint
        endpoint = aiplatform.Endpoint(
            endpoint_name="projects/YOUR_PROJECT_ID/locations/us-central1/endpoints/YOUR_ENDPOINT_ID"
        )

        # Prepare features for prediction
        features = {
            'event_type': event['event_type'],
            'device_id': event['device_id'],
            'user_id': event.get('user_id', ''),
            'properties': event.get('properties', {})
        }

        # Get prediction
        prediction = endpoint.predict([features])
        return prediction.predictions[0]

    except Exception as e:
        print(f"Error getting prediction: {str(e)}")
        return None

@functions_framework.cloud_event
def process_event(cloud_event):
    """Cloud Function to process events and get predictions."""
    try:
        # Get the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        event = json.loads(pubsub_message)

        # Get prediction
        prediction = get_prediction(event)
        
        if prediction is not None:
            # Add prediction to event
            event['prediction_score'] = float(prediction)
            event['prediction_timestamp'] = datetime.datetime.utcnow().isoformat()

            # Publish to the predictions topic
            topic_path = publisher.topic_path(
                cloud_event.data["message"]["attributes"]["projectId"],
                "predictions"
            )
            
            future = publisher.publish(
                topic_path,
                json.dumps(event).encode('utf-8')
            )
            future.result()

            return {"status": "success", "message": "Event processed with prediction"}

    except Exception as e:
        print(f"Error processing event: {str(e)}")
        raise 