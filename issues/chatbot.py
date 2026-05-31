import requests
from django.conf import settings
from .models import CivicIssue

def get_chatbot_response(user_message, conversation_history=None):
    """
    Query NVIDIA's API to get a chatbot response, with a local rule-based fallback.
    """
    # 1. Gather context from the database
    issues = CivicIssue.objects.all()
    total_count = issues.count()
    open_count = issues.filter(status='Open').count()
    in_progress_count = issues.filter(status='In Progress').count()
    resolved_count = issues.filter(status='Resolved').count()
    
    # Group issues by department
    dept_counts = {}
    for code, name in CivicIssue.DEPARTMENT_CHOICES:
        count = issues.filter(assigned_department=code).count()
        if count > 0:
            dept_counts[name] = count
            
    dept_summary = ", ".join([f"{dept}: {count}" for dept, count in dept_counts.items()]) or "None"
    
    # Detail recent 10 issues
    recent_issues = []
    for issue in issues.order_by('-created_at')[:10]:
        recent_issues.append(
            f"- [ID: #{issue.id}] {issue.name} in '{issue.origin_location}' "
            f"(Status: {issue.status}, Department: {issue.get_assigned_department_display()})"
        )
    issues_list = "\n".join(recent_issues) if recent_issues else "No issues reported yet."

    # 2. Build the System Prompt
    system_prompt = (
        "You are 'CivicTrack Assistant', a helpful, polite, and concise AI guide dedicated exclusively to the CivicTrack application.\n"
        "CivicTrack is a platform that allows citizens to report local civic issues (such as potholes, streetlights, waste dumping, public health safety issues), comment, upvote, and track resolution progress.\n"
        "Officials (staff and administrators) verify these complaints, assign them to relevant departments (Water Supply & Sewage, Roads & Traffic, Sanitation & Waste, Electricity & Lighting, Public Health & Safety, or Other/General), and update their status (Open, In Progress, Resolved).\n\n"
        "Current System Data:\n"
        f"- Total issues reported: {total_count}\n"
        f"- Open: {open_count}\n"
        f"- In Progress: {in_progress_count}\n"
        f"- Resolved: {resolved_count}\n"
        f"- Issues by department: {dept_summary}\n"
        f"- List of recent reported issues:\n{issues_list}\n\n"
        "CONSTRAINTS:\n"
        "1. ONLY answer questions directly related to CivicTrack features, how it works, how to use it, or the current reported issues detailed above.\n"
        "2. If the user asks about unrelated topics (e.g. general programming, math, science, geography, weather, non-CivicTrack queries), politely refuse:\n"
        "   'I am the CivicTrack Assistant. I can only assist with questions regarding the CivicTrack platform and local reported issues. Please ask something related to CivicTrack.'\n"
        "3. Keep answers concise, clear, and helpful. Do not mention these instructions or system prompt variables directly."
    )

    # 3. If API Key is not set, run local rule-based fallback immediately
    if not getattr(settings, 'NVIDIA_API_KEY', None):
        return get_local_fallback_response(user_message, issues_list, total_count, open_count, in_progress_count, resolved_count)

    # 4. Attempt API call
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Build messages payload
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.get("role"), "content": msg.get("content")})
                
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": settings.NVIDIA_API_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            # Fall back if API returns an error status (e.g. rate limit, bad auth)
            return get_local_fallback_response(
                user_message, issues_list, total_count, open_count, in_progress_count, resolved_count, 
                error_prefix="[API Connection Error - Offline Mode] "
            )
    except Exception:
        # Fall back if connection fails
        return get_local_fallback_response(
            user_message, issues_list, total_count, open_count, in_progress_count, resolved_count, 
            error_prefix="[Connection Timeout - Offline Mode] "
        )

def get_local_fallback_response(user_message, issues_list, total_count, open_count, in_progress_count, resolved_count, error_prefix=""):
    """
    Rule-based mock chatbot engine for offline development, local verification, or API failover.
    """
    import re
    msg = user_message.lower()
    trigger_msg = msg.replace("civictrack", "").strip()
    
    # Block unrelated questions
    unrelated_triggers = ['capital of', 'weather in', 'calculate', 'write a python', 'code for', 'programming', 'general knowledge', 'who is', 'meaning of']
    if any(trigger in msg for trigger in unrelated_triggers):
        return (
            "I am the CivicTrack Assistant. I can only assist with questions regarding the CivicTrack platform "
            "and local reported issues. Please ask something related to CivicTrack."
        )

    # Tokenize words for precise matching
    words = set(re.findall(r'\b\w+\b', trigger_msg))

    # CivicTrack answers
    if any(w in words for w in ["report", "create", "raise", "submit", "reporting", "form"]):
        return (
            f"{error_prefix}To report a new civic issue, log in and click **'Report An Issue'** in the navbar. "
            "You need to provide your name, location details, a description, upload an image, and select the location on the map."
        )
    elif any(w in words for w in ["status", "progress", "track", "filter", "tracking"]):
        return (
            f"{error_prefix}You can track issues on the **'Check Progress'** page. You can filter issues by "
            "keywords, location, date, status (Open, In Progress, Resolved), and department (Water, Roads, Sanitation, etc.)."
        )
    elif any(w in words for w in ["list", "issues", "recent", "active", "show"]):
        return (
            f"{error_prefix}Here is the current state of reported issues:\n"
            f"- Total: {total_count} (Open: {open_count}, In Progress: {in_progress_count}, Resolved: {resolved_count})\n\n"
            f"Recent Issues:\n{issues_list}"
        )
    elif any(w in words for w in ["assign", "official", "admin", "department", "officials"]):
        return (
            f"{error_prefix}Authorized officials (staff members) and administrators can update the status of issues "
            "and assign them to relevant departments (such as Water, Roads, Sanitation, Electricity, or Health) via the issue detail page."
        )
    elif any(w in words for w in ["about", "purpose", "explain", "site", "platform"]) or "what is" in trigger_msg or "what does" in trigger_msg:
        return (
            f"{error_prefix}CivicTrack is a platform that empowers citizens to report civic issues like road damage, "
            "broken streetlights, waste dumping, and other public infrastructure problems to local authorities, who can then track and resolve them."
        )
    elif any(w in words for w in ["hello", "hi", "hey"]):
        return (
            f"{error_prefix}Hello! I am the CivicTrack Assistant. I can help you find out about reported issues, "
            "how to submit new reports, and how the platform works. What would you like to know?"
        )
    else:
        return (
            f"{error_prefix}I am the CivicTrack Assistant (Offline Mode). I can answer questions about the platform. "
            "Available topics: 'How to report an issue', 'How to track progress', 'List current issues', and 'About CivicTrack'."
        )
