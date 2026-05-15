from __future__ import annotations


ROLE_DEPARTMENT_ACCESS = {
    "employee": ["general", "hr"],
    "hr": ["general", "hr"],
    "finance": ["general", "finance"],
    "manager": ["general", "hr", "engineering"],
    "executive": ["general", "hr", "finance", "engineering"],
    "admin": ["general", "hr", "finance", "engineering"],
}


def get_allowed_departments(role: str) -> list[str]:
    """Return document departments a role can search."""

    return ROLE_DEPARTMENT_ACCESS.get(role.lower(), ["general"])


def build_department_filter(role: str) -> dict:
    """Build a Chroma metadata filter for the role."""

    allowed_departments = get_allowed_departments(role)
    if len(allowed_departments) == 1:
        return {"department": allowed_departments[0]}

    return {"department": {"$in": allowed_departments}}
