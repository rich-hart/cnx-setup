# Link webview to local archive
sed -i "s/devarchive.cnx.org/$ipaddr/" ~/webview/src/scripts/settings.js
sed -i 's/port: 80$/port: 6543/' ~/webview/src/scripts/settings.js
sudo sed -i 's/archive.cnx.org/localhost:6543/' /etc/nginx/sites-available/webview

# Link webview to local accounts
sed -i "s%accountProfile: .*%accountProfile: 'https://$ipaddr:3000/profile',%" ~/webview/src/scripts/settings.js


