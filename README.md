# Squire
A re-introduction of the web application for ESRG Knights of the Kitchen Table.

## Getting started with development

1. Install Python 3, Pip and Virtualenv. If you are on Windows, you can download Python from [python.org]
1. Clone this git repository using Git.
1. Start a command prompt/terminal in the folder you have put the Squire sources in. Use this terminal to execute the rest of the commands (in order)
1. Create a new virtual environment: `virtualenv --python=python3 venv`. This ensures that this project's dependencies don't conflict with other Python applications.
1. Activate your virtual environment: `source venv/bin/activate`. If this is successful, your terminal line will start with `(venv)`. We assume that any commands ran beyond this point are ran inside a virtualenv for this project.
1. Install the dependencies: `pip install -r requirements.txt`. Because we haven't got all year, we use some dependencies to help speed up the process.
1. Setup the database by running `python manage.py migrate`. This ensures your database can store the items we expect to store in it.
1. Start the server: `python manage.py runserver`. This starts a web server, which you can access using your webbrowser and going to `localhost:8000`.
