# Copyright The Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from collections.abc import Sequence
from typing import Any, Optional, Union
from tqdm import tqdm

import torch
from torch import Tensor, tensor

# from torchmetrics.functional.text.cer import _cer_compute, _cer_update
from torchmetrics.metric import Metric
from torchmetrics.utilities.imports import _MATPLOTLIB_AVAILABLE
from torchmetrics.utilities.plot import _AX_TYPE, _PLOT_OUT_TYPE

from torchmetrics.functional.text.helper import _edit_distance

if not _MATPLOTLIB_AVAILABLE:
    __doctest_skip__ = ["CharErrorRate.plot"]


def _cer_update(
    preds: Union[str, list[str]],
    target: Union[str, list[str]],
    clip_at_one: bool = True,
) -> tuple[Tensor, Tensor]:
    """Update the cer score with the current set of references and predictions.

    Args:
        preds: Transcription(s) to score as a string or list of strings
        target: Reference(s) for each speech input as a string or list of strings
        clip_at_one: If True, for each sentence clip per-sentence CER at 1.0 by
            doing: errors_i = min(edit_distance, len(target_tokens)).
    Returns:
        Number of edit operations to get from the reference to the prediction, summed over all samples
        Number of character overall references

    """
    if isinstance(preds, str):
        preds = [preds]
    if isinstance(target, str):
        target = [target]
    errors = tensor(0, dtype=torch.float)
    total = tensor(0, dtype=torch.float)
    for pred, tgt in zip(preds, target):
        pred_tokens = pred
        tgt_tokens = tgt
        ed = _edit_distance(list(pred_tokens), list(tgt_tokens))
        tgt_len = len(tgt_tokens)
        if clip_at_one and tgt_len > 0:
            # clip per-utterance CER at 1.0 => ed_i <= len(target_i)
            ed = min(ed, tgt_len)
        errors += ed
        total += tgt_len
    return errors, total


def _cer_update_min_two_refs(
    preds: Union[str, list[str]],
    target1: Union[str, list[str]],
    target2: Union[str, list[str]],
    clip_at_one: bool = True,
) -> tuple[Tensor, Tensor]:
    """Update CER using two references per prediction and take the smaller per-sentence CER."""
    if isinstance(preds, str):
        preds = [preds]
    if isinstance(target1, str):
        target1 = [target1]
    if isinstance(target2, str):
        target2 = [target2]

    errors = tensor(0, dtype=torch.float)
    total = tensor(0, dtype=torch.float)

    for pred, tgt1, tgt2 in tqdm(zip(preds, target1, target2)):
        pred_tokens = pred
        tgt1_tokens = tgt1
        tgt2_tokens = tgt2
        ed1 = _edit_distance(list(pred_tokens), list(tgt1_tokens))
        ed2 = _edit_distance(list(pred_tokens), list(tgt2_tokens))
        len1 = len(tgt1_tokens)
        len2 = len(tgt2_tokens)
        if clip_at_one:
            if len1 > 0:
                ed1 = min(ed1, len1)
            if len2 > 0:
                ed2 = min(ed2, len2)
        cer1 = float(ed1) / len1 if len1 > 0 else float("inf")
        cer2 = float(ed2) / len2 if len2 > 0 else float("inf")
        if cer1 < cer2:
            errors += ed1
            total += len1
        elif cer2 < cer1:
            errors += ed2
            total += len2
        else:
            errors += 0.5 * (ed1 + ed2)
            total += 0.5 * (len1 + len2)
    return errors, total


def _cer_compute(errors: Tensor, total: Tensor) -> Tensor:
    """Compute the Character error rate.

    Args:
        errors: Number of edit operations to get from the reference to the prediction, summed over all samples
        total: Number of characters over all references

    Returns:
        Character error rate score

    """
    return errors / total


class CharErrorRate(Metric):
    r"""Character Error Rate (`CER`_) is a metric of the performance of an automatic speech recognition (ASR) system.

    This value indicates the percentage of characters that were incorrectly predicted.
    The lower the value, the better the performance of the ASR system with a CharErrorRate of 0 being
    a perfect score.
    Character error rate can then be computed as:

    .. math::
        CharErrorRate = \frac{S + D + I}{N} = \frac{S + D + I}{S + D + C}

    where:
        - :math:`S` is the number of substitutions,
        - :math:`D` is the number of deletions,
        - :math:`I` is the number of insertions,
        - :math:`C` is the number of correct characters,
        - :math:`N` is the number of characters in the reference (N=S+D+C).

    Compute CharErrorRate score of transcribed segments against references.

    As input to ``forward`` and ``update`` the metric accepts the following input:

    - ``preds`` (:class:`~str`): Transcription(s) to score as a string or list of strings
    - ``target`` (:class:`~str`): Reference(s) for each speech input as a string or list of strings

    As output of ``forward`` and ``compute`` the metric returns the following output:

    -  ``cer`` (:class:`~torch.Tensor`): A tensor with the Character Error Rate score

    Args:
        kwargs: Additional keyword arguments, see :ref:`Metric kwargs` for more info.

    Examples:
        >>> from torchmetrics.text import CharErrorRate
        >>> preds = ["this is the prediction", "there is an other sample"]
        >>> target = ["this is the reference", "there is another one"]
        >>> cer = CharErrorRate()
        >>> cer(preds, target)
        tensor(0.3415)

    """

    is_differentiable: bool = False
    higher_is_better: bool = False
    full_state_update: bool = False
    plot_lower_bound: float = 0.0
    plot_upper_bound: float = 1.0

    errors: Tensor
    total: Tensor

    def __init__(
        self,
        clip_at_one: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.add_state("errors", tensor(0, dtype=torch.float), dist_reduce_fx="sum")
        self.add_state("total", tensor(0, dtype=torch.float), dist_reduce_fx="sum")
        self.clip_at_one = clip_at_one

    def update(
        self, preds: Union[str, list[str]], target: Union[str, list[str]]
    ) -> None:
        """Update state with predictions and targets."""
        errors, total = _cer_update(preds, target, clip_at_one=self.clip_at_one)
        self.errors += errors
        self.total += total

    def compute(self) -> Tensor:
        """Calculate the character error rate."""
        return _cer_compute(self.errors, self.total)

    def plot(
        self,
        val: Optional[Union[Tensor, Sequence[Tensor]]] = None,
        ax: Optional[_AX_TYPE] = None,
    ) -> _PLOT_OUT_TYPE:
        """Plot a single or multiple values from the metric.

        Args:
            val: Either a single result from calling `metric.forward` or `metric.compute` or a list of these results.
                If no value is provided, will automatically call `metric.compute` and plot that result.
            ax: An matplotlib axis object. If provided will add plot to that axis

        Returns:
            Figure and Axes object

        Raises:
            ModuleNotFoundError:
                If `matplotlib` is not installed

        .. plot::
            :scale: 75

            >>> # Example plotting a single value
            >>> from torchmetrics.text import CharErrorRate
            >>> metric = CharErrorRate()
            >>> preds = ["this is the prediction", "there is an other sample"]
            >>> target = ["this is the reference", "there is another one"]
            >>> metric.update(preds, target)
            >>> fig_, ax_ = metric.plot()

        .. plot::
            :scale: 75

            >>> # Example plotting multiple values
            >>> from torchmetrics.text import CharErrorRate
            >>> metric = CharErrorRate()
            >>> preds = ["this is the prediction", "there is an other sample"]
            >>> target = ["this is the reference", "there is another one"]
            >>> values = [ ]
            >>> for _ in range(10):
            ...     values.append(metric(preds, target))
            >>> fig_, ax_ = metric.plot(values)

        """
        return self._plot(val, ax)


class CharErrorRateMinTwoRefs(CharErrorRate):
    """Character error rate with two references per prediction.

    For each sample, given (target1, target2, pred), compute CER(pred, target1)
    and CER(pred, target2), then use the smaller one to accumulate global CER.
    """

    def __init__(
        self,
        clip_at_one: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(clip_at_one=clip_at_one, **kwargs)

    def update(
        self,
        preds: Union[str, list[str]],
        target1: Union[str, list[str]],
        target2: Union[str, list[str]],
    ) -> None:
        """Update state with predictions and two sets of references."""
        errors, total = _cer_update_min_two_refs(
            preds, target1, target2, clip_at_one=self.clip_at_one
        )
        self.errors += errors
        self.total += total
