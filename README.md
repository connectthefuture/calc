# CALC

[![Build Status](https://travis-ci.org/18F/calc.svg?branch=develop)](https://travis-ci.org/18F/calc)
[![Code Climate](https://codeclimate.com/github/18F/calc/badges/gpa.svg)](https://codeclimate.com/github/18F/calc)
[![Test Coverage](https://codeclimate.com/github/18F/calc/badges/coverage.svg)](https://codeclimate.com/github/18F/calc/coverage)
[![Dependency Status](https://gemnasium.com/badges/github.com/18F/calc.svg)](https://gemnasium.com/github.com/18F/calc)

CALC (formerly known as "Hourglass"), which stands for Contracts Awarded Labor Category, is a tool to help contracting personnel estimate their per-hour labor costs for a contract, based on historical pricing information. The tool is live at [https://calc.gsa.gov](https://calc.gsa.gov). You can track our progress on our [trello board](https://trello.com/b/LjXJaVbZ/prices) or file an issue on this repo.

## Related repositories

* [18F/calc-analysis](https://github.com/18F/calc-analysis) contains
  data science experiments and other analyses that use CALC
  data.

## Setup

To install the requirements, use:

```sh
pip install -r requirements-dev.txt
npm install
```

CALC is a [Django] project. You can configure everything by running:

```sh
cp .env.sample .env
```

Edit the `.env` file to contain your local database configuration. Note
that you need to use postgres as a backend, since CALC uses its full-text
search functionality.

You'll also want to make sure you have a local instance of redis running,
on its default port, as we use it for CALC's task queue.

Here's some guidance on installing Redis:

* [Installing Redis on Mac OSX](https://medium.com/@petehouston/install-and-config-redis-on-mac-os-x-via-homebrew-eb8df9a4f298#.fa2s6i1my)

* [Installing Redis on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-redis-on-ubuntu-16-04)

Assuming you have Postgres installed you can create the database:

`createdb hourglass`

Now run:

```sh
./manage.py syncdb
./manage.py initgroups
```

to set up the database. After that, you can load all of the data by running:

```sh
./manage.py load_data
./manage.py load_s70
```

From there, you're just a hop, skip and a jump away from your own dev server:

```sh
./manage.py runserver
```

In another terminal, you will also need to run `gulp` to watch and rebuild static assets.
All the static assets (SASS for CSS and ES6 JavaScript) are located in the [`frontend/source/`](frontend/source/) directory. Outputs from the gulp build are placed in `frontend/static/frontend/built/`. Examine [gulpfile.js](gulpfile.js) for details of our gulp asset pipeline.

Note that if you are using our [Docker setup](#using-docker-optional), running gulp will be handled for you.

```sh
npm run gulp
```

If you just want to build the assets once without watching for changes, run

```sh
npm run gulp -- build
```

Also, in yet another terminal, you will want to run
`python manage.py rqworker` to process all the tasks in the task queue.

If you are managing https://calc.gsa.gov or any other cloud.gov-based deployment, see [`deploy.md`][].

## Testing

CALC provides a custom Django management command to run all linters and tests:

```sh
python manage.py ultratest
```

### Unit Tests
To run just unit tests:

```sh
py.test
```

For more information on running only specific tests, see
[`py.test` Usage and Invocations][pytest].

### Browser tests via Selenium

By default, CALC's browser-based tests will run via PhantomJS. This
is nice because it requires no configuration (aside from installing
PhantomJS, if you're not using the Docker setup).

However, it might also be preferable to run the browser-based tests in
a real-world browser. This can be done via Selenium/WebDriver. The
trade-off is that this requires configuration.

For details on how to do this, see [`selenium.md`](selenium.md).

### Security Scans

We use [bandit](https://github.com/openstack/bandit) for security-related static analysis.

To run bandit:

```sh
bandit -r .
```

bandit's configuration is in the [.bandit](/.bandit) file.

## Using Docker (optional)

A Docker setup potentially makes development and deployment easier.

To use it, install [Docker][] and [Docker Compose][] and read the
[18F Docker guide][] if you haven't already.

Then run:

```sh
cp .env.sample .env
ln -sf docker-compose.local.yml docker-compose.override.yml
docker-compose build
docker-compose run app python manage.py syncdb
docker-compose run app python manage.py initgroups
```

You can optionally load some data into your dockerized database with:

```sh
docker-compose run app python manage.py load_data
docker-compose run app python manage.py load_s70
```

Once the above commands are successful, run:

```sh
docker-compose up
```

This will start up all required servers in containers and output their
log information to stdout. You should be able to visit http://localhost:8000/
directly to access the site.

### Changing the exposed port

If you don't want to serve your app on port 8000, you can change
the value of `DOCKER_EXPOSED_PORT` in your `.env` file.

### Accessing the app container

You'll likely want to run `manage.py` or `py.test` to do other things at
some point. To do this, it's probably easiest to run:

```sh
docker-compose run app bash
```

This will run an interactive bash session inside the main app container.
In this container, the `/calc` directory is mapped to the root of
the repository on your host; you can run `manage.py` or `py.test` from there.

Note that if you don't have Django installed on your host system, you
can just run `python manage.py` directly from outside the container--the
`manage.py` script has been modified to run itself in a Docker container
if it detects that Django isn't installed.

### Updating the containers

All the project's dependencies, such as those mentioned in `requirements.txt`,
are contained in Docker container images.  Whenever these dependencies change,
you'll want to re-run `docker-compose build` to rebuild the containers.

### Reading email

In the development Docker configuration, we use a container with
[MailCatcher][] to make it easy to read the emails sent by the app. You
can view it at port 1080 of your Docker host.

[MailCatcher]: https://mailcatcher.me/

### Deploying to cloud environments

The Docker setup can also be used to deploy to cloud environments.

To do this, you'll first need to
[configure Docker Machine for the cloud][docker-machine-cloud],
which involves provisioning a host on a cloud provider and setting up
your local environment to make Docker's command-line tools use that
host. For example, to do this on Amazon EC2, you might use:

```
docker-machine create aws16 --driver=amazonec2 --amazonec2-instance-type=t2.large
```

Also, unlike local development, cloud deploys don't support an
`.env` file. So you'll want to create a custom
`docker-compose.override.yml` file that defines the app's
environment variables:

```yaml
app:
  environment:
    - DEBUG=yup
rq_worker:
  environment:
    - DEBUG=yup
rq_scheduler:
  environment:
    - DEBUG=yup
```

You'll also want to tell Docker Compose what port to listen on,
which can be done in the terminal by running
`export DOCKER_EXPOSED_PORT=8000`.

At this point, you can use Docker's command-line tools, such as
`docker-compose up`, and your actions will take effect on the remote
host instead of your local machine.

**Note:** Docker Machine's cloud drivers intentionally don't support
folder sharing, which means that you can't just edit a file on
your local system and see the changes instantly on the remote host.
Instead, your app's source code is part of the container image,
which means that every time you make a source code change, you will
need to re-run `docker-compose build`.

## Environment Variables

Unlike traditional Django settings, we use environment variables
for configuration to be compliant with [twelve-factor][] apps.

You can define environment variables using your environment, or
(if you're developing locally) an `.env` file in the root directory
of the repository. For more information on configuring
environment variables on cloud.gov, see [`deploy.md`][].

**Note:** When an environment variable is described as representing a
boolean value, if the variable exists with *any* value (even the empty
string), the boolean is true; otherwise, it's false.

* `DEBUG` is a boolean value that indicates whether debugging is enabled
  (this should always be false in production).

* `HIDE_DEBUG_UI` is a boolean value that indicates whether to hide
  various development and debugging affordances in the UI, such as the
  [Django Debug Toolbar][]. This can be useful when demoing or user testing
  a debug build.

* `SECRET_KEY` is a large random value corresponding to Django's
  [`SECRET_KEY`][] setting. It is automatically set to a known, insecure
  value when `DEBUG` is true.

* `DATABASE_URL` is the URL for the database, as per the
  [DJ-Database-URL schema][].

* `EMAIL_URL` is the URL for the service to use when sending
  email, as per the [dj-email-url schema][]. When `DEBUG` is true,
  this defaults to `console:`. If it is set to `dummy:` then no emails will
  be sent and messages about email notifications will not be shown to users.
  The setting can easily be manually tested via the `manage.py sendtestemail`
  command.

* `DEFAULT_FROM_EMAIL` is the email from-address to use in all system
  generated emails to users. It corresponds to Django's [`DEFAULT_FROM_EMAIL`][]
  setting. It defaults to `noreply@localhost` when `DEBUG=True`.

* `SERVER_EMAIL` is the email from-address to use in all system generated
  emails to managers and admins. It corresponds to Django's [`SERVER_EMAIL`][]
  setting. It defaults to `system@localhost` when `DEBUG=True`.

* `HELP_EMAIL` is the email  used as the reply-to address in system
  generated emails to users. It is also the email address used in the site
  footer and for other contact purposes. It should refer to an inbox that is
  monitored. If not set, it will use the same value as `DEFAULT_FROM_EMAIL`.

* `REDIS_URL` is the URL for redis, which is used by the task queue.
  When `DEBUG` is true, it defaults to `redis://localhost:6379/0`.

* `REDIS_TEST_URL` is the redis URL to use when running tests.
  When `DEBUG` is true *and* `REDIS_URL` isn't defined, it defaults to
  `redis://localhost:6379/1`.

* `ENABLE_SEO_INDEXING` is a boolean value that indicates whether to
  indicate to search engines that they can index the site.

* `FORCE_DISABLE_SECURE_SSL_REDIRECT` is a boolean value that indicates
  whether to disable redirection from http to https. Because such
  redirection is enabled by default when `DEBUG` is false, this option
  can be useful when you want to simulate *almost* everything about a
  production environment without having to setup SSL.

* `UAA_CLIENT_ID` is your cloud.gov/Cloud Foundry UAA client ID. It
  defaults to `calc-dev`.

* `UAA_CLIENT_SECRET` is your cloud.gov/Cloud Foundry UAA client secret.
  If this is undefined and `DEBUG` is true, then a built-in Fake UAA Provider
  will be used to "simulate" cloud.gov login.

* `WHITELISTED_IPS` is a comma-separated string of IP addresses that specifies
  IPs that the REST API will accept requests from. Any IPs not in the list
  attempting to access the API will receive a 403 Forbidden response.
  Example: `127.0.0.1,192.168.1.1`.

* `API_HOST` is the relative or absolute URL used to access the
  API hosted by CALC. It defaults to `/api/` but may need to be changed
  if the API has a proxy in front of it, as it likely will be if deployed
  on government infrastructure. For more information, see [`deploy.md`][].

* `SECURITY_HEADERS_ON_ERROR_ONLY` is a boolean value that indicates whether
  security-related response headers (such as `X-XSS-Protection`)
  should only be added on error (status code >= 400) responses. This setting
  will likely only be used for cloud.gov deployments, where the built-in proxy
  sets those security headers on 200 responses but not on others.

* `GA_TRACKING_ID` is the tracking ID (e.g. `'UA-12345678-12'`)
  for the associated Google Analytics account.
  It will default to the empty string if not found in the environment.

* `ETHNIO_SCREENER_ID` is the ID for the https://ethn.io screener script to
  include on CALC pages. If it is not present, then the ethn.io script will not
  be included.

* `NON_PROD_INSTANCE_NAME` is an optional instance name that when specified
  will cause a banner to be shown at the top of every page to let users know
  that they are viewing a non-production instance of CALC.

* `NEW_RELIC_LICENSE_KEY` is the private New Relic license key for this project.
  If it is present, then the WSGI app will be wrapped with the  New Relic agent.

* `TEST_WITH_ROBOBROWSER` is a boolean that indicates whether to run
  some integration tests using [RoboBrowser][] instead of Selenium/WebDriver.
  Running tests with RoboBrowser can be much faster and less error-prone
  than via Selenium, but it also means that the tests are less end-to-end.

## Authentication and Authorization

We use cloud.gov/Cloud Foundry's User Account and Authentication (UAA)
server to authenticate users. When a user logs in via UAA, their email
address is looked up in Django's user database; if a matching email is
found, the user is logged in. If not, however, the user is *not* logged in,
and will be shown an error message.

Running `manage.py initgroups` will initialize all Django groups for CALC.
Currently, authorization is set up as follows:

* **Non-staff users** in the **Contract Officers** group can upload individual
  price lists for approval.
* **Staff users** in the **Data Administrators** group can
  * create and edit users and assign them to groups,
  * review submitted price lists and approve/reject/retire them,
  * bulk upload data exports (only Region 10 data for now).
* **Superusers** can do anything, but only infrastructure/operational
  engineers should be given this capability.

An initial superuser can be created via e.g.:

```
python manage.py createsuperuser --noinput --username foo --email foo@localhost
```

This will create a user without a password, which is fine since CALC doesn't
use password authentication.

## API

If you're interested in the underlying data, please see https://github.com/18F/calc/blob/master/updating_data.md

### Rates API
You can access rate information at `http://localhost:8000/api/rates/`.

#### Labor Categories
You can search for prices of specific labor categories by using the `q`
parameter. For example:

```
http://localhost:8000/api/rates/?q=accountant
```

You can change the way that labor categories are searched by using the
`query_type` parameter, which can be either:

* `match_words` (the default), which matches all words in the query;
* `match_phrase`, which matches the query as a phrase; or
* `match_exact`, which matches labor categories exactly

You can search for multiple labor categories separated by a comma.

```
http://localhost:8000/api/rates/?q=trainer,instructor
```

All of the query types are case-insenstive.

#### Education and Experience Filters
###### Experience
You can also filter by the minimum years of
experience and maximum years of experience. For example:

```
http://localhost:8000/api/rates/?&min_experience=5&max_experience=10&q=technical
```

Or, you can filter with a single, comma-separated range.
For example, if you wanted results with more than five years and less
than ten years of experience:

```
http://localhost:8000/api/rates/?experience_range=5,10
```

###### Education
The valid values for the education endpoints are `HS` (high school), `AA` (associates),
`BA` (bachelors), `MA` (masters), and `PHD` (Ph.D).

There are two ways to filter based on education, `min_education` and `education`.

To filter by specific education levels, use `education`. It accepts one or more
education values as defined above:

```
http://localhost:8000/api/rates/?education=AA,BA
```

You can also get all results that match and exceed the selected education level
by using `min_education`. The following example will return results that have
an education level of MA or PHD:

```
http://localhost:8000/api/rates/?min_education=MA
```

The default pagination is set to 200. You can paginate using the `page`
parameter:

```
http://localhost:8000/api/rates/?q=translator&page=2
```

#### Price Filters
You can filter by price with any of the `price` (exact match), `price__lte`
(price is less than or equal to) or `price__gte` (price is greater than or
equal to) parameters:

```
http://localhost:8000/api/rates/?price=95
http://localhost:8000/api/rates/?price__lte=95
http://localhost:8000/api/rates/?price__gte=95
```

The `price__lte` and `price__gte` parameters may be used together to search for
a price range:

```
http://localhost:8000/api/rates/?price__gte=95&price__lte=105
```

#### Excluding Records
You can also exclude specific records from the results by passing in an `exclude` parameter and a comma separated list of ids:
```
http://localhost:8000/api/rates/?q=environmental+technician&exclude=875173,875749
```

The `id` attribute is available in api response.

#### Other Filters
Other parameters allow you to filter by:
 * The contract schedule of the transaction.
 * The contract SIN of the transaction.
 * Whether or not the vendor is a small business (valid values: `s` [small] and
`o` [other]).
 * Whether or not the vendor works on the contractor or customer site.

Here is an example with all four parameters (`schedule`, `sin`, `site`, and
`business_size`) included:

```
http://localhost:8000/api/rates/?schedule=mobis&sin=874&site=customer&business_size=s
```

For schedules, there are 8 different values that will return results (case
insensitive):

 - Environmental
 - AIMS
 - Logistics
 - Language Services
 - PES
 - MOBIS
 - Consolidated
 - IT Schedule 70

For SIN codes, there are several possible codes. They will contain the following
numbers for their corresponding schedules:

 - 899 - Environmental
 - 541 - AIMS
 - 87405 - Logistics
 - 73802 - Language Services
 - 871 - PES
 - 874 - MOBIS
 - 132 - IT Schedule 70

For site, there are only 3 values (also case insensitive):

 - Customer
 - Contractor
 - both

And the `small_business` parameter can be either `s` for small business, or `o`
for other than small business.

[twelve-factor]: http://12factor.net/
[Django]: https://www.djangoproject.com/
[18F Docker guide]: https://pages.18f.gov/dev-environment-standardization/virtualization/docker/
[Docker]: https://www.docker.com/
[Docker Compose]: https://docs.docker.com/compose/
[`SECRET_KEY`]: https://docs.djangoproject.com/en/1.8/ref/settings/#secret-key
[`DEFAULT_FROM_EMAIL`]: https://docs.djangoproject.com/en/1.8/ref/settings/#std:setting-DEFAULT_FROM_EMAIL
[`SERVER_EMAIL`]: https://docs.djangoproject.com/en/1.8/ref/settings/#std:setting-SERVER_EMAIL
[SASS]: http://sass-lang.com/
[`deploy.md`]: https://github.com/18F/calc/blob/master/deploy.md
[DJ-Database-URL schema]: https://github.com/kennethreitz/dj-database-url#url-schema
[dj-email-url schema]: https://github.com/migonzalvar/dj-email-url#supported-backends
[pytest]: https://pytest.org/latest/usage.html
[docker-machine-cloud]: https://docs.docker.com/machine/get-started-cloud/
[Django Debug Toolbar]: https://github.com/jazzband/django-debug-toolbar/
[RoboBrowser]: http://robobrowser.readthedocs.io/
