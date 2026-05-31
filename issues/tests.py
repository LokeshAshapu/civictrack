import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from .models import CivicIssue, Comment

class CivicTrackViewsTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testcitizen@example.com', email='testcitizen@example.com', password='testpassword', first_name='Test')
        self.admin = User.objects.create_superuser(username='admin@example.com', email='admin@example.com', password='adminpassword')
        
        # Create a test issue
        self.issue = CivicIssue.objects.create(
            name="Broken Pothole",
            origin_location="Main Street",
            issue_details="Large pothole on the main crossing.",
            uploaded_image="download_4.jpeg",  # dummy filename
            user=self.user,
            latitude=40.7128,
            longitude=-74.0060
        )
        
        self.client = Client()

    def test_issue_detail_view(self):
        url = reverse('issue_detail', args=[self.issue.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Broken Pothole")
        self.assertContains(response, "Large pothole on the main crossing.")

    def test_issue_detail_view_no_user(self):
        # Create an issue with user=None
        issue_no_user = CivicIssue.objects.create(
            name="Anonymous Issue",
            origin_location="Highway 1",
            issue_details="Debris on road.",
            uploaded_image="download_4.jpeg",
            user=None,
            latitude=40.7128,
            longitude=-74.0060
        )
        url = reverse('issue_detail', args=[issue_no_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anonymous Issue")
        self.assertContains(response, "Anonymous")

    def test_upvote_issue_requires_login(self):
        url = reverse('upvote_issue', args=[self.issue.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_upvote_issue_toggle(self):
        self.client.login(username='testcitizen@example.com', password='testpassword')
        url = reverse('upvote_issue', args=[self.issue.id])
        
        # First upvote
        response = self.client.post(url)
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        self.assertEqual(self.issue.votes.count(), 1)
        self.assertIn(self.user, self.issue.votes.all())
        
        # Toggle upvote (remove it)
        response = self.client.post(url)
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        self.assertEqual(self.issue.votes.count(), 0)

    def test_add_comment_requires_login(self):
        url = reverse('add_comment', args=[self.issue.id])
        response = self.client.post(url, {'content': 'This is a test comment'})
        self.assertEqual(response.status_code, 302)

    def test_add_comment(self):
        self.client.login(username='testcitizen@example.com', password='testpassword')
        url = reverse('add_comment', args=[self.issue.id])
        
        response = self.client.post(url, {'content': 'This is a test comment'})
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.content, 'This is a test comment')
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.issue, self.issue)

    def test_change_status_sends_email(self):
        self.client.login(username='admin@example.com', password='adminpassword')
        url = reverse('change_status', args=[self.issue.id])
        
        # Clear outbox
        mail.outbox = []
        
        # Change status from Open to In Progress
        response = self.client.post(url, {'status': 'In Progress'}, HTTP_REFERER=reverse('issue_detail', args=[self.issue.id]))
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, 'In Progress')
        
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f"[CivicTrack] Status Update: {self.issue.name}")
        self.assertIn("In Progress", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['testcitizen@example.com'])

    def test_contact_submit_success(self):
        url = reverse('contact_submit')
        mail.outbox = []
        response = self.client.post(url, {
            'email': 'sender@example.com',
            'topic': 'Pothole request',
            'message': 'Please fix the pothole at 5th avenue.'
        })
        self.assertRedirects(response, '/#Contact', fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[CivicTrack Contact Form] Pothole request")
        self.assertEqual(mail.outbox[0].to, ['lokeshashapu@gmail.com'])
        self.assertIn("sender@example.com", mail.outbox[0].body)
        self.assertIn("Please fix the pothole at 5th avenue.", mail.outbox[0].body)

    def test_contact_submit_missing_fields(self):
        url = reverse('contact_submit')
        mail.outbox = []
        response = self.client.post(url, {
            'email': '',
            'topic': 'Pothole request',
            'message': 'Please fix.'
        })
        self.assertRedirects(response, '/#Contact', fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_login_fallback_email(self):
        # Create user with custom username 'superuser_custom' but email 'custom_super@example.com'
        User.objects.create_superuser(username='superuser_custom', email='custom_super@example.com', password='superpassword')
        
        # Now try to log in using their email 'custom_super@example.com' in the email field
        login_url = reverse('login')
        response = self.client.post(login_url, {
            'email': 'custom_super@example.com',
            'password': 'superpassword'
        })
        self.assertRedirects(response, reverse('home'))

    def test_edit_issue_owner_success(self):
        self.client.login(username='testcitizen@example.com', password='testpassword')
        url = reverse('update', args=[self.issue.id])
        
        # Get the update page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Broken Pothole")
        
        # Post the update
        data = {
            'name': 'Updated Broken Pothole',
            'location': 'New Street Location',
            'issue_details': 'Updated details of the pothole.',
            'latitude': 41.1234,
            'longitude': -75.5678,
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('home'))
        
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.name, 'Updated Broken Pothole')
        self.assertEqual(self.issue.origin_location, 'New Street Location')
        self.assertEqual(self.issue.issue_details, 'Updated details of the pothole.')
        self.assertEqual(self.issue.latitude, 41.1234)
        self.assertEqual(self.issue.longitude, -75.5678)
        # Should retain original image
        self.assertEqual(self.issue.uploaded_image, "download_4.jpeg")

    def test_edit_issue_owner_with_image(self):
        self.client.login(username='testcitizen@example.com', password='testpassword')
        url = reverse('update', args=[self.issue.id])
        
        # Create a dummy image
        from django.core.files.uploadedfile import SimpleUploadedFile
        new_image = SimpleUploadedFile("new_image.jpeg", b"file_content", content_type="image/jpeg")
        
        data = {
            'name': 'Updated Broken Pothole with Image',
            'location': 'Main Street',
            'issue_details': 'Large pothole details.',
            'image': new_image,
            'latitude': 40.7128,
            'longitude': -74.0060
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('home'))
        
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.name, 'Updated Broken Pothole with Image')
        self.assertIn('new_image', self.issue.uploaded_image.name)

    def test_edit_issue_unauthorized_user(self):
        # Create another citizen
        other_user = User.objects.create_user(username='other@example.com', email='other@example.com', password='otherpassword')
        self.client.login(username='other@example.com', password='otherpassword')
        
        url = reverse('update', args=[self.issue.id])
        data = {
            'name': 'Hacked Pothole',
            'location': 'Hacked Street',
            'issue_details': 'Hacked details.',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('home'))
        
        # Verify it did not change in database
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.name, "Broken Pothole")

    def test_edit_issue_admin_success(self):
        # Log in as admin
        self.client.login(username='admin@example.com', password='adminpassword')
        url = reverse('update', args=[self.issue.id])
        
        data = {
            'name': 'Admin Updated Pothole',
            'location': 'Main Street',
            'issue_details': 'Large pothole on the main crossing updated by admin.',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('home'))
        
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.name, 'Admin Updated Pothole')

    def test_assign_department_by_official(self):
        # Log in as admin (staff)
        self.client.login(username='admin@example.com', password='adminpassword')
        url = reverse('change_status', args=[self.issue.id])
        
        # Update status and assign to Roads
        data = {
            'status': 'In Progress',
            'department': 'Roads'
        }
        response = self.client.post(url, data, HTTP_REFERER=reverse('issue_detail', args=[self.issue.id]))
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, 'In Progress')
        self.assertEqual(self.issue.assigned_department, 'Roads')

    def test_assign_department_by_unauthorized_user(self):
        # Log in as normal citizen
        self.client.login(username='testcitizen@example.com', password='testpassword')
        url = reverse('change_status', args=[self.issue.id])
        
        data = {
            'status': 'Resolved',
            'department': 'Water'
        }
        response = self.client.post(url, data, HTTP_REFERER=reverse('issue_detail', args=[self.issue.id]))
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        
        self.issue.refresh_from_db()
        # Verify no changes
        self.assertEqual(self.issue.status, 'Open')
        self.assertEqual(self.issue.assigned_department, 'Other')

    def test_filter_issues_by_department(self):
        # Create an issue assigned to Electricity
        electricity_issue = CivicIssue.objects.create(
            name="Broken street light",
            origin_location="Broad Street",
            issue_details="Light pole #12 is out.",
            uploaded_image="download_4.jpeg",
            user=self.user,
            assigned_department='Electricity'
        )
        url = reverse('check_progress')
        
        # Filter by Electricity
        response = self.client.get(url, {'department': 'Electricity'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Broken street light")
        self.assertNotContains(response, "Broken Pothole")
        
        # Filter by Roads
        response = self.client.get(url, {'department': 'Roads'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Broken street light")
        self.assertNotContains(response, "Broken Pothole")

    def test_edit_comment_by_author(self):
        comment = Comment.objects.create(
            issue=self.issue,
            user=self.user,
            content="Original comment"
        )
        self.client.login(username='testcitizen@example.com', password='testpassword')
        url = reverse('edit_comment', args=[comment.id])
        
        response = self.client.post(url, {'content': 'Updated comment content'})
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'Updated comment content')

    def test_edit_comment_by_non_author(self):
        comment = Comment.objects.create(
            issue=self.issue,
            user=self.user,
            content="Original comment"
        )
        self.client.login(username='admin@example.com', password='adminpassword')
        url = reverse('edit_comment', args=[comment.id])
        
        response = self.client.post(url, {'content': 'Hacked content'})
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'Original comment')

    def test_delete_comment_by_admin(self):
        comment = Comment.objects.create(
            issue=self.issue,
            user=self.user,
            content="Irrelevant comment"
        )
        self.client.login(username='admin@example.com', password='adminpassword')
        url = reverse('delete_comment', args=[comment.id])
        
        response = self.client.post(url)
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        self.assertEqual(Comment.objects.filter(id=comment.id).count(), 0)

    def test_delete_comment_by_non_admin(self):
        comment = Comment.objects.create(
            issue=self.issue,
            user=self.user,
            content="Good comment"
        )
        self.client.login(username='testcitizen@example.com', password='testpassword')
        url = reverse('delete_comment', args=[comment.id])
        
        response = self.client.post(url)
        self.assertRedirects(response, reverse('issue_detail', args=[self.issue.id]))
        self.assertEqual(Comment.objects.filter(id=comment.id).count(), 1)


class CivicTrackChatbotTestCase(TestCase):
    def setUp(self):
        from django.conf import settings
        self.client = Client()
        self.original_api_key = getattr(settings, 'NVIDIA_API_KEY', None)
        settings.NVIDIA_API_KEY = None
        
        # Create some test issues to check recent list / counts
        self.user = User.objects.create_user(username='testcitizen@example.com', email='testcitizen@example.com', password='testpassword')
        CivicIssue.objects.create(
            name="Pothole on Road",
            origin_location="Sector 4",
            issue_details="Major pothole needs fixing.",
            user=self.user,
            status='Open',
            assigned_department='Roads'
        )

    def tearDown(self):
        from django.conf import settings
        settings.NVIDIA_API_KEY = self.original_api_key

    def test_chatbot_api_invalid_method(self):
        url = reverse('chatbot_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertIn('error', data)

    def test_chatbot_api_invalid_json(self):
        url = reverse('chatbot_api')
        response = self.client.post(url, "invalid json data", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_chatbot_api_empty_message(self):
        url = reverse('chatbot_api')
        response = self.client.post(url, json.dumps({'message': ''}), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_chatbot_api_about_platform(self):
        url = reverse('chatbot_api')
        response = self.client.post(url, json.dumps({'message': 'What is CivicTrack?'}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('response', data)
        self.assertIn('CivicTrack is a platform', data['response'])

    def test_chatbot_api_list_issues(self):
        url = reverse('chatbot_api')
        response = self.client.post(url, json.dumps({'message': 'can you list the issues?'}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('response', data)
        self.assertIn('Pothole on Road', data['response'])
        self.assertIn('Total: 1', data['response'])

    def test_chatbot_api_refusal_general_query(self):
        url = reverse('chatbot_api')
        response = self.client.post(url, json.dumps({'message': 'Write a Python program to sort a list'}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('response', data)
        self.assertIn('I am the CivicTrack Assistant', data['response'])
        self.assertIn('only assist with questions regarding the CivicTrack platform', data['response'])


class CivicTrackPasswordResetTestCase(TestCase):
    def setUp(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        from django.contrib.auth.tokens import default_token_generator
        self.client = Client()
        self.user = User.objects.create_user(
            username='resetcitizen@example.com',
            email='resetcitizen@example.com',
            password='oldpassword'
        )

    def test_password_reset_form_view(self):
        url = reverse('password_reset')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'password_reset_form.html')

    def test_password_reset_post_sends_email(self):
        url = reverse('password_reset')
        mail.outbox = []
        response = self.client.post(url, {'email': 'resetcitizen@example.com'})
        # Verify it redirects to the done URL
        self.assertRedirects(response, reverse('password_reset_done'))
        # Verify email was dispatched
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[CivicTrack] Password Reset Request')
        self.assertIn('resetcitizen@example.com', mail.outbox[0].to)
        # Verify link is in email body
        self.assertIn('password-reset-confirm', mail.outbox[0].body)

    def test_password_reset_confirm_view_valid(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        from django.contrib.auth.tokens import default_token_generator
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        
        # Test GET request loads the form (following session-based redirect)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'password_reset_confirm.html')
        self.assertContains(response, 'Enter New Password')
        
        # Get the redirected session-based URL to submit the new password
        redirect_url = response.redirect_chain[0][0]

        # Test POST request to reset the password
        response = self.client.post(redirect_url, {
            'new_password1': 'newsecurepassword123',
            'new_password2': 'newsecurepassword123'
        })
        self.assertRedirects(response, reverse('password_reset_complete'))
        
        # Verify user can log in with new password
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'email': 'resetcitizen@example.com',
            'password': 'newsecurepassword123'
        })
        self.assertRedirects(login_response, reverse('home'))

    def test_password_reset_confirm_view_invalid(self):
        # Invalid uid or token
        url = reverse('password_reset_confirm', kwargs={'uidb64': 'invalid_uid', 'token': 'invalid_token'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'password_reset_confirm.html')
        self.assertContains(response, 'Invalid Link')

    def test_password_reset_complete_view(self):
        url = reverse('password_reset_complete')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'password_reset_complete.html')
        self.assertContains(response, 'Password Reset Complete!')

