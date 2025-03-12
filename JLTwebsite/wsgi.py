import os
import sys

# Add your project path
sys.path.append('/home/maxoufaya33/JLTwebsite')

# Activate the virtual environment
VENV_PATH = '/home/maxoufaya33/.virtualenvs/myvenv'
if os.path.exists(VENV_PATH):
    activate_script = os.path.join(VENV_PATH, 'bin', 'activate_this.py')
    exec(open(activate_script).read(), {'__file__': activate_script})

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'JLTwebsite.settings'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
