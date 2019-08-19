# Squire
A re-introduction of the web application for ESRG Knights of the Kitchen Table.

## Getting started with development

1. Install the latest version of Python 3. If you are on Windows, you can download Python from [python.org]. If you are not, check if you already have a recent version by runnning `python3 --version`. As of writing, Python 3.5 or higher is recent enough, but this may change in the future.
1. Clone this git repository using Git, preferably to a location without spaces or other non-alphanumerical characters in it. Having spaces or other non-alphanumerical characters in the path can cause strange issues later down the road.
1. Start a command prompt/terminal in the folder you have put the Squire sources in. Use this terminal to execute the rest of the commands (in order)
1. Create a new virtual environment. On Windows, this can be done by running `py -3 -m venv venv`. On other operating systems this is done by running `python3 -m venv venv`. This ensures that this project's dependencies don't conflict with other Python applications on your system.
1. Activate your virtual environment by running `venv\Scripts\activate` if you are on Windows. Otherwise run `source venv/bin/activate`. If this is successful, your terminal line will start with `(venv)`. We assume that any commands ran beyond this point are ran inside a virtualenv for this project. This step needs to be done for each terminal you are using for this project, so if you later return to continue working on the program, you need to rerun this command.
1. Install the dependencies: `pip install -r requirements/dev.txt`. These dependencies include common dependencies (such as *Django*) as well as dev-dependencies that speed up or ease the development process (such as *coverage.py*). For more information about dependencies, view the *Dependencies* section below.
1. Setup the database by running `python manage.py migrate`. This ensures your database can store the items we expect to store in it.
1. Start the server: `python manage.py runserver`. This starts a web server, which you can access using your webbrowser and going to `localhost:8000`.
<br/><br/>

## Dependencies
Because we haven't got all year, we use some dependencies to help speed up the development process. These dependencies, called dev-dependencies, will however not be used in a production environment (as they are only used for development). Likewise, prod-dependencies can exist as well: dependencies that are needed in production but not during development. Lastly, there are some dependencies (such as *Django*) that are needed in *any* environment. These are called common-dependencies.

In order to keep things clear and to make it easier to use, these requirements are split into different files:
- `requirements/common.txt`: Contains common requirements. I.e. those that are needed for any environment.
- `requirements/dev.txt`: Contains development requirements. I.e. those that are needed during development. Automatically includes the common requirements.
- `requirements/prod.txt`: Contains production requirements. I.e. those that are needed during production. Automatically includes the common requirements.
- `requirements.txt`: Shorthand for `requirements/prod.txt`. Necessary since some services (such as *GitHub's Dependency Graph*) look for files with this specific name.

## Testing!
### Creating Tests
Django automatically recognises test files of the format *<python_app>/tests.py*. Each test case is described using Django's TestCase class, which can be imported using `from django.test import TestCase`.

More information on Django Testcases can be accessed online at the [Django Documentation](https://docs.djangoproject.com/en/2.2/topics/testing/).

NB: It is important to **not** use the *unittest.TestCase* class!
<br/><br/>

### Testing Tool
Squire makes use of *Coverage.py*. As taken from their [website](https://coverage.readthedocs.io/en/v4.5.x/), "*Coverage.py is a tool for measuring code coverage of Python programs. It monitors your program, noting which parts of the code have been executed, then analyzes the source to identify code that could have been executed but was not.*"
*Coverage.py* also provides nice functionality to visualise code coverage.
<br/><br/>

### Running Tests
Running tests can be done using the following command:
```coverage run manage.py test```.

Obtaining the coverage report in the command line can then be done using:
```coverage report```.

Alternatively, the following command can be used to obtain the coverage report in HTML-format:
```coverage html```.

NB: If an error occurs before the tests are run, then make sure you have created a */coverage*-folder in the root of the repository. Also make sure you've actually installed the *coverage.py* package by calling `pip install -r requirements/dev.txt`\
NB: You'll need to re-run the first command each time you make a change to your source code or test file in order to obtain an up-to-date coverage report.
<br/><br/>


### Ignoring Files
In order to exclude files that do not need to be tested (and show up in the coverage report), you'll need to edit *.coveragerc* in the root of the repository. Even though the file has no extension, it should be in a *.ini* file format. More information on this configuration file can be accessed online at *coverage.py*'s [website](https://coverage.readthedocs.io/en/v4.5.x/config.html).

NB: Only files with a *.py* extension are tested by default.
<br/><br/>