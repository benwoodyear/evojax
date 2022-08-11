# Copyright 2022 The EvoJAX Authors.
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

import logging
from typing import Tuple

import jax
import jax.numpy as jnp
from jax import random

from flax import linen as nn
from flax.training import train_state

import optax

from evojax.policy.base import PolicyNetwork
from evojax.policy.base import PolicyState
from evojax.task.base import TaskState
from evojax.util import create_logger
from evojax.util import get_params_format_fn


class Mask(nn.Module):
    """Mask network for MNIST."""
    def __init__(self, base_model):
        super(Mask, self).__init__()

        in_features = base_model.linear.in_features
        out_features = base_model.linear.out_features
        self.mask_size = in_features * out_features

    @nn.compact
    def __call__(self, x, round_output=True):
        x = nn.Dense(features=10)(x)
        x = nn.relu(x)
        x = nn.Dense(features=100)(x)
        x = nn.relu(x)
        x = nn.Dense(features=self.mask_size)(x)
        x = nn.sigmoid(x)
        if round_output:
            x = jnp.round(x)
        return x


class MaskPolicy(PolicyNetwork):
    """A dense neural network for masking the MNIST classification task."""

    def __init__(self, logger: logging.Logger = None, mnist_model=None):
        if logger is None:
            self._logger = create_logger('ConvNetPolicy')
        else:
            self._logger = logger

        model = Mask(mnist_model)
        params = model.init(random.PRNGKey(0), jnp.zeros([1, 1]))
        self.num_params, format_params_fn = get_params_format_fn(params)
        self._logger.info(f'Mask.num_params = {self.num_params}')
        self._format_params_fn = jax.vmap(format_params_fn)
        self._forward_fn = jax.vmap(model.apply)

    def get_actions(self,
                    t_states: TaskState,
                    params: jnp.ndarray,
                    p_states: PolicyState) -> Tuple[jnp.ndarray, PolicyState]:
        params = self._format_params_fn(params)
        return self._forward_fn(params, t_states.obs), p_states