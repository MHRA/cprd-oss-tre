from pydantic import BaseModel, Field


class DataMoveRequestCreate(BaseModel):

    title: str = Field("Airlock Request", title="Brief title for the request")
    businessJustification: str = Field("Business Justifications", title="Explanation that will be provided to the request reviewer")
    isEUUAAccepted: bool = Field("User Agreement Acceptance", title="Mark if the User Agreement was accepted")
    properties: dict = Field({}, title="Airlock request parameters", description="Values for the parameters required by the Airlock request specification")

    class Config:
        schema_extra = {
            "example": {
                "type": "import",
                "title": "a request title",
                "businessJustification": "some business justification",
                "isEUUAAccepted": "true"
            }
        }
