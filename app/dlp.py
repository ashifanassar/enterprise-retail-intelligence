from google.cloud import dlp_v2

from app.config import PROJECT_ID


dlp_client = dlp_v2.DlpServiceClient()


def redact_pii(text: str) -> tuple[str, bool]:
    inspect_config = {
        "info_types": [
            {"name": "EMAIL_ADDRESS"},
            {"name": "PHONE_NUMBER"},
            {"name": "CREDIT_CARD_NUMBER"},
            {"name": "INDIA_AADHAAR_INDIVIDUAL"},
        ],
        "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
    }
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {
                    "primitive_transformation": {
                        "replace_with_info_type_config": {}
                    }
                }
            ]
        }
    }
    response = dlp_client.deidentify_content(
        request={
            "parent": f"projects/{PROJECT_ID}",
            "inspect_config": inspect_config,
            "deidentify_config": deidentify_config,
            "item": {"value": text},
        }
    )
    redacted = response.item.value
    return redacted, redacted != text
