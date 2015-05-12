# Link authoring to accounts
sed -i 's/openstax_accounts.stub = .*/openstax_accounts.stub = false/' ~/cnx-authoring/development.ini
sed -i "s%^.*openstax_accounts.server_url = .*%openstax_accounts.server_url = https://$ipaddr:3000/%" ~/cnx-authoring/development.ini
sed -i "s%^.*openstax_accounts.application_url = .*%openstax_accounts.application_url = http://$ipaddr:8080/%" ~/cnx-authoring/development.ini
sed -i "s/^.*openstax_accounts.application_id = .*/openstax_accounts.application_id = $app_uid/" ~/cnx-authoring/development.ini
sed -i "s/^.*openstax_accounts.application_secret = .*/openstax_accounts.application_secret = $app_secret/" ~/cnx-authoring/development.ini


