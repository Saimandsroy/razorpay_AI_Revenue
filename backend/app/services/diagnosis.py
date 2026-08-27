from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnosis:
    category: str
    root_cause: str
    base_score: float


ERROR_CODES: dict[str, Diagnosis] = {
    "BAD_REQUEST_CARD_EXPIRED": Diagnosis("card_expired", "The customer's card has expired.", 0.74),
    "BAD_REQUEST_INSUFFICIENT_BALANCE": Diagnosis("insufficient_funds", "The payment instrument lacks sufficient balance.", 0.80),
    "BAD_REQUEST_INSUFFICIENT_FUNDS": Diagnosis("insufficient_funds", "The payment instrument lacks sufficient balance.", 0.80),
    "BAD_REQUEST_MANDATE_REJECTED": Diagnosis("mandate_rejected", "The recurring mandate was rejected by the bank or customer.", 0.36),
    "BAD_REQUEST_MANDATE_CANCELLED": Diagnosis("mandate_rejected", "The recurring mandate was cancelled.", 0.36),
    "BAD_REQUEST_INVALID_3DS_RESPONSE": Diagnosis("authentication_failed", "3DS authentication did not complete successfully.", 0.60),
    "BAD_REQUEST_OTP_FAILED": Diagnosis("authentication_failed", "OTP authentication failed.", 0.60),
    "BAD_REQUEST_AUTH_NOT_COMPLETED": Diagnosis("authentication_failed", "Customer authentication was not completed.", 0.60),
}

UNKNOWN = Diagnosis("unknown_failure", "Razorpay did not return a supported failure code.", 0.30)


def diagnose(error_code: str | None) -> Diagnosis:
    return ERROR_CODES.get(error_code or "", UNKNOWN)
