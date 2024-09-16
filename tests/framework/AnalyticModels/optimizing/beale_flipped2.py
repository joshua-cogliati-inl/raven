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
# from https://en.wikipedia.org/wiki/Test_functions_for_optimization
#
# takes input parameters x,y
# returns value in "ans"
# optimal maximum at f(3,0.5) = 0
# parameter range is -4.5 <= x,y <= 4.5

def evaluate(x,y):
  beale = (1.5 - x + x*y)**2 + (2.25 - x + x*y*y)**2 + (2.625 - x + x*y*y*y)**2
  return -1.0 * beale

def run(self,Inputs):
  self.obj1 = -1* evaluate(self.x,self.y)
  self.obj2 = evaluate(self.x,self.y)