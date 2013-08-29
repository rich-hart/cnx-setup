===========================
README for connexions-setup
===========================

Installation
------------

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

Example Usage
-------------

1. Create a VM or have a server with Ubuntu 13.04 (which we will call raring).

2. (Optional) Set up your ssh key and hostname in your ssh config.

3. Set up oer.exports on raring:

   ``./bin/fab -H raring export_setup``

4. Run the tests in oer.exports on raring:

   ``./bin/fab -H raring export_test``

5. Try generating a pdf with oer.exports on raring:

   ``./bin/fab -H raring export_generate_pdf``
