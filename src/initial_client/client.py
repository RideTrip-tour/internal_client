import logging
import time

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
        jwt_secret: str

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
                timeout=10.0,
            )
            logger.debug("Initial client initialized")


    def _get_headers(self, user_context: str) -> dict[str, str]:
        return {
            "X-Service-ID": self.service_id,
            "X-Service-Token": self.service_token,
            "X-User-Context": user_context,
        }

    def _build_user_context(self, claims: dict | None) -> str:
        if claims is None:
            logger.error("Failed to build user context: user claims are not available")
            raise RuntimeError("User claims are not available")
        if not all(
            required_claim in claims
            for required_claim in ("id", "is_active", "is_superuser")
        ):
            logger.error(
                "Failed to build user context: required user claims are not available"
            )
            raise RuntimeError("Required user claims are not available")
        data = {
            "sub": str(claims["id"]),
            "is_active": bool(claims["is_active"]),
            "is_superuser": bool(claims["is_superuser"]),
            "aud": self.gateway_name,
            "exp": int(time.time()) + self.access_token_expire_sec,
        }
        return jwt.encode(
            data,
            self.jwt_secret,
            algorithm="HS256",
        )

    async def _request(
        self,
        method: str,
        path: str,
        user_context: str,
        params: dict[str, int] | None = None,
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
                headers=self._get_headers(user_context),
                params=params
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

    async def close(self) -> None:
        await self.client.aclose()
