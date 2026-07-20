"""
Module: auth_api

Description:
Client pour vérifier un token porteur auprès de l'API d'authentification.
Reproduit le contrat de POST /user/verify-token tel qu'implémenté par
UserController#verifyToken côté API_authentification : requête
{"token": "..."}, réponse {"username": "...", "role": "..."} sur 200.
(Note : le DTO `TokenResponse(String user, String role)` utilisé côté
API_joueur/API_monstres attend un champ `user` qui n'existe pas dans cette
réponse — l'attribut `username` qu'ils posent sur la requête est donc
toujours null ; bug préexistant hors périmètre de ce service.)
"""

import httpx
import logging

from app.clients.base import BaseClient

logger = logging.getLogger(__name__)


class AuthTokenInvalidError(Exception):
    """Le token est absent, invalide ou expiré (401/403 côté API auth)."""

    pass


class AuthServiceUnavailableError(Exception):
    """L'API d'authentification est injoignable ou renvoie une erreur serveur."""

    pass


class AuthApiClient(BaseClient):
    """Client pour vérifier un token auprès de l'API d'authentification."""

    def __init__(self, base_url: str, timeout: int = 5):
        super().__init__(api_key="", base_url=base_url)
        self.timeout = timeout

    async def verify_token(self, token: str) -> str:
        """
        Vérifie le token auprès de l'API d'authentification.

        Args:
            token: le token brut (sans préfixe "Bearer ")

        Returns:
            Le nom d'utilisateur associé au token.

        Raises:
            AuthTokenInvalidError: token manquant, invalide ou expiré.
            AuthServiceUnavailableError: service d'authentification injoignable/en erreur.
        """
        url = f"{self.base_url}/user/verify-token"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={"token": token},
                    headers={"Content-Type": "application/json"},
                )
        except httpx.RequestError as e:
            logger.error(f"Service d'authentification injoignable ({url}): {e}")
            raise AuthServiceUnavailableError(str(e)) from e

        if response.status_code == 200:
            try:
                body = response.json()
            except ValueError as e:
                raise AuthServiceUnavailableError(
                    f"Réponse invalide de l'API auth: {e}"
                ) from e
            user = body.get("username")
            if not user:
                raise AuthTokenInvalidError("Réponse de vérification sans utilisateur")
            return user

        # Fail-safe aligné sur l'AuthInterceptor des services Java : toute réponse
        # HTTP reçue (4xx ou 5xx, y compris le 500 que l'API auth renvoie
        # aujourd'hui pour un token malformé au lieu d'un 401) est traitée comme
        # "token invalide" plutôt que "service indisponible". Seule une requête
        # qui n'obtient aucune réponse (service injoignable) est une vraie panne.
        logger.warning(
            f"Token refusé par l'API auth: {response.status_code} {response.text}"
        )
        raise AuthTokenInvalidError(f"Token refusé ({response.status_code})")
