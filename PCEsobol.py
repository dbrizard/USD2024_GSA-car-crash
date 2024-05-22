#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Trying different modules for PCE approximation.

- [x] Openturns runnings
- [ ] Pythia-uq 
  - 2.0.0 installed (no documentation online)
  - latest is 4.0.3 (runs with python 3.9)
- [ ] pygpc 0.2.7.5
  - I cannot provide simulation output myself
- [ ] Chaospy 4.2.7 installed. 
  - Usage does not seem straightforward
- [ ] Uncertainpy
- [ ] UQpy 4.1.5 
  - https://uqpyproject.readthedocs.io/en/latest/auto_examples/surrogates/pce/index.html



Created on Fri Apr  5 11:03:36 2024

@author: dbrizard
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker
# from matplotlib import pylab as plt
import openturns as ot
import openturns.viewer as viewer
ot.Log.Show(ot.Log.NONE)


# from UQpy.surrogates.polynomial_chaos.PolynomialChaosExpansion import PolynomialChaosExpansion
# from UQpy.sensitivity.PceSensitivity import PceSensitivity


class EricPCESobol():
    """Import and plot Sobol indices computed by Eric
    
    """
    
    def __init__(self):
        """Load and store data
        
        """
        folder = '/home/dbrizard/Calcul/25_car/GSA/car_v223_right-impact_v30/Eric/EricPCEsobol'
        self.S1 = {}
        self.S1_mean = {}
        self.ST = {}
        self.ST_mean = {}
        self.output = ('dmax', 'fmax', 'IE', 'vfin')
        self.input = ['tbumper', 'trailb', 'trailf', 'tgrill', 'thood', 'ybumper', 'yrailf', 'yrailb', 'ybody']
        
        for oo in self.output:
            self.S1[oo] = np.genfromtxt(os.path.join(folder,'SI-Y-%s.txt'%oo), delimiter='  ')  # loadtxt not working
            self.ST[oo] = np.genfromtxt(os.path.join(folder,'SI-tot-Y-%s.txt'%oo), delimiter='  ')  # loadtxt not working
            self.S1_mean[oo] = self.S1[oo].mean(axis=0)
            self.ST_mean[oo] = self.ST[oo].mean(axis=0)
        
    def plotS1ST(self, figname='', xmargin=0.3, ylim=True):
        """Plot S1 and ST, for each output, on the same graph
        
        :param str figname: prefix for the name of the figures 
        :param float xmargin: x axis margins
        :param bool ylim: set ylim to [0,1]
        """
        for oo in self.output:
            plt.figure('%s-%s'%(figname, oo))
            plt.plot(self.ST[oo].T, '+r')
            plt.plot(self.S1[oo].T, '+k')
            plt.plot(self.ST_mean[oo], '+r', label='ST_mean', ms=15)
            plt.plot(self.S1_mean[oo], '+k', label='S1_mean', ms=15)
            plt.xlim(xmin=-xmargin, xmax=len(self.input)-1+xmargin)
            plt.xticks(ticks=range(len(self.input)), labels=self.input, rotation=45)
            plt.title(oo)
            plt.legend()
            if ylim:
                plt.ylim([0,1])
    

class OpenTurnsPCESobol():
    """My take on PCE Sobol indices with Openturns
    
    """
    
    def __init__(self, basepath='LHS/LHS-', ns=120):
        """Set the problem, inputs and outputs
        
        :param str basepath: base path for the input and output files
        :param int ns: number of samples in the LHS DOE
        """
        mm, mpa = 'mm', 'MPa'
        problem = {'names': ['tbumper', 'trailb', 'trailf', 'tgrill', 'thood',
                             'ybumper', 'yrailf', 'yrailb', 'ybody'],
                   'units': [mm, mm, mm, mm, mm,
                             mpa, mpa, mpa, mpa],
                   'num_vars': 9,
                   'bounds': [[2, 4], [1,3], [3,7], [0.5,1.5], [0.5, 1.5],
                              [300, 500], [300, 500], [300, 500], [300, 500]],
                   }
        
        self.problem = problem
        self.input = problem['names']
        self.output = ('dmax', 'fmax', 'IE', 'vfin')
        
        # Import X and Y
        self.X = np.loadtxt('%s%i_X.csv'%(basepath, ns), delimiter=',')
        self.Y = {}
        for oo in self.output:
            self.Y[oo] = np.loadtxt('%s%i_Y_%s.csv'%(basepath, ns, oo), delimiter=',')
        

        # OpenTURNS variables and definitions 
        ot.ResourceMap.SetAsUnsignedInteger("FittingTest-LillieforsMaximumSamplingSize", 100)
        self.inputSample = ot.Sample(self.X)
        self.inputSample.setDescription(self.input)
        self.outputSample = {}
        for oo in self.output:
            self.outputSample[oo] = ot.Sample(self.Y[oo][:,np.newaxis])
            self.outputSample[oo].setDescription([oo])
            
        distlist = [ot.Uniform(aa, bb) for (aa, bb) in self.problem['bounds']]
        # distribution = ot.ComposedDistribution([ot.Uniform()]*len(self.input))
        self.distribution = ot.ComposedDistribution(distlist)
    
    
    def computeChaosSensitivity(self, strategy='cleaning', q=0.4):
        """Compute PCE metamodel and get Sobol indices for all outputs

        :param str strategy: adaptive strategy ('fixed' or 'cleaning')
        :param float q: q-quasi norm parameter. If not precised, q = 0.4. (see HyperbolicAnisotropicEnumerateFunction)
        """
        self.chaosSI = {}
        self.metamodel = {}
        self.S1 = {}
        self.ST = {}
        for oo in self.output:
            print('='*20, oo, '='*20, '\n')
            self.S1[oo], self.ST[oo] = self._computeChaosSensitivity(self.inputSample, self.outputSample[oo], strategy=strategy, q=q, verbose=False)
            
    
    def _computeChaosSensitivity(self, inputSample, outputSample, 
                                 strategy='cleaning', q=0.4, verbose=False):
        """Compute PCE metamodel and return Sobol indices for a specific output
        
        :param Sample inputSample: 
        :param Sample outputSample: 
        :param str strategy: adaptive strategy ('fixed' or 'cleaning')
        :param float q: q-quasi norm parameter. If not precised, q = 0.4. (see HyperbolicAnisotropicEnumerateFunction)
        """

        # https://openturns.github.io/openturns/latest/user_manual/response_surface/_generated/openturns.FixedStrategy.html#openturns.FixedStrategy
        polyColl = [0.0]*len(self.input)
        for i in range(self.distribution.getDimension()):
            polyColl[i] = ot.StandardDistributionPolynomialFactory(self.distribution.getMarginal(i))
        # enumerateFunction = ot.LinearEnumerateFunction(len(self.input))
        enumerateFunction = ot.HyperbolicAnisotropicEnumerateFunction(len(self.input), q)
        productBasis = ot.OrthogonalProductPolynomialFactory(polyColl, enumerateFunction)

        if strategy=='fixed':
            # Number of terms of the basis.
            degree = 2
            indexMax = enumerateFunction.getStrataCumulatedCardinal(degree)
            # XXX attention à l'overfitting !!
            print('indexMax', indexMax)
            adaptiveStrategy = ot.FixedStrategy(productBasis, indexMax)  # https://openturns.github.io/openturns/latest/user_manual/response_surface/_generated/openturns.FixedStrategy.html#openturns.FixedStrategy
        elif strategy=='cleaning':
            # Maximum index that can be used by the EnumerateFunction to 
            # determine the last term of the basis.
            maximumDimension = 200
            # Parameter that characterizes the cleaning strategy. 
            # It represents the number of efficient coefficients of the basis. 
            # Its default value is set to 20.
            maximumSize = 20
            # Parameter used as a threshold for selecting the efficient coefficients 
            # of the basis. The real threshold represents the multiplication of 
            # the significanceFactor with the maximum magnitude of the current 
            # determined coefficients. Its default value is equal to 1e^{-4}.
            significanceFactor = 1e-4
            adaptiveStrategy = ot.CleaningStrategy(productBasis, maximumDimension, maximumSize, significanceFactor)


        oo = outputSample.getDescription()[0]
        # PCE
        # ot.ResourceMap.SetAsUnsignedInteger("FunctionalChaosAlgorithm-MaximumTotalDegree", 15)
        algo = ot.FunctionalChaosAlgorithm(
            inputSample, outputSample, self.distribution, adaptiveStrategy)
        algo.run()
        result = algo.getResult()
        self.metamodel[oo] = result.getMetaModel()
        
        self.chaosSI[oo] = ot.FunctionalChaosSobolIndices(result)
        if verbose:
            print(self.chaosSI[oo].summary())
    
        S1 = [self.chaosSI[oo].getSobolIndex(ii) for ii in range(len(self.input))]
        ST = [self.chaosSI[oo].getSobolTotalIndex(ii) for ii in range(len(self.input))]
        return S1, ST
    
        # XXX Metamodel validation
        # val = ot.MetaModelValidation(X_test, Y_test, metamodel)
        # https://openturns.github.io/openturns/latest/auto_meta_modeling/polynomial_chaos_metamodel/plot_chaos_sobol_confidence.html#sphx-glr-auto-meta-modeling-polynomial-chaos-metamodel-plot-chaos-sobol-confidence-py


    def computeBootstrapChaosSobolIndices(self, bootstrap_size, verbose=True, plot=True):
        """
        Computes a bootstrap sample of first and total order indices from polynomial chaos.
        
        https://openturns.github.io/openturns/latest/auto_meta_modeling/polynomial_chaos_metamodel/plot_chaos_sobol_confidence.html#sphx-glr-auto-meta-modeling-polynomial-chaos-metamodel-plot-chaos-sobol-confidence-py

    
        :param interval bootstrap_size: The bootstrap sample size
        :param bool verbose: tell human where computer is
        :param bool plot: plot S_1 and S_T (one figure per output)
        """
        X = self.inputSample
        dim_input = X.getDimension()

        FO = {}
        TO = {}
        FOI = {}
        TOI = {}
        for oo in self.output:
            if verbose:
                print('*'*20, oo, '*'*20, '\n')
            Y = self.outputSample[oo]
            fo_sample = ot.Sample(0, dim_input)
            to_sample = ot.Sample(0, dim_input)
            unit_eps = ot.Interval([1e-9] * dim_input, [1 - 1e-9] * dim_input)
            for i in range(bootstrap_size):
                X_boot, Y_boot = multiBootstrap(X, Y)
                first_order, total_order = self._computeChaosSensitivity(X_boot, Y_boot)
                if unit_eps.contains(first_order) and unit_eps.contains(total_order):
                    fo_sample.add(first_order)
                    to_sample.add(total_order)
            # compute confidence intervals
            fo_interval, to_interval = computeSobolIndicesConfidenceInterval(fo_sample, to_sample)
            # Store
            FO[oo] = fo_sample
            TO[oo] = to_sample
            FOI[oo] = fo_interval
            TOI[oo] = to_interval
            
            if plot:
                graph = ot.SobolIndicesAlgorithm.DrawSobolIndices(
                    self.inputSample.getDescription(),
                    fo_sample.computeMean(),
                    to_sample.computeMean(),
                    fo_interval,
                    to_interval,
                )
        self.bootstrap = {'FO':FO, 'TO':TO, 'FOI':FOI, 'TOI':TOI}


    def bootstrapSobolIndices(self, N, ):
        """
        
        https://openturns.github.io/openturns/latest/auto_meta_modeling/polynomial_chaos_metamodel/plot_chaos_sobol_confidence.html#sphx-glr-auto-meta-modeling-polynomial-chaos-metamodel-plot-chaos-sobol-confidence-py
        
        :param int N: 
        """
        for oo in self.output:
            X, Y = self.X, self.Y[oo]
            X_boot, Y_boot = multiBootstrap(X, Y)
            print(X_boot[:5])
            print(Y_boot[:5])
            
            bootstrap_size = 500
            fo_sample, to_sample = computeBootstrapChaosSobolIndices(
                X, Y, basis, total_degree, distribution, bootstrap_size
            )
                    
            fo_interval, to_interval = computeSobolIndicesConfidenceInterval(fo_sample, to_sample)
        
            graph = ot.SobolIndicesAlgorithm.DrawSobolIndices(
                input_names,
                fo_sample.computeMean(),
                to_sample.computeMean(),
                fo_interval,
                to_interval,
            )
            graph.setTitle(f"Sobol' indices - N={N}")
            graph.setIntegerXTick(True)
                
        
    def plotS1ST(self, figname='', color=None, label='', 
                 xmargin=0.3, xoffset=0.2, ylim=True):
        """Plot S1 and ST, for each output, on the same graph
        
        :param str figname: prefix for the name of the figures
        :param str color: color for the markers
        :param float xmargin: x axis margins
        :param float xoffset: horizontal offset of the points (in [0, 1] interval)
        :param bool ylim: set ylim to [0,1]
        """
        for oo in self.output:
            plt.figure('%s-%s'%(figname, oo))
            x = np.arange(0, len(self.input)) + xoffset
            plt.plot(x, self.ST[oo], '+', label='ST_%s'%label, ms=14, color=color)
            plt.plot(x, self.S1[oo], 'x', label='S1_%s'%label, ms=10, color=color)
            plt.xlim(xmin=-xmargin, xmax=len(self.input)-1+xmargin)
            plt.xticks(ticks=range(len(self.input)), labels=self.input , rotation=45)
            plt.title(oo)
            plt.legend()
            if ylim:
                plt.ylim([0,1]) 
    
    
    def plotRanking(self, figname=''):
        """
        
        :param str figname: base name for the figure (S1/ST and output name are added)
        """
        for oo in self.output:
            iS1 = np.argsort(self.S1[oo]) + 1
            iST = np.argsort(self.ST[oo]) + 1
            S1 = np.sort(self.S1[oo])
            ST = np.sort(self.ST[oo])

            fn = '%s_%s_'%(figname, oo)
            plotSobolRanking(iS1[::-1,np.newaxis], figname=fn+'S1',
                             yticks=S1[::-1], xlabel='Sobol S1')
            plotSobolRanking(iST[::-1,np.newaxis], figname=fn+'ST',
                             yticks=ST[::-1], xlabel='Sobol ST')
       

def plotSobolRanking(matrix, figname=None, xlabel=None, yticks=None):
    """
    
    """
    nparam = matrix.shape[0]
    nrepet = matrix.shape[1]
    
    fig, ax = plt.subplots(num=figname, figsize=(nrepet*1.5, nparam/3))
    ax.matshow(matrix, cmap='viridis_r')
    
    # plt.title(title)
    plt.xlabel(xlabel, ha='left')
    plt.ylabel('ranking')
    if yticks is not None:
        plt.xticks([])
        # ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
        yticks = ['%.3f'%tt for tt in yticks]
        plt.yticks(range(nparam), yticks)
        ax.yaxis.tick_right()
    else:
        plt.xticks([])
        plt.yticks([])
    plt.box(False)
    
    for ii in range(nrepet):
        for jj in range(nparam):
            ax.text(ii, jj, str(matrix[jj,ii]), va='center', ha='center')


#%% The following functions were taken from:
# https://openturns.github.io/openturns/latest/auto_meta_modeling/polynomial_chaos_metamodel/plot_chaos_sobol_confidence.html#sphx-glr-auto-meta-modeling-polynomial-chaos-metamodel-plot-chaos-sobol-confidence-py

def multiBootstrap(*data):
    """
    Bootstrap multiple samples at once.

    Parameters
    ----------
    data : sequence of Sample
        Multiple samples to bootstrap.

    Returns
    -------
    data_boot : sequence of Sample
        The bootstrap samples.
    """
    assert len(data) > 0, "empty list"
    size = data[0].getSize()
    selection = ot.BootstrapExperiment.GenerateSelection(size, size)
    return [Z[selection] for Z in data]


def computeSobolIndicesConfidenceInterval(fo_sample, to_sample, alpha=0.95):
    """
    From a sample of first or total order indices,
    compute a bilateral confidence interval of level alpha.

    Estimates the distribution of the first and total order Sobol' indices
    from a bootstrap estimation.
    Then computes a bilateral confidence interval for each marginal.

    Parameters
    ----------
    fo_sample: ot.Sample(n, dim_input)
        The first order indices
    to_sample: ot.Sample(n, dim_input)
        The total order indices
    alpha : float
        The confidence level

    Returns
    -------
    fo_interval : ot.Interval
        The confidence interval of first order Sobol' indices
    to_interval : ot.Interval
        The confidence interval of total order Sobol' indices
    """
    dim_input = fo_sample.getDimension()
    fo_lb = [0] * dim_input
    fo_ub = [0] * dim_input
    to_lb = [0] * dim_input
    to_ub = [0] * dim_input
    for i in range(dim_input):
        fo_i = fo_sample[:, i]
        to_i = to_sample[:, i]
        beta = (1.0 - alpha) / 2
        fo_lb[i] = fo_i.computeQuantile(beta)[0]
        fo_ub[i] = fo_i.computeQuantile(1.0 - beta)[0]
        to_lb[i] = to_i.computeQuantile(beta)[0]
        to_ub[i] = to_i.computeQuantile(1.0 - beta)[0]

    # Create intervals
    fo_interval = ot.Interval(fo_lb, fo_ub)
    to_interval = ot.Interval(to_lb, to_ub)
    return fo_interval, to_interval



if __name__=='__main__':
    plt.close('all')
    
    #%% Plot Eric's results
    if True:
        Eric = EricPCESobol()
        Eric.plotS1ST(figname='S1ST')


    #%% Openturns on LS-DYNA car simulation data
    if True:
        OTS120 = OpenTurnsPCESobol(ns=120)
        OTS120.computeChaosSensitivity()
        OTS120.plotS1ST(figname='S1ST', color='C0', label='LHS-120')
        OTS120.plotRanking(figname='sobol120')
                
        OTS330 = OpenTurnsPCESobol(ns=330)
        OTS330.computeChaosSensitivity()
        OTS330.plotS1ST(figname='S1ST', color='C2', label='LHS-330')
        OTS330.plotRanking(figname='sobol330')
            
        OTS330.computeBootstrapChaosSobolIndices(40)
        # TODO: metamodel quality
            
    
    #%% Openturns example
    if False:
        """https://openturns.github.io/openturns/latest/auto_meta_modeling/polynomial_chaos_metamodel/plot_functional_chaos.html#sphx-glr-auto-meta-modeling-polynomial-chaos-metamodel-plot-functional-chaos-py
        
        How to provide input and output Sample?
        
        """
        
        ot.RandomGenerator.SetSeed(0)
        dimension = 2
        input_names = ["x1", "x2"]
        formulas = ["cos(x1 + x2)", "(x2 + 1) * exp(x1)"]
        model = ot.SymbolicFunction(input_names, formulas)
        
        distribution = ot.Normal(dimension)
        samplesize = 80
        inputSample = distribution.getSample(samplesize)
        outputSample = model(inputSample)
        
        ot.ResourceMap.SetAsUnsignedInteger("FittingTest-LillieforsMaximumSamplingSize", 100)  # ??
        
        algo = ot.FunctionalChaosAlgorithm(inputSample, outputSample)
        algo.run()
        result = algo.getResult()
        metamodel = result.getMetaModel()



        x1index = 0
        x1value = 0.5
        x2min = -3.0
        x2max = 3.0
        outputIndex = 1
        metamodelParametric = ot.ParametricFunction(metamodel, [x1index], [x1value])
        graph = metamodelParametric.getMarginal(outputIndex).draw(x2min, x2max)
        graph.setLegends(["Metamodel"])
        modelParametric = ot.ParametricFunction(model, [x1index], [x1value])
        curve = modelParametric.getMarginal(outputIndex).draw(x2min, x2max).getDrawable(0)
        curve.setColor("red")
        curve.setLegend("Model")
        graph.add(curve)
        graph.setLegendPosition("bottomright")
        graph.setXTitle("X2")
        graph.setTitle("Metamodel Validation, output #%d" % (outputIndex))
        view = viewer.View(graph)
        
        n_valid = 100
        inputTest = distribution.getSample(n_valid)
        outputTest = model(inputTest)
        
        # Plot the corresponding validation graphics.
        val = ot.MetaModelValidation(inputTest, outputTest, metamodel)
        Q2 = val.computePredictivityFactor()
        graph = val.drawValidation()
        graph.setTitle("Metamodel validation Q2=" + str(Q2))
        view = viewer.View(graph)


        
        
        #---Compute and print Sobol’ indices---
        chaosSI = ot.FunctionalChaosSobolIndices(result)
        print(chaosSI.summary())
        
        
        #---Testing the sensitivity to the degree---
        ot.ResourceMap.GetAsUnsignedInteger("FunctionalChaosAlgorithm-MaximumTotalDegree")
        
        degrees = range(5, 12)
        q2 = ot.Sample(len(degrees), 2)
        for maximumDegree in degrees:
            ot.ResourceMap.SetAsUnsignedInteger(
                "FunctionalChaosAlgorithm-MaximumTotalDegree", maximumDegree
            )
            print("Maximum total degree =", maximumDegree)
            algo = ot.FunctionalChaosAlgorithm(inputSample, outputSample)
            algo.run()
            result = algo.getResult()
            metamodel = result.getMetaModel()
            for outputIndex in range(2):
                val = ot.MetaModelValidation(
                    inputTest, outputTest[:, outputIndex], metamodel.getMarginal(outputIndex)
                )
                q2[maximumDegree - degrees[0], outputIndex] = val.computePredictivityFactor()[0]
        
        graph = ot.Graph("Predictivity", "Total degree", "Q2", True)
        cloud = ot.Cloud([[d] for d in degrees], q2[:, 0])
        cloud.setLegend("Output #0")
        cloud.setPointStyle("bullet")
        graph.add(cloud)
        cloud = ot.Cloud([[d] for d in degrees], q2[:, 1])
        cloud.setLegend("Output #1")
        cloud.setColor("red")
        cloud.setPointStyle("bullet")
        graph.add(cloud)
        graph.setLegendPosition("topright")
        view = viewer.View(graph)
        plt.show()
        
        ot.ResourceMap.Reload() #Reset default settings

