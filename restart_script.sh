# Create a init script so that all the services will start automatically when
# the VM is started
cat <<EOF >/tmp/cnx-dev-vm
#!/bin/sh -e
# cnx-dev-vm
#
# Restart the cnx services
PATH="/bin:/usr/bin"
USER=`echo /home/*/openstax-setup | cut -d '/' -f3`
start_services() {
    cd /home/\$USER/openstax-setup
    sudo -u \$USER ./bin/fab -H localhost accounts_run_unicorn
    sleep 10  # wait for accounts to run
    cd /home/\$USER/cnx-setup
    sudo -u \$USER ./bin/fab -H localhost archive_run:bg=True
    sudo -u \$USER ./bin/fab -H localhost webview_run
    sudo -u \$USER ./bin/fab -H localhost publishing_run:bg=True
    sudo -u \$USER ./bin/fab -H localhost authoring_run:bg=True
    cd /home/\$USER
    sudo /home/\$USER/smtp_server.py &
}
case "\$1" in
start)
    rm /home/\$USER/cnx-archive/paster.pid
    rm /home/\$USER/cnx-publishing/paster.pid
    rm /home/\$USER/cnx-authoring/pyramid.pid
    start_services
    ;;
restart)
    start_services
    ;;
*)
    echo "Usage: /etc/init.d/cnx-dev-vm {start|restart}"
    exit 1
    ;;
esac
exit 0
EOF
sudo mv /tmp/cnx-dev-vm /etc/init.d/
sudo chmod 755 /etc/init.d/cnx-dev-vm
sudo update-rc.d cnx-dev-vm defaults

# Set up ssh keys using the default insecure key
wget https://raw.github.com/mitchellh/vagrant/master/keys/vagrant.pub
cat vagrant.pub >>~/.ssh/authorized_keys
rm vagrant.pub
