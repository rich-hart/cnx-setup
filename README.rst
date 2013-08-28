README for connexions-setup
---------------------------

1. Install virtualenv

   ``sudo apt-get install virtualenv``

   OR

   Download it from https://pypi.python.org/pypi/virtualenv

2. Set up virtual env

   ``virtualenv .``

3. Install fabric

   ``./bin/pip install fabric``

4. Check whether paramiko is broken:

   1. Try running:

      ``./bin/fab -H localhost test``

      If you see this error "NameError: global name 'host' is not defined" then go to 4.2.

   2. Patch paramiko: (See bug https://github.com/paramiko/paramiko/pull/179)

      ``sed -i "59 s/host/socket.gethostname().split('.')[0]/" local/lib/python2.7/site-packages/paramiko/config.py``

5. Have a look at what tasks are available:

   ``./bin/fab -l``
