#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 25 03:10:24 2017

"""

import pandas as pd
from scipy.stats.mstats import winsorize
import statsmodels.api as sm
import statsmodels.formula.api as smf
from tqdm import tqdm
import seaborn as sns

percent = pd.read_csv("percentage_data.csv", sep='\t')
verb_list = percent.columns[8:]

# Do two version of data. One is percentage, meaning ratio in a book in one gender.
# Another is original count. 

def show_verb_ratio_plot(percent_mi, verb, plot=0, limits=(0,0.01)):
    df_verb = percent_mi.ix[:,verb].unstack()
    col = df_verb.columns
    wins = pd.DataFrame(winsorize(df_verb, limits=limits))
    wins.columns = col
    if plot==1:
        g = wins.plot.scatter('F','M',xlim=[0,max(wins.F)],ylim=[0,max(wins.M)],title=verb)
    elif plot==2:
        g = sns.lmplot(x='F',y='M',data=wins,fit_reg=True) 
        g = g.set(xlim=(0, max(wins.F)), ylim=(0, max(wins.M)))#, xticks=[10, 30, 50], yticks=[2, 6, 10])
        
    results = smf.ols('M~F-1', data=wins).fit()
    
    return results   #small to be female word, large - male
    
percent_mi = percent.set_index(['book','pn_gender'])
verb_result = pd.DataFrame({})
for verb in tqdm(verb_list):
    results = show_verb_ratio_plot(percent_mi, verb)
    verb_result = verb_result.append([[verb, results.params.F,results.rsquared,results.tvalues.F]])
    
verb_result.columns=['verb','coeff','rsquared','tvalue']
verb_result.to_csv('verb_result.csv',index=False)



#==============================================================================
# Method 2
#==============================================================================

zero_row = percent.ix[:,8:].apply(lambda x:len(x[x>0]), axis=1)
percent['least_unit'] = percent.ix[~(zero_row==0),8:].apply(lambda x: min(x[x>0]), axis=1)
percent.least_unit = percent['least_unit'].fillna(1)

wf_count = percent.ix[:,8:].apply(lambda x: x/x.least_unit, axis=1)
wf_count.index = percent_mi.index
wf_count_int = wf_count.round(0)
wf_count_int.apply(sum, axis=0).sort_values().to_csv('word_total_freq.csv')

check_diff = abs(wf_count - wf_count_int>1e-3).sum(1)
check_diff[check_diff>0]

verb_result2 = pd.DataFrame({})
for verb in tqdm(verb_list):
    results = show_verb_ratio_plot(wf_count_int, verb)
    verb_result2 = verb_result2.append([[verb, results.params.F,results.rsquared,results.tvalues.F]])
    
verb_result2.columns=['verb','coeff','rsquared','tvalue']
verb_result2.to_csv('verb_result_2.csv',index=False)


#==============================================================================
# Rank correlation test
#==============================================================================
c = ['verb','coeff']
feature_df = pd.read_csv('feature_data.csv')
feature = feature_df[['id','1-score']] # positive male, negative female
feature.columns = c

m = pd.merge(verb_result[c], verb_result2[c], how='outer', on='verb')
m = m.merge(feature, how='outer', on='verb')
m = m.fillna(0)
m.columns = ['verb','coeff_percentage','coeff_count_number','coeff_NSC']

m.corr('kendall')
m.corr('spearman')
m.to_csv('verb_merge.csv')

feature.sort_values('coeff',inplace=1)
verb_result.sort_values('coeff',inplace=1)
verb_result2.sort_values('coeff',inplace=1)
a=pd.merge(feature[:50], verb_result[c][:50], how='inner', on='verb')
b=pd.merge(feature[-50:], verb_result[c][-50:], how='inner', on='verb')
