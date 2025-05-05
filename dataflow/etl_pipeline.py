import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery
import json
import datetime
import uuid

class EventProcessor(beam.DoFn):
    def process(self, element):
        try:
            # Parse the input element
            if isinstance(element, bytes):
                element = element.decode('utf-8')
            event = json.loads(element)
            
            # Add processing timestamp and event ID if not present
            if 'event_id' not in event:
                event['event_id'] = str(uuid.uuid4())
            if 'event_timestamp' not in event:
                event['event_timestamp'] = datetime.datetime.utcnow().isoformat()
            
            # Ensure required fields are present
            required_fields = ['event_type', 'device_id']
            if all(field in event for field in required_fields):
                yield event
            else:
                print(f"Missing required fields in event: {event}")
        except Exception as e:
            print(f"Error processing event: {e}")

def run_pipeline(argv=None):
    pipeline_options = PipelineOptions(argv)
    pipeline_options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=pipeline_options) as pipeline:
        # Read from Pub/Sub
        events = (
            pipeline
            | 'ReadFromPubSub' >> beam.io.ReadFromPubSub(
                topic='projects/{}/topics/iot-events'.format(pipeline_options.project)
            )
            | 'ProcessEvents' >> beam.ParDo(EventProcessor())
        )

        # Write to BigQuery
        events | 'WriteToBigQuery' >> WriteToBigQuery(
            table='{}.events_dataset.events'.format(pipeline_options.project),
            schema='SCHEMA_AUTODETECT',
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
        )

if __name__ == '__main__':
    run_pipeline() 