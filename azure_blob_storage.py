from azure.storage.blob import BlobServiceClient
import os

class AzureBlobStorage:
    def __init__(self):
        # Initialize the BlobServiceClient using the connection string from environment variables
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("Azure Storage connection string is not set in environment variables.")
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    def upload_resume(self, container_name, file_name, content):
        # Ensure the container exists
        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()

        # Upload the resume content as a blob
        blob_client = container_client.get_blob_client(file_name)
        blob_client.upload_blob(content, overwrite=True)
        return f"Resume uploaded successfully to {container_name}/{file_name}"

    def download_resume(self, container_name, file_name):
        # Download the resume content from the blob
        blob_client = self.blob_service_client.get_blob_client(container_name, file_name)
        if not blob_client.exists():
            raise FileNotFoundError(f"The file {file_name} does not exist in container {container_name}.")
        return blob_client.download_blob().readall()
