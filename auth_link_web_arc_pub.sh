# Link authoring to local webview, archive, publishing
sed -i "s%cors.access_control_allow_origin = .*%& http://$ipaddr:8000%" ~/cnx-authoring/development.ini
sed -i "s%webview.url = .*%webview.url = http://$ipaddr:8000/%" ~/cnx-authoring/development.ini
sed -i "s%archive.url = .*%archive.url = http://$ipaddr:6543/%" ~/cnx-authoring/development.ini
sed -i "s%publishing.url = .*%publishing.url = http://$ipaddr:6544/%" ~/cnx-authoring/development.ini

