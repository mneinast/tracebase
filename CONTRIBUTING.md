# Contributing to the TraceBase project

This document described the basics of how to set up the TraceBase Project Repo
in order to start developing/contributing.

## Getting Started

### Install Python and Postgres Dependencies

#### Python

Install the latest Python (version 3.9.1), and make sure it is in your path:

    $ python --version
    Python 3.9.1

Test to make sure that the `python` command now shows your latest python install:

    $ python --version
    Python 3.9.1

#### Postgres

Install Postgres via package installer from
[https://www.postgresql.org](https://www.postgresql.org).  Be sure to make note
of where it installs the `psql` command-line utility, so you can add it to your
PATH, e.g. if you see:

    Command Line Tools Installation Directory: /Library/PostgreSQL/13

Then, add this to your PATH:

    /Library/PostgreSQL/13/bin

Configuration:

    Username: postgres
    Password: tracebase
    Port: 5432

In the Postgres app interface, you can find where the `postgresql.conf` file is
located.  Open it in a text editor and make sure these settings are uncommented
& correct:

    client_encoding: 'UTF8'
    default_transaction_isolation: 'read committed'
    log_timezone = 'America/New_York'

Manually create the tracebase database (`tracebase`) in postgres:

    createdb -U postgres tracebase

Optional: Manually create the validation database (`tracebase_validation`) in
postgres (to allow users to validate their load file submissions):

    createdb -U postgres tracebase_validation

Note that subsequent commands in this doc that reference tracebase_validation
or `--database validation` are conditionally required based on your election to
perform the step above.

Create a tracebase postgres user:

    > create user tracebase with encrypted password 'mypass';
    > ALTER USER tracebase CREATEDB;
    > grant all privileges on database tracebase to tracebase;

### Setup the TraceBase project

#### Clone the repository

    git clone https://github.com/Princeton-LSI-ResearchComputing/tracebase.git
    cd tracebase

#### Create a virtual environment

Create a virtual environment (from a bash shell) and activate it, for example:

    python3 -m venv .venv
    source .venv/bin/activate

Install Django and psycopg2 dependencies as well as linters and other
development related tools. Use `requirements/prod.txt` for production
dependencies.

    python -m pip install -U pip  # Upgrade pip
    python -m pip install -r requirements/dev.txt  # Install requirements

#### Verify Installations

Django:

    python
    > import django
    > print(django.get_version())
    3.2.4

### Configure TraceBase

Create a new secret:

    python -c "import secrets; print(secrets.token_urlsafe())"

Database and secret key information should not be stored directly in settings
that are published to the repository.  We use environment variables to store
configuration data.  This makes it possible to easily change between
environments of a deployed application (see [The Twelve-Factor
App](https://www.12factor.net/config)).  The .env file you create here is pre-
configured to be ignored by the repository, so do not explicitly check it in.

Copy the TraceBase environment example:

    cp TraceBase/.env.example TraceBase/.env

Update the .env file to reflect the new secret key and the database credentials
you used when setting up Postgres.

Set up the project's postgres databases:

    python manage.py migrate
    python manage.py createcachetable

    python manage.py migrate --database validation
    python manage.py createcachetable --database validation

### (Optional) Load Some Example Data

    python manage.py load_compounds --compounds DataRepo/example_data/consolidated_tracebase_compound_list.tsv
    python manage.py load_study DataRepo/example_data/tissues/loading.yaml
    python manage.py load_animals_and_samples --sample-table-filename DataRepo/example_data/obob_samples_table.tsv --animal-table-filename DataRepo/example_data/obob_animals_table.tsv --table-headers DataRepo/example_data/sample_and_animal_tables_headers.yaml
    python manage.py load_accucor_msruns --protocol Default --accucor-file DataRepo/example_data/obob_maven_6eaas_inf.xlsx --date 2021-04-29 --researcher "Anon" --new-researcher

### Start TraceBase

Make sure the project's postgres database is current:

    python manage.py migrate
    python manage.py migrate --database validation

Note that the the default migrations must be done in order to migrate the
validation database.

Verify you can run the development server.  Run:

    python manage.py runserver

Then go to this site in your web browser:

    http://127.0.0.1:8000/

### Create an Admin User

To be able to access the admin page, on the command-line, run:

    python manage.py createsuperuser

and supply your desired account credentials for testing.

## Pull Requests

### Code Formatting Standards

All pull requests must pass linting prior to being merged.

Currently, all pushes are linted using [GitHub's
Super-Linter](https://github.com/github/super-linter). The configuration files
for the most used linters have been setup in the project root to facilitate
linting on developers machines. These include:

* [Markdown-lint](https://github.com/igorshubovych/markdownlint-cli#readme) - `.markdown-lint.yml`
* [Flake8](https://flake8.pycqa.org/en/latest/) - `.flake8`
* [Pylint](https://www.pylint.org/) - `.python-lint` -> `.pylintrc`
* [isort](https://pycqa.github.io/isort/) - `.isort.cfg`

#### Linting

Linting for this project runs automatically on GitHub when a PR is submitted,
but this section describes how to lint your changes locally.

##### Individual linters

For the most commonly used linters (*e.g.* for python, HTML, and markdown
files) it is recommended to install linters locally and run them in your
editor. Some linters that may be useful to install locally include:

* Python
  * [Flake8](https://flake8.pycqa.org/en/latest/) - python style checker
  * [Pylint](https://www.pylint.org/) - python code analysis
  * [Black](https://black.readthedocs.io/en/stable/) - code formatter
  * [isort](https://pycqa.github.io/isort/) - sort imports
  * [mypy](https://mypy.readthedocs.io/) - static type checker
* HTML
  * [HTMLHint](https://htmlhint.com/) - static analysis for HTML
* Markdown
  * [Markdown-lint](https://github.com/igorshubovych/markdownlint-cli#readme)
    \- style checker for Markdown
* General
  * [jscpd](https://github.com/kucherenko/jscpd) - Copy/paste detector for
    programming source code
  * [standard](https://standardjs.com) - JavaScript linting
  * [editorconfig-checker](https://www.npmjs.com/package/editorconfig-checker)
    \- Config linting
  * [stylelint](https://stylelint.io) - CSS linting

It is recommended to run superlinter (described below) routinely or
automatically before submitting a PR, but if you want a quick check while
developing, you can run these example linting commands on the command-line:

    black --exclude 'migrations|.venv' .
    isort --skip migrations --skip .venv .
    markdownlint .
    flake8 .
    pylint -d E1101 TraceBase DataRepo *.py
    mypy .
    dotenv-linter TraceBase DataRepo
    find . \( ! -iname "*bootstrap*" -not -path '*/\.*' -iname "*.js" \) \
        -exec standard --fix --verbose {} \;
    find . \( -type f -not -path '*/\.*' -not -path "*bootstrap*" \
        -not -path "*__pycache__*" \) -exec jscpd {} \;
    find . \( -type f -not -path '*/\.*' -not -path "*bootstrap*" \
        -not -path "*__pycache__*" \) -exec editorconfig-checker {} \;
    npx stylelint **/*.css

##### Superlinter

In addition to linting files as you write them, developers may wish to [run
Superlinter on the entire repository
locally](https://github.com/github/super-linter/blob/master/docs/run-linter-locally.md).
This is most easily accomplished using [Docker](https://docs.docker.com/get-docker/)].
Create a script outside of the repository that runs superlinter via docker and run it
from the repository root directory. Example script:

    #!/usr/bin/env sh
    docker pull github/super-linter:slim-v4

    docker run \
        -e FILTER_REGEX_EXCLUDE="(\.pylintrc|migrations|static\/bootstrap.*)" \
        -e LINTER_RULES_PATH="/" \
        -e IGNORE_GITIGNORED_FILES=true \
        -e RUN_LOCAL=true \
        -v /full/path/to/tracebase/:/tmp/lint github/super-linter

Note: The options `FILTER_REGEX_EXCLUDE`, `LINTER_RULES_PATH`, and
`IGNORE_GITIGNORED_FILES` should match the settings in the GitHub Action in
`.github/workflows/superlinter.yml`

### Testing

#### Test Implementation

All pull requests must implement tests of the changes implemented prior to being
merged.  Each app should either contain `tests.py` or a `tests` directory
containing multiple test scripts.  Currently, all tests are implemented using
the TestCase framework.

See these resources for help implementing tests:

* [Testing in Django (Part 1) - Best Practices and
  Examples](https://realpython.com/testing-in-django-part-1-best-practices-and-examples/)
* [Django Tutorial Part 10: Testing a Django web
  application](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Testing)

All pull requests must pass all previous and new tests:

    python manage.py test

#### Quality Control

All pull requests must pass new and all previous tests before merging.  Run the
following locally before submitting a pull request:

    python manage.py test

### Model Updates

Any pull requests that include changes to the model, must include an update to
the migrations and the resulting auto-generated migration scripts must be
checked in.

#### Migration Process

Create the migration scripts:

    python manage.py makemigrations

Check for unapplied migrations:

    python manage.py showmigrations

Apply migrations to the postgres database:

    python manage.py migrate
