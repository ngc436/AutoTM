#!/usr/bin/env python3
import logging
import logging.config
import sys
import uuid
from typing import Union, Optional

from autotm.algorithms_for_tuning.genetic_algorithm.statistics_collector import StatisticsCollector
from autotm.algorithms_for_tuning.genetic_algorithm.ga import GA
from autotm.algorithms_for_tuning.genetic_algorithm.surrogate import Surrogate
from autotm.algorithms_for_tuning.individuals import IndividualBuilder
from autotm.fitness.estimator import ComputableFitnessEstimator, SurrogateEnabledComputableFitnessEstimator, \
    DistributedSurrogateEnabledComputableFitnessEstimator
from autotm.fitness.tm import fit_tm, TopicModel
from autotm.utils import make_log_config_dict

logger = logging.getLogger(__name__)

NUM_FITNESS_EVALUATIONS = 150
SPEEDUP = True


def get_best_individual(
        dataset: str,
        data_path: str,
        exp_id: Union[int, str],
        topic_count: int,
        num_individuals: int = 11,
        num_iterations: int = 400,
        num_fitness_evaluations: int = None,
        mutation_type: str = "psm",
        crossover_type: str = "blend_crossover",
        selection_type: str = "fitness_prop",
        elem_cross_prob: float = None,
        cross_alpha: float = 0.5046,
        best_proc: float = 0.4439,
        log_file: str = "/var/log/tm-alg.log",
        tag: str = "v0",
        surrogate_name: str = None,  # fix
        gpr_kernel: str = None,
        gpr_alpha: float = None,
        gpr_normalize_y: float = None,
        use_pipeline: bool = False,
        use_nelder_mead_in_mutation: bool = False,
        use_nelder_mead_in_crossover: bool = False,
        use_nelder_mead_in_selector: bool = False,
        train_option: str = "offline",
        quiet_log: bool = False,
        statistics_collector: Optional[StatisticsCollector] = None,
        individual_type: str = "regular",
        fitness_estimator_type: str = "local", # distributed
        **kwargs
):
    """

    :param dataset: Dataset name that is being processed. The name will be used to store results
    :param data_path: Path to all the artifacts obtained after
    :param exp_id: Mlflow experiment id
    :param topic_count: desired count of SPECIFIC topics (in optimization process BACK topics are also produced, thus the total amount of topics can be more than topic_count)
    :param num_individuals: Number of individuals in generation
    :param num_iterations: Number of iterations to make
    :param num_fitness_evaluations: Max number of possible fitness estimations. This setting may lead to premature algorithm stopping even if there is more generations to go
    :param mutation_type: Mutation type can have value from (mutation_one_param, combined, psm, positioning_mutation)
    :param crossover_type: Crossover type can have value from (crossover_pmx, crossover_one_point, blend_crossover)
    :param selection_type: Selection type can have value from (fitness_prop, rank_based)
    :param elem_cross_prob: Сrossover probability for each of the elements
    :param cross_alpha: Alpha parameter for blend crossover
    :param best_proc: Number of best parents to propagate
    :param log_file: A log file to write logs of the algorithm execution to
    :param tag: Service tag for massive experiments to store the models with tags
    :param surrogate_name: Name of the surrogate model
    :param gpr_kernel: Kernel name for gpr surrogate
    :param gpr_alpha: Alpha parameter for gpr
    :param gpr_normalize_y: y normalization parameter for gpr
    :param use_nelder_mead_in_mutation:
    :param use_nelder_mead_in_crossover:
    :param use_nelder_mead_in_selector:
    :return:
    """

    assert (
            sum(
                [
                    use_nelder_mead_in_mutation,
                    use_nelder_mead_in_crossover,
                    use_nelder_mead_in_selector,
                ]
            )
            <= 1
    )

    logger.debug(f"Command line: {sys.argv}")

    run_uid = str(uuid.uuid4())
    tag = tag if tag is not None else str(run_uid)
    logging_config = make_log_config_dict(filename=log_file, uid=run_uid, quiet=quiet_log)
    logging.config.dictConfig(logging_config)

    logger.info(f"Starting a new run of algorithm. Args: {sys.argv[1:]}")

    if elem_cross_prob is not None:
        elem_cross_prob = float(elem_cross_prob)

    if cross_alpha is not None:
        cross_alpha = float(cross_alpha)

    ibuilder = IndividualBuilder(individual_type)

    if fitness_estimator_type == "local" and surrogate_name:
        fitness_estimator = SurrogateEnabledComputableFitnessEstimator(
            ibuilder,
            Surrogate(surrogate_name),
            "type1",
            SPEEDUP,
            num_fitness_evaluations,
            statistics_collector
        )
    elif fitness_estimator_type == "local":
        fitness_estimator = ComputableFitnessEstimator(ibuilder, num_fitness_evaluations, statistics_collector)
    elif fitness_estimator_type == "distributed" and surrogate_name:
        fitness_estimator = DistributedSurrogateEnabledComputableFitnessEstimator(
            ibuilder,
            Surrogate(surrogate_name),
            "type1",
            SPEEDUP,
            num_fitness_evaluations,
            statistics_collector
        )
    elif fitness_estimator_type == "distributed":
        fitness_estimator = ComputableFitnessEstimator(ibuilder, num_fitness_evaluations, statistics_collector)
    else:
        raise ValueError("Incorrect settings")

    g = GA(
        dataset=dataset,
        data_path=data_path,
        num_individuals=num_individuals,
        num_iterations=num_iterations,
        ibuilder=ibuilder,
        fitness_estimator=fitness_estimator,
        mutation_type=mutation_type,
        crossover_type=crossover_type,
        selection_type=selection_type,
        elem_cross_prob=elem_cross_prob,
        num_fitness_evaluations=num_fitness_evaluations,
        best_proc=best_proc,
        alpha=cross_alpha,
        exp_id=exp_id,
        topic_count=topic_count,
        tag=tag,
        surrogate_name=surrogate_name,
        gpr_kernel=gpr_kernel,
        gpr_alpha=gpr_alpha,
        normalize_y=gpr_normalize_y,
        use_pipeline=use_pipeline,
        use_nelder_mead_in_mutation=use_nelder_mead_in_mutation,
        use_nelder_mead_in_crossover=use_nelder_mead_in_crossover,
        use_nelder_mead_in_selector=use_nelder_mead_in_selector,
        train_option=train_option,
        statistics_collector=statistics_collector,
        **kwargs
    )
    best_individual = g.run(verbose=True)
    logger.info(f"Best individual fitness_value: {best_individual.fitness_value * (-1)}")

    return best_individual


def run_algorithm(
        dataset: str,
        data_path: str,
        exp_id: Union[int, str],
        topic_count: int,
        num_individuals: int = 11,
        num_iterations: int = 50,
        num_fitness_evaluations: int = None,
        mutation_type: str = "psm",
        crossover_type: str = "blend_crossover",
        selection_type: str = "fitness_prop",
        elem_cross_prob: float = None,
        cross_alpha: float = 0.5046,
        best_proc: float = 0.4439,
        log_file: str = "/var/log/tm-alg.log",
        tag: str = "v0",
        surrogate_name: str = None,  # fix
        gpr_kernel: str = None,
        gpr_alpha: float = None,
        gpr_normalize_y: float = None,
        use_pipeline: bool = True,
        use_nelder_mead_in_mutation: bool = False,
        use_nelder_mead_in_crossover: bool = False,
        use_nelder_mead_in_selector: bool = False,
        train_option: str = "offline",
        quiet_log: bool = False,
        individual_type: str = "regular",
        fitness_estimator_type: str = "local"
) -> TopicModel:
    best_individual = get_best_individual(dataset, data_path, exp_id, topic_count, num_individuals, num_iterations,
                                          num_fitness_evaluations, mutation_type, crossover_type, selection_type,
                                          elem_cross_prob, cross_alpha, best_proc, log_file, tag, surrogate_name,
                                          gpr_kernel, gpr_alpha, gpr_normalize_y, use_pipeline,
                                          use_nelder_mead_in_mutation, use_nelder_mead_in_crossover,
                                          use_nelder_mead_in_selector, train_option, quiet_log,
                                          individual_type=individual_type,
                                          fitness_estimator_type=fitness_estimator_type)

    best_topic_model = fit_tm(
        preproc_data_path=data_path,
        topic_count=topic_count,
        params=best_individual.params,
        train_option=train_option
    )

    return best_topic_model
