## xbmc-tvshowhelper

This script parses all TV Shows in a XBMC library. For each TV show TheTVDB is queried to find how many aired episodes exist in each season. The returned value from TheTVDB is then compared against the locally availalbe episodes. TV show seasons missing episodes are written to a csv file along with what episodes are missing.

## Configuration

This script relys on a configuration file, settings.conf. For the script to run, an API key must be obtained from TheTVDB and XBMC database settings must be input. The script works for both SQLite and MySQL databases.
