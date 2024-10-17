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
Module that contains a SimulationMode for Slurm and mpiexec
"""

import os
import math
import string
from ravenframework import Simulation

#For the mode information
modeName = "slurm"
modeClassName = "SlurmSimulationMode"

class SlurmSimulationMode(Simulation.SimulationMode):
  """
    SlurmSimulationMode is a specialized class of SimulationMode.
    It is aimed to distribute the runs on a Slurm cluster
  """

  def __init__(self, *args):
    """
      Constructor
      @ In, args, list, unused positional arguments
      @ Out, None
    """
    super().__init__(*args)
    #figure out if we are in Slurm
    self.__inSlurm = "SLURM_JOB_ID" in os.environ
    self.__nodefile = False
    self.printTag = 'SLURM SIMULATION MODE'

  def modifyInfo(self, runInfoDict):
    """
      This method is aimed to modify the Simulation instance in
      order to distribute the jobs using slurm
      @ In, runInfoDict, dict, the original runInfo
      @ Out, newRunInfo, dict, of modified values
    """
    newRunInfo = {}
    workingDir = runInfoDict['WorkingDir']
    if self.__nodefile or self.__inSlurm:
      if not self.__nodefile:
        nodeFile = os.path.join(workingDir,"slurmNodeFile_"+str(os.getpid()))
        #generate nodeFile
        os.system("srun --overlap -- hostname > "+nodeFile)
      else:
        nodefile = self.__nodefile
      self.raiseADebug('Setting up remote nodes based on "{}"'.format(nodefile))
      lines = open(nodefile,"r").readlines()
      #XXX This is an undocumented way to pass information back
      newRunInfo['Nodes'] = list(lines)
