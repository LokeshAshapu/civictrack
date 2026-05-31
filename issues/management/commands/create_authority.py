from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates a new authority (staff) user account'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email address of the authority user')
        parser.add_argument('--password', type=str, required=True, help='Password for the authority user')
        parser.add_argument('--name', type=str, default='', help='Full name of the authority user')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        name = options['name']

        if User.objects.filter(username=email).exists():
            self.stdout.write(self.style.ERROR(f"User with email '{email}' already exists."))
            return

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )
        user.is_staff = True
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Authority user '{email}' created successfully with staff privileges!"))
