DEPLOY_DIR=/opt
HOME=$DEPLOY_DIR
ipaddr='dev-vm.cnx.org'


# Link webview to local archive

sed -i "s/devarchive.cnx.org/$ipaddr/" ~/webview/src/scripts/settings.js

sed -i 's/port: 80$/port: 6543/' ~/webview/src/scripts/settings.js

sudo sed -i 's/archive.cnx.org/localhost:6543/' /etc/nginx/sites-available/webview



# Link webview to local accounts

sed -i "s%accountProfile: .*%accountProfile: 'https://$ipaddr:3000/profile',%" ~/webview/src/scripts/settings.js





#link publishing to accounts

sed -i 's/openstax_accounts.stub = .*/openstax_accounts.stub = false/' ~/cnx-publishing/development.ini

if [ -z "`grep openstax_accounts.server_url ~/cnx-publishing/development.ini`" ]

then

    sed -i "/openstax_accounts.application_url/ a openstax_accounts.server_url = https://$ipaddr:3000/" ~/cnx-publishing/development.ini

else

    sed -i "s%openstax_accounts.server_url = .*%openstax_accounts.server_url = https://$ipaddr:3000/%" ~/cnx-publishing/development.ini

fi

sed -i "s%openstax_accounts.application_url = .*%openstax_accounts.application_url = http://$ipaddr:6544/%" ~/cnx-publishing/development.ini

if [ -z "`grep openstax_accounts.application_id ~/cnx-publishing/development.ini`" ]

then

    sed -i "/openstax_accounts.application_url/ a openstax_accounts.application_id = $app_uid" ~/cnx-publishing/development.ini

else

    sed -i "s/openstax_accounts.application_id = .*/openstax_accounts.application_id = $app_uid/" ~/cnx-publishing/development.ini

fi

if [ -z "`grep openstax_accounts.application_secret ~/cnx-publishing/development.ini`" ]

then

    sed -i "/openstax_accounts.application_url/ a openstax_accounts.application_secret = $app_secret" ~/cnx-publishing/development.ini

else

    sed -i "s/openstax_accounts.application_secret = .*/openstax_accounts.application_secret = $app_secret/" ~/cnx-publishing/development.ini

fi

# Set up admin as a moderator in publishing

sed -i "/openstax_accounts.groups.moderators/ a\  admin" ~/cnx-publishing/development.ini



# Start publishing on another port, port 6544

sed -i 's/port = 6543/port = 6544/' ~/cnx-publishing/development.ini



# Link authoring to accounts

sed -i 's/openstax_accounts.stub = .*/openstax_accounts.stub = false/' ~/cnx-authoring/development.ini

sed -i "s%^.*openstax_accounts.server_url = .*%openstax_accounts.server_url = https://$ipaddr:3000/%" ~/cnx-authoring/development.ini

sed -i "s%^.*openstax_accounts.application_url = .*%openstax_accounts.application_url = http://$ipaddr:8080/%" ~/cnx-authoring/development.ini

sed -i "s/^.*openstax_accounts.application_id = .*/openstax_accounts.application_id = $app_uid/" ~/cnx-authoring/development.ini

sed -i "s/^.*openstax_accounts.application_secret = .*/openstax_accounts.application_secret = $app_secret/" ~/cnx-authoring/development.ini





# Link webview to local archive

sed -i "s/devarchive.cnx.org/$ipaddr/" ~/webview/src/scripts/settings.js

sed -i 's/port: 80$/port: 6543/' ~/webview/src/scripts/settings.js

sudo sed -i 's/archive.cnx.org/localhost:6543/' /etc/nginx/sites-available/webview



# Link webview to local accounts

sed -i "s%accountProfile: .*%accountProfile: 'https://$ipaddr:3000/profile',%" ~/webview/src/scripts/settings.js





# Link authoring to local webview, archive, publishing

sed -i "s%cors.access_control_allow_origin = .*%& http://$ipaddr:8000%" ~/cnx-authoring/development.ini

sed -i "s%webview.url = .*%webview.url = http://$ipaddr:8000/%" ~/cnx-authoring/development.ini

sed -i "s%archive.url = .*%archive.url = http://$ipaddr:6543/%" ~/cnx-authoring/development.ini

sed -i "s%publishing.url = .*%publishing.url = http://$ipaddr:6544/%" ~/cnx-authoring/development.ini
