import sys
if 'threading' in sys.modules:
    del sys.modules['threading']

# Monkey patch stdlib.
import gevent.monkey
gevent.monkey.patch_all(aggressive=False, subprocess=True)

# Set default encoding to UTF-8
reload(sys)
# noinspection PyUnresolvedReferences
sys.setdefaultencoding('utf-8')

import time
import sys
import json
import httplib
import traceback
import click
from flask import Flask, request, render_template, url_for, redirect, g
from flask.ext.cache import Cache
from flask.ext.login import LoginManager, current_user
from flask.ext.sqlalchemy import SQLAlchemy, declarative_base, Model, _QueryProperty
from flask.ext.assets import Environment, Bundle
from werkzeug.routing import BaseConverter
from werkzeug.exceptions import HTTPException

from realms.lib.util import to_canonical, remove_ext, mkdir_safe, gravatar_url, to_dict
from realms.lib.hook import HookModelMeta


class Application(Flask):

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO')

        if path_info and len(path_info) > 1 and path_info.endswith('/'):
            environ['PATH_INFO'] = path_info[:-1]

        scheme = environ.get('HTTP_X_SCHEME')

        if scheme:
            environ['wsgi.url_scheme'] = scheme

        real_ip = environ.get('HTTP_X_REAL_IP')

        if real_ip:
            environ['REMOTE_ADDR'] = real_ip

        return super(Application, self).__call__(environ, start_response)

    def discover(self):
        import_name = 'realms.modules'
        fromlist = (
            'assets',
            'commands',
            'models',
            'views',
            'hooks'
        )

        start_time = time.time()

        __import__(import_name, fromlist=fromlist)

        for module_name in self.config['MODULES']:
            sources = __import__('%s.%s' % (import_name, module_name), fromlist=fromlist)

            # Blueprint
            if hasattr(sources, 'views'):
                self.register_blueprint(sources.views.blueprint)

            # Click
            if hasattr(sources, 'commands'):
                cli.add_command(sources.commands.cli, name=module_name)

        print >> sys.stderr, ' * Ready in %.2fms' % (1000.0 * (time.time() - start_time))

    def make_response(self, rv):
        if rv is None:
            rv = '', httplib.NO_CONTENT
        elif not isinstance(rv, tuple):
            rv = rv,

        rv = list(rv)

        if isinstance(rv[0], (list, dict)):
            rv[0] = self.response_class(json.dumps(rv[0]), mimetype='application/json')

        return super(Application, self).make_response(tuple(rv))


class MySQLAlchemy(SQLAlchemy):

    def make_declarative_base(self):
        """Creates the declarative base."""
        base = declarative_base(cls=Model, name='Model',
                                metaclass=HookModelMeta)
        base.query = _QueryProperty(self)
        return base


class Assets(Environment):
    default_filters = {'js': 'rjsmin', 'css': 'cleancss'}
    default_output = {'js': 'assets/%(version)s.js', 'css': 'assets/%(version)s.css'}

    def register(self, name, *args, **kwargs):
        ext = args[0].split('.')[-1]
        filters = kwargs.get('filters', self.default_filters[ext])
        output = kwargs.get('output', self.default_output[ext])

        return super(Assets, self).register(name, Bundle(*args, filters=filters, output=output))


class RegexConverter(BaseConverter):
    """ Enables Regex matching on endpoints
    """
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def redirect_url(referrer=None):
    if not referrer:
        referrer = request.referrer
    return request.args.get('next') or referrer or url_for('index')


def error_handler(e):
    try:
        if isinstance(e, HTTPException):
            status_code = e.code
            message = e.description if e.description != type(e).description else None
            tb = None
        else:
            status_code = httplib.INTERNAL_SERVER_ERROR
            message = None
            tb = traceback.format_exc() if current_user.admin else None

        if request.is_xhr or request.accept_mimetypes.best in ['application/json', 'text/javascript']:
            response = {
                'message': message,
                'traceback': tb
            }
        else:
            response = render_template('errors/error.html',
                                       title=httplib.responses[status_code],
                                       status_code=status_code,
                                       message=message,
                                       traceback=tb)
    except HTTPException as e2:
        return error_handler(e2)

    return response, status_code



app = Application(__name__)
app.config.from_object('realms.config')
app.url_map.converters['regex'] = RegexConverter
app.url_map.strict_slashes = False

for status_code in httplib.responses:
    if status_code >= 400:
        app.register_error_handler(status_code, error_handler)


@app.before_request
def init_g():
    g.assets = dict(css=['main.css'], js=['main.js'])


@app.template_filter('datetime')
def _jinja2_filter_datetime(ts):
    return time.strftime('%b %d, %Y %I:%M %p', time.localtime(ts))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

if app.config['RELATIVE_PATH']:
    @app.route("/")
    def root():
        return redirect(url_for(app.config['ROOT_ENDPOINT']))


@click.group()
def cli():
    pass

# Init plugins here if possible
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

db = MySQLAlchemy(app)
cache = Cache(app)

assets = Assets(app)
assets.register('main.js',
                'vendor/jquery/dist/jquery.js',
                'vendor/components-bootstrap/js/bootstrap.js',
                'vendor/handlebars/handlebars.js',
                'vendor/js-yaml/dist/js-yaml.js',
                'vendor/marked/lib/marked.js',
                'js/html-sanitizer-minified.js',  # don't minify?
                'vendor/highlightjs/highlight.pack.js',
                'vendor/parsleyjs/dist/parsley.js',
                'vendor/datatables/media/js/jquery.dataTables.js',
                'vendor/datatables-plugins/integration/bootstrap/3/dataTables.bootstrap.js',
                'js/hbs-helpers.js',
                'js/mdr.js')

assets.register('main.css',
                'vendor/bootswatch-dist/css/bootstrap.css',
                'vendor/components-font-awesome/css/font-awesome.css',
                'vendor/highlightjs/styles/github.css',
                'vendor/datatables-plugins/integration/bootstrap/3/dataTables.bootstrap.css',
                'css/style.css')

app.discover()

# This will be removed at some point
db.create_all()






