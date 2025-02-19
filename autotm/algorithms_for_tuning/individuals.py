import os
import pickle
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from autotm.abstract_params import AbstractParams
from autotm.schemas import IndividualDTO
from autotm.utils import AVG_COHERENCE_SCORE, LLM_SCORE

SPARSITY_PHI = "sparsity_phi"
SPARSITY_THETA = "sparsity_theta"
SWITCHP_SCORE = "switchP"
DF_NAMES = {"20ng": 0, "lentaru": 1, "amazon_food": 2}

METRICS_COLS = [
    "avg_coherence_score",
    "perplexityScore",
    "backgroundTokensRatioScore",
    "avg_switchp",
    "coherence_10",
    "coherence_15",
    "coherence_20",
    "coherence_25",
    "coherence_30",
    "coherence_35",
    "coherence_40",
    "coherence_45",
    "coherence_50",
    "coherence_55",
    "contrast",
    "purity",
    "kernelSize",
    "sparsity_phi",
    "sparsity_theta",
    "topic_significance_uni",
    "topic_significance_vacuous",
    "topic_significance_back",
    "npmi_15",
    "npmi_25",
    "npmi_50",
]

PATH_TO_LEARNED_SCORING = "./scoring_func"


class Individual(ABC):
    id: str

    @property
    @abstractmethod
    def dto(self) -> IndividualDTO:
        ...

    @property
    @abstractmethod
    def fitness_value(self) -> float:
        ...

    @property
    @abstractmethod
    def params(self) -> AbstractParams:
        ...


class BaseIndividual(Individual, ABC):
    def __init__(self, dto: IndividualDTO):
        self._dto = dto

    @property
    def dto(self) -> IndividualDTO:
        return self._dto

    @property
    def params(self) -> AbstractParams:
        return self.dto.params


class RegularFitnessIndividual(BaseIndividual):
    @property
    def fitness_value(self) -> float:
        return self.dto.fitness_value[AVG_COHERENCE_SCORE]


class LearnedModel:
    def __init__(self, save_path, dataset_name):
        dataset_id = DF_NAMES[dataset_name]
        general_save_path = os.path.join(save_path, "general")
        native_save_path = os.path.join(save_path, "native")
        with open(
            os.path.join(general_save_path, f"general_automl_{dataset_id}.pickle"), "rb"
        ) as f:
            self.general_model = pickle.load(f)
        self.native_model = []
        for i in range(5):
            with open(
                os.path.join(
                    native_save_path, f"native_automl_{dataset_id}_fold_{i}.pickle"
                ),
                "rb",
            ) as f:
                self.native_model.append(pickle.load(f))

    def general_predict(self, df: pd.DataFrame):
        y = self.general_model.predict(df[METRICS_COLS])
        return y

    def native_predict(self, df: pd.DataFrame):
        y = []
        for k, nm in enumerate(self.native_model):
            y.append(nm.predict(df[METRICS_COLS]))
        y = np.array(y)
        return np.mean(y, axis=0)


class LearnedScorerFitnessIndividual(BaseIndividual):
    @property
    def fitness_value(self) -> float:
        # dataset_name = self.dto.dataset  # TODO: check namings
        # m = LearnedModel(save_path=PATH_TO_LEARNED_SCORING, dataset_name=dataset_name)
        # TODO: predict from metrics df
        raise NotImplementedError()


class SparsityScalerBasedFitnessIndividual(BaseIndividual):
    @property
    def fitness_value(self) -> float:
        # it is a handling of the situation when a fitness-worker wasn't able to correctly calculate this indvidual
        # due to some error in the proceess
        # and thus the fitness value doesn't have any metrics except dummy AVG_COHERENCE_SCORE equal to zero
        if self.dto.fitness_value[AVG_COHERENCE_SCORE] < 0.00000001:
            return 0.0

        alpha = 0.7
        if 0.2 <= self.dto.fitness_value[SPARSITY_THETA] <= 0.8:
            alpha = 1
        # if SWITCHP_SCORE in self.dto.fitness_value:
        #     return alpha * (self.dto.fitness_value[AVG_COHERENCE_SCORE] + self.dto.fitness_value[SWITCHP_SCORE])
        # else:
        #     return alpha * self.dto.fitness_value[AVG_COHERENCE_SCORE]
        return alpha * self.dto.fitness_value[AVG_COHERENCE_SCORE]


class LLMBasedFitnessIndividual(BaseIndividual):
    @property
    def fitness_value(self) -> float:
        return self.dto.fitness_value.get(LLM_SCORE, 0.0)


class IndividualBuilder:
    SUPPORTED_IND_TYPES = ["regular", "sparse", "llm"]

    def __init__(self, ind_type: str = "regular"):
        self._ind_type = ind_type

        if self._ind_type not in self.SUPPORTED_IND_TYPES:
            raise ValueError(f"Unsupported ind type: {self._ind_type}")

    @property
    def individual_type(self) -> str:
        return self._ind_type

    def make_individual(self, dto: IndividualDTO) -> Individual:
        if self._ind_type == "regular":
            return RegularFitnessIndividual(dto=dto)
        elif self._ind_type == "sparse":
            return SparsityScalerBasedFitnessIndividual(dto=dto)
        else:
            return LLMBasedFitnessIndividual(dto=dto)
