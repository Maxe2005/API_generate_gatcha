"""
Module: security

Description:
Authentification minimale des routes sensibles (admin, génération, import).
Deux voies acceptées :
  - Authorization: Bearer <token> vérifié auprès de l'API d'authentification
    (même contrat que l'AuthInterceptor des services Java) ;
  - X-Internal-Api-Key: <clé> pour les appels machine-à-machine (scripts, CI),
    uniquement si INTERNAL_API_KEY est configurée côté serveur.

Le service ne fait pas d'autorisation fine (rôles) : il s'agit d'un filtre
"authentifié ou non", cohérent avec le reste de l'architecture qui délègue
la vérité sur l'identité à API_authentification.
"""

from dataclasses import dataclass
from secrets import compare_digest
from typing import Optional

from fastapi import Header, HTTPException, status

from app.clients.auth_api import (
    AuthApiClient,
    AuthServiceUnavailableError,
    AuthTokenInvalidError,
)
from app.core.config import get_settings

BEARER_PREFIX = "Bearer "


@dataclass
class AuthContext:
    """Identité résolue pour la requête courante."""

    username: str
    # Token brut à re-transmettre aux appels sortants (API_invocations).
    # None quand l'appelant s'est authentifié via la clé interne.
    token: Optional[str] = None


def _extract_bearer_token(authorization: str) -> str:
    if authorization.startswith(BEARER_PREFIX):
        return authorization[len(BEARER_PREFIX) :]
    return authorization


async def require_auth(
    authorization: Optional[str] = Header(None),
    x_internal_api_key: Optional[str] = Header(None, alias="X-Internal-Api-Key"),
) -> AuthContext:
    """
    Dépendance FastAPI protégeant les routes admin/génération/import.

    Raises:
        HTTPException 401: token/clé manquant ou invalide.
        HTTPException 500: API d'authentification injoignable ou en erreur.
    """
    settings = get_settings()

    if settings.INTERNAL_API_KEY and x_internal_api_key:
        if compare_digest(x_internal_api_key, settings.INTERNAL_API_KEY):
            return AuthContext(username="internal-service", token=None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé interne invalide")

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise (token manquant)",
        )

    token = _extract_bearer_token(authorization)
    client = AuthApiClient(base_url=settings.AUTH_API_URL, timeout=settings.AUTH_API_TIMEOUT)

    try:
        username = await client.verify_token(token)
    except AuthTokenInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        ) from e
    except AuthServiceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service d'authentification indisponible",
        ) from e

    return AuthContext(username=username, token=token)
