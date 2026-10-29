import logging
import time
from typing import Any

import httpx
import jwt

logger = logging.getLogger(__name__)


class InitialClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        base_url: str,
        service_id: str,
        service_token: str,
        gateway_name: str,
        access_token_expire_sec: int,
        jwt_secret: str,
        timeout: float | httpx.Timeout = 10.0,
    ):
        if not hasattr(self, "client"):
            self.base_url = base_url
            self.service_id = service_id
            self.service_token = service_token
            self.gateway_name = gateway_name
            self.access_token_expire_sec = access_token_expire_sec
            self.jwt_secret = jwt_secret
            self.client = httpx.AsyncClient(
                base_url=base_url,
                timeout=timeout,
            )
            logger.debug("Initial client initialized")

    def _get_headers(self, user_context: str, request_id: str) -> dict[str, str]:
        return {
            "X-Service-ID": self.service_id,
            "X-Service-Token": self.service_token,
            "X-User-Context": user_context,
            "X-Request-ID": request_id,
        }

    def _validate_claims(self, claims: dict[str, Any] | None) -> dict[str, Any]:
        if claims is None:
            raise ValueError("User claims are not available")

        if not isinstance(claims, dict):
            raise TypeError("User claims must be a dictionary")

        required_claims = ("id", "is_active", "is_superuser")
        missing_claims = [key for key in required_claims if key not in claims]

        if missing_claims:
            raise ValueError(
                f"Required user claims are missing: {', '.join(missing_claims)}"
            )

        if claims["id"] is None or isinstance(claims["id"], bool):
            raise ValueError("Claim 'id' must be a valid identifier")

        if not isinstance(claims["is_active"], bool):
            raise TypeError("Claim 'is_active' must be a boolean")

        if not isinstance(claims["is_superuser"], bool):
            raise TypeError("Claim 'is_superuser' must be a boolean")

        return claims

    def _build_token_payload(self, claims: dict[str, Any]) -> dict[str, Any]:
        return {
            "sub": str(claims["id"]),
            "is_active": claims["is_active"],
            "is_superuser": claims["is_superuser"],
            "aud": self.gateway_name,
            "exp": int(time.time()) + self.access_token_expire_sec,
        }

    def _build_user_context(self, claims: dict[str, Any] | None) -> str:
        payload = self._build_token_payload(self._validate_claims(claims))
        return jwt.encode(
            payload,
            self.jwt_secret,
            algorithm="HS256",
        )

    async def _request(
        self,
        method: str,
        path: str,
        user_context: str,
        request_id: str,
        params: dict[str, int] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:

        started_at = time.monotonic()

        logger.info(
            "Gateway request started: %s: %s",
            method,
            path,
        )

        try:
            response = await self.client.request(
                method,
                path,
                headers=self._get_headers(
                    user_context=user_context,
                    request_id=request_id,
                ),
                params=params,
                json=json,
            )
            elapsed = time.monotonic() - started_at
            response.raise_for_status()
            logger.info(
                "Gateway request completed: %s: %s -> %s in %s s",
                method,
                path,
                response.status_code,
                elapsed,
            )
            return response
        except Exception:
            elapsed = time.monotonic() - started_at

            logger.exception(
                "Gateway request failed: %s: %s in %s s",
                method,
                path,
                elapsed,
            )
            raise

    async def request(
        self,
        method: str,
        path: str,
        user_context: str,
        request_id: str,
        params: dict[str, int] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return await self._request(
            method=method,
            path=path,
            user_context=user_context,
            request_id=request_id,
            params=params,
            json=json,
        )

    async def close(self) -> None:
        await self.client.aclose()
