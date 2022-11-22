# Copyright 2017 Battelle Energy Alliance, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Created on 2022-Nov-22

This is a CodeInterface for the StarCCM+ code.

"""

import os
import glob
import re
import numpy as np
import xarray as xr
import pandas as pd

from ..Generic.GenericCodeInterface import GenericCode

class StarCCM(GenericCode):
  """
    This class is used to run the starccm+ code
  """

  def finalizeCodeOutput(self, command, codeLogFile, subDirectory):
    """
      Convert csv information to RAVEN's prefered formats
      @ In, command, ignored
      @ In, codeLogFile, ignored
      @ In, subDirectory, string, the subdirectory where the information is.
      @ Out, dictionary, dict, the returned information format:
        {field : array-like} or {field : dict} (read by pd.DataFrame.from_dict)
    """
    outDict = {}
    print("finalizeCodeOutput", command, codeLogFile, subDirectory)
    names = glob.glob(os.path.join(subDirectory, "XYZ_Internal_Table_Fluid_table_*.csv"))
    dataDict = {}
    for name in names:
      intRE = ".*_([0-9]+).csv"
      floatRE = ".*_([0-9]+\.[0-9]*[eE][+-][0-9]+).csv"
      intMatch = re.match(intRE, name)
      if intMatch:
        value = int(intMatch.group(1))
      else:
        floatMatch = re.match(floatRE, name)
        if floatMatch:
          value = float(floatMatch.group(1))
      if not intMatch and not floatMatch:
        print("no id found in",name)
        continue
      data = pd.read_csv(name)
      dataDict[value] = data
    #print("names", names)
    #print("dataDict", dataDict)
    sortedKeys = sorted(dataDict.keys())
    print("keys", sortedKeys)
    columns = dataDict[sortedKeys[0]].columns
    for column in columns:
      outDict[column] = []
    outDict['index'] = []
    outDict['autoindex'] = []
    for key in sortedKeys:
      data = dataDict[key]
      length = data.shape[0]
      outDict['index'].extend([key]*length)
      prev = len(outDict['autoindex'])
      outDict['autoindex'].extend(range(prev, prev+length))
      for column in columns:
        outDict[column].extend(data[column])
    return outDict
    #out = super().finalizeCodeOutput(command, codeLogFile, subDirectory)
    #print("out", out, type(out))
    #return out
