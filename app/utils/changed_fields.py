"""
Utility: compute_changed_fields

Contient la fonction `compute_changed_fields` utilisée pour détecter
les changements entre deux snapshots JSON, avec gestion fine des listes.
"""

import json
from difflib import SequenceMatcher


def compute_changed_fields(before: dict, after: dict, prefix: str = "") -> dict:
    changed_fields = []
    diff_payload = {}

    def is_primitive(v):
        return v is None or isinstance(v, (str, int, float, bool))

    def find_id_key(list_of_dicts):
        if not list_of_dicts:
            return None
        candidate_keys = ["id", "uuid", "name"]
        keys = set()
        for d in list_of_dicts:
            if isinstance(d, dict):
                keys.update(d.keys())
        for k in candidate_keys:
            if k in keys:
                return k
        return None

    def lcs_opcodes(a_seq, b_seq):
        sm = SequenceMatcher(None, a_seq, b_seq)
        return sm.get_opcodes()

    def match_lists(before_list, after_list, path_prefix):
        # Case: list of primitives
        if all(is_primitive(x) for x in before_list + after_list):
            a = before_list
            b = after_list
            opcodes = lcs_opcodes(a, b)
            for tag, i1, i2, j1, j2 in opcodes:
                if tag == "equal":
                    continue
                if tag in ("replace", "delete"):
                    for idx in range(i1, i2):
                        path = f"{path_prefix}[{idx}]"
                        changed_fields.append(path)
                        diff_payload[path] = {"before": a[idx], "after": None}
                if tag in ("replace", "insert"):
                    for j in range(j1, j2):
                        path = f"{path_prefix}[{j}]"
                        if path in diff_payload:
                            diff_payload[path]["after"] = b[j]
                        else:
                            changed_fields.append(path)
                            diff_payload[path] = {"before": None, "after": b[j]}
            return

        # Case: list of dicts with id key
        if all(isinstance(x, dict) for x in before_list + after_list):
            id_key = find_id_key(before_list + after_list)
            if id_key:
                before_map = {str(item.get(id_key)): item for item in before_list if id_key in item}
                after_map = {str(item.get(id_key)): item for item in after_list if id_key in item}

                # Deletions
                for _id, item in before_map.items():
                    if _id not in after_map:
                        path = f"{path_prefix}[{id_key}={_id}]"
                        changed_fields.append(path)
                        diff_payload[path] = {"before": item, "after": None}

                # Insertions
                for _id, item in after_map.items():
                    if _id not in before_map:
                        path = f"{path_prefix}[{id_key}={_id}]"
                        changed_fields.append(path)
                        diff_payload[path] = {"before": None, "after": item}

                # Common elements: compare recursively
                for _id in set(before_map.keys()) & set(after_map.keys()):
                    b_item = before_map[_id]
                    a_item = after_map[_id]
                    nested = compute_changed_fields(
                        b_item, a_item, f"{path_prefix}[{id_key}={_id}]"
                    )
                    changed_fields.extend(nested["changed_fields"])
                    diff_payload.update(nested["diff_payload"])
                return

        # Fallback: try to match by serialized equality using SequenceMatcher
        before_serial = [json.dumps(x, sort_keys=True) for x in before_list]
        after_serial = [json.dumps(x, sort_keys=True) for x in after_list]
        opcodes = lcs_opcodes(before_serial, after_serial)
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                # for equal blocks, still compare deeply to detect nested changes
                for off in range(i2 - i1):
                    bi = i1 + off
                    aj = j1 + off
                    b_item = before_list[bi]
                    a_item = after_list[aj]
                    if isinstance(b_item, dict) and isinstance(a_item, dict):
                        nested = compute_changed_fields(b_item, a_item, f"{path_prefix}[{aj}]")
                        changed_fields.extend(nested["changed_fields"])
                        diff_payload.update(nested["diff_payload"])
                continue
            if tag in ("replace", "delete"):
                for idx in range(i1, i2):
                    path = f"{path_prefix}[{idx}]"
                    changed_fields.append(path)
                    diff_payload[path] = {"before": before_list[idx], "after": None}
            if tag in ("replace", "insert"):
                for j in range(j1, j2):
                    path = f"{path_prefix}[{j}]"
                    if path in diff_payload:
                        diff_payload[path]["after"] = after_list[j]
                    else:
                        changed_fields.append(path)
                        diff_payload[path] = {"before": None, "after": after_list[j]}

    # Vérifier toutes les clés
    all_keys = set(before.keys()) | set(after.keys())

    for key in all_keys:
        path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        before_val = before.get(key)
        after_val = after.get(key)

        # Deux dicts -> récursion
        if isinstance(before_val, dict) and isinstance(after_val, dict):
            nested = compute_changed_fields(before_val, after_val, path)
            changed_fields.extend(nested["changed_fields"])
            diff_payload.update(nested["diff_payload"])
        # Listes -> gestion fine
        elif isinstance(before_val, list) and isinstance(after_val, list):
            match_lists(before_val, after_val, path)
        # Cas classiques ou mismatched types
        elif before_val != after_val:
            changed_fields.append(path)
            diff_payload[path] = {"before": before_val, "after": after_val}

    return {"changed_fields": changed_fields, "diff_payload": diff_payload}
