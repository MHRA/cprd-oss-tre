from pydantic import BaseModel, Field

class NotifyUkMessageInput(BaseModel):
    recipients: str = Field("Recipient list to be sent to Notify UK Platform", title="Recipient list to be sent to Notify UK Platform")
    name: str = Field("Name of the Researcher who sent the support request", title="Name of the Researcher who sent the support request")
    email: str = Field("Email address of the Researcher who sent the support request", title="Email address of the Researcher who sent the support request")
    workspace: str = Field("Workspace ID of the workspace where the problem happened", title="Workspace ID of the workspace where the problem happened")
    issue_type: str = Field("Issue type related to the problem reported", title="Issue type related to the problem reported")
    error_message: str = Field("Error message received by the Researcher", title="Error message received by the Researcher")
    issue_description: str = Field("Issue description given by the Researcher", title="Issue description given by the Researcher")

    class Config:
        schema_extra = {
            "example": {
                "recipients": "email@domain.com",
                "name": "John Smith",
                "email": "john.smith@email.com",
                "workspace": "b0aec2c5-658a-4a74-b48e-e0ee6cd1d8a4",
                "issue_type": "Issue type 1",
                "error_message": "Error message received by user",
                "issue_description": "I have an error"
            }
        }

class NotifyUkResponse(BaseModel):
    response: dict = Field({}, title="HTTP response sent by Notify UK Platform", description="HTTP response sent by Notify UK Platform")

    class Config:
        schema_extra = {
            "example": {
                "response": "HTTP/1.1 201 CREATED"
            }
        }
