def member_context(request):
    return {
        "member": getattr(request, "member", None),
    }
