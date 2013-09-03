from fabric.api import *
import fabric.contrib.files

env.use_ssh_config = True

def _setup():
    """Install packages necessary for the connexion projects
    """
    sudo('apt-get install --yes git python-setuptools python-dev')

def _install_postgresql():
    # taken from https://wiki.postgresql.org/wiki/Apt and https://wiki.postgresql.org/wiki/Apt/FAQ#I_want_to_try_the_beta_version_of_the_next_PostgreSQL_release
    if not fabric.contrib.files.exists('/etc/apt/sources.list.d/pgdg.list'):
        fabric.contrib.files.append('/etc/apt/sources.list.d/pgdg.list', 'deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main 9.3', use_sudo=True)
        sudo('wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | apt-key add -')
        sudo('apt-get update')
        sudo('apt-get install --yes postgresql-9.3 libpq-dev postgresql-plpython-9.3')
        fabric.contrib.files.sed('/etc/postgresql/9.3/main/pg_hba.conf', '^local\s*all\s*all\s*peer\s*$', 'local all all md5', use_sudo=True)
        sudo('/etc/init.d/postgresql restart')

def _postgres_user_exists(username):
    return '1' in sudo('psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname=\'%s\'"' % username, user='postgres')

def _postgres_db_exists(dbname):
    return dbname in sudo('psql -l', user='postgres')

def archive_setup():
    """Set up cnx-archive
    """
    _setup()
    _install_postgresql()
    if not fabric.contrib.files.exists('cnx-archive'):
        run('git clone https://github.com/Connexions/cnx-archive.git')
    if not _postgres_user_exists('cnxarchive'):
        print 'Please type in "cnxarchive" as the password'
        sudo('createuser --no-createdb --no-createrole --superuser --pwprompt cnxarchive', user='postgres')

    if _postgres_db_exists('cnxarchive'):
        sudo('dropdb cnxarchive', user='postgres')
    sudo('createdb -O cnxarchive cnxarchive', user='postgres')
    sudo('createlang plpythonu cnxarchive', user='postgres')
    with cd('cnx-archive'):
        sudo('python setup.py install')
        run('initialize_cnx-archive_db development.ini')
        print 'Please type in "cnxarchive" as the password'
        run('psql -U cnxarchive cnxarchive -f example-data.sql')

def archive_run():
    """Run cnx-archive
    """
    with cd('cnx-archive'):
        run('paster serve development.ini')

def archive_test():
    """Test cnx-archive
    """
    if 'cnxarchive-testing' in sudo('psql -l', user='postgres'):
        sudo('dropdb cnxarchive-testing', user='postgres')
    sudo('createdb -O cnxarchive cnxarchive-testing', user='postgres')
    sudo('createlang plpythonu cnxarchive-testing', user='postgres')
    # forward port 3333 to 5432 because testing.ini uses
    # port 3333 but the default postgresql port is 5432
    if not run('pgrep -f "3333:localhost:5432"', warn_only=True):
        run('ssh -fNL 3333:localhost:5432 localhost')
    with cd('cnx-archive'):
        with shell_env(TESTING_CONFIG='testing.ini'):
            run('python -m unittest discover')

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
    if not fabric.contrib.files.exists('/etc/nginx/sites-available/webview'):
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
    sudo('apt-get install --yes python-virtualenv libxslt1-dev libxml2-dev zlib1g-dev '
            'librsvg2-bin otf-stix imagemagick inkscape ruby libxml2-utils zip '
            'openjdk-7-jre-headless docbook-xsl-ns')
    sudo('apt-get install --yes xsltproc') # used for generating epub
    if not fabric.contrib.files.exists('oer.exports'):
        run('git clone https://github.com/Connexions/oer.exports.git')
    with cd('oer.exports'):
        run('virtualenv .')
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
        print 'Please type in "cnxuser" as the password'
        sudo('createuser --no-createdb --no-createrole --no-superuser --pwprompt cnxuser', user='postgres')
    if _postgres_db_exists('cnxuser'):
        sudo('dropdb cnxuser', user='postgres')
    sudo('createdb -O cnxuser cnxuser', user='postgres')

    if not fabric.contrib.files.exists('cnx-user'):
        run('git clone https://github.com/Connexions/cnx-user.git')
    if not fabric.contrib.files.exists('velruse'):
        run('git clone -b cnx-master https://github.com/pumazi/velruse.git')
        with cd('velruse'):
            sudo('python setup.py install')
    with cd('cnx-user'):
        # change velruse to use 1.0.3 which is the version from pumazmi/veruse
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
        run('pserve development.ini')

def user_test():
    """Run tests for cnx-user
    """
    with cd('cnx-user'):
        run('python -m unittest discover')

def repo_setup():
    """Set up rhaptos2.repo
    """
    _setup()
    _install_postgresql()

    if not _postgres_user_exists('rhaptos2repo'):
        print 'Please type in "rhaptos2repo" as the password'
        sudo('createuser --pwprompt --superuser rhaptos2repo', user='postgres')
    if _postgres_db_exists('rhaptos2repo'):
        sudo('dropdb rhaptos2repo', user='postgres')
    if _postgres_db_exists('rhaptos2users'):
        sudo('dropdb rhaptos2users', user='postgres')
    sudo('createdb -O rhaptos2repo rhaptos2repo', user='postgres')
    sudo('createdb -O rhaptos2repo rhaptos2users', user='postgres')

    if not fabric.contrib.files.exists('rhaptos2.repo'):
        run('mkdir rhaptos2.repo')
        run('wget https://raw.github.com/Connexions/rhaptos2.repo/master/quickdownload.sh')
        sudo('rm -rf ~/tmp') # ~/tmp is needed for npm
        run('bash quickdownload.sh rhaptos2.repo')
        run('rm quickdownload.sh')

def repo_run_user_server():
    """Run rhaptos2.repo user server
    """
    with cd('rhaptos2.repo'):
        with prefix('source venvs/vrepo/bin/activate'):
            run('cd src/rhaptos2.user && python rhaptos2/user/run.py --config local.ini --port 8081')

def repo_run_content_repo():
    """Run rhaptos2.repo content repository instance
    """
    if not fabric.contrib.files.exists('/opt'):
        sudo('mkdir /opt')
    if not fabric.contrib.files.exists('/opt/cnx'):
        sudo('mkdir /opt/cnx')
    if not fabric.contrib.files.exists('/opt/cnx/log'):
        sudo('mkdir /opt/cnx/log')
    sudo('chown %s:%s /opt/cnx/log' % (env.user, env.user))
    with cd('rhaptos2.repo/venvs/vrepo'):
        with prefix('source bin/activate'):
            run('rhaptos2repo-run --debug --config=develop.ini')

def test():
    """A test task to see whether paramiko is broken
    """
    run('uname -a')
