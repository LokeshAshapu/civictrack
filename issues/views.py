from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.paginator import Paginator

from .models import CivicIssue
from .forms import CivicIssueForm


from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def civictrack_form(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location')
        issue_details = request.POST.get('issue_details')
        image = request.FILES.get('image')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Convert lat/lng to float if present
        if latitude:
            try:
                latitude = float(latitude)
            except ValueError:
                latitude = None
        if longitude:
            try:
                longitude = float(longitude)
            except ValueError:
                longitude = None
        
        CivicIssue.objects.create(
            name=name, 
            origin_location=location, 
            issue_details=issue_details, 
            uploaded_image=image,
            user=request.user,
            latitude=latitude,
            longitude=longitude
        )
        return redirect('home')
    return render(request, 'raise_an_issue.html')

@login_required
def home(request):
    civic_details = CivicIssue.objects.all()
    return render(request, 'home.html', {
        'civic_details': civic_details,
        'is_admin': request.user.is_superuser,
        'is_authority': request.user.is_staff,
    })

@login_required
def update(request, id):
    issue = get_object_or_404(CivicIssue, id=id)
    if not (issue.user == request.user or request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You don't have permission to edit this issue.")
        return redirect('home')
    if request.method == 'POST':
        name = request.POST.get('name')
        location = request.POST.get('location')
        issue_details = request.POST.get('issue_details')
        image = request.FILES.get('image')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        issue.name = name
        issue.origin_location = location
        issue.issue_details = issue_details
        if image:
            issue.uploaded_image = image
            
        # Convert lat/lng to float if present
        if latitude:
            try:
                issue.latitude = float(latitude)
            except ValueError:
                issue.latitude = None
        else:
            issue.latitude = None
            
        if longitude:
            try:
                issue.longitude = float(longitude)
            except ValueError:
                issue.longitude = None
        else:
            issue.longitude = None
            
        issue.save()
        return redirect('home')
    return render(request, 'raise_an_issue.html', {'issue': issue})


def register_view(request):
    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
        else:
            # We'll use email as username
            user = User.objects.create_user(username=email, email=email, password=password, first_name=fullname)
            user.save()
            messages.success(request, "Account created successfully! You can now login.")
            return redirect('login')
            
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        
        # 1. Try directly with username=email
        user = authenticate(request, username=email, password=password)
        
        # 2. If not authenticated, look up by email field in User database
        if user is None and email:
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
                
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid email or password.")
            
    return render(request, 'login.html')



def check_progress_view(request):
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    location = request.GET.get('location', '').strip()
    date_str = request.GET.get('date', '').strip()
    sort = request.GET.get('sort', '').strip()
    department = request.GET.get('department', '').strip()

    issues = CivicIssue.objects.all()

    # Search filter (title or details)
    if search:
        issues = issues.filter(Q(name__icontains=search) | Q(issue_details__icontains=search))
    
    # Location filter
    if location:
        issues = issues.filter(origin_location__icontains=location)
        
    # Status filter
    if status:
        issues = issues.filter(status=status)

    # Department filter
    if department:
        issues = issues.filter(assigned_department=department)
        
    # Date filter
    if date_str:
        try:
            issues = issues.filter(created_at__date=date_str)
        except (ValueError, TypeError):
            pass

    # Sorting
    if sort == 'oldest':
        issues = issues.order_by('created_at')
    elif sort == 'title':
        issues = issues.order_by('name')
    else:
        # Default to newest first
        issues = issues.order_by('-created_at')

    total_count = CivicIssue.objects.count()
    filtered_count = issues.count()

    # Pagination: 6 issues per page
    paginator = Paginator(issues, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build query params string for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()

    return render(request, 'check_progress.html', {
        'issues': page_obj,
        'search': search,
        'status': status,
        'location': location,
        'date': date_str,
        'sort': sort,
        'department': department,
        'department_choices': CivicIssue.DEPARTMENT_CHOICES,
        'total_count': total_count,
        'filtered_count': filtered_count,
        'query_string': query_string,
    })

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def delete_issue(request, id):
    issue = get_object_or_404(CivicIssue, id=id)
    if request.user.is_staff or request.user.is_superuser:
        issue.delete()
        messages.success(request, "Issue deleted successfully.")
    else:
        messages.error(request, "You don't have permission to delete this issue.")
    return redirect('home')

@login_required
def change_status(request, id):
    issue = get_object_or_404(CivicIssue, id=id)
    if request.user.is_staff or request.user.is_superuser:
        new_status = request.POST.get('status', 'Open')
        new_dept = request.POST.get('department', 'Other')
        
        if new_status not in ['Open', 'In Progress', 'Resolved']:
            messages.error(request, "Invalid status value.")
            return redirect('check_progress')
            
        valid_depts = [code for code, name in CivicIssue.DEPARTMENT_CHOICES]
        if new_dept not in valid_depts:
            messages.error(request, "Invalid department selection.")
            return redirect('check_progress')
            
        status_changed = (issue.status != new_status)
        dept_changed = (issue.assigned_department != new_dept)
        
        if status_changed or dept_changed:
            old_status = issue.status
            issue.status = new_status
            issue.assigned_department = new_dept
            issue.save()
            
            success_msg = []
            if status_changed:
                success_msg.append(f"Status updated to '{new_status}'")
            if dept_changed:
                dept_name = dict(CivicIssue.DEPARTMENT_CHOICES).get(new_dept, new_dept)
                success_msg.append(f"Assigned to department '{dept_name}'")
            
            messages.success(request, ", ".join(success_msg) + ".")
            
            # Send email notification if status changed and user has email
            if status_changed and issue.user and issue.user.email:
                subject = f"[CivicTrack] Status Update: {issue.name}"
                message = (
                    f"Hello {issue.user.first_name or 'Citizen'},\n\n"
                    f"The status of your reported issue '{issue.name}' has been updated.\n\n"
                    f"Old Status: {old_status}\n"
                    f"New Status: {new_status}\n\n"
                    f"You can view the details here: {request.build_absolute_uri(f'/issue/{issue.id}/')}\n\n"
                    f"Thank you for using CivicTrack!\n"
                    f"CivicTrack Team"
                )
                
                # HTML Card Styled Notification
                detail_url = request.build_absolute_uri(f'/issue/{issue.id}/')
                
                def get_status_color(status_val):
                    if status_val == 'Resolved':
                        return '#16a34a' # green
                    elif status_val == 'In Progress':
                        return '#ca8a04' # amber/dark yellow
                    return '#2563eb' # blue (Open)
                
                old_color = get_status_color(old_status)
                new_color = get_status_color(new_status)
                
                html_message = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Status Update</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f3f4f6; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 550px; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05); overflow: hidden; border-collapse: separate;">
                    <tr>
                        <td align="center" style="background: linear-gradient(135deg, #0d3b73, #072142); padding: 30px 20px; border-top-left-radius: 16px; border-top-right-radius: 16px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td align="center" style="color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: 0.5px;">
                                        CivicTrack
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="color: #93c5fd; font-size: 14px; font-weight: 500; margin-top: 5px; opacity: 0.9;">
                                        Issue Progress Tracker
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 35px; background-color: #ffffff;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td style="font-size: 18px; font-weight: 700; color: #1f2937; margin-bottom: 15px; display: block;">
                                        Status Update
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 15px; line-height: 1.6; color: #4b5563; margin-bottom: 25px; display: block;">
                                        Hello {issue.user.first_name or 'Citizen'},<br><br>
                                        The status of your reported issue <strong>'{issue.name}'</strong> has been updated.
                                    </td>
                                </tr>
                                
                                <!-- Status Grid Info Card -->
                                <tr>
                                    <td style="background-color: #f9fafb; border: 1px solid #f3f4f6; border-radius: 12px; padding: 20px; margin-bottom: 30px; display: block;">
                                        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td width="50%" style="font-size: 13px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; padding-bottom: 5px;">
                                                    Previous Status
                                                </td>
                                                <td width="50%" style="font-size: 13px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; padding-bottom: 5px;">
                                                    Current Status
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="font-size: 16px; color: {old_color}; font-weight: 700; padding-top: 2px;">
                                                    {old_status}
                                                </td>
                                                <td style="font-size: 16px; color: {new_color}; font-weight: 700; padding-top: 2px;">
                                                    {new_status}
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- CTA Button -->
                                <tr>
                                    <td align="center" style="padding: 10px 0 25px 0;">
                                        <a href="{detail_url}" 
                                           style="display: inline-block; background-color: #0d3b73; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; padding: 14px 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(13, 59, 115, 0.15);">
                                            View Report Details
                                        </a>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="border-top: 1px solid #f3f4f6; padding-top: 25px; font-size: 14px; color: #4b5563; line-height: 1.5;">
                                        Thank you for contributing to your neighborhood,<br>
                                        <strong>The CivicTrack Team</strong>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="background-color: #f9fafb; padding: 25px 20px; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px; border-top: 1px solid #f3f4f6;">
                            <p style="margin: 0; font-size: 12px; color: #9ca3af; font-weight: 500;">
                                &copy; CivicTrack &bull; Real-time Citizen Feedback
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
                
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject,
                        message,
                        'noreply@civictrack.gov',
                        [issue.user.email],
                        fail_silently=True,
                        html_message=html_message,
                    )
                except Exception as e:
                    pass
        else:
            messages.info(request, "No changes were made.")
    else:
        messages.error(request, "You don't have permission to modify this issue.")
    
    # Redirect back to referring page or progress list
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('check_progress')

def issue_detail(request, id):
    issue = get_object_or_404(CivicIssue, id=id)
    return render(request, 'issue_detail.html', {
        'issue': issue,
        'department_choices': CivicIssue.DEPARTMENT_CHOICES
    })

@login_required
def upvote_issue(request, id):
    issue = get_object_or_404(CivicIssue, id=id)
    if request.method == 'POST':
        if request.user in issue.votes.all():
            issue.votes.remove(request.user)
            messages.success(request, "Upvote removed.")
        else:
            issue.votes.add(request.user)
            messages.success(request, "Issue upvoted successfully!")
    return redirect('issue_detail', id=id)

@login_required
def add_comment(request, id):
    issue = get_object_or_404(CivicIssue, id=id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            from .models import Comment
            Comment.objects.create(
                issue=issue,
                user=request.user,
                content=content
            )
            messages.success(request, "Comment posted successfully.")
        else:
            messages.error(request, "Comment content cannot be empty.")
    return redirect('issue_detail', id=id)


def terms_of_service_view(request):
    return render(request, 'terms_of_service.html')

def privacy_policy_view(request):
    return render(request, 'privacy_policy.html')

def imprint_view(request):
    return render(request, 'imprint.html')

def map_view(request):
    """Display interactive map with all reported issues"""
    issues = CivicIssue.objects.filter(latitude__isnull=False, longitude__isnull=False)
    return render(request, 'map.html', {'issues': issues})

@require_http_methods(["GET"])
def map_data_json(request):
    """API endpoint to get issues as JSON for map markers"""
    status = request.GET.get('status', None)
    
    issues = CivicIssue.objects.filter(latitude__isnull=False, longitude__isnull=False)
    
    if status:
        issues = issues.filter(status=status)
    
    issues_data = []
    for issue in issues:
        issues_data.append({
            'id': issue.id,
            'name': issue.name,
            'location': issue.origin_location,
            'details': issue.issue_details[:100] + '...' if len(issue.issue_details) > 100 else issue.issue_details,
            'status': issue.status,
            'latitude': float(issue.latitude),
            'longitude': float(issue.longitude),
            'created_at': issue.created_at.strftime('%Y-%m-%d %H:%M'),
            'image_url': issue.uploaded_image.url if issue.uploaded_image else None,
            'user': issue.user.first_name if issue.user else 'Anonymous'
        })
    
    return JsonResponse({'issues': issues_data})

def contact_submit_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        topic = request.POST.get('topic', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not email or not topic or not message:
            messages.error(request, "All fields are required.")
        else:
            subject = f"[CivicTrack Contact Form] {topic}"
            body = f"Sender Email: {email}\nTopic: {topic}\n\nMessage:\n{message}"
            
            # HTML Card Format message
            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Form Submission</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f3f4f6; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 550px; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05); overflow: hidden; border-collapse: separate;">
                    <tr>
                        <td align="center" style="background: linear-gradient(135deg, #0d3b73, #072142); padding: 30px 20px; border-top-left-radius: 16px; border-top-right-radius: 16px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td align="center" style="color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: 0.5px;">
                                        CivicTrack
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="color: #93c5fd; font-size: 14px; font-weight: 500; margin-top: 5px; opacity: 0.9;">
                                        Admin Notification
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 35px; background-color: #ffffff;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td style="font-size: 18px; font-weight: 700; color: #1f2937; margin-bottom: 20px; display: block;">
                                        New Contact Form Inquiry
                                    </td>
                                </tr>
                                
                                <!-- Metadata Box -->
                                <tr>
                                    <td style="background-color: #f9fafb; border: 1px solid #f3f4f6; border-radius: 12px; padding: 20px; margin-bottom: 25px; display: block;">
                                        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td style="font-size: 13px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                                    Sender Email
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="font-size: 14px; color: #1f2937; font-weight: 500; padding-top: 3px; padding-bottom: 15px;">
                                                    {email}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="font-size: 13px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                                    Topic
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="font-size: 14px; color: #1f2937; font-weight: 500; padding-top: 3px;">
                                                    {topic}
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Message Box -->
                                <tr>
                                    <td style="font-size: 13px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; display: block;">
                                        Message
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size: 15px; line-height: 1.6; color: #374151; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 15px; min-height: 100px; display: block; white-space: pre-wrap;">
                                        {message}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="background-color: #f9fafb; padding: 25px 20px; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px; border-top: 1px solid #f3f4f6;">
                            <p style="margin: 0; font-size: 12px; color: #9ca3af; font-weight: 500;">
                                CivicTrack Operations &bull; Automated System
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
            
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject,
                    body,
                    'noreply@civictrack.gov',
                    ['lokeshashapu@gmail.com'],
                    fail_silently=False,
                    html_message=html_body,
                )
            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")
                
    return redirect('/#Contact')


import json
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            history = data.get('history', [])
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
        from .chatbot import get_chatbot_response
        response_text = get_chatbot_response(user_message, conversation_history=history)
        return JsonResponse({'response': response_text})
        
    return JsonResponse({'error': 'Method not allowed'}, status=405)

