import typing as tp
import unittest

from benchbuild.utils.actions import ProjectStep, StepResult

from tests.utils.test_experiment_util import BBTestProject
from varats.experiment.steps.combinators import IfThenElse


class ReturnResult(ProjectStep):
    """Step that always returns a specified StepResult."""

    NAME = "ReturnResult"
    DESCRIPTION = "Step that always returns the specified result."

    def __init__(self, result: StepResult) -> None:
        super().__init__(BBTestProject())
        self.result = result

    def __call__(self) -> StepResult:
        return self.result


class CallCounter(ProjectStep):
    """Step that counts how many times it has been called."""

    NAME = "CallCounter"
    DESCRIPTION = "Step that counts how many times it has been called."

    def __init__(self) -> None:
        super().__init__(BBTestProject())
        self.call_count = 0

    def __call__(self) -> StepResult:
        self.call_count += 1
        return StepResult.OK


class TestIfThenElse(unittest.TestCase):
    """Tests the IfThenElse combinator step."""

    def __condition_test_impl(
        self,
        condition: ProjectStep,
        then_step: ProjectStep,
        else_step: ProjectStep,
        valid_results: tp.Optional[tp.List[StepResult]] = None
    ) -> StepResult:

        if_then_else = IfThenElse(
            BBTestProject(),
            condition,
            then_step,
            else_step,
            valid_results=valid_results
        )

        result = if_then_else()

        return result

    def testConditionSuccess(self):
        """Tests that if the condition is successful, the then step is
        executed."""
        condition = ReturnResult(StepResult.OK)
        then_step = CallCounter()
        else_step = CallCounter()

        step_result = self.__condition_test_impl(
            condition, then_step, else_step
        )

        self.assertEqual(step_result, StepResult.OK)
        self.assertEqual(then_step.call_count, 1)
        self.assertEqual(else_step.call_count, 0)

    def testConditionCanContinue(self):
        """Tests that if the condition is CanContinue, the then step is
        executed."""
        condition = ReturnResult(StepResult.CAN_CONTINUE)
        then_step = CallCounter()
        else_step = CallCounter()

        result = self.__condition_test_impl(condition, then_step, else_step)

        self.assertEqual(result, StepResult.OK)
        self.assertEqual(then_step.call_count, 1)
        self.assertEqual(else_step.call_count, 0)

    def testConditionCustomResult(self):
        condition = ReturnResult(StepResult.UNSET)
        then_step = CallCounter()
        else_step = CallCounter()

        result = self.__condition_test_impl(
            condition, then_step, else_step, [StepResult.UNSET]
        )

        self.assertEqual(result, StepResult.OK)
        self.assertEqual(then_step.call_count, 1)
        self.assertEqual(else_step.call_count, 0)

    def testConditionFailure(self):
        """Tests that if the condition is ERROR, the else step is executed."""
        condition = ReturnResult(StepResult.ERROR)
        then_step = CallCounter()
        else_step = CallCounter()

        result = self.__condition_test_impl(condition, then_step, else_step)

        self.assertEqual(result, StepResult.OK)
        self.assertEqual(then_step.call_count, 0)
        self.assertEqual(else_step.call_count, 1)

    def testNoThenElse(self):
        """Tests that if no then or else step is provided, the condition result
        is returned."""
        condition = ReturnResult(StepResult.CAN_CONTINUE)
        then_step = None
        else_step = None

        result = self.__condition_test_impl(condition, then_step, else_step)

        self.assertEqual(result, StepResult.CAN_CONTINUE)
