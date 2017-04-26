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
import math

def initial_function(monitored, controlled, auxiliary):
  #print("monitored",monitored,"controlled",controlled,"auxiliary",auxiliary)
  auxiliary.Dummy1 = distributions.ANormalDistribution.getDistributionRandom()
  mult = 1.0
  auxiliary.func = 0
  controlled.pipe_Area = mult*controlled.pipe_Area
  controlled.pipe_Hw = mult*controlled.pipe_Hw
  controlled.pipe_Tw = mult*controlled.pipe_Tw
  return

def control_function(monitored, controlled, auxiliary):
  #print("monitored",monitored,"controlled",controlled,"auxiliary",auxiliary)
  mult = 1.0
  controlled.pipe_Area = mult*controlled.pipe_Area
  controlled.pipe_Hw = mult*controlled.pipe_Hw
  controlled.pipe_Tw = mult*controlled.pipe_Tw
  auxiliary.func     = math.sin(monitored.time+auxiliary.Dummy1)
  return
