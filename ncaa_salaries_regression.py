# -*- coding: utf-8 -*-
"""
@author: pbonnin
"""

import pandas as pd
import seaborn as sns
from bs4 import BeautifulSoup
import time
import re
import datetime
import urllib.request
import io
import matplotlib.pyplot as plt

#%% Some helpful functions and settings for working in Spyder

pd.options.display.max_columns = 100

# Pretty-print the column names
def colnames(pandas_df):
    column_names = list(pandas_df)
    print('\n',"There are "+str(len(column_names))+" columns:",sep="")
    for column in column_names:
        print(column)


# deduplicate lists without losing the order
def f7(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def how_many_nulls(pdx, norm='y'):
    if norm=='y':
        l = len(pdx)
    else:
        l = 1
    return(round(sum(pdx.isna())/l,2))



#%% Importing the original data set

file = 'C:/Users/pbonnin/Desktop/Local DataScience@Syracuse/Coaches9.csv'
coaches9 = pd.read_csv(file,sep=',')

# coaches9 is from 2018: http://sports.usatoday.com/ncaa/salaries/

# A list of conferences
conferences = list(coaches9['Conference'].unique())


#%% A web scraper to get the AP top 25 from ESPN

def get_AP_Top25(year,timeit = False):   
    
    # Initialize a time variable to time the run
    start_time = time.time()
    
    # compiling the url
    lookupurl = "http://www.espn.com/college-football/rankings/_/modifier/webview/platform/android/week/1/year/"+str(year)+"/seasontype/3"
    
    # this code makes it look like a request from a firefox browser in case ESPN doesn't like urlib
    class AppURLopener(urllib.request.FancyURLopener):
        version = "Mozilla/5.0"
    opener = AppURLopener()
    response = opener.open(lookupurl)
    htmlsoup = BeautifulSoup(response, 'html.parser')
    
    # turn the parsed html into a list of strings with the 'td' tag
    links2 = [str(link) for link in htmlsoup.find_all('td')]
    
    # this list has strings that contain records and points given by the ap poll (it's going to make it easier to extract unique values)
    rec_pts = [link for link in links2 if link.startswith('<td class="Table2__td"><div class="">')]
    
    # regex to get the values out of the list of tags 
    votes_pattern = re.compile('(?<="">)([0-9]+)(?=<\w*\/)')
    rec_pattern = re.compile('(?<="">)([0-9]+-[0-9]+)(?=<\w*\/)')
    school_name_pattern = re.compile('(?<=title=")(\w+[\s*\w*&amp;M]*)(?=")')
    abv_pattern = re.compile('(?<=">)(\w+[&amp;M]*)(?=<\/abbr)')
    
    #Extracting the team names in the top 25
    team_name = f7(school_name_pattern.findall(links2[0]))
    team_abv = f7(abv_pattern.findall(links2[0]))
    
    # Some empty lists to store the values
    record = []
    votes = []
    
    # record for the requested season                        
    for item in rec_pts:
        try:
            votes.append(votes_pattern.findall(item)[0])
        except:
            continue
    
    # number of votes awarded for the requested season      
    for item in rec_pts:
        try:
            record.append(rec_pattern.findall(item)[0])
        except:
            continue   
    
    
    column_list = ['Team_Name','Team_Abv','Record','Votes']
    
    # zip up into a data frame of results, adding the look-up title in another column (print na's if there are no matches)
    AP_Top25 = pd.DataFrame(list(zip(team_name,team_abv,record[:25],votes[:25])),columns= column_list)
    AP_Top25['Season']=year
    AP_Top25['Rank'] = AP_Top25.index+1
        
        # print how long it took if the user wants
    if timeit == True:
        print("--- %s seconds ---" % (time.time() - start_time),"\n")
    
    return(AP_Top25)


#%% A web scraper to get the records from all teams by year

def all_records(year,timeit = False):   
    
    # Initialize a time variable to time the run
    start_time = time.time()
    
    if int(year) == datetime.datetime.now().year-1:
        lookupurl = "http://www.espn.com/college-football/standings"
    else:
        lookupurl = "http://www.espn.com/college-football/standings/_/season/"+str(year)
    
    # this code makes it look like a request from a firefox browser in case ESPN doesn't like urlib
    class AppURLopener(urllib.request.FancyURLopener):
        version = "Mozilla/5.0"
    opener = AppURLopener()
    response = opener.open(lookupurl)
    htmlsoup = BeautifulSoup(response, 'html.parser')
    
    # turn the parsed html into a list of strings with the 'td' tag
    links2 = [str(link) for link in htmlsoup.find_all('tr')]
    
    # this list has contains only the tags that have info about the conferences
    conferences = [link for link in links2 if link.startswith('<tr><td class="v-top">')]
    
    # an empty list to compile the dataframes for each conference
    list_of_df = []
    
    # Regex to get the school names and the stats from the tags
    school_name_pattern = re.compile('(?<=title=")(\w+[\(\)\s*\w*\'&amp;M]*)(?=")')
    stats_pattern = re.compile('(?<=stat-cell">).+?(?=<)')
    
    #Extracting the headings for the data, the first conference will do
    #headings = school_name_pattern.findall(conferences[0])
    #headings = headings[len(headings)-18:][:9]
    headings = ['Conference_Record', 'Conf_Points_For', 'Conf_Points_Against', 'Overall_Record', 'Total_Points_For',
                'Total_Points_Against', 'Home_Record', 'Away_Record', 'Current_Streak', 'AP_Poll', 'USA_Poll']
    
    #for some reason these last two have different tags so I'm appending them manually
    #headings.append("AP Poll")
    #headings.append("USA Poll")
    
    # Iterating through the different conferences to pull out the teams and stats
    for item in conferences:
        teams_vars = school_name_pattern.findall(item)
        bunch_of_stats = stats_pattern.findall(item)
        
        #splitting the list every 11th item (to match the headings)
        chunks_of_stats = [bunch_of_stats[x:x+11] for x in range(0, len(bunch_of_stats), 11)]
        
        team_names =  f7(teams_vars)[:len(chunks_of_stats)]
        team_series = pd.Series(team_names)
        
        chunks_of_stats = pd.DataFrame(chunks_of_stats,columns=headings)
        chunks_of_stats["Team"] = team_series
        chunks_of_stats = chunks_of_stats.set_index("Team")
        list_of_df.append(chunks_of_stats)
    
    all_records = pd.concat(list_of_df)
    all_records["Season"]=year
            
            # print how long it took if the user wants
    if timeit == True:
        print("--- %s seconds ---" % (time.time() - start_time),"\n")
    
    return(all_records)



#%% Wikipedia Scrappers

coach_info_url = "https://en.wikipedia.org/wiki/List_of_current_NCAA_Division_I_FBS_football_coaches"
stadium_info_url = "https://en.wikipedia.org/wiki/List_of_U.S._stadiums_by_capacity"

class AppURLopener(urllib.request.FancyURLopener):
    version = "Mozilla/5.0"

opener = AppURLopener()
coach_info_response = opener.open(coach_info_url)
htmlsoup = BeautifulSoup(coach_info_response, 'html.parser')

tables = [str(link) for link in htmlsoup.find_all('table', class_='sortable')]

# Since the wikipedia page has multiple values inside the assistant coaches cells.... I cannot reliably just scraape all the values together
# Therefore, I had to get the ones that show a pattern that I can pick up on
# These are patterns to pick up team names, the year the 2018 coach started on that team and the conference

team_names_pattern = re.compile('(?<=football">)(\w+\/*\s*[A&amp;M]*\-*[\s*\w*\'*]*)(?=<)')
year_pattern = re.compile('(?<=">)\d+(?=<\/a)')

# This was a complicated pattern as lookbehinds on Python need to be constant, it will leave blank the conferences that I can't pick up (this will be fixed later)
conference_pattern = re.compile('(?<=USA">)|(?<=schools">)|(?<=Conference">)(\w+\/*\-*[\s*\w*\'*]*)(?=<\/a)')

# Regex for the stats
c_info_pattern2 = re.compile('(?<=<td>)(\.*[\w|\–]+)(?=\\n)')

#Compiling the information with the regex expressions
team_names = team_names_pattern.findall(tables[0])
conferences = conference_pattern.findall(tables[0])
year = year_pattern.findall(tables[0])

# All the blank spaces I left for the conferences (Ind and C-USA) I could not scrape will be replaced with C-USA, I'll change the indespendent individually later
all_conferences = []
for item in conferences:
    if item == "":
        all_conferences.append("C-USA")
    else:
        all_conferences.append(item)


# List of the independent teams
ind_teams = ["Army Black Knights","BYU Cougars","Liberty Flames","New Mexico State Aggies","Notre Dame Fighting Irish"]

coach_data = pd.DataFrame(list(zip(team_names,all_conferences,year)),columns= ["Team_Name","Conference","First_Season"])
coach_data = coach_data.replace(to_replace='Texas A&amp;M Aggies', value='Texas A&M Aggies')

coach_data.loc[coach_data['Team_Name'].isin(["Army Black Knights","BYU Cougars","Liberty Flames","New Mexico State Aggies","Notre Dame Fighting Irish"]),'Conference'] = "Independent"

c_info_pt2 = c_info_pattern2.findall(tables[0])

#stacking every 6th element
c_info_stack = [c_info_pt2[x:x+6] for x in range(0, len(c_info_pt2), 6)]

stat_columns = ["W","L","W%","Career W","Career L","Career W%"]
stats = pd.DataFrame(c_info_stack,columns= stat_columns)

# Since I could not scrape the coach name out of wikipedia I'm going to have to just match on the school. At the time of this writting Jan 2019, the two datasets are for 2018 so they will match correctly
wiki_stats = pd.concat([coach_data.reset_index(drop=True), stats], axis=1)

#output = 'C:/Users/pbonnin/Desktop/Local DataScience@Syracuse/output_lab3.csv'
#wiki_stats.to_csv(path_or_buf=output, sep=',')

#%% Stadium Size

from urllib import request

stadium_info_url = "http://www.collegegridirons.com/comparisonscap.htm"
response = request.urlopen(stadium_info_url)
html = response.read().decode('utf8')

# Use the html parser to interpret the file
soup = BeautifulSoup(html, 'html.parser')
links = [link.get_text() for link in soup.find_all('td')]
links2 = [link.replace('\r\n\t\t\t\t\t\t\t\t\t\t',"") for link in links]

# Eliminating the stuff I don't need at the at the end of the list
links2 = links2[:len(links2)-7]

# and at the beggining of the list
links2 = links2[-645:]

# stacking every 5 elements
list_links = [links2[x:x+5] for x in range(0, len(links2), 5)]

stadium_size = pd.DataFrame(list_links[1:],columns= list_links[0])


#%% The final scrapper! One for the rank of the recruiting class

def croot_rank(year,timeit = False):   
    
    # Initialize a time variable to time the run
    start_time = time.time()
    
    lookupurl = "https://247sports.com/Season/"+str(year)+"-Football/CompositeTeamRankings/"
    
    # this code makes it look like a request from a firefox browser in case 247 Sports doesn't like urlib
    class AppURLopener(urllib.request.FancyURLopener):
        version = "Mozilla/5.0"
    opener = AppURLopener()
    response = opener.open(lookupurl)
    htmlsoup = BeautifulSoup(response, 'html.parser')
    
    # turn the parsed html into a list of strings with the 'td' tag
    links2 = [str(link) for link in htmlsoup.find_all('a')]
    links3 = [str(link) for link in htmlsoup.find_all('div')]
    
    # shorten the list of tags into more manageable chunks
    team_names = [link for link in links2 if link.startswith('<a class="rankings-page__name-link"')]
    links_small = [link for link in links2 if link.startswith('<a href=')]
    special_croots = [link for link in links3 if link.startswith('<div class="wrapper"')]
    
    # regex patterns to extract recruiting class information
    pattern = re.compile('(?<=\/">).+(?=<)')
    star_croot = re.compile('(?<=>)\s+[0-9]+\s+(?=</div>)')
    avg_star = re.compile('(?<="avg">)\s+[0-9]+\.[0-9]+\s+(?=</div>)')
    
    
    # Compiling all the team names
    teams = []
    
    for item in team_names:
        teams.append(pattern.findall(item)[0])
    
    # Compiling the total number of commits
    commits = []
    
    for item in links_small:
        try:
            commits.append(pattern.findall(item)[0])
        except:
            continue
    
    commits = commits[20:len(teams)+20]
    
    # This one contains: the rank, the number of 5-star recruits, the number 4-star recruits and the number of 3-star recruits
    info_list = []
    
    for item in special_croots:
            info_list.append(star_croot.findall(item))
    
    # forcing into a pandas df
    recruitingDf = pd.DataFrame(info_list,columns= ["Rank","5-stars","4-stars","3-stars"])
    
    # This one has the 247 sports avg rating. More info here: https://247sports.com/Article/247Sports-Rating-Explanation-81574/
    avg_list = []
    
    for item in special_croots:
        avg_list.append(avg_star.findall(item)[0])
    
    # a list of all the other lists with information
    team_data = list(zip(teams,commits,avg_list))
    teamDf = pd.DataFrame(team_data,columns= ["Team","Total_commits","Avg_RecScore"])
    
    finalDF = pd.concat([recruitingDf.reset_index(drop=True), teamDf], axis=1)
    finalDF = finalDF.set_index("Team")
    finalDF["Season"] = year
    
    # print how long it took if the user wants
    if timeit == True:
        print("--- %s seconds ---" % (time.time() - start_time),"\n")
    
    return(finalDF)


#%% The hunt is over: The last pieces of data: Graduation rates

import requests

# Links containing the graduation and academic performance csv's from the NCAA
apr_link = "http://www.ncaa.org/sites/default/files/2018_APR_Data_Sharing_File_20180523_0.csv"
gsr_link = "https://ncaaorg.s3.amazonaws.com/research/gradrates/data/2018RES_File5-DISquadAggregationSA.csv"

gsr = requests.get(gsr_link).content
gsrDF = pd.read_csv(io.StringIO(gsr.decode('utf-8')))

#APR (academic progress rate) is mostly a good to have, I don't think i'm going to use it
apr = requests.get(apr_link).content
aprDF = pd.read_csv(io.StringIO(apr.decode('utf-8')))

# Removing other sports aside from Football (concentrating on gsr)
gsrDF = gsrDF[gsrDF['SPORT']=='MFB']


#%% Connecting the dots: Attempting to match all the names

# The different sources of names:
## The original dataset:
c9_teams = list(coaches9['School'].unique())

## The results from the AP poll scrapper: 
ap_top25 = get_AP_Top25(2018)
ap25_teams = ap_top25['Team_Name']

## The team names from the team record scrapper:
rec_2018 = all_records(2018,timeit=True)
rec18_teams = list(rec_2018.index)

# output = 'C:/Users/pbonnin/Desktop/Local DataScience@Syracuse/output_lab3.csv'
# rec_2018.to_csv(path_or_buf=output, sep=',')

## The team names from wikipedia:
wiki_teams = list(wiki_stats['Team_Name'])

## The team names from the stadium size DF:
stadium_teams = list(stadium_size['College'])

## The team names from the recruiting class scrapper. Since the data is for 2018, I will use the current rankings for the 2019 class
rr_2019 = croot_rank(2019)
rr19_teams = list(rr_2019.index)

## The graduation rate information
grad_teams = list(gsrDF['SCL_NAME'])


#%% FUZZY WUZZY!!!: a function to match the different lists

from fuzzywuzzy import process

## A function to match the names 
def match(list_a, list_b, a_name='Main', b_name='Matcher', score=95, print_nonmatch=False, export_nonmatch=False):
    
    # some lists to compile information
    matched_list = []
    non_matches = []
    team_name = []
    similarity_score = []
    
    # go through the main list and get the best match (only scores above the given number or 95 by default)
    for i in list_a:
        matched_list.append(process.extractOne(i, list_b, score_cutoff=score))
    
    # fuzzy wuzzy likes to output a tuple with the match and the similarity score, append none if there is nothing in the row    
    for tup in matched_list:
        if tup==None:
            team_name.append(None)
            similarity_score.append(None)
        else:
            team_name.append(tup[0])
            similarity_score.append(tup[1])
    
    # compile non-matches in case the user wants to see them
    for i in list_b:
        if i in team_name:
            continue
        else:
            non_matches.append(i)
    
    # Compile into a dataframe
    matched = pd.DataFrame(list(zip(list_a,matched_list,team_name,similarity_score)),columns= [a_name,str(b_name+"_(raw)"),str(b_name+"_Team_name"),str(b_name+"_Similarity")])
    matched = matched.set_index(a_name)
    
    # Compiling this name here makes it easier to index the DF ti print out a mtaching statement
    b_raw = str(str(b_name)+"_(raw)")
    print('\n',sum(matched[b_raw].value_counts()),"/ "+str(len(list_b)),"("+str(sum(matched[b_raw].value_counts())/len(list_b))+")",'matches','\n')
     
     # print the non-matches if the parameter is given
    if print_nonmatch == True:
        print("--->",str(len(non_matches))+" non-matching item(s):")
        for i in non_matches:
            print(i)
    
    if export_nonmatch == True:
        return(matched,non_matches)
    else:
        return(matched)


#%% Buildin a matching DF: Takes around 60 sec to run

start_time = time.time()

# The fuzzy matcher needs a TON of babysitting, how can this be trusted on a large scale??

import numpy as np

# Coahces9 vs AP25
c9_ap25 = match(c9_teams,ap25_teams, b_name='AP_Top25',print_nonmatch=True)

#only UCF is not matching, I'm going to fix this manually:
matchingDF = c9_ap25['AP_Top25_Team_name']
matchingDF.loc['Central Florida'] = "UCF"

# Coaches9 vs 2018 stats DF
# c9_rec18 = match(c9_teams,rec18_teams, b_name='Stats_2018')

# That did not work, maybe lowering the cutoff...
c9_rec18, non_match = match(c9_teams,rec18_teams, b_name='Stats_2018', score=90,export_nonmatch=True)

# If we take a look at the coaches data I can just copy and paste the names and replace manually
non_match_indexes = list(c9_rec18['Stats_2018_Similarity'].index[c9_rec18['Stats_2018_Similarity'].apply(np.isnan)])


# Copying, pasting and doing some text editor stuff to manually match the leftovers:
c9_rec18.loc['Arizona','Stats_2018_Team_name'] = 'Arizona Wildcats'
c9_rec18.loc[ 'Brigham Young','Stats_2018_Team_name'] = 'BYU Cougars'
c9_rec18.loc[ 'Central Florida','Stats_2018_Team_name'] = 'UCF Knights'
c9_rec18.loc[ 'Connecticut','Stats_2018_Team_name'] = 'UConn Huskies'
c9_rec18.loc[ 'Florida International','Stats_2018_Team_name'] = 'Florida Intl Golden Panthers'
c9_rec18.loc[ 'Hawaii','Stats_2018_Team_name'] = "Hawai'i Rainbow Warriors"
c9_rec18.loc['Louisiana-Lafayette','Stats_2018_Team_name'] = "Louisiana Ragin' Cajuns"
c9_rec18.loc[ 'Louisiana-Monroe','Stats_2018_Team_name'] = 'UL Monroe Warhawks'
c9_rec18.loc[ 'Massachusetts','Stats_2018_Team_name'] = 'UMass Minutemen'
c9_rec18.loc[ 'Miami (Fla.)','Stats_2018_Team_name'] = 'Miami Hurricanes'
c9_rec18.loc[ 'Miami (Ohio)','Stats_2018_Team_name'] = 'Miami (OH) RedHawks'
c9_rec18.loc[ 'Nevada-Las Vegas','Stats_2018_Team_name'] = 'UNLV Rebels'
c9_rec18.loc[ 'North Carolina State','Stats_2018_Team_name'] = 'NC State Wolfpack'
c9_rec18.loc[ 'Southern California','Stats_2018_Team_name'] = 'USC Trojans'
c9_rec18.loc[ 'Southern Methodist','Stats_2018_Team_name'] = 'SMU Mustangs'
c9_rec18.loc[ 'Texas A&M','Stats_2018_Team_name'] = 'Texas A&amp;M Aggies'
c9_rec18.loc[ 'Texas Christian','Stats_2018_Team_name'] = 'TCU Horned Frogs'
c9_rec18.loc[ 'Texas-El Paso','Stats_2018_Team_name'] = 'UTEP Miners'
c9_rec18.loc[ 'Texas-San Antonio','Stats_2018_Team_name'] = 'UTSA Roadrunners'
c9_rec18.loc[ 'Alabama at Birmingham','Stats_2018_Team_name'] = 'UAB Blazers'
c9_rec18.loc[ 'Utah','Stats_2018_Team_name'] = 'Utah Utes'

c9_rec18.loc[ 'Colorado','Stats_2018_Team_name'] = 'Colorado Buffaloes'
c9_rec18.loc[ 'Florida','Stats_2018_Team_name'] = 'Florida Gators'
c9_rec18.loc[ 'Georgia','Stats_2018_Team_name'] = 'Georgia Bulldogs'
c9_rec18.loc[ 'Iowa','Stats_2018_Team_name'] = 'Iowa Hawkeyes'
c9_rec18.loc[ 'Kansas','Stats_2018_Team_name'] = 'Kansas Jayhawks'
c9_rec18.loc[ 'Kentucky','Stats_2018_Team_name'] = 'Kentucky Wildcats'
c9_rec18.loc[ 'Tennessee','Stats_2018_Team_name'] = 'Tennessee Volunteers'
c9_rec18.loc[ 'Mississippi','Stats_2018_Team_name'] = 'Ole Miss Rebels'
c9_rec18.loc[ 'Ohio','Stats_2018_Team_name'] = 'Ohio Bobcats'
c9_rec18.loc[ 'New Mexico','Stats_2018_Team_name'] = 'New Mexico Lobos'


matchingDF = pd.concat([matchingDF,c9_rec18['Stats_2018_Team_name']],axis=1)


# Matching to the Wikipedia names
rec18_wiki, non_match = match(rec18_teams,wiki_teams, b_name='Coach_Stats_2018', export_nonmatch=True)
non_match_indexes = list(rec18_wiki['Coach_Stats_2018_Similarity'].index[rec18_wiki['Coach_Stats_2018_Similarity'].apply(np.isnan)])

# Only 5 did not match!
rec18_wiki.loc['UConn Huskies','Coach_Stats_2018_Team_name'] = 'Connecticut Huskies'
rec18_wiki.loc['Florida Intl Golden Panthers','Coach_Stats_2018_Team_name'] = 'Florida International Panthers'
rec18_wiki.loc['Southern Mississippi Golden Eagles','Coach_Stats_2018_Team_name'] = 'Southern Miss Golden Eagles'
rec18_wiki.loc["Hawai'i Rainbow Warriors",'Coach_Stats_2018_Team_name'] = 'Hawai'
rec18_wiki.loc['UL Monroe Warhawks','Coach_Stats_2018_Team_name'] = 'Louisiana-Monroe Warhawks'

# Append into the matching DF
matchingDF = matchingDF.join(rec18_wiki['Coach_Stats_2018_Team_name'], on='Stats_2018_Team_name')

# Now adding the stadium team names
c9_stadium, non_match = match(c9_teams,stadium_teams, b_name='Stadium_Size', score=92, export_nonmatch=True)
non_match_indexes = list(c9_stadium['Stadium_Size_Similarity'].index[c9_stadium['Stadium_Size_Similarity'].apply(np.isnan)])

# There are like 15 important ones to fix
c9_stadium.loc[ 'Brigham Young','Stadium_Size_Team_name'] = 'BYU'
c9_stadium.loc[ 'Massachusetts','Stadium_Size_Team_name'] = 'Umass'
c9_stadium.loc[ 'Southern Methodist','Stadium_Size_Team_name'] = 'SMU'
c9_stadium.loc[ 'Miami (Ohio)','Stadium_Size_Team_name'] = 'Miami-OH'
c9_stadium.loc[ 'Miami (Fla.)','Stadium_Size_Team_name'] = 'Miami'
c9_stadium.loc[ 'Nevada-Las Vegas','Stadium_Size_Team_name'] = 'UNLV'
c9_stadium.loc[ 'Southern California','Stadium_Size_Team_name'] = 'USC'
c9_stadium.loc[ 'Southern Mississippi','Stadium_Size_Team_name'] = 'Southern Miss'
c9_stadium.loc[ 'Texas Christian','Stadium_Size_Team_name'] = 'TCU'
c9_stadium.loc[ 'Texas-El Paso','Stadium_Size_Team_name'] = 'UTEP'
c9_stadium.loc[ 'Texas-San Antonio','Stadium_Size_Team_name'] = 'UTSA'
c9_stadium.loc[ 'North Carolina State','Stadium_Size_Team_name'] = 'NC State'

# Append into the matching DF
matchingDF = pd.concat([matchingDF,c9_stadium['Stadium_Size_Team_name']],axis=1)

# Matching to the recruiting class ranks
c9_rc19, non_match = match(c9_teams,rr19_teams, b_name='Recruiting_Class_2019', export_nonmatch=True)
non_match_indexes = list(c9_rc19['Recruiting_Class_2019_Similarity'].index[c9_rc19['Recruiting_Class_2019_Similarity'].apply(np.isnan)])

# Hallelujah! Only 4 misses
c9_rc19.loc['Southern California','Recruiting_Class_2019_Team_name'] = 'USC '
c9_rc19.loc['Mississippi','Recruiting_Class_2019_Team_name'] = 'Ole Miss '
c9_rc19.loc['North Carolina State','Recruiting_Class_2019_Team_name'] = 'N.C. State '
c9_rc19.loc["Texas Christian",'Recruiting_Class_2019_Team_name'] = 'TCU '
c9_rc19.loc["Miami (Fla.)",'Recruiting_Class_2019_Team_name'] = 'Miami '

# Append into the matching DF
matchingDF = pd.concat([matchingDF,c9_rc19['Recruiting_Class_2019_Team_name']],axis=1)

# Last column! Matching to the graduation rates, the new names say "university" on them so I'm going to lower the required score
c9_gsr, non_match = match(c9_teams,grad_teams, b_name='GSR_(08-11)', score=90, export_nonmatch=True)
non_match_indexes = list(c9_gsr['GSR_(08-11)_Similarity'].index[c9_gsr['GSR_(08-11)_Similarity'].apply(np.isnan)])



# The matching algorythm got some of these every confused... Important universities got jumbled up so there will be a lot of checking
# The main state universities all seem to have been attributed to another university

c9_gsr.loc[ 'Army','GSR_(08-11)_Team_name'] = 'U.S. Military Academy'
c9_gsr.loc[ 'Alabama','GSR_(08-11)_Team_name'] = 'University of Alabama'
c9_gsr.loc[ 'Arizona','GSR_(08-11)_Team_name'] = 'University of Arizona'
c9_gsr.loc[ 'Fresno State','GSR_(08-11)_Team_name'] = 'California State University, Fresno'
c9_gsr.loc[ 'Georgia','GSR_(08-11)_Team_name'] = 'University of Georgia'
c9_gsr.loc[ 'Georgia Tech','GSR_(08-11)_Team_name'] = 'Georgia Institute of Technology'
c9_gsr.loc[ 'Miami (Ohio)','GSR_(08-11)_Team_name'] = 'Miami University (Ohio)'
c9_gsr.loc[ 'Ohio','GSR_(08-11)_Team_name'] = 'Ohio University'
c9_gsr.loc[ 'Louisiana-Lafayette','GSR_(08-11)_Team_name'] = 'University of Louisiana at Lafayette'
c9_gsr.loc[ 'Louisiana-Monroe','GSR_(08-11)_Team_name'] = 'University of Louisiana at Monroe'
c9_gsr.loc[ 'Connecticut','GSR_(08-11)_Team_name'] = 'University of Connecticut'
c9_gsr.loc[ 'Iowa','GSR_(08-11)_Team_name'] = 'University of Iowa'
c9_gsr.loc[ 'Kansas','GSR_(08-11)_Team_name'] = 'University of Kansas'
c9_gsr.loc[ 'Kansas State','GSR_(08-11)_Team_name'] = 'Kansas State University'
c9_gsr.loc[ 'Kentucky','GSR_(08-11)_Team_name'] = 'University of Kentucky'
c9_gsr.loc[ 'LSU','GSR_(08-11)_Team_name'] = 'Louisiana State University'
c9_gsr.loc[ 'Miami (Fla.)','GSR_(08-11)_Team_name'] = 'University of Miami (Florida)'
c9_gsr.loc[ 'Nevada-Las Vegas','GSR_(08-11)_Team_name'] = 'University of Nevada, Las Vegas'
c9_gsr.loc[ 'Nevada','GSR_(08-11)_Team_name'] = 'University of Nevada, Reno'
c9_gsr.loc[ 'Navy','GSR_(08-11)_Team_name'] = 'U.S. Naval Academy'
c9_gsr.loc[ 'North Carolina','GSR_(08-11)_Team_name'] = 'University of North Carolina, Chapel Hill'
c9_gsr.loc[ 'Oklahoma','GSR_(08-11)_Team_name'] = 'University of Oklahoma'
c9_gsr.loc[ 'Oregon','GSR_(08-11)_Team_name'] = 'University of Oregon'
c9_gsr.loc[ 'Rutgers','GSR_(08-11)_Team_name'] = 'Rutgers, The State University of New Jersey, New Brunswick'
c9_gsr.loc[ 'Penn State','GSR_(08-11)_Team_name'] = 'Pennsylvania State University'
c9_gsr.loc[ 'Texas','GSR_(08-11)_Team_name'] = 'University of Texas at Austin'
c9_gsr.loc[ 'Texas-El Paso','GSR_(08-11)_Team_name'] = 'University of Texas at El Paso'
c9_gsr.loc[ 'Texas-San Antonio','GSR_(08-11)_Team_name'] = 'University of Texas at San Antonio'
c9_gsr.loc[ 'UCLA','GSR_(08-11)_Team_name'] = 'University of California, Los Angeles'
c9_gsr.loc[ 'Virginia Tech','GSR_(08-11)_Team_name'] = 'Virginia Polytechnic Institute and State Unive...'
c9_gsr.loc[ 'Utah','GSR_(08-11)_Team_name'] = 'University of Utah'
c9_gsr.loc[ 'Virginia','GSR_(08-11)_Team_name'] = 'University of Virginia'
c9_gsr.loc[ 'Washington','GSR_(08-11)_Team_name'] = 'University of Washington'

c9_gsr.loc[ 'Florida','GSR_(08-11)_Team_name'] = 'University of Florida'
c9_gsr.loc[ 'Michigan','GSR_(08-11)_Team_name'] = 'University of Michigan'
c9_gsr.loc[ 'Tennessee','GSR_(08-11)_Team_name'] = 'University of Tennessee at Chattanooga'


# The final append into the matching DF
matchingDF = pd.concat([matchingDF,c9_gsr['GSR_(08-11)_Team_name']],axis=1)

# Output to csv to check
output = 'C:/Users/pbonnin/Desktop/Local DataScience@Syracuse/output_lab3.csv'
matchingDF.to_csv(path_or_buf=output, sep=',')

print("--- %s seconds ---" % (time.time() - start_time),"\n")

#%% Clean every individual file for data types before joining

# Copies of the data:
coaches9_temp = coaches9
ap_top25_temp = ap_top25
rec_2018_temp = rec_2018
wiki_stats_temp = wiki_stats
stadium_size_temp = stadium_size
rr_2019_temp = rr_2019
gsrDF_temp = gsrDF


# The coaches dataset:
## Change the pay columns to numeric (eliminate commas and $ signs) and dropping assistant pay since its empty
for column in coaches9_temp.iloc[:,3:]:
    coaches9_temp[column] = coaches9_temp[column].str.replace(",","")
    coaches9_temp[column] = coaches9_temp[column].str.replace("$","")


cols = coaches9_temp.columns.drop(['School','Conference','Coach'])
coaches9_temp[cols] = coaches9_temp[cols].apply(pd.to_numeric, errors='coerce')
coaches9_temp = coaches9_temp.drop(columns='AssistantPay')

#coaches9[coaches9.isnull().any(axis=1)]
# Cleaning NULLs
values = {'Bonus': 0, 'BonusPaid': 0, 'Buyout': 0}
coaches9_temp = coaches9_temp.fillna(value=values)


# AP Top 25 dataset:
## Don't need Team_Abv, the season or the record. I'll get the record from a different dataset
ap_top25_temp = ap_top25_temp.drop(columns=['Team_Abv','Record','Season'])
cols = ap_top25_temp.columns.drop('Team_Name')
ap_top25_temp[cols] = ap_top25_temp[cols].apply(pd.to_numeric, errors='coerce')
ap_top25_temp.columns = ['Team_Name', 'AP_Votes_2018', 'AP_Rank_2018']

# 2018 records dataset
## Drop the current streak, season, AP Poll, USA Poll and plit all records into wins and losses for modeling and graphing
rec_2018_temp[['Conf_Wins','Conf_Losses','N/A']] = rec_2018_temp['Conference_Record'].str.split('-',expand=True)
rec_2018_temp[['Home_Wins','Home_Losses']] = rec_2018_temp['Home_Record'].str.split('-',expand=True)
rec_2018_temp[['Away_Wins','Away_Losses']] = rec_2018_temp['Away_Record'].str.split('-',expand=True)
rec_2018_temp[['Wins','Losses']] = rec_2018_temp['Overall_Record'].str.split('-',expand=True)
rec_2018_temp = rec_2018_temp.drop(columns=['Current_Streak','AP_Poll','USA_Poll','Season','Conference_Record','Home_Record','Away_Record','Overall_Record','N/A'])

rec_2018_temp = rec_2018_temp.apply(pd.to_numeric, errors='coerce')
rec_2018_temp.columns = ['Conf_Points_For_2018',  'Conf_Points_Against_2018',  'Total_Points_For_2018',  'Total_Points_Against_2018',  'Conf_Wins_2018',
                    'Conf_Losses_2018',  'Home_Wins_2018',  'Home_Losses_2018',  'Away_Wins_2018',  'Away_Losses_2018',  'Wins_2018', 'Losses_2018']

# 2017 records dataset
rec_2017 = all_records(2017,timeit=True)
## Drop the current streak, season, AP Poll, USA Poll and plit all records into wins and losses for modeling and graphing
rec_2017[['Conf_Wins','Conf_Losses','N/A']] = rec_2017['Conference_Record'].str.split('-',expand=True)
rec_2017[['Home_Wins','Home_Losses']] = rec_2017['Home_Record'].str.split('-',expand=True)
rec_2017[['Away_Wins','Away_Losses']] = rec_2017['Away_Record'].str.split('-',expand=True)
rec_2017[['Wins','Losses']] = rec_2017['Overall_Record'].str.split('-',expand=True)
rec_2017 = rec_2017.drop(columns=['Current_Streak','AP_Poll','USA_Poll','Season','Conference_Record','Home_Record','Away_Record','Overall_Record','N/A'])

rec_2017 = rec_2017.apply(pd.to_numeric, errors='coerce')
rec_2017.columns = ['Conf_Points_For_2017',  'Conf_Points_Against_2017',  'Total_Points_For_2017',  'Total_Points_Against_2017',  'Conf_Wins_2017',
                    'Conf_Losses_2017',  'Home_Wins_2017',  'Home_Losses_2017',  'Away_Wins_2017',  'Away_Losses_2017',  'Wins_2017', 'Losses_2017']

# Data about the coaches
## I will keep all the fields in this DF, the conference name is expanded and the comparison with wins and losses can help me validate who the coach is since I couldnt scrape it 
#wiki_stats.head()

cols = wiki_stats_temp.columns.drop(['Team_Name','Conference'])
wiki_stats_temp[cols] = wiki_stats_temp[cols].apply(pd.to_numeric, errors='coerce')
wiki_stats_temp = wiki_stats_temp.drop(columns='Conference')

# Data about stadium capacity
## This data is also fine, I'll drop the conference, since we have it in multiple fields already, and the stadium name since it's not really useful. Just converting to numeric
## Note: The capacity column has commas as delimiters
stadium_size_temp['Capacity'] = stadium_size_temp['Capacity'].str.replace(",","")
cols = stadium_size_temp.columns.drop(['Stadium','College','Conference'])

stadium_size_temp[cols] = stadium_size_temp[cols].apply(pd.to_numeric, errors='coerce')
stadium_size_temp = stadium_size_temp.drop(columns='Conference')
stadium_size_temp = stadium_size_temp.drop(columns='Stadium')


# Recruiting class info
## Remove "Commits" from the strings in the value and convert to numeric
rr_2019_temp['Total_commits'] = rr_2019_temp['Total_commits'].str.replace(" Commits","")
rr_2019_temp = rr_2019_temp.apply(pd.to_numeric, errors='coerce')
rr_2019_temp = rr_2019_temp.drop(columns='Season')
rr_2019_temp.columns = ['RecRank_2019', '5-stars_2019', '4-stars_2019', '3-stars_2019', 'Total_commits_2019', 'Avg_RecScore_2019']


# The graduation rate information
## This one came from a csv so its formatted properly. Just dropping unecessary columns and making sure only D1 teams are included
gsrDF_temp = gsrDF_temp[gsrDF_temp['SCL_SUBDIVISION']==1]
gsrDF_temp = gsrDF_temp.drop(columns=['SCL_UNITID','SCL_DIVISION','SCL_SUBDIVISION','SCL_CONFERENCE','DIV1_FB_CONFERENCE','SCL_HBCU','SPORT','SCL_PRIVATE','SPONSORED'])



#%% All Files are clean! Putting together the final DF

matchingDF2 = matchingDF
coaches92 = coaches9_temp
ap_top252 = ap_top25_temp
rec_20182 = rec_2018_temp
rec_20172 = rec_2017
wiki_stats2 = wiki_stats_temp
stadium_size2 = stadium_size_temp
rr_20192 = rr_2019_temp
gsrDF2 = gsrDF_temp


matchingDF2 = matchingDF2.join(coaches92.set_index('School'))

matchingDF2 = matchingDF2.join(ap_top252.set_index('Team_Name'), on = 'AP_Top25_Team_name')
matchingDF2 = matchingDF2.join(rec_20182, on = 'Stats_2018_Team_name')
matchingDF2 = matchingDF2.join(rec_20172, on = 'Stats_2018_Team_name')
matchingDF2 = matchingDF2.join(wiki_stats2.set_index('Team_Name'), on = 'Coach_Stats_2018_Team_name')
matchingDF2 = matchingDF2.join(stadium_size2.set_index('College'), on = 'Stadium_Size_Team_name')
matchingDF2 = matchingDF2.join(rr_20192, on = 'Recruiting_Class_2019_Team_name')
matchingDF2 = matchingDF2.join(gsrDF2.set_index('SCL_NAME'), on = 'GSR_(08-11)_Team_name')

#output_df = 'C:/Users/pbonnin/Desktop/Local DataScience@Syracuse/output_lab3_DF.csv'
#matchingDF2.to_csv(path_or_buf=output_df, sep=',')
#matchingDF2 = pd.read_csv(output_df)


final_df = matchingDF2.drop(columns=['AP_Top25_Team_name','Stats_2018_Team_name','Coach_Stats_2018_Team_name',
                                     'Stadium_Size_Team_name','Recruiting_Class_2019_Team_name', 'GSR_(08-11)_Team_name'])


#%% Data Exploration and munging

# Saving summary statistics
summary_stats = final_df.describe()

# How many nulls:
for i in final_df:
    print(i,how_many_nulls(final_df[i]))

# Total Pay shows a loose relationship with the AP top 25
sns.jointplot(y="TotalPay", x="AP_Votes_2018", data=final_df)

# Total and School pay are basically the same:
sns.jointplot(x="TotalPay", y="SchoolPay", data=final_df)
    
# Points and wins sseem normally distributed
sns.distplot(final_df["Conf_Points_For_2018"].dropna())

win_pay2018 = final_df.drop(columns=['Coach',
                                 'SchoolPay',
                                 'Bonus',
                                 'BonusPaid',
                                 'Buyout',
                                 'AP_Votes_2018',
                                 'AP_Rank_2018',
                                 'Conf_Points_For_2017',
                                 'Conf_Points_Against_2017',
                                 'Total_Points_For_2017',
                                 'Total_Points_Against_2017',
                                 'Conf_Wins_2017',
                                 'Conf_Losses_2017',
                                 'Home_Wins_2017',
                                 'Home_Losses_2017',
                                 'Away_Wins_2017',
                                 'Away_Losses_2017',
                                 'Wins_2017',
                                 'Losses_2017',
                                 'First_Season',
                                 'W',
                                 'L',
                                 'W%',
                                 'Career W',
                                 'Career L',
                                 'Career W%',
                                 'Capacity',
                                 'Opened',
                                 'RecRank_2019',
                                 '5-stars_2019',
                                 '4-stars_2019',
                                 '3-stars_2019',
                                 'Total_commits_2019',
                                 'Avg_RecScore_2019',
                                 'FED_RATE',
                                 'GSR'])

win_pay2017 = final_df.drop(columns=['Coach',
                                 'SchoolPay',
                                 'Bonus',
                                 'BonusPaid',
                                 'Buyout',
                                 'AP_Votes_2018',
                                 'AP_Rank_2018',
                                 'Conf_Points_For_2018',
                                 'Conf_Points_Against_2018',
                                 'Total_Points_For_2018',
                                 'Total_Points_Against_2018',
                                 'Conf_Wins_2018',
                                 'Conf_Losses_2018',
                                 'Home_Wins_2018',
                                 'Home_Losses_2018',
                                 'Away_Wins_2018',
                                 'Away_Losses_2018',
                                 'Wins_2018',
                                 'Losses_2018',
                                 'First_Season',
                                 'W',
                                 'L',
                                 'W%',
                                 'Career W',
                                 'Career L',
                                 'Career W%',
                                 'Capacity',
                                 'Opened',
                                 'RecRank_2019',
                                 '5-stars_2019',
                                 '4-stars_2019',
                                 '3-stars_2019',
                                 'Total_commits_2019',
                                 'Avg_RecScore_2019',
                                 'FED_RATE',
                                 'GSR'])
    
#sns.pairplot(win_pay.dropna())
# Interesting correlations among the win variables and point variables:
## Conference wins are more correlated to home wins than away wins
## Another interesting fact, total points for have almost no correlation to total points against so we can keep both of these
 
win_corr2018 = win_pay2018.corr()
sns.heatmap(win_corr2018)

# The highest correlation to total pay are home wins and away losses, i'll keep those two
win_vs_pay2018 = pd.DataFrame(win_corr2018['TotalPay']).sort_values(by='TotalPay', ascending=False)[1:]

# Quickly check if its similar for 2017
win_corr2017 = win_pay2017.corr()
win_vs_pay2017 = pd.DataFrame(win_corr2017['TotalPay']).sort_values(by='TotalPay', ascending=False)[1:]

# Avg. salary by conference
avg_salary = pd.DataFrame(final_df.groupby('Conference')['TotalPay'].mean().sort_values(ascending=False))
avg_salary = avg_salary.reset_index()


# lets check the Coaches data from wikipedia
sns.distplot(final_df["Career W"].dropna())

# I don't want current wins or losses since thats contained in a different data set
wiki_vs_pay = final_df.drop(columns=['Conference',
                                     'Coach',
                                     'SchoolPay',
                                     'Bonus',
                                     'BonusPaid',
                                     'Buyout',
                                     'AP_Votes_2018',
                                     'AP_Rank_2018',
                                     'Conf_Points_For_2018',
                                     'Conf_Points_Against_2018',
                                     'Total_Points_For_2018',
                                     'Total_Points_Against_2018',
                                     'Conf_Wins_2018',
                                     'Conf_Losses_2018',
                                     'Home_Wins_2018',
                                     'Home_Losses_2018',
                                     'Away_Wins_2018',
                                     'Away_Losses_2018',
                                     'Wins_2018',
                                     'Losses_2018',
                                     'Conf_Points_For_2017',
                                     'Conf_Points_Against_2017',
                                     'Total_Points_For_2017',
                                     'Total_Points_Against_2017',
                                     'Conf_Wins_2017',
                                     'Conf_Losses_2017',
                                     'Home_Wins_2017',
                                     'Home_Losses_2017',
                                     'Away_Wins_2017',
                                     'Away_Losses_2017',
                                     'Wins_2017',
                                     'Losses_2017',
                                     'Capacity',
                                     'Opened',
                                     'W',
                                     'L',
                                     'RecRank_2019',
                                     '5-stars_2019',
                                     '4-stars_2019',
                                     '3-stars_2019',
                                     'Total_commits_2019',
                                     'Avg_RecScore_2019',
                                     'FED_RATE',
                                     'GSR'])

       
#sns.pairplot(wiki_vs_pay.dropna())
        
# Tenured coaches seem to be getting paid more than new coaches as it would be expected
plt.xticks(rotation=45)
sns.swarmplot(x="First_Season", y="TotalPay", hue="Conference", data=final_df)
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)


#Career wins and losses seem to move pay up regardless, which tells me its just capturing the temporal element. I think career winning% might be the way to go
sns.jointplot(x="Career W%", y="TotalPay", data=final_df)
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

# Upon further inspection the wikipedia scrapper has is meesing up mid-way through the stats compilation...
# Only the name of the school and the year the coach started is correct. All numerical fields from this source need to be dropped
# I guess this is a lesson as to why wikipedia not the best source of info...
# I will keep the year the coach started however, should help establish the tenure of the coach

# Checking the recruitment class information
croots_vs_pay = final_df[['RecRank_2019',
                          '5-stars_2019',
                          '4-stars_2019',
                          '3-stars_2019',
                          'Total_commits_2019',
                          'Avg_RecScore_2019',
                          'TotalPay']]

#sns.pairplot(croots_vs_pay.dropna())

# A surprising stat, high numbers of 3 star recruits shows a negative effect with class rank

# This one contains really good data! A lot of the variables show correlation with total pay
# Lets check the R2s

croots_vs_pay = croots_vs_pay.corr()
sns.heatmap(croots_vs_pay)

# The highest correlation to total pay are home wins and away losses, i'll keep those two
croots_vs_pay = pd.DataFrame(croots_vs_pay['TotalPay']).sort_values(by='TotalPay', ascending=False)[1:]

# RecScore and RecRank show the same thing. Similar to the AP data, I will take the numerical variable rather than the rank since it gives more info
# I will also keep the 4 and 5 star recruit variables

# More than 60% of these values is NULL, so I will discretize them all into High/Med/Low
# The count values contain 0's so it is possible that replacing nulls witrh 0's could work

# This distribution is representing a ranking so replacing with values would significantly alter it
sns.distplot(final_df["Avg_RecScore_2019"].dropna())


# Checking the graduation rates
gsr_vs_pay = final_df[['FED_RATE','GSR','TotalPay']]

#sns.pairplot(gsr_vs_pay.dropna())

# Seeems like the new GSR metric is more favorable to the NCAA..
# both the federal rate and GSR are highly correlated with each other

# GSR has a nice normal distribution
sns.distplot(final_df['GSR'].dropna())


# Checking against stadium capacity. High correlation!!! (>.8)
sns.jointplot(x="Capacity", y="TotalPay", data=final_df)
sns.distplot(final_df['Capacity'].dropna())


#%% putting together the final df to further explore and model from the selected variables

model_df = final_df[['Conference',
                     'TotalPay',
                     'Bonus',
                     'BonusPaid',
                     'Buyout',
                     'AP_Votes_2018',
                     'Home_Wins_2018',
                     'Away_Losses_2018',
                     'Home_Wins_2017',
                     'Away_Losses_2017',
                     'First_Season',
                     'Capacity',
                     '5-stars_2019',
                     '4-stars_2019',
                     'Avg_RecScore_2019',
                     'GSR']]

#sns.pairplot(model_df.drop(columns=["AP_Votes_2018","Avg_RecScore_2019"]).dropna(), hue='Conference')

# Replacing Nulls (there are some schools without Pay, these will be dropped for modeling purposes although they could be used as a test for the model)
model_df = model_df.dropna(subset=['TotalPay'])
model_df_disc = model_df

# Discretize AP Votes instead of the rank so I can keep the hierarchy pd.cut gives the data    
model_df_disc["AP_Votes_2018"] = pd.cut(model_df_disc["AP_Votes_2018"],4, labels=["Low","Mid-Low","Mid", "High"])
model_df_disc['AP_Votes_2018'].cat.add_categories('NR',inplace=True)
model_df_disc['AP_Votes_2018'].cat.reorder_categories(['NR','Low', 'Mid-Low', 'Mid', 'High'],inplace=True)


# Discretizing similar to the AP poll votes
model_df_disc["Avg_RecScore_2019"] = pd.cut(model_df_disc["Avg_RecScore_2019"],4, labels=["Low","Mid-Low","Mid", "High"])
model_df_disc['Avg_RecScore_2019'].cat.add_categories('NR',inplace=True)
model_df_disc['AP_Votes_2018'].cat.reorder_categories(['NR','Low', 'Mid-Low', 'Mid', 'High'],inplace=True)

#had to remake the variable... not sure why it would discretize both at the same time
model_df = final_df[['Conference',
                     'TotalPay',
                     'Bonus',
                     'BonusPaid',
                     'Buyout',
                     'AP_Votes_2018',
                     'Home_Wins_2018',
                     'Away_Losses_2018',
                     'Home_Wins_2017',
                     'Away_Losses_2017',
                     'First_Season',
                     'Capacity',
                     '5-stars_2019',
                     '4-stars_2019',
                     'Avg_RecScore_2019',
                     'GSR']]

values = {'AP_Votes_2018': 0
          ,'5-stars_2019': 0
          ,'4-stars_2019': 0
          ,'Home_Wins_2017': final_df['Home_Wins_2017'].median()
          ,'Away_Losses_2017': final_df['Away_Losses_2017'].median()
          ,'Avg_RecScore_2019': 0
          ,'GSR': final_df['GSR'].mean()
          ,'Capacity': final_df['Capacity'].median()
          ,'Opened': final_df['Capacity'].median()}

model_df = model_df.fillna(value=values)

values2 = {'AP_Votes_2018': 'NR'
          ,'5-stars_2019': 0
          ,'4-stars_2019': 0
          ,'Home_Wins_2017': final_df['Home_Wins_2017'].median()
          ,'Away_Losses_2017': final_df['Away_Losses_2017'].median()
          ,'Avg_RecScore_2019': 'NR'
          ,'GSR': final_df['GSR'].mean()
          ,'Capacity': final_df['Capacity'].median()
          ,'Opened': final_df['Capacity'].median()}

model_df_disc = model_df_disc.fillna(value=values2)


# How many nulls:
for i in model_df:
    print(i,"-->",how_many_nulls(model_df[i],norm="n"))

#%%

# look for outliers in the conferences:

# SEC has the largest average salary 
plt.xticks(rotation=45)
sns.barplot(y="TotalPay",x="Conference",data=avg_salary)

# There are individuals in the Big10, ACC and Independent conferences that get paid a lot more than their peers
plt.xticks(rotation=45)
sns.boxplot(x="Conference", y="TotalPay", data=final_df, order=avg_salary['Conference'])


# CLear lead on the number of star recruits
final_df['Star4-5_2019']= final_df['5-stars_2019']+final_df['4-stars_2019']

plt.xticks(rotation=45)
sns.boxplot(x="Conference", y="Star4-5_2019", data=final_df, order=avg_salary['Conference'])
sns.barplot(y="Star4-5_2019",x="Conference",data=final_df)

# But they do not have the highest tenure
final_df['Tenure']= 2019 - final_df['First_Season']
avg_tenure = pd.DataFrame(final_df.groupby('Conference')['Tenure'].mean().sort_values(ascending=False))
avg_tenure = avg_tenure.reset_index()

plt.xticks(rotation=45)
sns.boxplot(x="Conference", y="Tenure", data=final_df, order=avg_tenure['Conference'])



# Some other plots...
sns.swarmplot(x="Total_commits_2019", y="TotalPay", hue="Conference", data=final_df)
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

plt.xticks(rotation=45)
sns.swarmplot(x="GSR", y="TotalPay", hue="Wins_2018", data=final_df)
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)


#%% Modeling

import numpy as np  # arrays and math functions
import statsmodels.formula.api as smf  # R-like model specification

model_df2 = model_df

model_df2 = model_df2.dropna(subset=['TotalPay'])

#Get a salary variable going
model_df2['Salary'] = model_df2['TotalPay'] - model_df2['Bonus']


# all_columns = " + ".join(list(coaches_train))


#Total Pay models

# Best model by far! (Adj. R-squared 0.845 with the whole dataset)
my_model = str('TotalPay ~ Conference + Home_Wins_2017 + Away_Losses_2017 + First_Season + Q("5-stars_2019") + Q("4-stars_2019") + Avg_RecScore_2019')
train_model_fit = smf.ols(my_model, data = model_df2).fit()
my_model_summary = train_model_fit.summary()

# Adj. R-squared 0.845 with the whole dataset - All p-values look good
my_model2 = str('TotalPay ~ Conference + Home_Wins_2017 + First_Season + Q("5-stars_2019") + Q("4-stars_2019")')
train_model_fit2 = smf.ols(my_model2, data = model_df2).fit()
my_model2_summary = train_model_fit2.summary()


#Salary models

# Adj. R-squared 0.743 with the whole dataset - most p-values look good
my_model3 = str('Salary ~ Conference + Home_Wins_2017 + First_Season + Q("5-stars_2019") + Q("4-stars_2019") + Avg_RecScore_2019')
train_model_fit3 = smf.ols(my_model3, data = model_df2).fit()
my_model3_summary = train_model_fit3.summary()


# Adj. R-squared 0.745 with the whole dataset - most p-values look good
my_model4 = str('Salary ~ Conference + Home_Wins_2017 + First_Season + Q("5-stars_2019") + Q("4-stars_2019") + Avg_RecScore_2019')
train_model_fit4 = smf.ols(my_model4, data = model_df2).fit()
my_model4_summary = train_model_fit4.summary()


# Adj. R-squared 0.771 the interaction between starred recruits and conference helps!
my_model5 = str('Salary ~ Conference*Q("5-stars_2019")+ Home_Wins_2017 + First_Season + Q("5-stars_2019") + Q("4-stars_2019") + Avg_RecScore_2019')
train_model_fit5 = smf.ols(my_model5, data = model_df2).fit()
my_model5_summary = train_model_fit5.summary()



# Lets try some prediction on the overfitted models
columns= ['Conference','Home_Wins_2017','First_Season','5-stars_2019','4-stars_2019','Avg_RecScore_2019']

test_value = pd.DataFrame(model_df2.loc['Syracuse',columns])

# Could not figure out how to get this to work so my predictions were done manually with the coefficients
train_model_fit4.predict(test_value)
