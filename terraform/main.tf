terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Pub/Sub resources
resource "google_pubsub_topic" "iot_events" {
  name = "iot-events"
}

resource "google_pubsub_subscription" "iot_events_sub" {
  name  = "iot-events-sub"
  topic = google_pubsub_topic.iot_events.name
}

# Cloud Storage buckets
resource "google_storage_bucket" "raw_data" {
  name          = "${var.project_id}-raw-data"
  location      = var.region
  force_destroy = true
}

resource "google_storage_bucket" "processed_data" {
  name          = "${var.project_id}-processed-data"
  location      = var.region
  force_destroy = true
}

# BigQuery dataset
resource "google_bigquery_dataset" "events_dataset" {
  dataset_id  = "events_dataset"
  description = "Dataset for storing event data"
  location    = var.region
}

# BigQuery table
resource "google_bigquery_table" "events_table" {
  dataset_id = google_bigquery_dataset.events_dataset.dataset_id
  table_id   = "events"

  time_partitioning {
    type = "DAY"
    field = "event_timestamp"
  }

  clustering = ["event_type", "device_id"]

  schema = file("${path.module}/schemas/events_schema.json")
}

# Cloud Composer environment
resource "google_composer_environment" "data_pipeline" {
  name   = "data-pipeline-composer"
  region = var.region

  config {
    software_config {
      image_version = "composer-2.0.32-airflow-2.2.5"
    }

    node_config {
      network    = google_compute_network.composer_network.id
      subnetwork = google_compute_subnetwork.composer_subnet.id
    }
  }
}

# VPC Network for Composer
resource "google_compute_network" "composer_network" {
  name = "composer-network"
}

resource "google_compute_subnetwork" "composer_subnet" {
  name          = "composer-subnet"
  ip_cidr_range = "10.0.0.0/24"
  network       = google_compute_network.composer_network.id
  region        = var.region
}

# Service accounts and IAM
resource "google_service_account" "dataflow_sa" {
  account_id   = "dataflow-sa"
  display_name = "Dataflow Service Account"
}

resource "google_project_iam_member" "dataflow_worker" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
}

resource "google_project_iam_member" "bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
} 