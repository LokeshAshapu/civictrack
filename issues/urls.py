
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('submit/', views.civictrack_form, name='civic_details'),
    path('update/<int:id>/', views.update, name='update'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),

    path('logout/', views.logout_view, name='logout'),
    path('progress/', views.check_progress_view, name='check_progress'),
    path('delete/<int:id>/', views.delete_issue, name='delete_issue'),
    path('status/<int:id>/', views.change_status, name='change_status'),
    
    path('terms-of-service/', views.terms_of_service_view, name='terms_of_service'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('imprint/', views.imprint_view, name='imprint'),
    
    # Password Reset Routes
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset_form.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        html_email_template_name='password_reset_email_html.html'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Issue detail, upvote, comment routes
    path('issue/<int:id>/', views.issue_detail, name='issue_detail'),
    path('issue/<int:id>/upvote/', views.upvote_issue, name='upvote_issue'),
    path('issue/<int:id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # Map routes
    path('map/', views.map_view, name='map'),
    path('api/map-data/', views.map_data_json, name='map_data_json'),
    path('contact/', views.contact_submit_view, name='contact_submit'),
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),
]