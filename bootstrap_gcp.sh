#!/bin/bash
# Run this once to bootstrap GCP before the first CD deploy.
# Prerequisites: gcloud CLI installed and authenticated.

PROJECT_ID="codebase-intel-500619"
REGION="us-central1"
REPO="codebase-intel"

echo "Setting project..."
gcloud config set project $PROJECT_ID

echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="Codebase Intel Docker images"

echo "Done! Artifact Registry ready at:"
echo "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO"
