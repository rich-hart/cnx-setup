import json
import os

from fabric.api import *
import fabric.contrib.files
from ilogue import fexpect

env.use_ssh_config = True

def _setup():
    """Install packages necessary for the connexion projects
    """
    sudo('apt-get update')
    sudo('apt-get install --yes git python-setuptools python-dev')

def _setup_virtualenv():
    """Install virtualenv and set up virtualenv in the current directory
    """
    sudo('apt-get install --yes python-virtualenv')
    run('virtualenv .')

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
    return dbname in sudo('psql -l', user='postgres')

def _install_plxslt():
    sudo('apt-get install --yes libxml2-dev libxslt-dev pkg-config')
    sudo('rm -rf plxslt')
    run('git clone https://github.com/petere/plxslt.git')
    with cd('plxslt'):
        run('make')
        sudo('make install')
    sudo('rm -rf plxslt')

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

def archive_setup(clone_url=None, sha=None, force_clone=False):
    """Set up cnx-archive
    """
    _setup()
    _install_postgresql()
    _install_plxslt()
    query_setup()
    upgrade_setup()
    if clone_url is None:
        clone_url = 'https://github.com/Connexions/cnx-archive.git'
    if force_clone:
        sudo('rm -rf cnx-archive')
    if not fabric.contrib.files.exists('cnx-archive'):
        run('git clone %s' % clone_url)
        if sha is not None:
            with cd('cnx-archive'):
                run('git reset --hard %s' % sha)

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
        run('initialize_cnx-archive_db --with-example-data development.ini')

def archive_run():
    """Run cnx-archive
    """
    with cd('cnx-archive'):
        run('paster serve development.ini')

def _archive_test_setup():
    if 'cnxarchive-testing' in sudo('psql -l --pset="pager=off"', user='postgres'):
        sudo('dropdb cnxarchive-testing', user='postgres')
    sudo('createdb -O cnxarchive cnxarchive-testing', user='postgres')
    sudo('createlang plpythonu cnxarchive-testing', user='postgres')
    with cd('plpydbapi'):
        sudo('python setup.py install')
    with cd('cnx-archive'):
        sudo('python setup.py install')

def archive_test(test_case=None):
    """Test cnx-archive
    """
    _archive_test_setup()
    with cd('cnx-archive'):
        with shell_env(TESTING_CONFIG='testing.ini'):
            return run('python -m unittest %s' % (test_case or 'discover'), warn_only=True)

def query_setup():
    """Set up cnx-query-grammar
    """
    if not fabric.contrib.files.exists('cnx-query-grammar'):
        run('git clone https://github.com/Connexions/cnx-query-grammar.git')
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

def upgrade_setup():
    """Set up cnx-upgrade
    """
    sudo('apt-get install --yes libxslt1-dev libxml2-dev')
    if not fabric.contrib.files.exists('cnx-upgrade'):
        run('git clone https://github.com/Connexions/cnx-upgrade.git')
    cnxmlutils_setup()
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
    run('wget http://nodejs.org/dist/v0.10.17/node-v0.10.17.tar.gz')
    run('tar xf node-v0.10.17.tar.gz')
    with cd('node-v0.10.17'):
        run('./configure')
        run('make')
        sudo('make install')
    run('rm -rf node-v0.10.17*')

def _configure_webview_nginx():
    sudo('apt-get install --yes nginx')
    put('webview_nginx.conf', '/etc/nginx/sites-available/webview', use_sudo=True)
    fabric.contrib.files.sed('/etc/nginx/sites-available/webview', '/path/to', run('pwd'), use_sudo=True)
    webview_run()

def webview_setup():
    """Set up webview
    """
    _setup()
    if not fabric.contrib.files.exists('webview'):
        run('git clone https://github.com/Connexions/webview.git')
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

def webview_run():
    """Run webview
    """
    sudo('rm /etc/nginx/sites-enabled/*')
    sudo('ln -s /etc/nginx/sites-available/webview /etc/nginx/sites-enabled/webview')
    sudo('/etc/init.d/nginx restart')

def webview_test():
    """Run tests in webview
    """
    with cd('webview'):
        run('npm test')

def webview_update():
    """Update webview after a git pull
    """
    sudo('rm -rf ~/tmp')
    with cd('webview'):
        run('npm install')
        run('npm update')
        run('bower update')

def export_setup():
    """Set up oer.exports
    """
    _setup()
    sudo('apt-get install --yes libxslt1-dev libxml2-dev zlib1g-dev '
            'librsvg2-bin otf-stix imagemagick inkscape ruby libxml2-utils zip '
            'openjdk-7-jre-headless docbook-xsl-ns')
    sudo('apt-get install --yes xsltproc') # used for generating epub
    if not fabric.contrib.files.exists('oer.exports'):
        run('git clone https://github.com/Connexions/oer.exports.git')
    with cd('oer.exports'):
        _setup_virtualenv()
        with prefix('source bin/activate'):
            run('easy_install lxml argparse pillow')
    if not run('which prince', warn_only=True):
        run('wget http://www.princexml.com/download/prince_9.0-2_ubuntu12.04_amd64.deb')
        sudo('apt-get install libtiff4 libgif4') # install dependencies of princexml
        sudo('dpkg -i prince_9.0-2_ubuntu12.04_amd64.deb')
        run('rm prince_9.0-2_ubuntu12.04_amd64.deb')

def export_test():
    """Run tests in oer.exports
    """
    with cd('oer.exports'):
        with prefix('source bin/activate'):
            run('python -m unittest discover')

def export_generate_pdf():
    """Generate a PDF in oer.exports
    """
    with cd('oer.exports'):
        with prefix('source bin/activate'):
            run('python collectiondbk2pdf.py -p %s -d ./test-ccap -s ccap-physics ./result.pdf' % run('which prince'))
    get('oer.exports/result.pdf', '/tmp/result.pdf')
    local('evince /tmp/result.pdf')
    local('rm /tmp/result.pdf')

def export_generate_epub():
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
    sudo('initialize_cnx-archive_db --with-example-data cnx-archive/testing.ini')
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

def cnxmlutils_setup():
    """Set up rhaptos.cnxmlutils
    """
    if not fabric.contrib.files.exists('rhaptos.cnxmlutils'):
        run('git clone git@github.com:Connexions/rhaptos.cnxmlutils.git')
    with cd('rhaptos.cnxmlutils'):
        sudo('python setup.py install')

def cnxmlutils_test():
    """Run rhaptos.cnxmlutils tests
    """
    with cd('rhaptos.cnxmlutils'):
        run('python -m unittest discover')

def cnxepub_setup():
    """Set up cnx-epub
    """
    if not fabric.contrib.files.exists('cnx-epub'):
        run('git clone git@github.com:Connexions/cnx-epub.git')
    with cd('cnx-epub'):
        sudo('python setup.py install')

def cnxepub_test():
    """Run cnx-epub tests
    """
    with cd('cnx-epub'):
        run('python -m unittest discover')

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

def test():
    """A test task to see whether paramiko is broken
    """
    run('uname -a')
