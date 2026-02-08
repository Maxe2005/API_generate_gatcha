"""
Module: constants

Description:
Constantes globales de l'application

Author: Copilot
Date: 2026-02-08
"""

# Messages d'erreur
ERROR_MONSTER_NOT_FOUND = "Monster not found"
ERROR_INVALID_TRANSITION = "Invalid state transition"
ERROR_TRANSMISSION_FAILED = "Failed to transmit monster to invocation API"
ERROR_VALIDATION_FAILED = "Monster validation failed"

# Messages de succès
SUCCESS_MONSTER_GENERATED = "Monster generated successfully"
SUCCESS_MONSTER_APPROVED = "Monster approved successfully"
SUCCESS_MONSTER_TRANSMITTED = "Monster transmitted successfully"

# Limites
MAX_BATCH_SIZE = 15
MAX_LIST_LIMIT = 200
DEFAULT_LIST_LIMIT = 50

# Timeouts (secondes)
DEFAULT_API_TIMEOUT = 30
HEALTH_CHECK_TIMEOUT = 5
