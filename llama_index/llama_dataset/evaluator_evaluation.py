"""Labelled Evaluation Class."""

import asyncio
import time
from typing import List, Optional

from pandas import DataFrame as PandasDataFrame

from llama_index.bridge.pydantic import Field
from llama_index.evaluation import (
    BaseEvaluator,
    EvaluationResult,
    PairwiseComparisonEvaluator,
)
from llama_index.evaluation.pairwise import EvaluationSource
from llama_index.llama_dataset.base import (
    BaseLlamaDataExample,
    BaseLlamaDataset,
    BaseLlamaExamplePrediction,
    BaseLlamaPredictionDataset,
    CreatedBy,
)


class EvaluatorExamplePrediction(BaseLlamaExamplePrediction):
    """Evaluation example prediction class.

    Args:
        feedback (Optional[str]): The evaluator's feedback.
        score (Optional[float]): The evaluator's score.
    """

    feedback: str = Field(
        default_factory=str,
        description="The generated (predicted) response that can be compared to a reference (ground-truth) answer.",
    )
    score: Optional[float] = Field(
        default=None,
        description="The generated (predicted) response that can be compared to a reference (ground-truth) answer.",
    )
    invalid_prediction: bool = Field(
        default=False, description="Whether or not the prediction is a valid one."
    )
    invalid_reason: Optional[str] = Field(
        default=None, description="Reason as to why prediction is invalid."
    )

    @property
    def class_name(self) -> str:
        """Data example class name."""
        return "EvaluatorExamplePrediction"


class LabelledEvaluatorDataExample(BaseLlamaDataExample):
    """Evaluation example class.

    This data class contains the ingredients to perform a new "prediction" i.e.,
    evaluation. Here an evaluator is meant to evaluate a response against an
    associated query as well as optionally contexts.

    Args:
        query (str): The user query
        query_by (CreatedBy): Query generated by human or ai (model-name)
        contexts (Optional[List[str]]): The contexts used for response
        answer (str): Answer to the query that is to be evaluated.
        answer_by: The reference answer generated by human or ai (model-name).
        ground_truth_answer (Optional[str]):
        ground_truth_answer_by (Optional[CreatedBy]):
        reference_feedback (str): The reference feedback evaluation.
        reference_score (float): The reference score evaluation.
        reference_evaluation_by (CreatedBy): Evaluation generated by human or ai (model-name)
    """

    query: str = Field(
        default_factory=str, description="The user query for the example."
    )
    query_by: Optional[CreatedBy] = Field(
        default=None, description="What generated the query."
    )
    contexts: Optional[List[str]] = Field(
        default_factory=None,
        description="The contexts used to generate the answer.",
    )
    answer: str = Field(
        default_factory=str,
        description="The provided answer to the example that is to be evaluated.",
    )
    answer_by: Optional[CreatedBy] = Field(
        default=None, description="What generated the answer."
    )
    ground_truth_answer: Optional[str] = Field(
        default=None,
        description="The ground truth answer to the example that is used to evaluate the provided `answer`.",
    )
    ground_truth_answer_by: Optional[CreatedBy] = Field(
        default=None, description="What generated the ground-truth answer."
    )
    reference_feedback: Optional[str] = Field(
        default=None,
        description="The reference feedback (ground-truth).",
    )
    reference_score: float = Field(
        default_factory=float, description="The reference score (ground-truth)."
    )
    reference_evaluation_by: Optional[CreatedBy] = Field(
        default=None, description="What generated the evaluation (feedback and score)."
    )

    @property
    def class_name(self) -> str:
        """Data example class name."""
        return "LabelledEvaluatorDataExample"


class EvaluatorPredictionDataset(BaseLlamaPredictionDataset):
    """Evaluation Prediction Dataset Class."""

    _prediction_type = EvaluatorExamplePrediction

    def to_pandas(self) -> PandasDataFrame:
        """Create pandas dataframe."""
        data = {}
        if self.predictions:
            data = {
                "feedback": [t.feedback for t in self.predictions],
                "score": [t.score for t in self.predictions],
            }

        return PandasDataFrame(data)

    @property
    def class_name(self) -> str:
        """Class name."""
        return "EvaluatorPredictionDataset"


class LabelledEvaluatorDataset(BaseLlamaDataset):
    """LabelledEvalationDataset class."""

    _example_type = LabelledEvaluatorDataExample

    def to_pandas(self) -> PandasDataFrame:
        """Create pandas dataframe."""
        data = {
            "query": [t.query for t in self.examples],
            "answer": [t.answer for t in self.examples],
            "contexts": [t.contexts for t in self.examples],
            "ground_truth_answer": [t.ground_truth_answer for t in self.examples],
            "query_by": [str(t.query_by) for t in self.examples],
            "answer_by": [str(t.answer_by) for t in self.examples],
            "ground_truth_answer_by": [
                str(t.ground_truth_answer_by) for t in self.examples
            ],
            "reference_feedback": [t.reference_feedback for t in self.examples],
            "reference_score": [t.reference_score for t in self.examples],
            "reference_evaluation_by": [
                t.reference_evaluation_by for t in self.examples
            ],
        }

        return PandasDataFrame(data)

    async def _apredict_example(
        self,
        evaluator: BaseEvaluator,
        example: LabelledEvaluatorDataExample,
        sleep_time_in_seconds: int,
    ) -> EvaluatorExamplePrediction:
        """Async predict RAG example with a query engine."""
        await asyncio.sleep(sleep_time_in_seconds)
        eval_kwargs = {
            "query": example.query,
            "response": example.answer,
            "contexts": example.contexts,
            "reference": example.ground_truth_answer,
            "sleep_time_in_seconds": sleep_time_in_seconds,
        }
        eval_result: EvaluationResult = await evaluator.aevaluate(**eval_kwargs)
        return EvaluatorExamplePrediction(
            feedback=eval_result.feedback, score=eval_result.score
        )

    def _predict_example(
        self,
        evaluator: BaseEvaluator,
        example: LabelledEvaluatorDataExample,
        sleep_time_in_seconds: int = 0,
    ) -> EvaluatorExamplePrediction:
        """Predict RAG example with a query engine."""
        time.sleep(sleep_time_in_seconds)
        eval_kwargs = {
            "query": example.query,
            "response": example.answer,
            "contexts": example.contexts,
            "reference": example.ground_truth_answer,
            "sleep_time_in_seconds": sleep_time_in_seconds,
        }
        eval_result: EvaluationResult = evaluator.evaluate(**eval_kwargs)
        return EvaluatorExamplePrediction(
            feedback=eval_result.feedback, score=eval_result.score
        )

    def _construct_prediction_dataset(
        self, predictions: List[EvaluatorExamplePrediction]
    ) -> EvaluatorPredictionDataset:
        """Construct prediction dataset."""
        return EvaluatorPredictionDataset(predictions=predictions)

    def class_name(self) -> str:
        """Class name."""
        return "LabelledEvaluatorDataset"


class PairwiseEvaluatorExamplePrediction(BaseLlamaExamplePrediction):
    """Pairwise evaluation example prediction class.

    Args:
        feedback (Optional[str]): The evaluator's feedback.
        score (Optional[float]): The evaluator's score.
        evaluation_source (EvaluationSource): If the evaluation came from original order or flipped; or inconclusive.
    """

    feedback: str = Field(
        default_factory=str,
        description="The generated (predicted) response that can be compared to a reference (ground-truth) answer.",
    )
    score: Optional[float] = Field(
        default=None,
        description="The generated (predicted) response that can be compared to a reference (ground-truth) answer.",
    )
    evaluation_source: Optional[EvaluationSource] = Field(
        default=None,
        description=(
            "Whether the evaluation comes from original, or flipped ordering. Can also be neither here indicating inconclusive judgement."
        ),
    )
    invalid_prediction: bool = Field(
        default=False, description="Whether or not the prediction is a valid one."
    )
    invalid_reason: Optional[str] = Field(
        default=None, description="Reason as to why prediction is invalid."
    )

    @property
    def class_name(self) -> str:
        """Data example class name."""
        return "PairwiseEvaluatorExamplePrediction"


class PairwiseEvaluatorPredictionDataset(BaseLlamaPredictionDataset):
    """Pairwise evaluation predictions dataset class."""

    _prediction_type = PairwiseEvaluatorExamplePrediction

    def to_pandas(self) -> PandasDataFrame:
        """Create pandas dataframe."""
        data = {}
        if self.predictions:
            data = {
                "feedback": [t.feedback for t in self.predictions],
                "score": [t.score for t in self.predictions],
                "ordering": [t.evaluation_source.value for t in self.predictions],
            }

        return PandasDataFrame(data)

    def class_name(self) -> str:
        """Class name."""
        return "PairwiseEvaluatorPredictionDataset"


class LabelledPairwiseEvaluatorDataExample(LabelledEvaluatorDataExample):
    """Labelled pairwise evaluation data example class."""

    second_answer: str = Field(
        default_factory=str,
        description="The second answer to the example that is to be evaluated along versus `answer`.",
    )
    second_answer_by: Optional[CreatedBy] = Field(
        default=None, description="What generated the second answer."
    )

    @property
    def class_name(self) -> str:
        """Data example class name."""
        return "LabelledPairwiseEvaluatorDataExample"


class LabelledPairwiseEvaluatorDataset(BaseLlamaDataset):
    """Labelled pairwise evaluation dataset. For evaluating the evaluator in
    performing pairwise evaluations.

    Args:
        BaseLlamaDataset (_type_): _description_
    """

    _example_type = LabelledPairwiseEvaluatorDataExample

    def to_pandas(self) -> PandasDataFrame:
        """Create pandas dataframe."""
        data = {
            "query": [t.query for t in self.examples],
            "answer": [t.answer for t in self.examples],
            "second_answer": [t.second_answer for t in self.examples],
            "contexts": [t.contexts for t in self.examples],
            "ground_truth_answer": [t.ground_truth_answer for t in self.examples],
            "query_by": [str(t.query_by) for t in self.examples],
            "answer_by": [str(t.answer_by) for t in self.examples],
            "second_answer_by": [str(t.second_answer_by) for t in self.examples],
            "ground_truth_answer_by": [
                str(t.ground_truth_answer_by) for t in self.examples
            ],
            "reference_feedback": [t.reference_feedback for t in self.examples],
            "reference_score": [t.reference_score for t in self.examples],
            "reference_evaluation_by": [
                t.reference_evaluation_by for t in self.examples
            ],
        }

        return PandasDataFrame(data)

    async def _apredict_example(
        self,
        evaluator: PairwiseComparisonEvaluator,
        example: LabelledPairwiseEvaluatorDataExample,
        sleep_time_in_seconds: int,
    ) -> PairwiseEvaluatorExamplePrediction:
        """Async predict evaluation example with an Evaluator."""
        await asyncio.sleep(sleep_time_in_seconds)
        try:
            eval_result: EvaluationResult = await evaluator.aevaluate(
                query=example.query,
                response=example.answer,
                second_response=example.second_answer,
                contexts=example.contexts,
                reference=example.ground_truth_answer,
                sleep_time_in_seconds=sleep_time_in_seconds,
            )
        except Exception as err:
            # TODO: raise warning here as well
            return PairwiseEvaluatorExamplePrediction(
                invalid_prediction=True, invalid_reason=f"Caught error {err!s}"
            )

        if not eval_result.invalid_result:
            return PairwiseEvaluatorExamplePrediction(
                feedback=eval_result.feedback,
                score=eval_result.score,
                evaluation_source=eval_result.pairwise_source,
            )
        else:
            return PairwiseEvaluatorExamplePrediction(
                invalid_prediction=True, invalid_reason=eval_result.invalid_reason
            )

    def _predict_example(
        self,
        evaluator: PairwiseComparisonEvaluator,
        example: LabelledPairwiseEvaluatorDataExample,
        sleep_time_in_seconds: int = 0,
    ) -> PairwiseEvaluatorExamplePrediction:
        """Predict RAG example with a query engine."""
        time.sleep(sleep_time_in_seconds)
        eval_kwargs = {
            "query": example.query,
            "response": example.answer,
            "second_response": example.second_answer,
            "contexts": example.contexts,
            "reference": example.ground_truth_answer,
            "sleep_time_in_seconds": sleep_time_in_seconds,
        }
        eval_result: EvaluationResult = evaluator.evaluate(**eval_kwargs)
        return PairwiseEvaluatorExamplePrediction(
            feedback=eval_result.feedback,
            score=eval_result.score,
            evaluation_source=eval_result.pairwise_source,
        )

    def _construct_prediction_dataset(
        self, predictions: List[PairwiseEvaluatorExamplePrediction]
    ) -> PairwiseEvaluatorPredictionDataset:
        """Construct prediction dataset."""
        return PairwiseEvaluatorPredictionDataset(predictions=predictions)

    def class_name(self) -> str:
        """Class name."""
        return "LabelledPairwiseEvaluatorDataset"


# British English + American English
LabeledEvaluatorDataExample = LabelledEvaluatorDataExample
LabeledEvaluatorDataset = LabelledEvaluatorDataset
LabeledPairwiseEvaluatorDataExample = LabelledPairwiseEvaluatorDataExample
LabeledPairwiseEvaluatorDataset = LabelledPairwiseEvaluatorDataset
