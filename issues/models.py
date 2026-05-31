from django.db import models
from django.contrib.auth.models import User

class CivicIssue(models.Model):
    name = models.CharField(max_length=150)
    origin_location = models.CharField(max_length=255)
    issue_details = models.TextField()
    uploaded_image = models.ImageField(upload_to='civic_issues_gallery/', blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Open')
    
    # Added for Role-Based Access and Geolocation
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Voting System
    votes = models.ManyToManyField(User, related_name='voted_issues', blank=True)

    DEPARTMENT_CHOICES = [
        ('Water', 'Water Supply & Sewage'),
        ('Roads', 'Roads & Traffic'),
        ('Sanitation', 'Sanitation & Waste'),
        ('Electricity', 'Electricity & Lighting'),
        ('Health', 'Public Health & Safety'),
        ('Other', 'Other/General'),
    ]
    assigned_department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        default='Other',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.name} - {self.origin_location} ({self.status})"


class Comment(models.Model):
    issue = models.ForeignKey(CivicIssue, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.issue.name}"
