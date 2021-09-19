# This file contains the code to produce the output files

# import libraries 
import pandas as pd
import replication_code_function

# load data
complete_data = pd.read_csv('Data/complete_data.csv.gz', 
                                  compression='gzip')
terminals_ownership = pd.read_csv(
  'Data/only_uk_terminal_ownership.csv.gz', compression='gzip')

# CREATE SAMPLES  

# Sample 1: Terminals as UK companies that own none,
#     and UK companies that own < 50% of others (+ own 'NaN'%)  
# Sample 2: Terminals just as UK companies that own none.  
# Sample 3: Terminals just as UK companies that own < 50% 
#     of others (+ own 'NaN')
# Sample 4: Sample 1 but branches 

# all data, removing branches
sample1 = complete_data[complete_data.entityType != "Q"] 
# series containing BvD of companies that own others
shareholder_terminals = terminals_ownership.loc[pd.notnull(
  terminals_ownership["subsidiaryBvD"]), "BvD"].drop_duplicates() 
non_shareholder_terminals = terminals_ownership.loc[pd.isnull(
  terminals_ownership["subsidiaryBvD"]), "BvD"].drop_duplicates()
#filter for not in shareholder_terminals  
sample2 = sample1.loc[~sample1["BvD.1"].isin(
  set(shareholder_terminals))] 
#filter for in shareholder_terminals
sample3 = sample1.loc[~sample1["BvD.1"].isin(set(
    non_shareholder_terminals))] 
non_branch_terminals = set(terminals_ownership["BvD"]) & set(
  complete_data.loc[complete_data["entityType"] != "Q", "BvD.1"])
# remove non branch terminals
sample4 = complete_data[~complete_data.isin(non_branch_terminals)]   


samples = [sample1, sample2, sample3, sample4]
sample_names = ["1", "2", "3", "4"]


# RUN SAMPLES THROUGH FUNCTION

for i in range(len(samples)):
  
  sample = samples[i] 
  sample_name = sample_names[i]
  replication_code_function.replication_code(sample, sample_name)


