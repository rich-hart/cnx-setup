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

