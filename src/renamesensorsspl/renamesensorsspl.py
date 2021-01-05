# -*- coding: utf-8 -*-
###############################################################
# Author:       patrice.ponchant@furgo.com  (Fugro Brasil)    #
# Created:      10/12/2020                                    #
# Python :      3.x                                           #
###############################################################

# The future package will provide support for running your code on Python 2.6, 2.7, and 3.3+ mostly unchanged.
# http://python-future.org/quickstart.html
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

##### Basic packages #####
import datetime
import sys, os
import pandas as pd
import math
import re

##### CMD packages #####
from tqdm import tqdm
#from tabulate import tabulate

##### GUI packages #####
from gooey import Gooey, GooeyParser
from colored import stylize, attr, fg

# 417574686f723a205061747269636520506f6e6368616e74
##########################################################
#                       Main code                        #
##########################################################
# this needs to be *before* the @Gooey decorator!
# (this code allows to only use Gooey when no arguments are passed to the script)
if len(sys.argv) >= 2:
    if not '--ignore-gooey' in sys.argv:
        sys.argv.append('--ignore-gooey')
        cmd = True 
    else:
        cmd = False  
        
# GUI Configuration
# Preparing your script for packaging https://chriskiehl.com/article/packaging-gooey-with-pyinstaller
# Prevent stdout buffering # https://github.com/chriskiehl/Gooey/issues/289     
@Gooey(
    program_name='Rename tool for sensors using the spreadsheet generated by splsensors',
    progress_regex=r"^progress: (?P<current>\d+)/(?P<total>\d+)$",
    progress_expr="current / total * 100",
    hide_progress_msg=True,
    richtext_controls=True,
    #richtext_controls=True,
    terminal_font_family = 'Courier New', # for tabulate table nice formatation
    #dump_build_config=True,
    #load_build_config="gooey_config.json",
    default_size=(800, 750),
    timing_options={        
        'show_time_remaining':True,
        'hide_time_remaining_on_complete':True
        },
    tabbed_groups=True,
    navigation='Tabbed',
    header_bg_color = '#95ACC8',
    #body_bg_color = '#95ACC8',
    menu=[{
        'name': 'File',
        'items': [{
                'type': 'AboutDialog',
                'menuTitle': 'About',
                'name': 'renamensensorsspl',
                'description': 'Rename tool for sensors using the spreadsheet generated by splsensors',
                'version': '0.2.0',
                'copyright': '2020',
                'website': 'https://github.com/Shadoward/renamesensors-spl',
                'developer': 'patrice.ponchant@fugro.com',
                'license': 'MIT'
                }]
        },{
        'name': 'Help',
        'items': [{
            'type': 'Link',
            'menuTitle': 'Documentation',
            'url': ''
            }]
        }]
    )

def main():
    desc = "Rename tool for sensors using the spreadsheet generated by splsensors"    
    parser = GooeyParser(description=desc)
    
    mainopt = parser.add_argument_group('Full Rename Options', gooey_options={'columns': 1})
    lnopt = parser.add_argument_group('LineName Rename Options', gooey_options={'columns': 1})
    revertopt = parser.add_argument_group('Reverse Renaming Options', 
                                          description='This option is to be used in csae or you need to rename back the renamed files', 
                                          gooey_options={'columns': 1})
     
    # Full Rename Arguments
    mainopt.add_argument(
        '-i',
        '--xlsxFile', 
        dest='xlsxFile',       
        metavar='sheets_combined.xlsx File Path', 
        help='This is the merge file with all the Final spreadsheet generated by the splsensors tool.\n Please be sure that you have QC the spreadsheet!',
        widget='FileChooser',
        gooey_options={'wildcard': "Excel Files(.xlsx)|*.xlsx"})
    
    mainopt.add_argument(
        '-n', '--filename', 
        dest='filename',
        metavar='Filename', 
        widget='TextField',
        type=str,
        help='File name to be use to rename the file.\nYou can use the following wildcard to automate the linename:\n[V] = vessel;\n[LN] = Linename from SPL;\n[ST] = Sensor Type;\n[SD] = Start Date from the sensor (yyyymmdd_hhmmss);\n[N] = sequence number if the sensor have split.\ne.g: [V]_[LN]_[SD]_ASOW.')       

    mainopt.add_argument(
        '-s', '--seqnumber',
        dest='seqnumber',
        metavar='Sequence Number Format', 
        widget='TextField',
        #default='FugroBrasilis-CRP-Position',
        help='Sequence number format for split files. e.g.: 000 or 00')
    
    mainopt.add_argument(
        '-t', '--timeFormat',
        dest='timeFormat',
        metavar='Timestamp Format', 
        widget='TextField',
        default='%Y%m%d_%H%M',
        help='Timestamp format to be use in the file name.\ne.g.: %Y%m%d_%H%M%S --> 20201224_152432')
    
    # LineName Rename Arguments
    lnopt.add_argument(
        '-I',
        '--xlsxFile2', 
        dest='xlsxFile2',       
        metavar='sheets_combined.xlsx File Path', 
        help='This is the merge file with all the Final spreadsheet generated by the splsensors tool.\n Please be sure that you have QC the spreadsheet!',
        widget='FileChooser',
        gooey_options={'wildcard': "Excel Files(.xlsx)|*.xlsx"})
       
    # Additional Arguments
    revertopt.add_argument(
        '-r',
        '--reverseFile', 
        dest='reverseFile',       
        metavar='reverse_rename.csv File Path', 
        help='This is the file generate by this tool after you have rename the files.\nThe file can be edited to remove what you do not need to reverse back the name.',
        widget='FileChooser',
        gooey_options={'wildcard': "Comma separated file (*.csv)|*reverse*.csv"})

    # Use to create help readme.md. TO BE COMMENT WHEN DONE
    # if len(sys.argv)==1:
    #    parser.print_help()
    #    sys.exit(1)   
        
    args = parser.parse_args()
    process(args, cmd)

def process(args, cmd):
    """
    Uses this if called as __main__.
    """
    xlsxFile = args.xlsxFile
    xlsxFile2 = args.xlsxFile2 
    filename = args.filename
    reverseFile = args.reverseFile
    seqnumber = args.seqnumber if args.seqnumber is not None else "000"
    timeFormat = args.timeFormat
    Fseqnumber = len(seqnumber)

    ##########################################################
    #              Checking before continuing                #
    ##########################################################      
    # Check if Final merge spreadsheet is selected
    if not xlsxFile and not xlsxFile2:
        print ('')
        sys.exit(stylize('Final spreadsheet was not selected. Please select the Final spreadsheet created by splsensors tool, quitting', fg('red')))
    
    if xlsxFile: 
        try:
            xl = pd.read_excel(xlsxFile, sheet_name=None, engine='openpyxl')
            sheets = xl.keys()
        except IOError:
                print('')
                sys.exit(stylize(f'The following file is lock ({xlsxFile}). Please close the files, quitting.', fg('red')))
    
    if xlsxFile2: 
        try:
            xl = pd.read_excel(xlsxFile2, sheet_name=None, engine='openpyxl')
            sheets = xl.keys()
        except IOError:
                print('')
                sys.exit(stylize(f'The following file is lock ({xlsxFile}). Please close the files, quitting.', fg('red')))       
    
    if not any(key in list(sheets) for key in ['Full_List', 'Rename_LN']):
        print ('')
        sys.exit(stylize('Correct Final spreadsheet was not selected. Please select a correct Final spreadsheet created by splsensors tool, quitting', fg('red')))
     
    # Check if filename is defined    
    if xlsxFile and not filename:
        print ('')
        sys.exit(stylize('Filename empty. Please define the new file name, quitting', fg('red')))
    

    ##########################################################
    #                   Reverse Naming                       #
    ##########################################################  

    if args.reverseFile is not None:
        print('', flush = True)
        print('##################################################', flush = True)
        print('RENAMING BACK THE FILES. PLEASE WAIT....', flush = True)
        print('##################################################', flush = True)
        now = datetime.datetime.now() # record time of the subprocess
        
        dfreverse = pd.read_csv(reverseFile, usecols=["OldName","NewName"])
        
        pbar = tqdm(total=len(dfreverse)) if cmd else print(f"Renaming the files.\nNote: Output show file counting every {math.ceil(len(dfreverse)/10)}") #cmd vs GUI 
        for index, row in dfreverse.iterrows():
            oldname = row['OldName']
            newname = row['NewName']
            if os.path.exists(newname):            
                os.rename(newname, oldname)      
            progressBar(cmd, pbar, index, dfreverse)
        
        print('', flush = True)
        print('##################################################', flush = True)
        print('SUMMARY', flush = True)
        print('##################################################', flush = True)       
        print('', flush = True)
        print(f'A total of {len(dfreverse)} files were renamed back.\n', flush = True)
        print("Subprocess Duration: ", (datetime.datetime.now() - now), flush = True)
        sys.exit()
        

    # Remove old reverse log
    if xlsxFile:
        xlsxFilePath = os.path.dirname(os.path.abspath(xlsxFile))
    else:
        xlsxFilePath = os.path.dirname(os.path.abspath(xlsxFile2))
    if os.path.exists(xlsxFilePath + '\\reverse_rename.csv'):
        try:
            os.remove(xlsxFilePath + '\\reverse_rename.csv')
        except IOError:
            print('')
            sys.exit(stylize(f'The reverse_rename.csv file is lock. Please close the files, quitting.', fg('red')))      

    ##########################################################
    #                 Listing the files                      #
    ##########################################################  
    print('', flush = True)
    print('##################################################', flush = True)
    print('READING THE SPREADSHEET AND RENAMING THE FILES.', flush = True)
    print('PLEASE WAIT....', flush = True)
    print('##################################################', flush = True)

    if args.xlsxFile2 is not None:
        dfreverse = lnrename(xlsxFile2)
    else:
        dfreverse = fullrename(xlsxFile, timeFormat, Fseqnumber, filename)
          
    dfreverse.to_csv(xlsxFilePath + '\\reverse_rename.csv', index=True)  
    
    print('', flush = True)
    print('##################################################', flush = True)
    print('SUMMARY', flush = True)
    print('##################################################', flush = True)       
    print('', flush = True)
    print(f'A total of {len(dfreverse)} files were renamed.\n', flush = True)
    print('')
    print(f'Reverse Log can be found in {xlsxFilePath}.\n', flush = True)
          
##########################################################
#                       Functions                        #
########################################################## 
def lnrename(xlsxFile2):
    dfRename = pd.read_excel(xlsxFile2, sheet_name='Rename_LN', engine='openpyxl')
    dfreverse = pd.DataFrame(columns = ["OldName", "NewName"])    
    
    pbar = tqdm(total=len(dfRename)) if cmd else print(f"Renaming the files.\nNote: Output show file counting every {math.ceil(len(dfRename)/10)}") #cmd vs GUI 
    
    for index, row in dfRename.iterrows():
        FilePath = row['FilePath']
        path = os.path.dirname(os.path.abspath(FilePath))
        ext = os.path.splitext(os.path.basename(FilePath))[1]
        newname = row['New LineName']
        
        # Renaming
        if os.path.exists(FilePath):
            os.rename(FilePath, os.path.join(path, newname + ext))                    
            # Generate log reverse
            dfreverse = dfreverse.append(pd.Series([FilePath, os.path.join(path, newname + ext)], 
                                                    index=dfreverse.columns), ignore_index=True)         

        progressBar(cmd, pbar, index, dfRename)

    return dfreverse
    
    
def fullrename(xlsxFile, timeFormat, Fseqnumber, filename):
    dfRename = pd.read_excel(xlsxFile, sheet_name='Full_List', engine='openpyxl')
    coldrop = ['Summary', 'Difference Start [s]', 'Session Start', 'Session End', 'Session Name', 'Session MaxGap', 'Sensor FileName']
    dfRename.drop(columns=coldrop, inplace=True)
    dfRename.dropna(subset=['SPL LineName'], inplace = True)
    dfRename['Incremental'] = None
    # https://stackoverflow.com/questions/59875334/add-incremental-value-for-duplicates
    # https://stackoverflow.com/questions/56137222/pandas-group-by-then-apply-throwing-a-warning # Try using .loc[row_indexer,col_indexer] = value instead
    dftmp = dfRename[dfRename.duplicated(subset='SPL LineName', keep=False)]
    dfRename.loc[dftmp.index, 'Incremental'] = dftmp.groupby(['SPL LineName']).cumcount() + 1 
    dfRename.update(dftmp)
    dfreverse = pd.DataFrame(columns = ["OldName", "NewName", "Incremental", "Sensor Type", "Vessel Name"])
    
    pbar = tqdm(total=len(dfRename)) if cmd else print(f"Renaming the files.\nNote: Output show file counting every {math.ceil(len(dfRename)/10)}") #cmd vs GUI 
    
    for index, row in dfRename.iterrows():
        FilePath = row['FilePath']
        path = os.path.dirname(os.path.abspath(FilePath))
        ext = os.path.splitext(os.path.basename(FilePath))[1]
        SensorStart = datetime.datetime.strftime(row['Sensor Start'], timeFormat)
        VesselName = row['Vessel Name']
        SensorType = row['Sensor Type']
        SPLLineName = row['SPL LineName']
        Incremental = row['Incremental']
        # https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
        if Incremental is not None:
            seqnumber = str(int(Incremental)).zfill(Fseqnumber)
            rep = {"[V]": VesselName, "[LN]": SPLLineName, "[ST]": SensorType, "[SD]": SensorStart, "[N]": str(seqnumber)} # define desired replacements here
        else:
            rep = {"[V]": VesselName, "[LN]": SPLLineName, "[ST]": SensorType, "[SD]": SensorStart, "[N]": ''}
        
        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))
        if '[N]' in filename:
            newname = pattern.sub(lambda m: rep[re.escape(m.group(0))], filename)
        else:
            seqnumber = str(int(Incremental)).zfill(3) if Incremental else None
            newname = pattern.sub(lambda m: rep[re.escape(m.group(0))], filename) + '_' + str(seqnumber)

        newname = newname.replace('__', '_').replace('_None', '')
        
        # Renaming
        if os.path.exists(FilePath):
            os.rename(FilePath, os.path.join(path, newname + ext))                    
            # Generate log reverse
            dfreverse = dfreverse.append(pd.Series([FilePath, os.path.join(path, newname + ext), Incremental, SensorType, VesselName], 
                                                    index=dfreverse.columns), ignore_index=True)            
        #print(f'OldName: {oldname}\nNewName: {newname}')
        progressBar(cmd, pbar, index, dfRename)
    return dfreverse

# from https://www.pakstech.com/blog/python-gooey/
def print_progress(index, total):
    print(f"progress: {index+1}/{total}", flush = True)
    
# Progrees bar GUI and CMD
def progressBar(cmd, pbar, index, ls):
    if cmd:
        pbar.update(1)
    else:
        print_progress(index, len(ls)) # to have a nice progress bar in the GU            
        if index % math.ceil(len(ls)/10) == 0: # decimate print
            print(f"Files Process: {index+1}/{len(ls)}", flush = True) 

##########################################################
#                        __main__                        #
########################################################## 
if __name__ == "__main__":
    now = datetime.datetime.now() # time the process
    main()
    print('')
    print("Process Duration: ", (datetime.datetime.now() - now)) # print the processing time. It is handy to keep an eye on processing performance.