# Copyright 2025 Battelle Energy Alliance, LLC
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
  Created on May 13, 2025
  @author: cogljj
  Class for pyKAN used for Kolmogorov-Arnold Networks
"""

#External Modules------------------------------------------------------------------------------------
import kan
#External Modules End--------------------------------------------------------------------------------


#Internal Modules------------------------------------------------------------------------------------
from ..utils import InputData, InputTypes
from .SupervisedLearning import SupervisedLearning
#Internal Modules End--------------------------------------------------------------------------------

class KAN(SupervisedLearning):
  """
    Class for pyKAN used for Kolmogorov-Arnold Networks
  """

  @classmethod
  def getInputSpecification(cls):
    """
      Method to get a reference to a class that specifies the input data for
      class cls.
      @ In, cls, the class for which we are retrieving the specification
      @ Out, inputSpecification, InputData.ParameterInput, class to use for
        specifying input of cls.
    """
    inputSpecification = super().getInputSpecification()
    # number and size of inner layers
    inputSpecification.addSub(InputData.parameterInputFactory('layers',contentType=InputTypes.IntegerListType,
            descr="Integer list of number of nodes in each interior layer."))
    # number of steps (and prune) order
    inputSpecification.addSub(InputData.parameterInputFactory('steps',contentType=InputTypes.StringListType,
            descr="List of steps to follow in training.  Integers are number of fitting steps to run, 'prune' asks for the network to be pruned."))
    # seed
    inputSpecification.addSub(InputData.parameterInputFactory('seed',contentType=InputTypes.IntegerType,
            descr="Seed to use to initialize KAN network"))
    return inputSpecification

  def __init__(self):
    """
      A constructor that will appropriately intialize a keras deep neural network object
      @ In, None
      @ Out, None
    """
    super().__init__()
    self.kan = None #Store the kan network here
    self.layers = [] #Store the number of nodes in each layer
    self.seed = None #Integer seed if not none
    self.steps = [] #List of steps to follow

  def _handleInput(self, paramInput):
    """
      Function to handle the common parts of the model parameter input.
      @ In, paramInput, InputData.ParameterInput, the already parsed input.
      @ Out, None
    """
    super()._handleInput(paramInput)
    for sub in paramInput.subparts:
      if sub.getName().lower() == "seed":
        self.seed = sub.value
      elif sub.getName().lower() == "steps":
        self.steps = sub.value
        for i in range(len(self.steps)):
          try:
            self.steps[i] = int(self.steps[i])
          except ValueError:
            pass
      elif sub.getName().lower() == "layers":
        self.layers = sub.value
    print(f"{self.layers=} {self.steps=} {self.seed=}")

  def __confidenceLocal__(self,featureVals):
    """
      This should return an estimation of the quality of the prediction.
      @ In, featureVals,numpy.array, 2-D or 3-D numpy array, [n_samples,n_features]
        or shape=[numSamples, numTimeSteps, numFeatures]
      @ Out, confidence, float, the confidence
    """
    self.raiseAnError(NotImplementedError,'KerasBase   : __confidenceLocal__ method must be implemented!')

  def __evaluateLocal__(self,featureVals):
    """
      Perform regression on samples in featureVals.
      classification labels will be returned based on num_classes
      @ In, featureVals, numpy.array, 2-D for static case and 3D for time-dependent case, values of features
      @ Out, prediction, dict, predicted values
    """
    #XXX implement

  def __resetLocal__(self):
    """
      Reset ROM. After this method the ROM should be described only by the initial parameter settings
      @ In, None
      @ Out, None
    """
    #XXX implement

  def __returnCurrentSettingLocal__(self):
    """
      Returns a dictionary with the parameters and their current values
      @ In, None
      @ Out, params, dict, dictionary of parameter names and current values
    """
    #XXX implement

  def __returnInitialParametersLocal__(self):
    """
      Returns a dictionary with the parameters and their initial values
      @ In, None
      @ Out, params, dict,  dictionary of parameter names and initial values
    """
    #XXX implement

  def _train(self,featureVals,targetVals):
    """
      Perform training on samples in featureVals with responses y.
      For an one-class model, +1 or -1 is returned.
      @ In, featureVals, {array-like, sparse matrix}, shape=[n_samples, n_features],
        an array of input feature or shape=[numSamples, numTimeSteps, numFeatures]
      @ Out, targetVals, array, shape = [n_samples], an array of output target
        associated with the corresponding points in featureVals
    """
    #XXX implement
