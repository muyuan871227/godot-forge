"""GodotForge pricing plans and usage limits."""

PRICING_PLANS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "ai_generations_per_day": 20,
        "projects": 3,
        "storage_gb": 1,
        "export_platforms": ["web"],
        "templates": "basic",
        "priority_gpu": False,
        "custom_models": False,
        "collaboration": False,
        "features": [
            "AI code generation (20/day)",
            "Basic 2D asset generation",
            "Web export",
            "3 projects",
            "Community templates",
        ],
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 19.99,
        "ai_generations_per_day": 200,
        "projects": 50,
        "storage_gb": 20,
        "export_platforms": ["web", "windows", "macos", "linux", "android"],
        "templates": "all",
        "priority_gpu": True,
        "custom_models": True,
        "collaboration": False,
        "features": [
            "AI code generation (200/day)",
            "Full 2D/3D/audio asset generation",
            "All export platforms",
            "50 projects, 20GB storage",
            "All templates",
            "Priority GPU queue",
            "Custom model upload",
        ],
    },
    "team": {
        "name": "Team",
        "price_monthly_per_seat": 29.99,
        "seats_min": 3,
        "ai_generations_per_day": 500,
        "projects": -1,  # unlimited
        "storage_gb": 100,
        "export_platforms": "all",
        "templates": "all",
        "priority_gpu": True,
        "custom_models": True,
        "collaboration": True,
        "features": [
            "Everything in Pro",
            "Unlimited projects",
            "100GB shared storage",
            "Real-time collaboration",
            "Team admin dashboard",
            "Shared asset library",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": "custom",
        "private_deployment": True,
        "custom_model_training": True,
        "sso": True,
        "sla": True,
        "dedicated_support": True,
        "features": [
            "Everything in Team",
            "Private on-premise deployment",
            "Custom model training on your data",
            "SSO/SAML integration",
            "SLA guarantees",
            "Dedicated support engineer",
            "Audit logging",
        ],
    },
}


def get_plan_limits(plan: str) -> dict:
    """Get the limits for a given plan."""
    return PRICING_PLANS.get(plan, PRICING_PLANS["free"])


def check_usage_limit(plan: str, usage_type: str, current_count: int) -> bool:
    """Check if a user is within their plan limits."""
    limits = get_plan_limits(plan)

    if usage_type == "ai_generations":
        max_gen = limits.get("ai_generations_per_day", 0)
        return current_count < max_gen
    elif usage_type == "projects":
        max_proj = limits.get("projects", 0)
        if max_proj == -1:
            return True
        return current_count < max_proj
    elif usage_type == "storage":
        max_gb = limits.get("storage_gb", 0)
        return current_count < max_gb * 1024 * 1024 * 1024

    return True
