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
  Created on May 8, 2021

  @author: Andrea Alfonsi
"""

#External Modules--------------------------------------------------------------------------------
import copy
import gc
import numpy as np
import itertools
import time
from collections import defaultdict
from scipy.stats import spearmanr
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
#External Modules End----------------------------------------------------------------------------

#Internal Modules--------------------------------------------------------------------------------
from ...utils.mathUtils import compareFloats
from ...utils import InputData, InputTypes
from ...Decorators.Parallelization import Parallel
from .FeatureSelectionBase import FeatureSelectionBase
#Internal Modules End----------------------------------------------------------------------------

class RFE(FeatureSelectionBase):
  """
    Feature ranking with recursive feature elimination.
    Given an external estimator that assigns weights to features (e.g., the
    coefficients of a linear model), the goal of recursive feature elimination
    (Augmented-RFE) is to select features by recursively considering smaller and smaller
    sets of features. First, the estimator is trained on the initial set of
    features and the importance of each feature is obtained through a
    ``feature_importances_``  property.
    Then, the least important features are pruned from current set of features.
    That procedure is recursively repeated on the pruned set until the desired
    number of features to select is eventually reached.

    References:
    Guyon, I., Weston, J., Barnhill, S., & Vapnik, V., "Gene selection
    for cancer classification using support vector machines",
    Mach. Learn., 46(1-3), 389--422, 2002.
  """

  needROM = True # the estimator is needed

  @classmethod
  def getInputSpecification(cls):
    """
      Method to get a reference to a class that specifies the input data for
      class cls.
      @ In, cls, the class for which we are retrieving the specification
      @ Out, inputSpecification, InputData.ParameterInput, class to use for
        specifying input of cls.
    """
    spec = super().getInputSpecification()
    spec.description = r"""The \xmlString{Augmented-RFE} (Recursive Feature Elimination) is a feature selection algorithm.
        Feature selection refers to techniques that select a subset of the most relevant features for a model (ROM).
        Fewer features can allow ROMs to run more efficiently (less space or time complexity) and be more effective.
        Indeed, some ROMs (machine learning algorithms) can be misled by irrelevant input features, resulting in worse
        predictive performance.
        Augmented-RFE is a wrapper-type feature selection algorithm. This means that a different ROM is given and used in the core of the
        method,
        is wrapped by Augmented-RFE, and used to help select features.
        \\Augmented-RFE works by searching for a subset of features by starting with all features in the training dataset and successfully
        removing
        features until the desired number remains.
        This is achieved by fitting the given ROME used in the core of the model, ranking features by importance,
        discarding the least important features, and re-fitting the model. This process is repeated until a specified number of
        features remains.
        When the full model is created, a measure of variable importance is computed that ranks the predictors from most
        important to least.
        At each stage of the search, the least important predictors are iteratively eliminated prior to rebuilding the model.
        Features are scored either using the ROM model (if the model provides a mean to compute feature importances) or by
        using a statistical method.
        \\In RAVEN the \xmlString{Augmented-RFE} class refers to an augmentation of the basic algorithm, since it allows, optionally,
        to perform the search on multiple groups of targets (separately) and then combine the results of the search in a
        single set. In addition, when the Augmented-RFE search is concluded, the user can request to identify the set of features
        that bring to a minimization of the score (i.e. maximimization of the accuracy).
        In addition, using the ``applyClusteringFiltering'' option, the algorithm can, using an hierarchal clustering algorithm,
        identify highly correlated features to speed up the subsequential search.
        """
    spec.addSub(InputData.parameterInputFactory('nFeaturesToSelect',contentType=InputTypes.IntegerType,
        descr=r"""Exact Number of features to select. If not inputted, ``nFeaturesToSelect'' will be set to $1/2$ """
        """of the features in the training dataset.""", default=None))
    spec.addSub(InputData.parameterInputFactory('maxNumberFeatures',contentType=InputTypes.IntegerType,
        descr=r"""Maximum Number of features to select, the algorithm will """
        """automatically determine the feature list to minimize a total score.""",
        default=None))
    spec.addSub(InputData.parameterInputFactory('onlyOutputScore',contentType=InputTypes.BoolType,
        descr=r"""If maxNumberFeatures is on, only output score should be"""
        """considered?.""",
        default=False))
    spec.addSub(InputData.parameterInputFactory('searchTol',contentType=InputTypes.FloatType,
        descr=r"""Relative tolerance for search! Only if maxNumberFeatures is set""",
        default=1e-4))
    spec.addSub(InputData.parameterInputFactory('applyClusteringFiltering',contentType=InputTypes.BoolType,
        descr=r"""Applying clustering correlation  before Augmented-RFE search?""",
        default=False))
    spec.addSub(InputData.parameterInputFactory('applyCrossCorrelation',contentType=InputTypes.BoolType,
        descr=r"""Applying cross correlation in case of subgroupping at the """
        """end of the Augmented-RFE""",
        default=False))
    spec.addSub(InputData.parameterInputFactory('step',contentType=InputTypes.FloatType,
        descr=r"""If greater than or equal to 1, then step corresponds to the (integer) number
        of features to remove at each iteration. If within (0.0, 1.0), then step
        corresponds to the percentage (rounded down) of features to remove at
        each iteration.""", default=1))
    subgroup = InputData.parameterInputFactory("subGroup", contentType=InputTypes.InterpretedListType,
        descr=r"""Subgroup of output variables on which to perform the search. Multiple nodes of this type"""
        """ can be inputted. The Augmented-RFE search will be then performed on each ``subgroup'' separately and then the"""
        """ the union of the different feature sets are used for the final ROM.""")
    spec.addSub(subgroup)

    return spec

  def __init__(self):
    super().__init__()
    self.printTag = 'FEATURE SELECTION - Augmented-RFE'
    self.estimator = None
    self.nFeaturesToSelect = None
    self.maxNumberFeatures = None
    self.searchTol = None
    self.applyClusteringFiltering = False
    self.onlyOutputScore = False
    self.applyCrossCorrelation = False
    self.step = 1
    self.subGroups = []

  def __getstate__(self):
    """
      Method for choosing what gets serialized in this class
      @ In, None
      @ Out, d, dict, things to serialize
    """
    d = copy.deepcopy(self.__dict__)
    return d

  def setEstimator(self, estimator):
    """
      Set estimator
      @ In, estimator, instance, instance of the ROM
      @ Out, None
    """
    self.estimator = estimator

  def _handleInput(self, paramInput):
    """
      Function to handle the common parts of the model parameter input.
      @ In, paramInput, InputData.ParameterInput, the already parsed input.
      @ Out, None
    """
    super()._handleInput(paramInput)
    nodes, notFound = paramInput.findNodesAndExtractValues(['whichSpace','step','nFeaturesToSelect','onlyOutputScore',
                                                            'maxNumberFeatures', 'searchTol','applyClusteringFiltering',
                                                            'applyCrossCorrelation'])
    assert(not notFound)
    self.step = nodes['step']
    self.nFeaturesToSelect = nodes['nFeaturesToSelect']
    self.maxNumberFeatures = nodes['maxNumberFeatures']
    self.searchTol = nodes['searchTol']
    self.applyClusteringFiltering = nodes['applyClusteringFiltering']
    self.onlyOutputScore = nodes['onlyOutputScore']
    self.applyCrossCorrelation = nodes['applyCrossCorrelation']
    self.whichSpace = nodes['whichSpace'].lower()
    # check if subgroups present
    for child in paramInput.subparts:
      if child.getName() == 'subGroup':
        self.subGroups.append(child.value)
    # checks
    if self.nFeaturesToSelect is not None and self.maxNumberFeatures is not None:
      raise self.raiseAnError(ValueError, '"nFeaturesToSelect" and "maxNumberFeatures" have been both set. They are mutually exclusive!' )
    if self.nFeaturesToSelect and self.nFeaturesToSelect > len(self.parametersToInclude):
      raise self.raiseAnError(ValueError, '"nFeaturesToSelect" > number of parameters in "parametersToInclude"!' )
    if self.maxNumberFeatures and self.maxNumberFeatures > len(self.parametersToInclude):
      raise self.raiseAnError(ValueError, '"maxNumberFeatures" > number of parameters in "parametersToInclude"!' )
    if self.step <= 0:
      raise self.raiseAnError(ValueError, '"step" parameter must be > 0' )
    if self.applyCrossCorrelation and not len(self.subGroups):
      self.raiseAWarning("'applyCrossCorrelation' requested but not subGroup node(s) is(are) specified. Ignored!")
      self.applyCrossCorrelation = False

  def __applyClusteringPrefiltering(self, X, y, mask, support_):
    """
      Apply clustering pre-filtering
      @ In, X, numpy.array, feature data (nsamples,nfeatures) or (nsamples, nTimeSteps, nfeatures)
      @ In, y, numpy.array, target data (nsamples,nTargets) or (nsamples, nTimeSteps, nTargets)
      @ In, mask, np.array, indeces of features to search within (parameters to include None if search is whitin targets)
      @ In, support_, np.array, boolean array of selected features
      @ Out, support_, np.array, boolean array of selected features
    """
    if self.whichSpace == 'feature':
      space = X[:, mask] if len(X.shape) < 3 else np.average(X[:, :,mask],axis=0)
    else:
      space = y[:, mask] if len(y.shape) < 3 else  np.average(y[:, :,mask],axis=0)

    # compute spearman
    # we fill nan with 1.0 (so the distance for such variables == 0 (will be discarded)
    corr = np.nan_to_num(spearmanr(space,axis=0).correlation,nan=1.0)
    corr = (corr + corr.T) / 2.
    np.fill_diagonal(corr, 1)
    # We convert the correlation matrix to a distance matrix before performing
    # hierarchical clustering using Ward's linkage.
    distanceMatrix = 1. - np.abs(corr)
    distLinkage = hierarchy.ward(squareform(distanceMatrix))
    t = float('{:.3e}'.format(1.e-6*np.max(distLinkage)))
    self.raiseAMessage("Applying hierarchical clustering on feature to eliminate possible collinearities")
    self.raiseAMessage(f"Applying distance clustering tollerance of <{t}>")
    clusterIds = hierarchy.fcluster(distLinkage, t, criterion="distance")
    clusterIdToFeatureIds = defaultdict(list)
    for idx, clusterId in enumerate(clusterIds):
      clusterIdToFeatureIds[clusterId].append(idx)
    selectedFeatures = [v[0] for v in clusterIdToFeatureIds.values()]
    self.raiseAMessage(f"Features reduced via clustering (before Augmented-RFE search) from {len(support_)} to {len(selectedFeatures)}!")
    support_[:] = False
    support_[np.asarray(selectedFeatures)] = True
    return support_

  def _train(self, X, y, featuresIds, targetsIds, maskF = None, maskT = None):
    """
      Train the RFE model and perform search of best features
      @ In, X, numpy.array, feature data (nsamples,nfeatures) or (nsamples, nTimeSteps, nfeatures)
      @ In, y, numpy.array, target data (nsamples,nTargets) or (nsamples, nTimeSteps, nTargets)
      @ In, featuresIds, list, list of features
      @ In, targetsIds, list, list of targets
      @ In, maskF, optional, np.array, indeces of features to search within (parameters to include None if search is whitin targets)
      @ In, maskT, optional, np.array, indeces of targets to search within (parameters to include None if search is whitin features)
      @ Out, newFeatures or newTargets, list, list of new features/targets
      @ Out, supportOfSupport_, np.array, boolean mask of the selected features
      @ Out, whichSpace, str, which space?
      @ Out, vals, dict, dictionary of new values
    """
    useParallel = False
    jhandler = self.estimator._assembledObjects.get('jobHandler')
    if jhandler is not None:
      useParallel = jhandler.runInfoDict['batchSize'] > 1

    #FIXME: support and ranking for targets is only needed now because
    #       some features (e.g. DMDC state variables) are stored among the targets
    #       This will go away once (and if) MR #1718 (https://github.com/idaholab/raven/pull/1718) gets merged
    #       whatever marked with ""FIXME 1718"" will need to be modified
    # Initialization
    nFeatures = X.shape[-1]
    nTargets = y.shape[-1]
    #FIXME 1718
    nParams = len(self.parametersToInclude)
    # support and ranking for features
    support_ = np.ones(nParams, dtype=np.bool)
    featuresForRanking = np.arange(nParams)[support_]
    ranking_ = np.ones(nParams, dtype=np.int)
    supportOfSupport_ = np.ones(nFeatures, dtype=np.bool) if self.whichSpace == 'feature' else np.ones(nTargets, dtype=np.bool)
    mask = maskF if self.whichSpace == 'feature' else maskT
    # initialize coefs = None
    coefs = None
    # number of subgroups
    nGroups = max(len(self.subGroups), 1)
    # features to select
    nFeaturesToSelect = self.nFeaturesToSelect if self.nFeaturesToSelect is not None else self.maxNumberFeatures
    # if both None ==> nFeatures/2
    if nFeaturesToSelect is None:
      nFeaturesToSelect = nFeatures // 2
    else:
      if nGroups > 1 and self.applyCrossCorrelation:
        # we duouble the number of features because we apply the cross correlation later on to identify the
        # number of features (nFeaturesToSelect)
        nFeaturesToSelect *= 2
    nFeaturesToSelect = nFeaturesToSelect if self.parametersToInclude is None else min(nFeaturesToSelect,nParams)

    # get estimator parameter
    originalParams = self.estimator.paramInput

    # clustering appraoch here
    if self.applyClusteringFiltering:
      support_ = self.__applyClusteringPrefiltering(X, y, mask, support_)

    # compute number of steps
    setStep = int(self.step) if self.step > 1 else int(max(1, self.step * nParams))
    # number of steps
    nSteps = (int(np.sum(support_)) - nFeaturesToSelect)/setStep
    # compute first step
    diff = nSteps - int(nSteps)
    firstStep = int(setStep * (1+diff))
    step = firstStep
    # we check the number of subgroups
    outputspace = None
    supportCandidates = []
    outputSpaceToKeep = []
    if nGroups > 1:
      # re initialize support containers
      groupFeaturesForRanking = copy.deepcopy(featuresForRanking)
      groupRanking_ = copy.deepcopy(ranking_)
      groupSupportOfSupport_ = copy.deepcopy(supportOfSupport_)

    supportDataRFE = {'featuresForRanking':featuresForRanking,'mask':mask,'nFeatures':nFeatures,
                   'nTargets':nTargets,'nParams':nParams,'targetsIds':targetsIds,
                   'originalParams':originalParams,'supportOfSupport_':supportOfSupport_,
                   'ranking_':ranking_,'nFeaturesToSelect':nFeaturesToSelect,'firstStep':step,
                   'setStep':setStep,'subGroups':self.subGroups,
                   'originalSupport':support_, 'parametersToInclude':self.parametersToInclude,
                   'whichSpace':self.whichSpace}

    if useParallel:
      # send some data to workers
      self.raiseADebug("Sending large data objects to Workers for parallel")
      supportDataForRFERef = jhandler.sendDataToWorkers(supportDataRFE)
      yRef = jhandler.sendDataToWorkers(y)
      XRef = jhandler.sendDataToWorkers(X)
      estimatorRef = jhandler.sendDataToWorkers(self.estimator)
      self.raiseADebug("Large data objects have been sent to workers")
      collectedOutput = 0
      g = 0
      while g < nGroups:
        if jhandler.availability() > 0:
          if nGroups > 1:
            outputspace = self.subGroups[g]
            self.raiseAMessage("Subgroupping with targets: {}".format(",".join(outputspace)))
          else:
            outputspace = None
          prefix = f'subgroup_{g}'
          jhandler.addJob((estimatorRef, XRef, yRef, g, outputspace, supportDataForRFERef,),self._rfe, prefix, uniqueHandler='RFE_subgroup')
          g += 1

        finishedJobs = jhandler.getFinished(uniqueHandler='RFE_subgroup')
        if not finishedJobs:
          while jhandler.availability() == 0:
            time.sleep(jhandler.sleepTime)
        for finished in finishedJobs:
          supportParallel_, indexToKeepParallel = finished.getEvaluation()
          self.raiseAMessage(f"Collecting results from subgroup {finished.identifier}")
          collectedOutput+=1
          if nGroups > 1:
            # store candidates in case of sugroupping
            supportCandidates.append(copy.deepcopy(supportParallel_))
            outputSpaceToKeep.append(copy.deepcopy(indexToKeepParallel))
          else:
            support_ = supportParallel_
      while collectedOutput < nGroups:
        finishedJobs = jhandler.getFinished(uniqueHandler='RFE_subgroup')
        for finished in finishedJobs:
          self.raiseAMessage(f"Collecting results from subgroup {finished.identifier}")
          supportParallel_, indexToKeepParallel = finished.getEvaluation()
          collectedOutput += 1
          if nGroups > 1:
            # store candidates in case of sugroupping
            supportCandidates.append(copy.deepcopy(supportParallel_))
            outputSpaceToKeep.append(copy.deepcopy(indexToKeepParallel))
          else:
            support_ = supportParallel_
    else:
      for g in range(nGroups):
        # loop over groups
        if nGroups > 1:
          outputspace = self.subGroups[g]
          self.raiseAMessage("Subgroupping with targets: {}".format(",".join(outputspace)))
        # apply RFE
        supportParallel_, indexToKeepParallel = self._rfe.original_function(self.estimator, X, y, g, outputspace, supportDataRFE)

        if nGroups > 1:
          # store candidates in case of sugroupping
          supportCandidates.append(copy.deepcopy(supportParallel_))
          outputSpaceToKeep.append(copy.deepcopy(indexToKeepParallel))
        else:
          support_ = supportParallel_

    if nGroups > 1:
      support_[:] = False
      featuresForRanking = copy.deepcopy(groupFeaturesForRanking)
      ranking_ = copy.deepcopy(groupRanking_)
      supportOfSupport_ = copy.deepcopy(groupSupportOfSupport_)
      for g in range(nGroups):
        subGroupMask = np.where(supportCandidates[g] == True)
        support_[subGroupMask] = True
      self.raiseAMessage("After subGroupping stragety, number of candidate features are {}".format(np.sum(support_)))
      # apply cross correlation if activated
      if self.applyCrossCorrelation:
        supportIndex = 0
        for idx in range(len(supportOfSupport_)):
          if mask[idx]:
            supportOfSupport_[idx] = support_[supportIndex]
            supportIndex=supportIndex+1
        if self.whichSpace == 'feature':
          features = np.arange(nFeatures)[supportOfSupport_]
          targets = np.arange(nTargets)
        else:
          features = np.arange(nFeatures)
          targets = np.arange(nTargets)[supportOfSupport_]

        if self.whichSpace == 'feature':
          space = X[:, features] if len(X.shape) < 3 else np.average(X[:, :,features],axis=0)
        else:
          space = y[:, targets] if len(y.shape) < 3 else  np.average(y[:, :,targets],axis=0)

        from sklearn.feature_selection import mutual_info_regression
        ti = None
        ranksss = []
        for g in range(nGroups):
          tspace = y[:, outputSpaceToKeep[g]] if len(y.shape) < 3 else  np.average(y[:, :,outputSpaceToKeep[g]],axis=0)
          mi = np.ravel(mutual_info_regression(space,tspace[:,0]))
          if ti is None:
            ti = mi
          else:
            ti = ti - mi
          ranksss.append(np.ravel(np.argsort(-1*mi)))
          print(mi[ranksss[-1]])

        # compute spearman
        # we fill nan with 1.0 (so the distance for such variables == 0 (will be discarded)
        corr = np.nan_to_num(spearmanr(space,axis=0).correlation,nan=1.0)
        corr = (corr + corr.T) / 2.
        np.fill_diagonal(corr, 1)
        # We convert the correlation matrix to a distance matrix before performing
        # hierarchical clustering using Ward's linkage.

        distance_matrix = 1. - np.abs(corr)
        dist_linkage = hierarchy.ward(squareform(distance_matrix))

        t = float('{:.3e}'.format(0.000001*np.max(dist_linkage)))

        self.raiseAMessage("Applying hierarchical clustering on feature to eliminate possible collinearities")
        self.raiseAMessage(f"Applying distance clustering tollerance of <{t}>")
        cluster_ids = hierarchy.fcluster(dist_linkage, t, criterion="distance")
        cluster_id_to_feature_ids = defaultdict(list)
        for idx, cluster_id in enumerate(cluster_ids):
          cluster_id_to_feature_ids[cluster_id].append(idx)
        selected_features = [v[0] for v in cluster_id_to_feature_ids.values()]


        self.raiseAMessage(f"Features reduced via clustering (before RFE search) from {len(support_)} to {len(selected_features)}!")
        support_[:] = False
        support_[np.asarray(selected_features)] = True

    # now we check if maxNumberFeatures is set and in case perform an
    # additional reduction based on score
    # removing the variables one by one
    if self.maxNumberFeatures is not None:
      #featuresForRanking = np.arange(nParams)[support_]
      f = np.asarray(self.parametersToInclude)
      self.raiseAMessage("Starting Features are {}".format( " ".join(f[support_]) ))
      #######
      # NEW SEARCH
      # in here we perform a best subset search
      initialNumbOfFeatures = int(np.sum(support_))
      featuresForRanking = np.arange(nParams)[support_]
      originalSupport = copy.copy(support_)
      scorelist = []
      featureList = []
      bestForNumberOfFeatures = {}
      supportData = {'featuresForRanking':featuresForRanking,'mask':mask,'nFeatures':nFeatures,
                     'nTargets':nTargets,'nParams':nParams,'targetsIds':targetsIds,
                     'originalParams':originalParams,'supportOfSupport_':supportOfSupport_,
                     'originalSupport':originalSupport, 'parametersToInclude':self.parametersToInclude,
                     'whichSpace':self.whichSpace,'onlyOutputScore':self.onlyOutputScore}

      def updateBestScore(it, k, score, combo, survivors):
        """
          Update score and combo containers
          @ In, k, int, number of features
          @ In, score, float, the score for this combination
          @ In, combo, list(int), list of integers (combinations)
          @ Out, None
        """
        if k in bestForNumberOfFeatures.keys():
          if bestForNumberOfFeatures[k][0] > score:
            bestForNumberOfFeatures[k] = [score,f[np.asarray(combo)]]
        else:
          bestForNumberOfFeatures[k] = [score,f[np.asarray(combo)]]
        scorelist.append(score)
        featureList.append(combo)
        self.raiseAMessage("Iter. #: {}. Score: {:.6e}. Variables (# {}):  {}".format(it,score,len(survivors)," ".join(survivors)))

      # this can be time consuming
      # check if parallel is available
      if useParallel:
        # send some data to workers
        self.raiseADebug("Sending large data objects to Workers for parallel")
        supportDataRef = jhandler.sendDataToWorkers(supportData)
        #yRef = jhandler.sendDataToWorkers(y)
        #XRef = jhandler.sendDataToWorkers(X)
        #estimatorRef = jhandler.sendDataToWorkers(self.estimator)
        self.raiseADebug("Large data objects have been sent")
        # we use the parallelization
        for k in range(1,initialNumbOfFeatures + 1):
          #Looping over all possible combinations: from initialNumbOfFeatures choose k
          collectedCnt = 0
          combinations = list(itertools.combinations(featuresForRanking,k))
          it = 0
          while it < len(combinations):
            # train and get score
            if jhandler.availability() > 0:
              prefix = f'{k}_{it+1}'
              #jhandler.addJob((copy.deepcopy(self.estimator), X, y, combo,supportData,),self._scoring,prefix, uniqueHandler='RFE')
              jhandler.addJob((estimatorRef, XRef, yRef, combinations[it], supportDataRef,),self._scoring, prefix, uniqueHandler='RFE_scoring')
              it += 1
            finishedJobs = jhandler.getFinished(uniqueHandler='RFE_scoring')
            if not finishedJobs:
              while jhandler.availability() == 0:
                time.sleep(jhandler.sleepTime)
            for finished in finishedJobs:
              score, survivors, combo = finished.getEvaluation()
              collectedCnt+=1
              updateBestScore(collectedCnt, k, score, combo, survivors)
          while not jhandler.isFinished(uniqueHandler="RFE_scoring"):
            finishedJobs = jhandler.getFinished(uniqueHandler='RFE_scoring')
            for finished in finishedJobs:
              score, survivors, combo = finished.getEvaluation()
              collectedCnt+=1
              updateBestScore(collectedCnt, k, score, combo, survivors)

      else:
        for k in range(1,initialNumbOfFeatures + 1):
          #Looping over all possible combinations: from initialNumbOfFeatures choose k
          for it, combo in enumerate(itertools.combinations(featuresForRanking,k)):
            # train and get score
            score, survivors, _ = self._scoring.original_function(copy.deepcopy(self.estimator), X, y, combo,supportData)
            updateBestScore(it, k, score, combo, survivors)
      idxx = np.argmin(scorelist)
      support_ = copy.copy(originalSupport)
      support_[featuresForRanking] = False
      support_[np.asarray(featureList[idxx])] = True
      for k in bestForNumberOfFeatures:
        self.raiseAMessage(f"Best score for {k} features is {bestForNumberOfFeatures[k][0]} with the following features {bestForNumberOfFeatures[k][1]} ")

    # Set final attributes
    supportIndex = 0
    for idx in range(len(supportOfSupport_)):
      if mask[idx]:
        supportOfSupport_[idx] = support_[supportIndex]
        supportIndex = supportIndex + 1
    if self.whichSpace == 'feature':
      features = np.arange(nFeatures)[supportOfSupport_]
      targets = np.arange(nTargets)
    else:
      features = np.arange(nFeatures)
      targets = np.arange(nTargets)[supportOfSupport_]

    self.estimator_ = copy.deepcopy(self.estimator)
    toRemove = [self.parametersToInclude[idx] for idx in range(nParams) if not support_[idx]]
    vals = {}
    if toRemove:
      for child in originalParams.subparts:
        if isinstance(child.value,list):
          newValues = copy.copy(child.value)
          for el in toRemove:
            if el in child.value:
              newValues.pop(newValues.index(el))
          vals[child.getName()] = newValues
      self.estimator_.paramInput.findNodesAndSetValues(vals)
      self.estimator_._handleInput(self.estimator_.paramInput)
    self.estimator_._train(X[:, features] if len(X.shape) < 3 else X[:, :,features], y[:, targets] if len(y.shape) < 3 else y[:, :,targets])


    self.nFeatures_ = support_.sum()
    self.support_ = support_
    self.ranking_ = ranking_

    return features if self.whichSpace == 'feature' else targets, supportOfSupport_, self.whichSpace, vals

  @Parallel()
  def _rfe(estimatorObj, X, y, groupId, outputspace, supportData):
    """
      Method to apply recursive feature elimination
      @ In, estimatorObj, object, surrogate model instance
      @ In, X, numpy.array, feature data (nsamples,nfeatures) or (nsamples, nTimeSteps, nfeatures)
      @ In, y, numpy.array, target data (nsamples,nTargets) or (nsamples, nTimeSteps, nTargets)
      @ In, groupId, int, subGroupIndex
      @ In, outputspace, list, list of output space variables (if None, not distinction is needed)
      @ In, supportData, dict, dictionary containing data for performing the training/score:
                               featuresForRanking: intial feature set
                               nFeaturesToSelect: number of features to select
                               firstStep: the intial step to use
                               setStep: the subsequential step to use
                               mask: mask for the X (or y) array (based on parameters to include)
                               nFeatures: number of features
                               nTargets: number of targets
                               nParams: number of total parameters
                               targetsIds: ids of targets
                               originalParams: original parameter container (InputData) for ROM initialization
                               originalSupport: boolean array of the initial support to mask features
                               supportOfSupport_: boolean array of the initial support to mask X or y (parameters included and not)
                               parametersToInclude: list of parameters to include
                               whichSpace: which space? feature or target?
                               onlyOutputScore: score on output only?

      @ Out, score, float, the score for this combination
      @ Out, survivors,list(str), the list of parameters for this combination
      @ Out, featureCombination, numpy.ndarray(int), list of feature that should be tested (indeces of features)
    """
    # copy arrays that will be modified during the search
    support_ = copy.copy(supportData['originalSupport'])
    featuresForRanking = copy.copy(supportData['featuresForRanking'])
    ranking_ = copy.copy(supportData['ranking_'])
    supportOfSupport_ = copy.copy(supportData['supportOfSupport_'])
    # get immutable settings
    nFeaturesToSelect = supportData['nFeaturesToSelect']
    subGroups = supportData['subGroups']
    step = supportData['firstStep']
    setStep = supportData['setStep']
    mask = supportData['mask']
    nFeatures = supportData['nFeatures']
    nTargets = supportData['nTargets']
    nParams = supportData['nParams']
    targetsIds = supportData['targetsIds']
    originalParams = supportData['originalParams']

    parametersToInclude = supportData['parametersToInclude']
    whichSpace = supportData['whichSpace']
    
    fg = open(f"debug_parallel_{groupId}","w")
    import sys
    np.set_printoptions(threshold=sys.maxsize)
    fg.write("INITIAL\n")
    fg.write("support_\n")
    fg.write(str(support_))
    fg.write("\nfeaturesForRanking\n")
    fg.write(str(featuresForRanking))
    fg.write("\nranking_\n")
    fg.write(str(ranking_))
    fg.write("\noutputspace\n")
    fg.write(str(outputspace))
    fg.write("\n END INITIAL\n")

    # initialize working dir
    indexToKeep = None
    # the search is done at least once
    doAtLeastOnce = True
    while np.sum(support_) > nFeaturesToSelect or doAtLeastOnce:
      # Remaining features
      estimator = copy.deepcopy(estimatorObj)
      raminingFeatures = int(np.sum(support_))
      featuresForRanking = np.arange(nParams)[support_]
      # subgrouping
      outputToRemove = None
      if outputspace != None:
        indexToRemove = []
        outputToRemove = []
        indexToKeep = []
        sg = copy.deepcopy(subGroups)
        outputToKeep = sg.pop(groupId)
        for grouptoremove in sg:
          outputToRemove += grouptoremove
        for t in outputToRemove:
          indexToRemove.append(targetsIds.index(t))
        for t in outputToKeep:
          indexToKeep.append(targetsIds.index(t))
        if whichSpace != 'feature':
          supportOfSupport_[np.asarray(indexToRemove)] = False
          supportOfSupport_[np.asarray(indexToKeep)] = True

      supportIndex = 0
      for idx in range(len(supportOfSupport_)):
        if mask[idx]:
          supportOfSupport_[idx] = support_[supportIndex]
          supportIndex=supportIndex+1
      if whichSpace == 'feature':
        features = np.arange(nFeatures)[supportOfSupport_]
        targets = np.arange(nTargets)
      else:
        features = np.arange(nFeatures)
        targets = np.arange(nTargets)[supportOfSupport_]
      # Rank the remaining features
      print("(            ) FEATURE SELECTION - RFE  : Message         -> Fitting estimator with %d features." % np.sum(support_))
      toRemove = [parametersToInclude[idx] for idx in range(nParams) if not support_[idx]]
      if outputToRemove is not None:
        toRemove += outputToRemove
      vals = {}

      if toRemove:
        for child in originalParams.subparts:
          if isinstance(child.value,list):
            newValues = copy.copy(child.value)
            for el in toRemove:
              if el in child.value:
                newValues.pop(newValues.index(el))
            vals[child.getName()] = newValues
        estimator.paramInput.findNodesAndSetValues(vals)
        estimator._handleInput(estimator.paramInput)
      estimator._train(X[:, features] if len(X.shape) < 3 else X[:, :,features], y[:, targets] if len(y.shape) < 3 else y[:, :,targets])

      # Get coefs
      coefs = None
      if hasattr(estimator, 'featureImportances_'):
        importances = estimator.featureImportances_

        # since we get the importance, highest importance must be kept => we get the inverse of coefs
        parametersRemained = [parametersToInclude[idx] for idx in range(nParams) if support_[idx]]
        indexMap = {v: i for i, v in enumerate(parametersRemained)}
        #coefs = np.asarray([importances[imp] for imp in importances if imp in self.parametersToInclude])
        subSetImportances = {k: importances[k] for k in parametersRemained}
        sortedList = sorted(subSetImportances.items(), key=lambda pair: indexMap[pair[0]])
        coefs = np.asarray([sortedList[s][1] for s in range(len(sortedList))])
        if coefs.shape[0] == raminingFeatures:
          coefs = coefs.T
      if coefs is None:
        coefs = np.ones(raminingFeatures)

      # Get ranks (for sparse case ranks is matrix)
      ranks = np.ravel(np.argsort(np.sqrt(coefs).sum(axis=0)) if coefs.ndim > 1 else np.argsort(np.sqrt(coefs)))
      # Eliminate the worse features
      threshold = min(step, np.sum(support_) - nFeaturesToSelect)
      step = setStep

      fg.write("Remaining features \n")
      fg.write("raminingFeatures\n")
      fg.write(str(raminingFeatures))
      fg.write("features\n")
      fg.write(str(features))
      fg.write("\ntargets\n")
      fg.write(str(targets))
      fg.write("\ntoRemove_\n")
      fg.write(str(toRemove))
      fg.write("\nsupportOfSupport_\n")
      fg.write(str(supportOfSupport_))
      fg.write("\nranks\n")
      fg.write(str(ranks))
      fg.write("\ncoefs\n")
      fg.write(str(coefs))
      fg.write("\n \n")

      # Compute step score on the previous selection iteration
      # because 'estimator' must use features
      # that have not been eliminated yet
      support_[featuresForRanking[ranks][:threshold]] = False
      ranking_[np.logical_not(support_)] += 1
      # delete estimator to free memory
      del estimator
      gc.collect()
      # we do the search at least once
      doAtLeastOnce = False
    
    fg.close()
    return support_, indexToKeep

  @Parallel()
  def _scoring(estimator, X, y, featureCombination, supportData):
    """
      Method to train and score an estimator based on a set of feature combination
      @ In, estimator, object, surrogate model instance
      @ In, X, numpy.array, feature data (nsamples,nfeatures) or (nsamples, nTimeSteps, nfeatures)
      @ In, y, numpy.array, target data (nsamples,nTargets) or (nsamples, nTimeSteps, nTargets)
      @ In, featureCombination, numpy.ndarray(int), array of feature that should be tested (indeces of features)
      @ In, supportData, dict, dictionary containing data for performing the training/score:
                               featuresForRanking: intial feature set
                               mask: mask for the X (or y) array (based on parameters to include)
                               nFeatures: number of features
                               nTargets: number of targets
                               nParams: number of total parameters
                               targetsIds: ids of targets
                               originalParams: original parameter container (InputData) for ROM initialization
                               originalSupport: boolean array of the initial support to mask features
                               supportOfSupport_: boolean array of the initial support to mask X or y (parameters included and not)
                               parametersToInclude: list of parameters to include
                               whichSpace: which space? feature or target?
                               onlyOutputScore: score on output only?

      @ Out, score, float, the score for this combination
      @ Out, survivors,list(str), the list of parameters for this combination
      @ Out, featureCombination, numpy.ndarray(int), list of feature that should be tested (indeces of features)
    """
    featuresForRanking = supportData['featuresForRanking']
    mask = supportData['mask']
    nFeatures = supportData['nFeatures']
    nTargets = supportData['nTargets']
    nParams = supportData['nParams']
    targetsIds = supportData['targetsIds']
    originalParams = supportData['originalParams']
    supportOfSupport_ = copy.copy(supportData['supportOfSupport_'])
    parametersToInclude = supportData['parametersToInclude']
    whichSpace = supportData['whichSpace']
    onlyOutputScore = supportData['onlyOutputScore']
    # intialize support and working vars
    support_ = copy.copy(supportData['originalSupport'])
    support_[featuresForRanking] = False
    support_[np.asarray(featureCombination)] = True
    supportIndex = 0
    for idx in range(len(supportOfSupport_)):
      if mask[idx]:
        supportOfSupport_[idx] = support_[supportIndex]
        supportIndex=supportIndex+1
    if whichSpace == 'feature':
      features = np.arange(nFeatures)[supportOfSupport_]
      targets = np.arange(nTargets)
    else:
      features = np.arange(nFeatures)
      targets = np.arange(nTargets)[supportOfSupport_]

    #estimator = copy.deepcopy(self.estimator)
    toRemove = [parametersToInclude[idx] for idx in range(nParams) if not support_[idx]]
    survivors = [parametersToInclude[idx] for idx in range(nParams) if support_[idx]]
    vals = {}
    if toRemove:
      for child in originalParams.subparts:
        if isinstance(child.value,list):
          newValues = copy.copy(child.value)
          for el in toRemove:
            if el in child.value:
              newValues.pop(newValues.index(el))
          vals[child.getName()] = newValues
      estimator.paramInput.findNodesAndSetValues(vals)
      estimator._handleInput(estimator.paramInput)
    estimator._train(X[:, features] if len(X.shape) < 3 else X[:, :,features], y[:, targets] if len(y.shape) < 3 else y[:, :,targets])

    # evaluate
    score = 0.0
    for samp in range(X.shape[0]):
      evaluated = estimator._evaluateLocal(X[samp:samp+1, features] if len(X.shape) < 3 else np.atleast_2d(X[samp:samp+1, :,features]))
      scores = {}
      for target in evaluated:
        if target in targetsIds:
          if target not in parametersToInclude:
            # if not state variable, then this target is output variable
            w = 1/float(len(targets)-1-len(featureCombination))
          else:
            w = 1/float(len(featureCombination))
            if onlyOutputScore:
              continue
          tidx = targetsIds.index(target)
          avg = np.average(y[:,tidx] if len(y.shape) < 3 else y[samp,:,tidx])
          std = np.std(y[:,tidx] if len(y.shape) < 3 else y[samp,:,tidx],ddof=1)
          if compareFloats (avg, 0.):
            avg = 1
          if compareFloats (std, 0.):
            std = 1.
          ev = (evaluated[target] - avg)/std
          ref = ((y[:,tidx] if len(y.shape) < 3 else y[samp,:,tidx]) - avg )/std
          s = np.sum(np.square(ref-ev))
          scores[target] = s*w
          score +=  s*w
    # free memory and call garbage collector
    del estimator
    gc.collect()

    return score, survivors, featureCombination
