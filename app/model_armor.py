import logging

from google.api_core.client_options import ClientOptions
from google.cloud import modelarmor_v1

from app.config import MODEL_ARMOR_LOCATION, MODEL_ARMOR_TEMPLATE_ID, PROJECT_ID


class ModelArmorBlockedError(RuntimeError):
    pass


def _client() -> modelarmor_v1.ModelArmorClient:
    return modelarmor_v1.ModelArmorClient(
        client_options=ClientOptions(
            api_endpoint=f"modelarmor.{MODEL_ARMOR_LOCATION}.rep.googleapis.com"
        )
    )


def sanitize_model_response(text: str) -> str:
    if not MODEL_ARMOR_TEMPLATE_ID:
        return text

    request = modelarmor_v1.SanitizeModelResponseRequest(
        name=(
            f"projects/{PROJECT_ID}/locations/{MODEL_ARMOR_LOCATION}/"
            f"templates/{MODEL_ARMOR_TEMPLATE_ID}"
        ),
        model_response_data=modelarmor_v1.DataItem(text=text),
    )
    response = _client().sanitize_model_response(request=request)
    result = response.sanitization_result

    if result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
        logging.warning("Model Armor blocked model response: %s", result)
        raise ModelArmorBlockedError("Model response blocked by Model Armor.")

    return text