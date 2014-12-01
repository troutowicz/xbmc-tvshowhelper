#!/usr/bin/python
# -*- coding: utf-8 -*-

#########################################################################
# Modified By: Tim Routowicz
#
# Copyright 2013 Andreas Ruppen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#########################################################################

import sys, math, csv, ConfigParser
import logging, logging.config
from datetime import date

from sqlalchemy import create_engine, Table, MetaData, func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from pytvdbapi import api

class TvShowHelper:
    def __init__(self):
        logging.basicConfig(level=logging.ERROR)
        logging.config.fileConfig('logging.conf')
        self.__log = logging.getLogger('TVShowHelper')
        
        config = ConfigParser.SafeConfigParser()
        config.read('settings.conf')
      
        self.__api_key = config.get('Config', 'api_key')
        self.__dialect = config.get('Config', 'dialect')
        self.__xbmcDb = config.get('Config', 'xbmc_db')

        if self.__dialect == 'mysql':
            self.__user = config.get('Config', 'user')
            self.__pw = config.get('Config', 'pw')
            self.__hostname = config.get('Config', 'hostname')

        self.__numTvShows = 0
        self.__numCheckedTvShows = 0

        sessionMaker = sessionmaker()
        engine = self.getXbmcDbEngine()
        sessionMaker.configure(bind=engine)        
        self.__session = sessionMaker()

        metaData = MetaData()
        metaData.bind = engine

        # Map XBMC tables to objects
        self.__tvshow = Table('tvshow', metaData, autoload=True)
        self.__seasons = Table('seasons', metaData, autoload=True)
        self.__episodeview = Table('episodeview', metaData, autoload=True)

    def getXbmcDbEngine(self):
        try:
            if self.__dialect == 'mysql':
                engine = create_engine('mysql+mysqlconnector://' + self.__user + ':' + self.__pw + '@' + self.__hostname + '/' + self.__xbmcDb)
            elif self.__dialect == 'sqlite':
                engine = create_engine('sqlite:///' + self.__xbmcDb)

            self.__log.debug('Connected to database ' + self.__xbmcDb)

            return engine
        except ProgrammingError:
            self.__log.error('Connection to database ' + self.__xbmcDb + ' failed')
            print 'Connection to database ' + self.__xbmcDb + ' failed'

    def hasEpisodeAired(self, episode):
            if type(episode.FirstAired) is date:
                return episode.FirstAired < date.today()
            
            return False

    def getNumAiredEpisodes(self,  seriesId,  season):
        tvdb = api.TVDB(self.__api_key)
        numEpisodes = 0
        self.__numCheckedTvShows += 1
        progress = self.__numCheckedTvShows * 100 / self.__numTvShows

        sys.stdout.write('\r')
        sys.stdout.write('[%-100s] %d%%' % ('=' * int(math.ceil(progress)), progress ))
        sys.stdout.flush()

        show = tvdb.get_series(seriesId, 'en')
        numEpisodes = len(show[season].filter(self.hasEpisodeAired))
            
        return numEpisodes

    def getLibraryTvShows(self):
        session = self.__session
        tvshow = self.__tvshow
        seasons = self.__seasons
        episodeview = self.__episodeview

        query = session.query(
            tvshow.c.c00.label('Title'),
            episodeview.c.c12.label('Szn'),
            func.count().label('Episodes'),
            tvshow.c.c12.label('SeriesID')
        ).select_from(
            episodeview.join(
                seasons, seasons.c.idSeason == episodeview.c.idSeason
            ).join(
                tvshow, tvshow.c.idShow == seasons.c.idShow
            )
        ).group_by(
            'Title', 'Szn'
        ).order_by(
            'Title'
        )

        tvShows = query.all()
        self.__numTvShows = len(tvShows)

        return tvShows

    def getTvShowsInformation(self):
        tvShows = self.getLibraryTvShows()
        incompleteTvShows = []

        session = self.__session
        tvshow = self.__tvshow
        seasons = self.__seasons
        episodeview = self.__episodeview
        
        for tvShow in tvShows:
            # Season 0 is TV show specials
            if int(tvShow[1]) == 0:
                continue
            title = tvShow[0].encode('utf-8')
            seriesId = tvShow[3]
            season = tvShow[1]
            localEpisodes = tvShow[2]

            self.__log.debug('Checking series {:s} with id: {:s} and season: {:s}'.format(title,  seriesId,  season))

            numEpisodes = self.getNumAiredEpisodes(int(seriesId),  int(season))
            fullEpisodes = range(1, numEpisodes + 1)

            self.__log.debug('{:35s}: Season {:2s} has {:2d}/{:2d} episodes'.format(title,  season,  localEpisodes,  numEpisodes))

            if int(localEpisodes) < int(numEpisodes):
                # Select all availalbe Episodes of current Series and Season
                query = session.query(
                    episodeview.c.c13.label('Episode')
                ).select_from(
                    episodeview.join(
                        seasons, seasons.c.idSeason == episodeview.c.idSeason
                    ).join(
                        tvshow, tvshow.c.idShow == seasons.c.idShow
                    )
                ).filter(
                    (episodeview.c.c12 == season) & (tvshow.c.c12 == seriesId)
                ).order_by(
                    tvshow.c.c00, episodeview.c.c12, 'Episode'
                )

                episodes = query.all()
                episodesFound = []
                for episode in episodes:
                    episodesFound.append(episode[0])

                episodesFound = map(int, episodesFound)
                episodesMissing = list(set(fullEpisodes) - set(episodesFound))
                episodesFound.sort(key=int)
                episodesMissing.sort(key=int)

                self.__log.debug('Episodes found: ' + str(episodesFound)[1:-1])
                self.__log.debug('Episodes missing: ' + str(episodesMissing)[1:-1])
                self.__log.debug('Checked {:d} of {:d} TV shows'.format(self.__numCheckedTvShows,  self.__numTvShows))

                incompleteTvShows.append({
                    'Title': title,
                    'Season': season,
                    'LocalEpisodes': str(localEpisodes),
                    'AvailableEpisodes': str(numEpisodes),
                    'MissingEpisodes': str(episodesMissing)
                })
        
        return incompleteTvShows
        
    def main(self):
        print('Collecting information for TV shows in library')
        incompleteTvShows = self.getTvShowsInformation()

        sys.stdout.write('\n')

        with open('incomplete_tv_shows.csv', 'wb') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'Season (Local/Available)', 'Missing'])

            for tvShow in incompleteTvShows:
                writer.writerow([tvShow['Title'], tvShow['Season'] + ' (' + tvShow['LocalEpisodes'] + '/' + tvShow['AvailableEpisodes'] + ')', tvShow['MissingEpisodes']])

if __name__ == '__main__':
    tvShowHelper = TvShowHelper()
    tvShowHelper.main()
