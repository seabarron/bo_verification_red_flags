# This file creates a function which each sample
# passed to in the main file

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import copy 
import openpyxl
from time import time

def replication_code(df, sample_name):
  "Produces the outcomes for the given sample dataframe"
  
   # load terminals data
  terminals_bvd = pd.read_csv('Data/only_uk_terminal.csv.gz',
                  compression='gzip')
  
  ### CREATING THE CHAINS AND BVD TABLE 
  
  
  
  # remove unwanted entity types
  non_layer_entities = {"I", "D", "L", "Z", "M"}
  #layer or entity=null
  layer_entities = df.loc[~df["entityType"].isin(
    non_layer_entities)] 
  # while loop faster with None than condition != NaN 
  layer_entities["shareholderBvD"] = layer_entities[
    "shareholderBvD"].replace({np.nan: None}) 
  layer_entities_bvd = set(layer_entities["BvD.1"])
  #Create dictionaries
  # each column is a dictionary where key=bvd
  dics = layer_entities.set_index("BvD.1").to_dict() 
  shareholders = dics["shareholderBvD"]
  #Check terminals with data
  # create a set with all the terminals (i.e is in both dataframe)
  terminals_data = set(df["BvD.1"]) & set(terminals_bvd["BvD"]) 
  start = time()
  chains = []
  #Create the chains for each channel independently 
  for count_t,terminal in enumerate(terminals_data):
    if count_t%1000 == 0:
      print("{} ({}*100%, {}s elapsed)".format(
        count_t,count_t/len(terminals_data),time()-start))
    #Add all the shareholders to the chain
    chain = [terminal]
    shareholder = shareholders.get(terminal)
    while (shareholder is not None) and (
      shareholder in layer_entities_bvd) and (shareholder not in chain):  
      # while shareholder is in the dict, is a layer entity,
      #and not in chain (preventing loops)
      chain.append(shareholder)
      shareholder = shareholders.get(shareholder)
    #Add the chain to the list of chains
    chains.append(chain)
    
  # calculate number of layers
  num_layers = []  
  for chain in chains:
    num_layers.append(len(chain)-1)
  
  #get list for column names
  layer_names = []
  i = 0
  while i <= max(num_layers): 
    layer_names.append("layer"+ str(i))
    i = i+1 
  #convert list to dataframe  
  bvd_by_layer = pd.DataFrame(chains, columns=layer_names)  


  # CREATING COUNTRY AND ENTITY TABLES

  #get dictionaries
  country = dics["iso2"]                         
  entity = dics["entityType"]
  
  chains_iso2 = []   # create empty list for country chains 
  chains_entity = []
  iso2_list = []              # create a list for each ownership chain
  entity_list = []
  for i in range(len(chains)):                                 
    for j in range(len(chains[i])):            # for each element in each chain     
      iso2_list.append(country[chains[i][j]])# add country for this element, from dictionary
      entity_list.append(entity[chains[i][j]])  
    chains_iso2.append(iso2_list)
    chains_entity.append(entity_list)
    iso2_list = []
    entity_list = [] 
  print("complete")

  # convert lists to dataframes 
  country_by_layer = pd.DataFrame(chains_iso2, columns=layer_names)  
  entity_by_layer = pd.DataFrame(chains_entity, columns=layer_names)

  # write csv
  bvd_by_layer.to_csv('output/sample_{}_bvd_by_layer.csv.gz'.format(sample_name), compression = 'infer')
  country_by_layer.to_csv('output/sample_{}_country_by_layer.csv.gz'.format(sample_name), compression = 'infer')
  entity_by_layer.to_csv('output/sample_{}_entity_by_layer.csv.gz'.format(sample_name), compression = 'infer')




  ### CREATING FEATURES
  
  # make a table that includes all features per chain 
  
  # terminal bvd
  s1 = bvd_by_layer["layer0"].rename("terminal_bvd") 
  #number of layers (convert to series) 
  s2 = pd.Series(num_layers, name="num_layers") 
  # merge to create dataframe 
  chain_features = pd.concat([s1, s2], axis=1).reset_index() 
  
  # create terminal features from df 
  chain_features = chain_features.merge(df[[
    "BvD.1", "entityType", "operatingRevenue", "numberEmployees",
    "GUO50company", "GUO50"]], how="left", left_on="terminal_bvd",
    right_on="BvD.1").rename(columns={"entityType":"terminal_entity_type",
    "operatingRevenue":"terminal_revenue", 
    "numberEmployees":"terminal_num_employees",
    "GUO50company":"guo_company", "GUO50":"guo_bvd"})
  
  # create guo features from df 
  chain_features = chain_features.merge(df[["BvD.1", "entityType", "iso2"]],
    how="left", left_on="guo_bvd", right_on="BvD.1").rename(columns={
    "entityType":"guo_entity_type", "iso2":"guo_iso2"})
  
  chain_features = chain_features.drop(columns=["BvD.1_x", "BvD.1_y"])
  
  
  # filter for number of layers = 0,
  # this is not total with 0 layers so would be confusing  
  chain_features = chain_features.loc[chain_features["num_layers"] > 0]
  
  # layers in UK  
  sub_country_by_layer = copy.copy(country_by_layer.iloc[:, 1:])
  for i in range(len(layer_names)-1):
    sub_country_by_layer.loc[sub_country_by_layer[
      "layer"+str(i+1)] != "GB", ["layer"+str(i+1)]] = 0 
  sub_country_by_layer = sub_country_by_layer.replace("GB", 1)
  
  s3 = pd.Series(sub_country_by_layer.sum(axis=1), name="num_uk_layers")
  chain_features = pd.concat([chain_features, s3], axis=1) # add to table
  
  # layers in uk per layer
  chain_features["uk_layers_per"] = (
    chain_features["num_uk_layers"]/chain_features["num_layers"])*100
  
  # cut off early, due to no 50% shareholder? i.e does last in chain = GUO50C 
  
  # find last company in each chain
  # create new dataframe
  final_bvds = pd.DataFrame(columns=["terminal_bvd", "final_bvd_in_chain"]) 
  i = 0 
  while i < max(num_layers):
     #filter for has 1 layer, select final layer
    final_bvd = bvd_by_layer.loc[(bvd_by_layer["layer"+str(i)].notnull()) &
      (bvd_by_layer["layer"+str(i+1)].isnull()), ["layer0", "layer"+str(i)]]
      # rename columns
    final_bvd.columns = ["terminal_bvd", "final_bvd_in_chain"]
      # concat to final bvds
    final_bvds = pd.concat([final_bvds, final_bvd], axis=0)  
    i = i+1
  # for final layer:
  #filter for has 1 layer, select final layer
  final_bvd = bvd_by_layer.loc[(bvd_by_layer["layer"+str(i)].notnull()), [
    "layer0", "layer"+str(i)]]
  # rename columns  
  final_bvd.columns = ["terminal_bvd", "final_bvd_in_chain"] 
  # concat to final bvds
  final_bvds = pd.concat([final_bvds, final_bvd], axis=0) 
  final_bvds = final_bvds.reset_index()
  # merge final_bvds with chain_features
  # create cut off variable
  chain_features = chain_features.merge(final_bvds, how="left",
    on="terminal_bvd") 
  chain_features["cut_off"] = np.where(chain_features[
    "final_bvd_in_chain"] == chain_features["guo_company"], 0, 1)

  # write csv
  chain_features.to_csv('output/sample_{}_chain_features.csv.gz'.format(sample_name), compression = 'infer')
  

  ### PLOTS 

  fig, axs = plt.subplots(3, 1) 
  fig.set_size_inches(6, 18)
  
  # number of layers
  chain_features["num_layers"].plot.hist(bins=int(max(
    chain_features["num_layers"])), ax=axs[0])
  axs[0].set_title("Number of Layers")
  axs[0].set_xlim([1,max(chain_features["num_layers"])]) 
  axs[0].set_xticks(range(1, int(max(chain_features["num_layers"])+1), 1))
  
  # number of UK layers
  chain_features["num_uk_layers"].plot.hist(
    bins=max(chain_features["num_uk_layers"]), ax=axs[1])
  axs[1].set_title("Number of UK Layers")
  axs[1].set_xticks(range(0, max(chain_features["num_uk_layers"])+1, 1))
  
  # percentage of UK layers
  chain_features["uk_layers_per"].plot.hist(
    bins=range(0, 110, 10), ax=axs[2])
  axs[2].set_title("Percentage of Layers in UK")
  axs[2].set_xticks(range(0, 110, 10))
  
  # adjust placement of subplots - stops titles overlapping
  fig.subplots_adjust(left=0.2, hspace= 0.5) 

  
  
  ### OUTPUTS 
  
  plt.savefig("output/sample_{}_histograms.png".format(sample_name), dpi = 150)

  print("replication_code finished") 
  
  return
