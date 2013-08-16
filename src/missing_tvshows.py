#!/usr/bin/python
# -*- coding: utf-8 -*-

##############################################################################################################
# This script is a simple management system for series made of exercises and solution.                                                                                                                                                    #
# It is possible to make zipped series for moodle, a zip containing all series. Furthermore one can                                                                                                                                   #
# generate previews for one exercise/solution. Two handy functions are the make-workbook and the                                                                                                                               #
# make-catalogue. The former one creaets a pdf containig all series, each one followed by its solution                                                                                                                             #
# just like they were distributed. The latter one create a sort of index of all available exercises in                                                                                                                                    #
# the system. Each exercise is followed by its solution.                                                                                                                                                                                                        #
#                                                                                                                                                                                                                                                                                             #
# The structure for a new exercise should be created by using the make-new-exercise function.                                                                                                                                       #
# For further help, please refer to the help function of the software.                                                                                                                                                                                   #
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#                                                                                                                                                                                                                                                                                             #
# Author: Andreas Ruppen                                                                                                                                                                                                                                                    #
# License: GPL                                                                                                                                                                                                                                                                       #
# This program is free software; you can redistribute it and/or modify                                                                                                                                                                                 #
#   it under the terms of the GNU General Public License as published by                                                                                                                                                                            #
#   the Free Software Foundation; either version 2 of the License, or                                                                                                                                                                                    #
#   (at your option) any later version.                                                                                                                                                                                                                                      #
#                                                                                                                                                                                                                                                                                               #
#   This program is distributed in the hope that it will be useful,                                                                                                                                                                                            #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of                                                                                                                                                                            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                                                                                                                                                                     #
#   GNU General Public License for more details.                                                                                                                                                                                                                   #
#                                                                                                                                                                                                                                                                                                #
#   You should have received a copy of the GNU General Public License                                                                                                                                                                                 #
#   along with this program; if not, write to the                                                                                                                                                                                                                         #
#   Free Software Foundation, Inc.,                                                                                                                                                                                                                                           #
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.                                                                                                                                                                                              #
################################################################################################################

import sqlite3
import sys, os, getopt, shutil
import logging
import logging.config
if float(sys.version[:3])<3.0:
    import ConfigParser
else: 
    import configparser as ConfigParser
import argparse
from pytvdbapi import api

class TVShows:
    def __init__(self):
        """Do some initialization stuff"""
        logging.basicConfig(level=logging.ERROR)
        logging.config.fileConfig('logging.conf')
        self.__log = logging.getLogger('TVShows')
        
        
        # Configure several elements depending on config file
        config = ConfigParser.SafeConfigParser()
        config.read("tvshows.cfg")
        self.__db = api.TVDB(config.get("Config", "api_key"))
        self.__database = config.get("Config", "db")
        self.__cwd = os.getcwd()
        self.__log.debug('Database '+self.__database)
        self.__log.debug("\033[1;33m"+self.__cwd+"\033[0m")
                            
    def main(self):
        """The main function"""
        self.__log.debug("input File is: "+self.__database)
        con = sqlite3.connect(self.__database)
        cur = con.cursor()
        
        print('##############################################################')
        print('###################### Unwatched Missing #####################')
        print('##############################################################')
        # Select TV-Shows where no episode has been watched
        cur.execute('select * from (select tvshow.c00 as Title, episodeview.c12 as Season, count(*) as Episodes, tvshow.c12 as SeriesiD, episodeview.idSeason as SeasoniD, max(episodeview.playCount) as Played from episodeview join seasons on seasons.idSeason = episodeview.idSeason join tvshow on tvshow.idShow = seasons.idShow group by tvshow.c00, episodeview.c12 order by tvshow.c00) where Played is NULL;')
        rows = cur.fetchall()
        finished_tvshows = []
        
        print('-------------------------------------------------------------------------------------------------------------------------------------------------')
        print('|{:44s} | {:s} ({:s}/{:s})| {:74s}|'.format('Title', 'Season', 'Downloaded',  'Available',  'Missing'))
        print('-------------------------------------------------------------------------------------------------------------------------------------------------')
        for row in rows:
            self.__log.debug('#####################################')
            self.__log.debug('Currently Treating {:s}'.format(row[0]))
            self.__log.debug('#####################################')
            if(int(row[1]) == 0): # Don't take into consideration Season 0
                continue
            show = self.__db.get(int(row[3]), "en" )
            number_of_episodes = len(show[int(row[1])])
            full_episodes = range(1, number_of_episodes+1)
            self.__log.debug('{:35s}: Season {:2s} and has {:2d}/{:2d} Episodes'.format( row[0],  row[1],  row[2],  number_of_episodes))
            
            if(int(number_of_episodes) != int(row[2])): # If number of local Episodes is different from TheTVDB
                cur.execute('select tvshow.c00 as Title, episodeview.c12 as Season, episodeview.c13 as Episode, tvshow.c12 as SeriesiD  from episodeview join seasons on seasons.idSeason = episodeview.idSeason join tvshow on tvshow.idShow = seasons.idShow where Season={:s} and SeriesiD={:s}  order by tvshow.c00, episodeview.c12, episodeview.c13;'.format(row[1],  row[3]))
                episodes = cur.fetchall()
                present_episodes = []
                for episode in episodes:
                    present_episodes.append(episode[2])
                present_episodes = map(int,  present_episodes)
                self.__log.debug('Present episodes '+str(present_episodes))
                missing_episodes = list(set(full_episodes) - set(present_episodes))
                self.__log.debug(str(missing_episodes)[1:-1])
                print('|{:43s}: | S{:2s} ({:2d}/{:2d})| missing: {:74s}|'.format(row[0],  row[1], row[2],  number_of_episodes,  str(missing_episodes)[1:-1]))
                print('-------------------------------------------------------------------------------------------------------------------------------------------------')
            else:
                finished_tvshows.append('{:35s}: Season {:2s} and has {:2d}/{:2d} Episodes'.format( row[0],  row[1],  row[2],  number_of_episodes))
                
        print('###############################################################')
        print('######################## Watched Missing ######################')
        print('###############################################################')
        # Select TV-Shows where at least one Episode was played
        cur.execute('select * from (select tvshow.c00 as Title, episodeview.c12 as Season, count(*) as Episodes, tvshow.c12 as SeriesiD, episodeview.idSeason as SeasoniD, sum(episodeview.playCount) as Played from episodeview join seasons on seasons.idSeason = episodeview.idSeason join tvshow on tvshow.idShow = seasons.idShow group by tvshow.c00, episodeview.c12 order by tvshow.c00) where Played is not NULL;')
        rows = cur.fetchall()
        finished_tvshows_watching = []
        print('-------------------------------------------------------------------------------------------------------------------------------------------------')
        print('|{:35s}({:8s})  | {:s} ({:s}/{:s})| {:74s}|'.format('Title', 'SeasonId', 'Season', 'Downloaded',  'Available',  'Missing'))
        print('-------------------------------------------------------------------------------------------------------------------------------------------------')
        for row in rows:
            self.__log.debug('#####################################')
            self.__log.debug('Currently Treating {:s}'.format(row[0]))
            self.__log.debug('#####################################')
            if(int(row[1]) == 0): # Don't take into consideration Season 0
                continue
            self.__log.debug('Currently treating series {:s} with id: {:s}'.format(row[0],  row[3]))
            show = self.__db.get(int(row[3]), "en" )
            number_of_episodes = len(show[int(row[1])])
            full_episodes = range(1, number_of_episodes+1)
            if(int(number_of_episodes) != int(row[2])): # If number of local Episodes is different from TheTVDB
                cur.execute('select tvshow.c00 as Title, episodeview.c12 as Season, episodeview.c13 as Episode, tvshow.c12 as SeriesiD  from episodeview join seasons on seasons.idSeason = episodeview.idSeason join tvshow on tvshow.idShow = seasons.idShow where Season={:s} and SeriesiD={:s}  order by tvshow.c00, episodeview.c12, episodeview.c13;'.format(row[1],  row[3]))
                episodes = cur.fetchall()
                present_episodes = []
                for episode in episodes:
                    present_episodes.append(episode[2])
                present_episodes = map(int,  present_episodes)
                self.__log.debug('Present episodes '+str(present_episodes))
                missing_episodes = list(set(full_episodes) - set(present_episodes))
                self.__log.debug(str(missing_episodes)[1:-1])
                print('|{:35s}({:8s}): | S{:2s} ({:2d}/{:2d})| missing: {:74s}|'.format(row[0], row[3], row[1], row[2],  number_of_episodes,  str(missing_episodes)[1:-1]))
                print('-------------------------------------------------------------------------------------------------------------------------------------------------')
            elif int(number_of_episodes) > row[5]:
                finished_tvshows_watching.append('{:35s}: Season {:2s} and has watched {:2d}/{:2d} Episodes'.format( row[0],  row[1],  row[5],  number_of_episodes))
                
        
        print('###############################################################')
        print('######################## Ready to Watch #######################')
        print('###############################################################')
        for finished in finished_tvshows:
            print(finished)
            
        print('###############################################################')
        print('#################### Complete and Watching ####################')
        print('###############################################################')
        for finished in finished_tvshows_watching:
            print(finished)
        
    def getArguments(self, argv):
        parser = argparse.ArgumentParser()
        parser.add_argument("-i",  "--input",  help="input sqlite database file",  required=False)
        args = parser.parse_args(argv)
        self.__database = args.input or self.__database
        self.main()
        
        
if __name__ == "__main__":
    sms = TVShows()
    sms.getArguments(sys.argv[1:])