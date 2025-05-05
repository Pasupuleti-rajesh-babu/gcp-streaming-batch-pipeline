import json
import base64
import functions_framework
from google.cloud import pubsub_v1
from google.cloud import storage
import datetime

# Initialize clients
publisher = pubsub_v1.PublisherClient()
storage_client = storage.Client()

@functions_framework.cloud_event
def preprocess_event(cloud_event):
    """Cloud Function to preprocess events before sending to Dataflow."""
    try:
        # Get the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        event = json.loads(pubsub_message)

        # Add preprocessing logic here
        # Example: Enrich event with additional data
        event['processed_timestamp'] = datetime.datetime.utcnow().isoformat()
        
        # Validate required fields
        required_fields = ['event_type', 'device_id']
        if not all(field in event for field in required_fields):
            raise ValueError(f"Missing required fields: {required_fields}")

        # Publish to the processed events topic
        topic_path = publisher.topic_path(
            cloud_event.data["message"]["attributes"]["projectId"],
            "processed-events"
        )
        
        future = publisher.publish(
            topic_path,
            json.dumps(event).encode('utf-8')
        )
        future.result()

        return {"status": "success", "message": "Event processed successfully"}

    except Exception as e:
        print(f"Error processing event: {str(e)}")
        # Store failed events in Cloud Storage for later analysis
        bucket = storage_client.bucket(f"{cloud_event.data['message']['attributes']['projectId']}-failed-events")
        blob = bucket.blob(f"failed_events/{datetime.datetime.utcnow().isoformat()}.json")
        blob.upload_from_string(
            json.dumps({
                "original_event": event,
                "error": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
        )
        raise 