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

# from torchmetrics.functional.text.wer import _wer_compute, _wer_update
from torchmetrics.metric import Metric
from torchmetrics.utilities.imports import _MATPLOTLIB_AVAILABLE
from torchmetrics.utilities.plot import _AX_TYPE, _PLOT_OUT_TYPE

from torchmetrics.functional.text.helper import _edit_distance

if not _MATPLOTLIB_AVAILABLE:
    __doctest_skip__ = ["WordErrorRate.plot"]

def _wer_update(
    preds: Union[str, list[str]],
    target: Union[str, list[str]],
    clip_at_one: bool = True,
) -> tuple[Tensor, Tensor]:
    """Update the wer score with the current set of references and predictions.

    Args:
        preds: Transcription(s) to score as a string or list of strings
        target: Reference(s) for each speech input as a string or list of strings
        clip_at_one: If True, for each sentence clip per-sentence WER at 1.0 by
            doing: errors_i = min(edit_distance, len(target_tokens)).

    Returns:
        Number of edit operations to get from the reference to the prediction, summed over all samples
        Number of words overall references
    """
    if isinstance(preds, str):
        preds = [preds]
    if isinstance(target, str):
        target = [target]
    errors = tensor(0, dtype=torch.float)
    total = tensor(0, dtype=torch.float)
    for pred, tgt in zip(preds, target):
        pred_tokens = pred.split()
        tgt_tokens = tgt.split()
        ed = _edit_distance(pred_tokens, tgt_tokens)
        tgt_len = len(tgt_tokens)
        if clip_at_one and tgt_len > 0:
            # clip per-utterance WER at 1.0 => ed_i <= len(target_i)
            ed = min(ed, tgt_len)
        errors += ed
        total += tgt_len
    return errors, total

def _wer_update_min_two_refs(
    preds: Union[str, list[str]],
    target1: Union[str, list[str]],
    target2: Union[str, list[str]],
    clip_at_one: bool = True,
) -> tuple[Tensor, Tensor]:
    """Update WER using two references per prediction and take the smaller per-sentence WER."""
    if isinstance(preds, str):
        preds = [preds]
    if isinstance(target1, str):
        target1 = [target1]
    if isinstance(target2, str):
        target2 = [target2]
    errors = tensor(0, dtype=torch.float)
    total = tensor(0, dtype=torch.float)
    for pred, tgt1, tgt2 in tqdm(zip(preds, target1, target2)):
        pred_tokens = pred.split()
        tgt1_tokens = tgt1.split()
        tgt2_tokens = tgt2.split()
        len1 = len(tgt1_tokens)
        len2 = len(tgt2_tokens)
        ed1 = _edit_distance(pred_tokens, tgt1_tokens)
        ed2 = _edit_distance(pred_tokens, tgt2_tokens)
        if clip_at_one:
            if len1 > 0:
                ed1 = min(ed1, len1)
            if len2 > 0:
                ed2 = min(ed2, len2)
        wer1 = float(ed1) / len1 if len1 > 0 else float("inf")
        wer2 = float(ed2) / len2 if len2 > 0 else float("inf")

        # 选 WER 更小的那对来累积
        if wer1 < wer2:
            errors += ed1
            total += len1
        elif wer2 < wer1:
            errors += ed2
            total += len2
        else:
            errors += 0.5 * (ed1 + ed2)
            total += 0.5 * (len1 + len2)
    return errors, total

def _wer_compute(errors: Tensor, total: Tensor) -> Tensor:
    """Compute the word error rate.

    Args:
        errors: Number of edit operations to get from the reference to the prediction, summed over all samples
        total: Number of words overall references

    Returns:
        Word error rate score

    """
    return errors / total

class WordErrorRate(Metric):
    r"""Word error rate (`WordErrorRate`_) is a common metric of the performance of an automatic speech recognition.

    This value indicates the percentage of words that were incorrectly predicted. The lower the value, the
    better the performance of the ASR system with a WER of 0 being a perfect score. Word error rate can then be
    computed as:

    .. math::
        WER = \frac{S + D + I}{N} = \frac{S + D + I}{S + D + C}

    where:
    - :math:`S` is the number of substitutions,
    - :math:`D` is the number of deletions,
    - :math:`I` is the number of insertions,
    - :math:`C` is the number of correct words,
    - :math:`N` is the number of words in the reference (:math:`N=S+D+C`).

    Compute WER score of transcribed segments against references.

    As input to ``forward`` and ``update`` the metric accepts the following input:

    - ``preds`` (:class:`~List`): Transcription(s) to score as a string or list of strings
    - ``target`` (:class:`~List`): Reference(s) for each speech input as a string or list of strings

    As output of ``forward`` and ``compute`` the metric returns the following output:

    -  ``wer`` (:class:`~torch.Tensor`): A tensor with the Word Error Rate score

    Args:
        kwargs: Additional keyword arguments, see :ref:`Metric kwargs` for more info.

    Examples:
        >>> from torchmetrics.text import WordErrorRate
        >>> preds = ["this is the prediction", "there is an other sample"]
        >>> target = ["this is the reference", "there is another one"]
        >>> wer = WordErrorRate()
        >>> wer(preds, target)
        tensor(0.5000)

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

    def update(self, preds: Union[str, list[str]], target: Union[str, list[str]]) -> None:
        """Update state with predictions and targets."""
        errors, total = _wer_update(preds, target, clip_at_one=self.clip_at_one)
        self.errors += errors
        self.total += total

    def compute(self) -> Tensor:
        """Calculate the word error rate."""
        return _wer_compute(self.errors, self.total)

    def plot(
        self, val: Optional[Union[Tensor, Sequence[Tensor]]] = None, ax: Optional[_AX_TYPE] = None
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
            >>> from torchmetrics.text import WordErrorRate
            >>> metric = WordErrorRate()
            >>> preds = ["this is the prediction", "there is an other sample"]
            >>> target = ["this is the reference", "there is another one"]
            >>> metric.update(preds, target)
            >>> fig_, ax_ = metric.plot()

        .. plot::
            :scale: 75

            >>> # Example plotting multiple values
            >>> from torchmetrics.text import WordErrorRate
            >>> metric = WordErrorRate()
            >>> preds = ["this is the prediction", "there is an other sample"]
            >>> target = ["this is the reference", "there is another one"]
            >>> values = [ ]
            >>> for _ in range(10):
            ...     values.append(metric(preds, target))
            >>> fig_, ax_ = metric.plot(values)

        """
        return self._plot(val, ax)

class WordErrorRateMinTwoRefs(WordErrorRate):
    """Word error rate with two references per prediction.

    For each sample, given (target1, target2, pred), compute WER(pred, target1)
    and WER(pred, target2), then use the smaller one to accumulate global WER.
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
        errors, total = _wer_update_min_two_refs(
            preds, target1, target2, clip_at_one=self.clip_at_one
        )
        self.errors += errors
        self.total += total