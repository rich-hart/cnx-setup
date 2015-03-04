import json
import os
import time

from fabric.api import *
import fabric.contrib.files
from ilogue import fexpect

env.use_ssh_config = True

def _setup():
    """Install packages necessary for the connexion projects
    """
    #sudo('apt-get update')
    sudo('apt-get install --yes git python-setuptools python-dev')

def _setup_virtualenv(with_python3=False):
    """Install virtualenv and set up virtualenv in the current directory
    """
    sudo('apt-get install --yes python-virtualenv')
    run('virtualenv %s .' % ('-p `which python3`' if with_python3 else ''))

def _install_postgresql():
    # taken from https://wiki.postgresql.org/wiki/Apt and https://wiki.postgresql.org/wiki/Apt/FAQ#I_want_to_try_the_beta_version_of_the_next_PostgreSQL_release
    if not fabric.contrib.files.exists('/etc/apt/sources.list.d/pgdg.list'):
        fabric.contrib.files.append('/etc/apt/sources.list.d/pgdg.list', 'deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main 9.3', use_sudo=True)
        sudo('wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | apt-key add -')
        sudo('apt-get update')
        sudo('apt-get install --yes postgresql-9.3 postgresql-server-dev-9.3 postgresql-client-9.3 postgresql-contrib-9.3 postgresql-plpython-9.3')
        fabric.contrib.files.sed('/etc/postgresql/9.3/main/pg_hba.conf', '^local\s*all\s*all\s*peer\s*$', 'local all all md5', use_sudo=True)
        sudo('/etc/init.d/postgresql restart')

def _postgres_user_exists(username):
    return '1' in sudo('psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname=\'%s\'"' % username, user='postgres')

def _postgres_db_exists(dbname):
    return dbname in sudo('psql -l --pset="pager=off"', user='postgres')

def _install_plxslt():
    sudo('apt-get install --yes libxml2-dev libxslt-dev pkg-config')
    sudo('rm -rf plxslt')
    run('git clone https://github.com/petere/plxslt.git')
    with cd('plxslt'):
        run('make')
        sudo('make install')
    sudo('rm -rf plxslt')

def _install_mongodb():
    sudo('apt-get install --yes mongodb')

def archive_setup_real_data():
    """Set up cnxarchive database with real data
    """
    if not _postgres_user_exists('cnxarchive'):
        prompts = []
        prompts += fexpect.expect('Enter password for new role:', 'cnxarchive')
        prompts += fexpect.expect('Enter it again:', 'cnxarchive')
        with fexpect.expecting(prompts):
            fexpect.sudo('createuser --no-createdb --no-createrole --superuser --pwprompt cnxarchive', user='postgres')

    if _postgres_db_exists('cnxarchive'):
        sudo('dropdb cnxarchive', user='postgres')
    sudo('createdb -O cnxarchive cnxarchive', user='postgres')
    sudo('createlang plpythonu cnxarchive', user='postgres')

    run('zcat cnx-archive/repo_test_data.sql.gz >cnx-archive/repo_test_data.sql')

    prompts = fexpect.expect('Password for user cnxarchive:', 'cnxarchive')
    with fexpect.expecting(prompts):
        fexpect.run('psql -U cnxarchive cnxarchive -f cnx-archive/repo_test_data.sql')

    run('rm -rf cnx-archive/repo_test_data.sql')
    run('cnx-upgrade v1')

def run_cnxupgrade(upgrade='to_html', filename=None):
    with cd('cnx-archive'):
        sudo('python setup.py install')
    with cd('cnx-upgrade'):
        sudo('python setup.py install')

    cmd = 'cnx-upgrade %s' % upgrade
    query = os.getenv('ID_SELECT_QUERY')
    if query:
        cmd += ' --id-select-query=%s' % json.dumps(query)
    if filename:
        cmd += ' --filename=%s' % filename
    if upgrade == 'to_html':
        cmd += ' --force'
    run(cmd)

def archive_setup(https=''):
    """Set up cnx-archive
    """
    _setup()
    _install_postgresql()
    _install_plxslt()
    query_setup(https=https)
    upgrade_setup(https=https)
    if not fabric.contrib.files.exists('cnx-archive'):
        if not https:
            run('git clone git@github.com:Connexions/cnx-archive.git')
        if https:
            run('git clone https://github.com/Connexions/cnx-archive.git')

    if not _postgres_user_exists('cnxarchive'):
        prompts = []
        prompts += fexpect.expect('Enter password for new role:', 'cnxarchive')
        prompts += fexpect.expect('Enter it again:', 'cnxarchive')
        with fexpect.expecting(prompts):
            fexpect.sudo('createuser --no-createdb --no-createrole --superuser --pwprompt cnxarchive', user='postgres')

    if _postgres_db_exists('cnxarchive'):
        sudo('dropdb cnxarchive', user='postgres')
    sudo('createdb -O cnxarchive cnxarchive', user='postgres')
    sudo('createlang plpythonu cnxarchive', user='postgres')
    with cd('cnx-archive'):
        sudo('python setup.py install')
        run('cnx-archive-initdb --with-example-data development.ini')

def archive_run(bg=''):
    """Run cnx-archive
    """
    if bg:
        bg = ' start'
    with cd('cnx-archive'):
        run('paster serve development.ini {}'.format(bg))

def _archive_test_setup():
    if _postgres_db_exists('cnxarchive-testing'):
        sudo('dropdb cnxarchive-testing', user='postgres')
    if _postgres_db_exists('oscaccounts-testing'):
        sudo('dropdb oscaccounts-testing', user='postgres')
    sudo('createdb -O cnxarchive cnxarchive-testing', user='postgres')
    sudo('createdb -O accounts oscaccounts-testing', user='postgres')
    sudo('createlang plpythonu cnxarchive-testing', user='postgres')
    with cd('rhaptos.cnxmlutils'):
        sudo('python setup.py install')
#   with cd('plpydbapi'):
#       sudo('python setup.py install')
    with cd('cnx-archive'):
        sudo('python setup.py install')

def archive_test(test_case=None):
    """Test cnx-archive
    """
    _archive_test_setup()
    if test_case:
        test_case = '-s {}'.format(test_case)
    with cd('cnx-archive'):
        return run('python setup.py test {}'.format(test_case or ''), warn_only=True)

def query_setup(https=''):
    """Set up cnx-query-grammar
    """
    if not fabric.contrib.files.exists('cnx-query-grammar'):
        if https:
            run('git clone https://github.com/Connexions/cnx-query-grammar.git')
        else:
            run('git clone git@github.com:Connexions/cnx-query-grammar.git')
    with cd('cnx-query-grammar'):
        sudo('python setup.py install')

def query_run(args):
    """Run the cnx-query-grammar script
    """
    run('query_parser %s' % args)

def query_test(test_case=None):
    """Run tests in cnx-query-grammar
    """
    with cd('cnx-query-grammar'):
        if test_case is None:
            test_case = 'discover'
        run('python -m unittest %s' % test_case)

def upgrade_setup(https=''):
    """Set up cnx-upgrade
    """
    sudo('apt-get install --yes libxslt1-dev libxml2-dev')
    if not fabric.contrib.files.exists('cnx-upgrade'):
        if https:
            run('git clone https://github.com/Connexions/cnx-upgrade.git')
        else:
            run('git clone git@github.com:Connexions/cnx-upgrade.git')
    cnxmlutils_setup(https=https)
    with cd('cnx-upgrade'):
        sudo('python setup.py install')

def upgrade_test(test_case=None):
    """Run tests in cnx-upgrade
    """
    if test_case:
        test_case = '-s %s' % test_case
    else:
        test_case = ''
    _archive_test_setup()
    with cd('cnx-upgrade'):
        sudo('python setup.py install')
        with shell_env(DB_CONNECTION_STRING=
                'dbname=cnxarchive-testing user=cnxarchive password=cnxarchive'
                ' host=localhost port=5432'):
            sudo('python setup.py test %s' % test_case)

def _install_nodejs():
    # the nodejs package in raring is too old for grunt-cli,
    # so manually installing it here
    if run('which node', warn_only=True):
        return
    sudo('apt-get install --yes make g++')
    run('wget http://nodejs.org/dist/v0.12.0/node-v0.12.0.tar.gz')
    run('tar xf node-v0.12.0.tar.gz')
    with cd('node-v0.12.0'):
        run('./configure')
        run('make')
        sudo('make install')
    run('rm -rf node-v0.12.0*')

def _configure_webview_nginx():
    sudo('apt-get install --yes nginx')
    put('webview_nginx.conf', '/etc/nginx/sites-available/webview', use_sudo=True)
    fabric.contrib.files.sed('/etc/nginx/sites-available/webview', '/path/to', run('pwd'), use_sudo=True)

def webview_setup(https=''):
    """Set up webview
    """
    _setup()
    if not fabric.contrib.files.exists('webview'):
        if https:
            run('git clone https://github.com/Connexions/webview.git')
        else:
            run('git clone git@github.com:Connexions/webview.git')
    _install_nodejs()
    sudo('apt-get install --yes npm')
    sudo('rm -rf ~/tmp') # ~/tmp is needed for npm
    sudo('npm install -g grunt-cli bower')
    # remove ~/tmp after a system npm install as ~/tmp is owned by root and
    # cannot be written as the user in the next step
    sudo('rm -rf ~/tmp')
    with cd('webview'):
        run('npm install')
    _configure_webview_nginx()
    webview_run()

def webview_run():
    """Run webview
    """
    sudo('rm /etc/nginx/sites-enabled/webview')
    sudo('ln -s /etc/nginx/sites-available/webview /etc/nginx/sites-enabled/webview')
    sudo('/etc/init.d/nginx restart')

def webview_test():
    """Run tests in webview
    """
    with cd('webview'):
        run('npm test')

def webview_compile():
    with cd('webview'):
        run('npm install')

def webview_update():
    """Update webview after a git pull
    """
    sudo('rm -rf ~/tmp')
    with cd('webview'):
        run('npm install')
        run('npm update')
        run('bower update')
    _configure_webview_nginx()

def exports_setup():
    """Set up oer.exports
    """
    _setup()
    sudo('apt-get install --yes libxslt1-dev libxml2-dev zlib1g-dev '
            'librsvg2-bin otf-stix imagemagick inkscape ruby libxml2-utils zip '
            'openjdk-7-jre-headless docbook-xsl-ns')
    sudo('apt-get install --yes xsltproc') # used for generating epub
    if not fabric.contrib.files.exists('oer.exports'):
        run('git clone git@github.com:Connexions/oer.exports.git')
    with cd('oer.exports'):
        _setup_virtualenv()
        with prefix('source bin/activate'):
            run('easy_install lxml argparse pillow')
    if not run('which prince', warn_only=True):
        run('wget http://www.princexml.com/download/prince_9.0-2_ubuntu12.04_amd64.deb')
        sudo('apt-get install libtiff4 libgif4') # install dependencies of princexml
        sudo('dpkg -i prince_9.0-2_ubuntu12.04_amd64.deb')
        run('rm prince_9.0-2_ubuntu12.04_amd64.deb')

def exports_test():
    """Run tests in oer.exports
    """
    with cd('oer.exports'):
        with prefix('source bin/activate'):
            run('python -m unittest discover')

def exports_generate_pdf():
    """Generate a PDF in oer.exports
    """
    with cd('oer.exports'):
        with prefix('source bin/activate'):
            run('python collectiondbk2pdf.py -p %s -d ./test-ccap -s ccap-physics ./result.pdf' % run('which prince'))
    get('oer.exports/result.pdf', '/tmp/result.pdf')
    local('evince /tmp/result.pdf')
    local('rm /tmp/result.pdf')

def exports_generate_epub():
    """Generate an EPUB in oer.exports
    """
    with cd('oer.exports'):
        with prefix('source bin/activate'):
            run('sh ./scripts/module2epub.sh "Connexions" ./test-ccap ./test-ccap.epub "col12345" ./xsl/dbk2epub.xsl ./static/content.css')
            run('python content2epub.py -c ./static/content.css -e ./xsl/dbk2epub.xsl -t "module" -o ./m123.epub -i "m123" ./test-ccap/m-section/')
            run('python content2epub.py -c ./static/content.css -e ./xsl/dbk2epub.xsl -t "collection" -o ./test-ccap.epub ./test-ccap/')
    get('oer.exports/m123.epub', '/tmp/m123.epub')
    get('oer.exports/test-ccap.epub', '/tmp/test-ccap.epub')

def user_setup():
    """Set up cnx-user
    """
    _setup()
    _install_postgresql()
    if not _postgres_user_exists('cnxuser'):
        prompts = []
        prompts += fexpect.expect('Enter password for new role:', 'cnxuser')
        prompts += fexpect.expect('Enter it again:', 'cnxuser')
        with fexpect.expecting(prompts):
            fexpect.sudo('createuser --no-createdb --no-createrole --no-superuser --pwprompt cnxuser', user='postgres')
    if _postgres_db_exists('cnxuser'):
        sudo('dropdb cnxuser', user='postgres')
    sudo('createdb -O cnxuser cnxuser', user='postgres')

    if not fabric.contrib.files.exists('cnx-user'):
        run('git clone https://github.com/Connexions/cnx-user.git')
    if not fabric.contrib.files.exists('velruse'):
        run('git clone -b cnx-master https://github.com/pumazi/velruse.git')
        with cd('velruse'):
            sudo('python setup.py install')
    _install_nodejs()
    sudo('apt-get install --yes npm')
    sudo('rm -rf ~/tmp') # ~/tmp is needed for npm
    sudo('npm install -g grunt-cli bower')
    # remove ~/tmp after a system npm install as ~/tmp is owned by root and
    # cannot be written as the user in the next step
    sudo('rm -rf ~/tmp')
    with cd('cnx-user/cnxuser/assets'):
        run('npm install')
    with cd('cnx-user'):
        # change velruse to use 1.0.3 which is the version from pumazmi/veruse
        if not fabric.contrib.files.contains('setup.py', 'velruse==1.0.3'):
            fabric.contrib.files.sed('setup.py', 'velruse', 'velruse==1.0.3')
        sudo('python setup.py install')
        # httplib2 top_level.txt is not readable by the user for some reason
        # (while other top_level.txt are).  This causes initialize_cnx-user_db
        # to fail with IOError permission denied
        sudo('chmod 644 /usr/local/lib/python2.7/dist-packages/httplib2-0.8-py2.7.egg/EGG-INFO/top_level.txt')
        run('initialize_cnx-user_db development.ini')

def user_run():
    """Run cnx-user
    """
    with cd('cnx-user'):
        sudo('python setup.py install')
        run('pserve development.ini')

def user_test(test_case=None):
    """Run tests for cnx-user
    """
    with cd('cnx-user'):
        sudo('python setup.py install')
        run('python -m unittest %s' % (test_case or 'discover',))

def repo_setup():
    """Set up rhaptos2.repo
    """
    _setup()
    _install_postgresql()
    sudo('apt-get install --yes libxml2-dev libxslt1-dev')
    _install_nodejs()
    sudo('apt-get install --yes npm')

    if not _postgres_user_exists('rhaptos2repo'):
        prompts = []
        prompts += fexpect.expect('Enter password for new role:', 'rhaptos2repo')
        prompts += fexpect.expect('Enter it again:', 'rhaptos2repo')
        with fexpect.expecting(prompts):
            fexpect.sudo('createuser --pwprompt --superuser rhaptos2repo', user='postgres')
    if _postgres_db_exists('rhaptos2repo'):
        sudo('dropdb rhaptos2repo', user='postgres')
    if _postgres_db_exists('rhaptos2users'):
        sudo('dropdb rhaptos2users', user='postgres')
    sudo('createdb -O rhaptos2repo rhaptos2repo', user='postgres')
    sudo('createdb -O rhaptos2repo rhaptos2users', user='postgres')

    if not fabric.contrib.files.exists('rhaptos2.common'):
        run('git clone git@github.com:Connexions/rhaptos2.common.git')
    with cd('rhaptos2.common'):
        sudo('python setup.py install')

    if not fabric.contrib.files.exists('rhaptos2.repo'):
        run('git clone -b fix-install git@github.com:Connexions/rhaptos2.repo.git')
    with cd('rhaptos2.repo'):
        sudo('python setup.py install')
        if fabric.contrib.files.exists('repo-error.log'):
            sudo('chown karen:karen repo-error.log')
        sudo('rhaptos2repo-initdb develop.ini')

    with cd('rhaptos2.repo'):
        if not fabric.contrib.files.exists('atc'):
            run('git clone git@github.com:Connexions/atc.git')
    with cd('rhaptos2.repo/atc'):
        sudo('npm update -g bower', warn_only=True)
        run('npm install')
        sudo('easy_install-2.7 PasteScript PasteDeploy waitress')

def repo_run():
    """Run rhaptos2.repo
    """
    with cd('rhaptos2.repo'):
        run('paster serve paster-development.ini')

def repo_test_server():
    with cd('rhaptos2.repo'):
        run('paster serve paster-testing.ini')

def _repo_test_setup():
    _archive_test_setup()
    sudo('cnx-archive-initdb --with-example-data cnx-archive/tests/testing.ini')
    if 'rhaptos2repo-testing' in sudo('psql -l --pset="pager=off"', user='postgres'):
        sudo('dropdb rhaptos2repo-testing', user='postgres')
    sudo('createdb -O rhaptos2repo rhaptos2repo-testing', user='postgres')
    with cd('rhaptos2.repo'):
        sudo('rm -rf build')
        sudo('python setup.py install')
        sudo('rhaptos2repo-initdb testing.ini')

def repo_test(test_type='wsgi'):
    """Run rhaptos.repo tests
    """
    _repo_test_setup()
    with cd('rhaptos2.repo/'):
        sudo('python setup.py test --test-type={}'.format(test_type))

def cnxmlutils_setup(https=''):
    """Set up rhaptos.cnxmlutils
    """
    if not fabric.contrib.files.exists('rhaptos.cnxmlutils'):
        if https:
            run('git clone https://github.com/Connexions/rhaptos.cnxmlutils.git')
        else:
            run('git clone git@github.com:Connexions/rhaptos.cnxmlutils.git')
    with cd('rhaptos.cnxmlutils'):
        sudo('python setup.py install')

def cnxmlutils_test(test_case=''):
    """Run rhaptos.cnxmlutils tests
    """
    if test_case:
        test_case = '-s %s' % test_case
    with cd('rhaptos.cnxmlutils'):
        sudo('python setup.py install')
        sudo('python setup.py develop')
        sudo('python setup.py test %s' % test_case)

def cnxepub_setup(https=''):
    """Set up cnx-epub
    """
    if not fabric.contrib.files.exists('cnx-epub'):
        if https:
            run('git clone https://github.com/Connexions/cnx-epub.git')
        else:
            run('git clone git@github.com:Connexions/cnx-epub.git')
    with cd('cnx-epub'):
        _setup_virtualenv()
        run('./bin/python setup.py install')
        if not fabric.contrib.files.exists('python3'):
            run('mkdir python3')
            with cd('python3'):
                run('ln -sf ../setup.py')
                run('ln -sf ../cnxepub')
                _setup_virtualenv(with_python3=True)
                run('./bin/python3 setup.py install')

def cnxepub_test(test_case=''):
    """Run cnx-epub tests
    """
    if test_case:
        test_case = '-s %s' % test_case
    with cd('cnx-epub'):
        run('./bin/python setup.py install')
        run('./bin/python setup.py test %s' % test_case)
        with cd('python3'):
            run('./bin/python3 setup.py install')
            run('./bin/python3 setup.py test %s' % test_case)

def draft_setup():
    """Set up draft-transforms
    """
    _setup()
    if not fabric.contrib.files.exists('draft-transforms'):
        run('git clone git@github.com:Connexions/draft-transforms.git')
    with cd('draft-transforms'):
        _setup_virtualenv()
        if not fabric.contrib.files.exists('requests-toolbelt'):
            run('git clone https://github.com/sigmavirus24/requests-toolbelt.git')
        with cd('requests-toolbelt'):
            run('../bin/python setup.py install')
        run('./bin/python setup.py install')

def authoring_setup(https=''):
    """Set up cnx-authoring
    """
    _setup()
    if not fabric.contrib.files.exists('cnx-authoring'):
        if https:
            run('git clone https://github.com/Connexions/cnx-authoring.git')
        else:
            run('git clone git@github.com:Connexions/cnx-authoring.git')
    with cd('cnx-authoring'):
        _setup_virtualenv()
        if not fabric.contrib.files.exists('python3'):
            run('mkdir python3')
            with cd('python3'):
                _setup_virtualenv(with_python3=True)
                run('ln -s ../development.ini')
                run('ln -s ../setup.py')
                run('ln -s ../cnxauthoring')
                run('ln -s ../testing.ini')

    with cd('cnx-query-grammar'):
        run('~/cnx-authoring/bin/python setup.py install')
        run('~/cnx-authoring/python3/bin/python3 setup.py install')
    with cd('cnx-epub'):
        run('~/cnx-authoring/bin/python setup.py install')
        run('~/cnx-authoring/python3/bin/python3 setup.py install')

    with cd('cnx-authoring'):
        run('./bin/python setup.py install')
        with cd('python3'):
            run('./bin/python3 setup.py install')

def authoring_run():
    """Run cnx-authoring
    """
    with cd('cnx-authoring'):
        run('./bin/python setup.py install')
        run('./bin/pserve development.ini')

def authoring_test(test_case=''):
    """Run cnx-authoring tests
    """
    if not _postgres_user_exists('cnxauthoring'):
        prompts = []
        prompts += fexpect.expect('Enter password for new role:', 'cnxauthoring')
        prompts += fexpect.expect('Enter it again:', 'cnxauthoring')
        with fexpect.expecting(prompts):
            fexpect.sudo('createuser --no-createdb --no-createrole --superuser --pwprompt cnxauthoring', user='postgres')
    if _postgres_db_exists('authoring-test'):
        sudo('dropdb authoring-test', user='postgres')
    sudo('createdb -O cnxauthoring authoring-test', user='postgres')
    if test_case:
        test_case = '-s %s' % test_case
    with cd('cnx-query-grammar'):
        sudo('python setup.py install')
    with cd('cnx-epub'):
        sudo('python setup.py install')
    with cd('rhaptos.cnxmlutils'):
        sudo('python setup.py install')
    with cd('plpydbapi'):
        sudo('python setup.py install')
    with cd('cnx-archive'):
        sudo('python setup.py install')
    _archive_test_setup()
    with cd('cnx-publishing'):
        sudo('python setup.py install')
    with cd('cnx-authoring'):
        sudo('python setup.py install')
        run('cnx-authoring-initialize_db cnxauthoring/tests/testing.ini')
        # conn.dsn doesn't work if the database requires password
        # authentication
        if run('grep storage.conn.dsn cnxauthoring/tests/test_functional.py', warn_only=True):
            fabric.contrib.files.sed(
                'cnxauthoring/tests/test_functional.py',
                'storage.conn.dsn',
                'self.settings["postgresql.db-connection-string"]')
        run('python setup.py test %s' % test_case)

#    sudo('dropdb authoring-test', user='postgres')
#    sudo('createdb -O cnxauthoring authoring-test', user='postgres')
#    with cd('cnx-authoring/python3'):
#        run('./bin/pip install -e ../../cnx-epub')
#        run('./bin/pip install -e ../../cnx-query-grammar')
#        run('rm -rf dist build')
#        run('./bin/python3 setup.py install')
#        run('./bin/cnx-authoring-initialize_db testing.ini')
#        run('./bin/python3 setup.py test %s' % test_case)

def publishing_setup(https=''):
    """Set up cnx-publishing
    """
    _setup()
    if not fabric.contrib.files.exists('cnx-publishing'):
        if https:
            run('git clone https://github.com/Connexions/cnx-publishing.git')
        else:
            run('git clone git@github.com:Connexions/cnx-publishing.git')

    with cd('cnx-epub'):
        sudo('python setup.py install')

    with cd('cnx-archive'):
        sudo('python setup.py install')

    with cd('cnx-publishing'):
        sudo('python setup.py install')
        run('cnx-publishing-initdb development.ini')

def publishing_run():
    """Run cnx-publishing
    """
    with cd('cnx-epub'):
        sudo('python setup.py install')

    with cd('cnx-publishing'):
        sudo('python setup.py install')
        run('paster serve development.ini')

def publishing_test(test_case=''):
    """Run cnx-publishing tests
    """
    if not _postgres_user_exists('cnxarchive'):
        prompts = []
        prompts += fexpect.expect('Enter password for new role:', 'cnxarchive')
        prompts += fexpect.expect('Enter it again:', 'cnxarchive')
        with fexpect.expecting(prompts):
            fexpect.sudo('createuser --no-createdb --no-createrole --superuser --pwprompt cnxarchive', user='postgres')

    if _postgres_db_exists('cnxarchive-testing'):
        sudo('dropdb cnxarchive-testing', user='postgres')
    sudo('createdb -O cnxarchive cnxarchive-testing', user='postgres')

    if test_case:
        test_case = '-s %s' % test_case

    with cd('cnx-epub'):
        sudo('python setup.py install')
    with cd('cnx-archive'):
        sudo('python setup.py install')

    with cd('cnx-publishing'):
        sudo('rm -rf dist build')
        sudo('python setup.py install')
        run('python setup.py test %s' % test_case)
        #run('python -m unittest %s' % (test_case or 'discover'))

def _install_pybit_dependencies():
    _install_postgresql()
    sudo('apt-get install -y rabbitmq-server')
    if not _postgres_user_exists('pybit'):
        sudo('psql -d postgres -c "CREATE USER pybit WITH SUPERUSER PASSWORD \'pybit\';"', user='postgres')
    if _postgres_db_exists('pybit'):
        sudo('dropdb pybit', user='postgres')
    sudo('createdb -O pybit pybit', user='postgres')

    if not fabric.contrib.files.exists('pybit'):
        run('git clone https://github.com/nicholasdavidson/pybit.git')
    with cd('pybit'):
        sudo('psql pybit -c \'\\i db/schema.sql\'', user='postgres')
        #sudo('psql pybit -c \'\\i db/populate.sql\'', user='postgres')
    if not fabric.contrib.files.exists('cnx-pybit'):
        run('git clone https://github.com/Connexions/pybit.git cnx-pybit')
    with cd('cnx-pybit'):
        sudo('psql pybit -c \'\\i db/populate_cnx.sql\'', user='postgres')

def acmeio_setup():
    """Set up acmeio"""
    _setup()
    _install_pybit_dependencies()
    if not fabric.contrib.files.exists('acmeio'):
        run('git clone git@github.com:Connexions/acmeio.git')
    with cd('acmeio'):
        sudo('psql pybit -c \'\\i sql_additions.sql\'', user='postgres')
        _setup_virtualenv()
        run('./bin/pip install -e ../pybit')
        run('./bin/python setup.py install')

def acmeio_test(test_case=''):
    """Run acmeio tests"""
    if test_case:
        test_case = '-s %s' % test_case
    with cd('acmeio'):
        run('./bin/python setup.py install')
        run('./bin/pserve production.ini start')
        time.sleep(5)
        run('./bin/python setup.py test %s' % test_case, warn_only=True)
        run('./bin/pserve production.ini stop')

def acmeio_run():
    """Run acmeio"""
    with cd('acmeio'):
        run('./bin/python setup.py install')
        run('./bin/pserve production.ini')

def buildout_setup():
    """Set up cnx-buildout"""
    if not fabric.contrib.files.exists('cnx-buildout'):
        run('git clone git@github.com:Rhaptos/cnx-buildout.git')

def roadrunners_setup():
    """Set up roadrunners"""
    _setup()
    _install_pybit_dependencies()
    coyote_setup()
    rhaptosprint_setup()
    exports_setup()
    buildout_setup()
    sudo('apt-get install --yes realpath')
    sudo('apt-get install --force-yes poppler-utils')
    if not fabric.contrib.files.exists('roadrunners'):
        run('git clone git@github.com:Connexions/roadrunners.git')
    with cd('roadrunners'):
        _setup_virtualenv()
        run('./bin/pip install -e ../pybit')
        run('./bin/pip install -e ../coyote')
        run('./bin/pip install Pillow')
        run('./bin/pip install -e ../Products.RhaptosPrint')
        pwd = run('pwd')
        fabric.contrib.files.sed('test.ini', 'output-dir = .*',
                                 'output-dir = {}'.format(pwd))
        fabric.contrib.files.sed(
                'test.ini', 'python = .*',
                'python = {}'.format(os.path.join(pwd, 'bin/python')))
        print_dir = run('realpath ../Products.RhaptosPrint/Products/'
                        'RhaptosPrint/printing')
        fabric.contrib.files.sed(
                'test.ini',  'print-dir = .*',
                'print-dir = {}'.format(print_dir))
        oerexports_path = run('realpath ../oer.exports')
        fabric.contrib.files.sed(
                'test.ini', 'oer.exports-dir = .*',
                'oer.exports-dir = {}'.format(oerexports_path))
        buildout_path = run('realpath ../cnx-buildout')
        fabric.contrib.files.sed(
                'test.ini', 'cnx-buildout-dir = .*',
                'cnx-buildout-dir = {}'.format(buildout_path))
        fabric.contrib.files.sed(
                'test.ini', '^pdf-generator = .*',
                'pdf-generator = {}'.format(run('which prince')))
        run('./bin/python setup.py install')

def roadrunners_test():
    """Run roadrunners tests"""
    with cd('roadrunners'):
        run('./bin/python setup.py install')
        run('./bin/python setup.py test')

def coyote_setup():
    """Set up coyote"""
    _setup()
    _install_pybit_dependencies()
    if not fabric.contrib.files.exists('coyote'):
        run('git clone git@github.com:Connexions/coyote.git')
    with cd('coyote'):
        _setup_virtualenv()
        run('./bin/pip install -e ../pybit')
        run('./bin/python setup.py install')

def rhaptosprint_setup():
    """Set up Products.RhaptosPrint"""
    _setup()
    if not fabric.contrib.files.exists('Products.RhaptosPrint'):
        run('git clone git@github.com:Rhaptos/Products.RhaptosPrint.git')
    sudo('apt-get install --yes texlive-full')
    with cd('Products.RhaptosPrint'):
        _setup_virtualenv()
        sudo('apt-get install --yes libjpeg62-dev')
        run('./bin/pip install Pillow')
        run('./bin/python setup.py install')

def coyote_setup():
    """Set up coyote"""
    _setup()
    if not fabric.contrib.files.exists('coyote'):
        run('git clone git@github.com:Connexions/coyote.git')
    _install_pybit_dependencies()
    with cd('coyote'):
        _setup_virtualenv()
        run('./bin/pip install -e ../pybit')
        run('./bin/pip install -e ../acmeio')
        run('./bin/python setup.py install')

def coyote_test():
    """Run coyote tests"""
    with cd('coyote'):
        run('./bin/python setup.py install')
        run('./bin/python setup.py test')

def test():
    """A test task to see whether paramiko is broken
    """
    run('uname -a')
