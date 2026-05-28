import logging
import httpx
import jwt
import time


from shared import config


async def send_status_event(message: dict) -> None:

    if not isinstance(message, dict):        return

    req = message.get("req") or {}

    # Generate JWT token
    iat_date = int(time.time())

    jwt_headers = {
        "typ": "JWT",
        "alg": "HS256"
    }

    token_payload = {
        "iss": config.NOTIFY_UK_ISS_ID,
        "iat": str(iat_date)
    }

    jwt_token = jwt.encode(
        token_payload,
        config.NOTIFY_UK_SECRET,
        headers=jwt_headers
    )

    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {jwt_token}"
    }

    logging.info("Sending status event notification")
    logging.info("headers -> %s", headers)

    try:
        async with httpx.AsyncClient() as client:

            template_data = {
                "email_address": req.get("createdBy", {}).get("email", ""),
                "template_id": config.NOTIFY_UK_TEMPLATE_ID,
                "personalisation": {
                    "status": message.get("status"),
                    "workspace_id": req.get("workspace_id"),
                    "transaction_id": message.get("transaction"),
                }
            }

            logging.info("template_data -> %s", template_data)

            response = await client.post(
                config.NOTIFY_UK_URL,
                headers=headers,
                json=template_data
            )

            response.raise_for_status()

            logging.info(
                "Notify UK response status -> %s",
                response.status_code
            )

    except httpx.HTTPStatusError:
        logging.exception(
            "Error contacting Notify UK API with error code %s",
            response.status_code
        )



    except Exception as exc:
        logging.exception(
            "Unexpected error while sending status event -> %s",
            str(exc)
        )


