from fabric.api import *
import fabric.contrib.files

env.use_ssh_config = True

def _setup():
    """Install packages necessary for the connexion projects
    """
    sudo('apt-get install --yes git python-setuptools python-dev')
    _install_postgresql()

def _install_postgresql():
    # taken from https://wiki.postgresql.org/wiki/Apt and https://wiki.postgresql.org/wiki/Apt/FAQ#I_want_to_try_the_beta_version_of_the_next_PostgreSQL_release
    if not fabric.contrib.files.exists('/etc/apt/sources.list.d/pgdg.list'):
        fabric.contrib.files.append('/etc/apt/sources.list.d/pgdg.list', 'deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main 9.3', use_sudo=True)
        sudo('wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | apt-key add -')
        sudo('apt-get update')
        sudo('apt-get install --yes postgresql-9.3 libpq-dev postgresql-plpython-9.3')
        fabric.contrib.files.sed('/etc/postgresql/9.3/main/pg_hba.conf', '^local\s*all\s*all\s*peer\s*$', 'local all all md5', use_sudo=True)
        sudo('/etc/init.d/postgresql restart')

def archive_setup():
    """Set up cnx-archive
    """
    _setup()
    if not fabric.contrib.files.exists('cnx-archive'):
        run('git clone https://github.com/Connexions/cnx-archive.git')
    if '1' not in sudo('psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname=\'cnxarchive\'"', user='postgres'):
        print 'Please type in "cnxarchive" as the password'
        sudo('createuser --no-createdb --no-createrole --superuser --pwprompt cnxarchive', user='postgres')

    if 'cnxarchive' in sudo('psql -l', user='postgres'):
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
    if run('which node'):
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
    _setup()
    if not fabric.contrib.files.exists('webview'):
        run('git clone https://github.com/Connexions/webview.git')
    _install_nodejs()
    sudo('apt-get install --yes npm')
    sudo('npm install -g grunt-cli')
    with cd('webview'):
        sudo('npm install')
    _configure_webview_nginx()

def webview_run():
    sudo('rm /etc/nginx/sites-enabled/*')
    sudo('ln -s /etc/nginx/sites-available/webview /etc/nginx/sites-enabled/webview')
    sudo('/etc/init.d/nginx restart')

def webview_test():
    with cd('webview'):
        run('npm test')

def test():
    """A test task to see whether paramiko is broken
    """
    run('uname -a')
