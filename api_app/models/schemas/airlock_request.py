import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from models.domain.operation import Operation
from models.schemas.operation import get_sample_operation
from models.domain.airlock_request import AirlockActions, AirlockRequest, AirlockRequestType


def get_sample_airlock_review(airlock_review_id: str) -> dict:
    return {
        "reviewId": airlock_review_id,
        "reviewDecision": "Describe why the request was approved/rejected",
        "decisionExplanation": "Describe why the request was approved/rejected"
    }


def get_sample_airlock_request(workspace_id: str, airlock_request_id: str) -> dict:
    return {
        "requestId": airlock_request_id,
        "workspaceId": workspace_id,
        "status": "draft",
        "type": "import",
        "files": [],
        "title": "a request title",
        "businessJustification": "some business justification",
        "createdBy": {
            "id": "a user id",
            "name": "a user name"
        },
        "createdWhen": datetime.utcnow().timestamp(),
        "reviews": [
            get_sample_airlock_review("29990431-5451-40e7-a58a-02e2b7c3d7c8"),
            get_sample_airlock_review("02dc0f29-351a-43ec-87e7-3dd2b5177b7f")]
    }


def get_sample_airlock_request_with_allowed_user_actions(workspace_id: str) -> dict:
    return {
        "airlockRequest": get_sample_airlock_request(workspace_id, str(uuid.uuid4())),
        "allowedUserActions": [AirlockActions.Cancel, AirlockActions.Review, AirlockActions.Submit],
    }


class AirlockRequestInResponse(BaseModel):
    airlockRequest: AirlockRequest

    class Config:
        schema_extra = {
            "example": {
                "airlockRequest": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestAndOperationInResponse(BaseModel):
    airlockRequest: AirlockRequest
    operation: Operation

    class Config:
        schema_extra = {
            "example": {
                "airlockRequest": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef"),
                "operation": get_sample_operation("121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestWithAllowedUserActions(BaseModel):
    airlockRequest: AirlockRequest = Field([], title="Airlock Request")
    allowedUserActions: List[str] = Field([], title="actions that the requesting user can do on the request")

    class Config:
        schema_extra = {
            "example": get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e"),
        }


class AirlockRequestWithAllowedUserActionsInList(BaseModel):
    airlockRequests: List[AirlockRequestWithAllowedUserActions] = Field([], title="Airlock Requests")

    class Config:
        schema_extra = {
            "example": {
                "airlockRequests": [
                    get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e"),
                    get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e")
                ]
            }
        }


class AirlockRequestInCreate(BaseModel):
    type: AirlockRequestType = Field("", title="Airlock request type", description="Specifies if this is an import or an export request")
    title: str = Field("Airlock Request", title="Brief title for the request")
    businessJustification: str = Field("Business Justifications", title="Explanation that will be provided to the request reviewer")
    properties: dict = Field({}, title="Airlock request parameters", description="Values for the parameters required by the Airlock request specification")

    class Config:
        schema_extra = {
            "example": {
                "type": "import",
                "title": "a request title",
                "businessJustification": "some business justification"
            }
        }


class AirlockReviewInCreate(BaseModel):
    approval: bool = Field("", title="Airlock review decision", description="Airlock review decision")
    decisionExplanation: str = Field("Decision Explanation", title="Explanation of the reviewer for the reviews decision")

    class Config:
        schema_extra = {
            "example": {
                "approval": "True",
                "decisionExplanation": "the reason why this request was approved/rejected"
            }
        }


class AirlockRequestTriageStatements(BaseModel):
    rdgConsistent: bool = Field("", title="Statement 1", description="Requested outputs are consistent with the RDG approved protocol associated with this workspace.")
    noPatientLevelData: bool = Field("", title="Statement 2", description="No event or patient level data are included in the requested outputs.")
    requestedOutputsClear: bool = Field("", title="Statement 3", description="All requested outputs are sufficiently clear and comprehensible to permit output checking without the need for dataset- or project-specific knowledge.")
    requestedOutputsStatic: bool = Field("", title="Statement 4", description="All requested outputs are static.")
    requestedOutputsPermittedFiles: bool = Field("", title="Statement 5", description="All requested outputs use permitted file types.")
    noHiddenInformation: bool = Field("", title="Statement 6", description="No hidden information has been included (e.g., embedded files), comments, track changes).")

    class Config:
        schema_extra = {
            "example": {
                "rdgConsistent": "True",
                "noPatientLevelData": "True",
                "requestedOutputsClear": "True",
                "requestedOutputsStatic": "True",
                "requestedOutputsPermittedFiles": "True",
                "noHiddenInformation": "True"
            }
        }


class AirlockRequestContactTeamForm(BaseModel):
    requiredDisclosureAlignment: str = Field("Question 1", title="Why are outputs required that do not align with the disclosure control rules?")
    measuresTakenMinimiseDisclosure: str = Field("Question 2", title="What measures have been taken to minimise the risk of potentially disclosive outputs?")
    transferToThirdParty: str = Field("Question 3", title="Will the outputs be transferred to any other third party?")

    class Config:
        schema_extra = {
            "example": {
                "requiredDisclosureAlignment": "I need this output because it'll be used in a very important publication.",
                "measuresTakenMinimiseDisclosure": "I took measures 1, 2, 3, 4, etc. for minimising diclosure information.",
                "transferToThirdParty": "The output generated will not be transferred to thrid parties."
            }
        }


class AirlockRequestStatisticsStatements(BaseModel):
    codeLists: bool = Field("", title="Statement 1", description="Code lists or programming code")
    safeStatistics: bool = Field("", title="Statement 2", description="Safe statistics")
    statisticalTests: bool = Field("", title="Statement 3", description="Statistical hypothesis tests (e.g., t-test, chi-square, R-square, standard errors)")
    coefficientsAssociation: bool = Field("", title="Statement 4", description="Coefficients of association (e.g., estimated coefficients, models, AN(C)OVA, correlation tables, density plots, kernel density plots)")
    shape: bool = Field("", title="Statement 5", description="Shape (e.g., standard deviation, skewness, kurtosis)")
    mode: bool = Field("", title="Statement 6", description="Mode")
    ratios: bool = Field("", title="Statement 7", description="Non-linear concentration ratios (e.g., Herfindahl-Hirchsmann index, diversity index)")
    giniCoefficients: bool = Field("", title="Statement 8", description="Gini coefficients or Lorenz curves")
    unsafeStatisticsStatements: bool = Field("", title="Statement 9", description="Unsafe statistics")
    frequencies: bool = Field("", title="Statement 10", description="Frequencies (e.g. frequency tables, histograms, shares, alluvial flow graphs, heat maps, line graphs, pie charts, scatter graphs, scatter plots, smoothed histograms, waterfall charts)")
    position: bool = Field("", title="Statement 11", description="Position (e.g., median, percentiles, box plots)")
    extremeValues: bool = Field("", title="Statement 12", description="Extreme values (e.g., maxima, minima)")
    linearAggregates: bool = Field("", title="Statement 13", description="Linear aggregates (e.g., means, totals, simple indexes, linear correlation ratios, bar graphs, mean plots)")
    riskRatios: bool = Field("", title="Statement 14", description="Odds ratios, risk ratios or other proportionate risks")
    survivalTables: bool = Field("", title="Statement 15", description="Hazard and survival tables (e.g., tables of survival/death rates, Kaplan-Meier graphs)")
    other: bool = Field("", title="Statement 16", description="Other")

    class Config:
        schema_extra = {
            "example": {
                "codeLists": "True",
                "safeStatistics": "True",
                "statisticalTests": "True",
                "coefficientsAssociation": "True",
                "shape": "True",
                "mode": "True",
                "ratios": "True",
                "giniCoefficients": "True",
                "unsafeStatisticsStatements": "True",
                "frequencies": "True",
                "position": "True",
                "extremeValues": "True",
                "linearAggregates": "True",
                "riskRatios": "True",
                "survivalTables": "True",
                "other": "True"
            }
        }


class AirlockRequestUnsafeStatisticsStatements(BaseModel):
    requestedOutputsStatisticsPosition: bool = Field("", title="Statement 1", description="You stated that your requested outputs include statistics of position. Please confirm the numbers for each group (and complementary groups) are ≥5.")
    requestedOutputsLinearAggregates: bool = Field("", title="Statement 2", description="You stated that your requested outputs include linear aggregates.")
    linearAggregatesDerivedGroups: bool = Field("", title="Statement 3", description="The linear aggregates have been derived from groups containing ≥5 patients or GP practices.")
    pRatioDominanceRule: bool = Field("", title="Statement 4", description="The P-ratio dominance rule has been calculated and is greater than 10%. (NB: ACRO will check this automatically).")
    nkDominanceRule: bool = Field("", title="Statement 5", description="The N-K dominance rule has been calculated for the 2 largest values and is less than 90%. (NB: ACRO will check this automatically).")

    class Config:
        schema_extra = {
            "example": {
                "requestedOutputsStatisticsPosition": "True",
                "requestedOutputsLinearAggregates": "True",
                "linearAggregatesDerivedGroups": "True",
                "pRatioDominanceRule": "False",
                "nkDominanceRule": "True"
            }
        }


class AirlockRequestSafeStatisticsStatements(BaseModel):
    testConfirmation: bool = Field("", title="Statement 1", description="You stated that your requested outputs include statistical hypothesis tests")
    coefficientsConfirmation: bool = Field("", title="Statement 2", description="You stated that your requested outputs include coefficients of association")
    residualDegrees: bool = Field("", title="Statement 3", description="The residual degrees of freedom (number of observations less number of variables) exceeds five")
    modelNotSaturated: bool = Field("", title="Statement 4", description="The model is not saturated (i.e., not all variables are categorical and fully interacted)")
    regressionNotIncluded: bool = Field("", title="Statement 5", description="Your outputs do not include a regression with a single binary explanatory variable")
    shapeConfirmation: bool = Field("", title="Statement 6", description="You stated that your requested outputs include statistics of shape")
    standardDeviations: bool = Field("", title="Statement 7", description="Any standard deviations are greater than zero")
    shapeMinFive: bool = Field("", title="Statement 8", description="All statistics of shape were calculated for a minimum of five patients or GP practices")
    modeConfirmation: bool = Field("", title="Statement 9", description="You stated that your requested outputs include modes")
    ratiosConfirmation: bool = Field("", title="Statement 10", description="You stated that your requested outputs include non-linear concentration ratios")
    nRatio: bool = Field("", title="Statement 11", description="N>2")
    hRatio: bool = Field("", title="Statement 12", description="H<0.81")
    giniCoefficientsConfirmation: bool = Field("", title="Statement 13", description="You stated that your requested outputs include Gini coefficients or Lorenz curves")
    nGiniCoefficient: bool = Field("", title="Statement 14", description="N>2")
    coefficientLessThan: bool = Field("", title="Statement 15", description="The coefficient is less than 100%")

    class Config:
        schema_extra = {
            "example": {
                "testConfirmation": "True",
                "coefficientsConfirmation": "True",
                "residualDegrees": "True",
                "modelNotSaturated": "True",
                "regressionNotIncluded": "True",
                "shapeConfirmation": "True",
                "standardDeviations": "True",
                "shapeMinFive": "True",
                "modeConfirmation": "True",
                "ratiosConfirmation": "True",
                "nRatio": "True",
                "hRatio": "True",
                "giniCoefficientsConfirmation": "True",
                "nGiniCoefficient": "True",
                "coefficientLessThan": "True"
            }
        }


class AirlockRequestOtherStatisticsStatements(BaseModel):
    requestedOutputsIncludeFrequencies: bool = Field("", title="Statement 1", description="You stated that your requested outputs include frequencies. Please confirm the following.")
    smallFrequenciesSuppressed: bool = Field("", title="Statement 2", description="All counts <5 and frequencies derived from groups containing <5 patients or GP practices have been suppressed.")
    zerosFullCells: bool = Field("", title="Statement 3", description="All zeroes and full cells (100%) are evidential or structural (i.e., something you would expect).")
    underlyingValuesIndependent: bool = Field("", title="Statement 4", description="Underlying values are genuinely independent (i.e., they do not come from the same patient, the patients do not all have the same family number and do not all come from the same GP practice).")
    categoriesComprehensiveData: bool = Field("", title="Statement 5", description="The categories are comprehensive and apply to all data (i.e., all categories of each categorical variable are presented).")
    requestedOutputsExtremeValues: bool = Field("", title="Statement 6", description="You stated that your requested outputs include extreme values. Please confirm the maximum or minimum presented are non-informative and structural.")
    requestedOutputsRatios: bool = Field("", title="Statement 7", description="You stated that your requested outputs include odds ratios, risk ratios or other proportionate risks. Please confirm the underlying contingency table has been produced and is included in the requested outputs.")
    requestedOutputsHazard: bool = Field("", title="Statement 8", description="You stated that your requested outputs include hazard or survival tables. Please confirm the following.")
    numberPatientsSurvived: bool = Field("", title="Statement 9", description="The number of patients who survived is ≥5.")
    exitDatesRelatives: bool = Field("", title="Statement 10", description="Exit dates are relative, not absolute.")
    noDatesWithSingleExit: bool = Field("", title="Statement 11", description="There are no dates with a single exit.")

    class Config:
        schema_extra = {
            "example": {
                "requestedOutputsIncludeFrequencies": "True",
                "smallFrequenciesSuppressed": "True",
                "zerosFullCells": "True",
                "underlyingValuesIndependent": "False",
                "categoriesComprehensiveData": "True",
                "requestedOutputsExtremeValues": "True",
                "requestedOutputsRatios": "True",
                "requestedOutputsHazard": "False",
                "numberPatientsSurvived": "True",
                "exitDatesRelatives": "True",
                "noDatesWithSingleExit": "True"
            }
        }


class AirlockRequestAcroConfirmation(BaseModel):
    isAcroUsed: bool = Field("", title="Statement 1", description="Is Acro used")

    class Config:
        schema_extra = {
            "example": {
                "isAcroUsed": "True"
            }
        }

